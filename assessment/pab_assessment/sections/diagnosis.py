"""Clinical Impression & ICD-11 Diagnosis section (core/06).

CAL-CP (ICD-11 Chronic Pain Classification Algorithm) walker — replaces the
old free-form mechanism/subtype/severity picker. See ../cal_cp_model.py for
the graph model and cal_cp/cal-cp-history.md for the algorithm's build history.

Phase 3 of the pabd integration: intro form (p6 chronic pain specifier),
two-generation lookahead tree, and notes/appendix/footnote text pushed into
the shared KB panel (Ctrl+K). Still single-workup — multi-workup tabs are
Phase 4.

Rendering model: the body is fully rebuilt (remove_children + mount_all) on
every state change rather than patching individual widgets in place, since
the lookahead tree's shape (number of boxes, container nesting) varies with
the current node's type. This mirrors the prototype's _render_active pattern
and an existing convention already used elsewhere in this codebase (see
tui.py's NavChips.set_context: remove_children() + mount(), both un-awaited,
processed in order via the widget message queue — no run_worker needed).
The one thing that does NOT settle synchronously is focus(), so refocusing
the node box after a rebuild goes through call_after_refresh().
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.message import Message
from textual.widgets import Button, Input, Label, RadioButton, RadioSet, Static

from .base import BaseSection
from ..cal_cp_model import (
    INTRO_FORM,
    TEMPORAL_PATTERN_OPTIONS,
    Workup,
    effective_view,
    is_answerable,
    render_hint,
    render_notes_panel,
)


class CalCpNodeBox(Static, can_focus=True):
    """Focusable display of the current CAL-CP node. Y/N/Enter/F/Backspace are
    scoped to this widget's focus (Textual's key_<key> convention — same
    pattern as widgets.CheckButton's key_y/key_n), never App-level bindings,
    so they don't collide with any other section's keys. Rebuilt fresh on
    every state change, so it takes its owning section directly rather than
    via a separate bind step."""

    DEFAULT_CSS = """
    CalCpNodeBox {
        height: auto; min-height: 3; width: 100%;
        background: $warning 35%; color: $text; text-style: bold;
        border: round $warning; padding: 0 1; margin-bottom: 1;
    }
    CalCpNodeBox:focus { border: round $accent; }
    """

    def __init__(self, text: str, section: "DiagnosisSection", **kwargs) -> None:
        super().__init__(text, **kwargs)
        self._section = section

    async def key_y(self) -> None:
        self._section.workup_answer("yes")

    async def key_n(self) -> None:
        self._section.workup_answer("no")

    async def key_enter(self) -> None:
        self._section.workup_confirm()

    async def key_f(self) -> None:
        self._section.workup_stop_as_level()

    async def key_backspace(self) -> None:
        self._section.workup_go_back()


class TreeNodeBox(Static):
    """A daughter or grandchild box in the lookahead-tree preview. Clicking it
    jumps straight to that node by applying its chain of Yes/No answers from
    the current node — one answer for a daughter, two for a grandchild. Not
    part of the tab/focus order (mouse/tap only, matching the prototype)."""

    def __init__(self, content: str, section: "DiagnosisSection", answers: list[str], classes: str = "") -> None:
        super().__init__(content, classes=classes)
        self._section = section
        self._click_answers = answers

    def on_click(self, event) -> None:
        event.stop()
        self._section.apply_click_answers(self._click_answers)


class DiagnosisSection(BaseSection):
    """Clinical Impression & ICD-11 Diagnosis section (core/06) — CAL-CP walker."""

    DEFAULT_CSS = """
    DiagnosisSection {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    .section_title  { text-style: bold; margin-bottom: 0; }
    .reference_note { color: $text-muted; margin-bottom: 1; }

    .breadcrumb     { color: $text-muted; margin-bottom: 1; height: auto; }
    .hint           { color: $accent; margin-top: 1; height: auto; }
    .result-banner {
        background: $success 20%; color: $text; padding: 0 1; margin-bottom: 1;
        border: round $success; height: auto;
    }
    .btn_row { height: auto; width: 100%; margin-bottom: 1; }
    .btn_row Button { width: auto; min-width: 16; margin-right: 1; }

    /* Two-generation lookahead tree — read-only reference, never focusable.
       Each daughter + its own two granddaughters is bounded together as one
       individual box, connected purely by plain vertical lines; nothing
       encloses the group. */
    .connector-row { height: 1; margin-bottom: 0; }
    .connector { width: 1fr; content-align: center middle; color: $text-muted; }
    .connector-subrow { width: 1fr; height: 1; }

    .families-row { height: auto; margin-bottom: 0; }
    .family-frame { width: 1fr; height: auto; margin: 0 1 0 0; }

    .daughter-box {
        height: auto; min-height: 3; width: 100%;
        border: round $border; padding: 0 1; margin-bottom: 0;
    }
    .daughter-box.clickable { pointer: pointer; }
    .daughter-box.clickable:hover { background: $accent 25%; border: round $accent; }

    .grandchild-group { width: 100%; height: auto; }
    .grandchild-box {
        height: auto; min-height: 3; width: 1fr;
        border: round $border; color: $text-muted; padding: 0 1; margin: 0 1 0 0;
    }
    .grandchild-box.clickable { pointer: pointer; }
    .grandchild-box.clickable:hover {
        background: $accent 25%; color: $text; border: round $accent;
    }
    .pathway-end {
        width: 1fr; height: auto; min-height: 3; color: $text-muted;
        text-style: italic; content-align: center middle; margin: 0 1 1 0;
    }

    /* Intro form (p6 chronic pain specifier) — plain Tab/mouse-driven data
       entry, unlike the keyboard-first Y/N trunk walk that follows it. */
    .field-label { color: $text-muted; }
    .intro-note  { color: $text-muted; text-style: italic; margin-bottom: 1; }
    .intro-row   { height: auto; }
    .intro-col   { width: 1fr; height: auto; margin-right: 2; }
    """

    # ------------------------------------------------------------------
    # compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Label("Clinical Impression & ICD-11 Diagnosis", classes="section_title")
        yield Label(
            "(Korwisi et al 2021, PAIN — CAL-CP: ICD-11 Chronic Pain Classification Algorithm)",
            classes="reference_note",
        )
        yield Vertical(id="dx_body")

    def on_mount(self) -> None:
        super().on_mount()
        # assessment_view.py mounts all sections then calls load_session()
        # synchronously in the same on_mount — load() can run and set
        # self._workup *before* this callback fires (compose()'s widgets
        # exist immediately on mount(), but on_mount itself is dispatched
        # later via the message queue). Only set defaults if load() hasn't
        # already run, so a restored partial walk isn't clobbered.
        if not hasattr(self, "_workup"):
            self._workup = Workup(id="w1", label="Site 1")
            self._legacy_dx: dict = {}
        self._schedule_rebuild()

    # ------------------------------------------------------------------
    # Workup control — called from CalCpNodeBox/TreeNodeBox and the
    # Restart/Start buttons
    # ------------------------------------------------------------------

    def workup_answer(self, ans: str) -> None:
        if self._workup.finished or not is_answerable(self._workup.current_node()):
            return
        self._workup.answer(ans)
        self._after_state_change()

    def workup_confirm(self) -> None:
        if self._workup.finished or is_answerable(self._workup.current_node()):
            return
        if self._workup.can_continue():
            self._workup.continue_step()
        elif self._workup.can_finish():
            self._workup.finish()
        else:
            return
        self._after_state_change()

    def workup_stop_as_level(self) -> None:
        if self._workup.finished:
            return
        if not (self._workup.can_continue() and self._workup.can_finish()):
            return
        self._workup.finish()
        self._after_state_change()

    def workup_go_back(self) -> None:
        self._workup.go_back()
        self._after_state_change()

    def apply_click_answers(self, answers: list[str]) -> None:
        if self._workup.finished:
            return
        for ans in answers:
            if not is_answerable(self._workup.current_node()):
                return
            self._workup.answer(ans)
        self._after_state_change()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "dx_restart":
            self._workup.restart()
            self._after_state_change()
        elif event.button.id == "dx_intro_start":
            self._workup.intro_done = True
            self._after_state_change()

    def _on_intro_field_changed(self, field_id: str, value) -> None:
        if field_id == "label":
            self._workup.label = value or self._workup.label
        else:
            self._workup.intro[field_id] = value
        self._after_data_change()

    def on_input_changed(self, event: Input.Changed) -> None:
        field_id = _INTRO_FIELD_IDS.get(event.input.id)
        if field_id:
            self._on_intro_field_changed(field_id, event.value)

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == "dx_intro_temporal" and event.pressed is not None:
            self._on_intro_field_changed("temporal_pattern", event.pressed.name)

    def _after_state_change(self) -> None:
        # State mutation (above) is synchronous and already committed by the
        # time this runs — collect()/autosave can happen immediately. The DOM
        # rebuild itself is deferred past the current event via
        # call_after_refresh: rebuilding synchronously (or even awaiting it
        # inline) while still inside a click/key handler on a widget that the
        # rebuild is about to remove deadlocks Textual's message pump —
        # removing an *ancestor* of the widget still handling its own event
        # never resolves. Confirmed via a minimal repro during testing;
        # deferring past the current event avoids it entirely.
        if not self._loading:
            self.post_message(self.FieldChanged())
        self.call_after_refresh(lambda: self._schedule_rebuild())

    def _after_data_change(self) -> None:
        # Field-by-field intro edits (every keystroke) autosave but must NOT
        # rebuild the body — that would destroy the Input's focus/cursor.
        if not self._loading:
            self.post_message(self.FieldChanged())

    # ------------------------------------------------------------------
    # Rendering — full rebuild on every state change (see module docstring).
    # remove_children()/mount_all() MUST be awaited in sequence — firing
    # them off un-awaited (as tui.py's NavChips.set_context does) races and
    # can leave both the old and new #dx_node_box mounted at once
    # (DuplicateIds), caught via testing here the same way the prototype's
    # own history log records catching an analogous double-mount race.
    # ------------------------------------------------------------------

    def _schedule_rebuild(self) -> None:
        # ROOT CAUSE (found via pab.log instrumentation during real pabd
        # debugging — see git history / conversation for the full trace):
        # on_mount() and load() can each trigger a rebuild in quick
        # succession (assessment_view.py's mount-then-load race, plus the
        # file watcher re-triggering load() again shortly after in real
        # pabd usage — three rebuilds within ~500ms was observed in
        # production). An earlier exclusive=True approach CANCELLED an
        # in-flight rebuild mid-mutation — one rebuild was cancelled while
        # awaiting body.mount_all(), the next two were each cancelled
        # mid-await inside body.remove_children() itself. Cancelling a
        # Textual remove_children()/mount_all() sequence partway through
        # leaves the DOM/compositor in a state Textual doesn't expect,
        # which produced a crash with no catchable Python exception, no
        # segfault, and total silence — not detectable any other way.
        # Fix: never cancel an in-flight rebuild. Coalesce instead — if a
        # rebuild is requested while one is already running, just mark
        # dirty and let the running one loop once more with the latest
        # state once it finishes cleanly.
        if getattr(self, "_rebuild_running", False):
            self._rebuild_dirty = True
            return
        self._rebuild_running = True
        self._rebuild_dirty = False
        self.run_worker(self._rebuild_loop(), group="dx_rebuild")

    async def _rebuild_loop(self) -> None:
        try:
            while True:
                await self._rebuild_body_once()
                if not self._rebuild_dirty:
                    break
                self._rebuild_dirty = False
        finally:
            self._rebuild_running = False

    async def _rebuild_body_once(self) -> None:
        try:
            body = self.query_one("#dx_body", Vertical)
        except NoMatches:
            # load() can run before this section's own compose() has been
            # dispatched — on_mount() will rebuild once it fires.
            return
        await body.remove_children()
        await body.mount_all(self._build_body_widgets())
        self._push_kb_notes()
        if self._workup.intro_done and not self._workup.finished:
            self.call_after_refresh(self._focus_node_box)

    def _focus_node_box(self) -> None:
        try:
            self.query_one("#dx_node_box", CalCpNodeBox).focus()
        except NoMatches:
            pass

    def _push_kb_notes(self) -> None:
        try:
            from ..objective.kb_panel import KBPanel
            self.app.query_one(KBPanel).show_raw(render_notes_panel(self._workup))
        except Exception:
            pass

    def _build_body_widgets(self) -> list:
        if not self._workup.intro_done:
            return self._build_intro_widgets()

        w = self._workup
        widgets: list = []
        if w.path:
            widgets.append(Static(w.breadcrumb(), classes="breadcrumb"))
        if w.finished:
            widgets.append(Static(f"  Result: {w.result_summary}  ", classes="result-banner"))

        view = effective_view(w.current_node_id)
        current_text = "\n".join(view["texts"])
        if view.get("criteria"):
            current_text += "\n" + "\n".join(f"  • {c}" for c in view["criteria"])
        widgets.append(CalCpNodeBox(current_text, self, id="dx_node_box"))

        if not w.finished and view["kind"] == "decision":
            shown: dict[str, str] = {rid: "current" for rid in view["raw_ids"]}
            widgets.append(Horizontal(
                Static("│", classes="connector"), Static("│", classes="connector"),
                classes="connector-row",
            ))
            yes_family = self._build_family("Yes", view["yes"], shown, "yes")
            no_family = self._build_family("No", view["no"], shown, "no")
            widgets.append(Horizontal(yes_family, no_family, classes="families-row"))

        widgets.append(Static(render_hint(w), classes="hint"))
        widgets.append(Horizontal(Button("Restart", id="dx_restart"), classes="btn_row"))
        return widgets

    # ------------------------------------------------------------------
    # Lookahead tree builders (ported from cal_cp/cal-cp-tui/app.py)
    # ------------------------------------------------------------------

    def _build_box(
        self, rel_label: str, target_id: str, shown: dict[str, str], css_class: str,
        click_answers: list[str] | None = None,
    ):
        view = effective_view(target_id)
        note = ""
        for rid in view["raw_ids"]:
            if rid in shown:
                note = f"\n[dim](= {shown[rid]}, above)[/dim]"
                break
        for rid in view["raw_ids"]:
            shown.setdefault(rid, rel_label)
        text = "\n".join(view["texts"])
        if view.get("criteria"):
            text += "\n" + "\n".join(f"  • {c}" for c in view["criteria"])
        if view["kind"] == "diagnosis":
            text = "[b]→ Diagnosis:[/b]\n" + text
        box_text = f"[b]{rel_label}:[/b] {text}{note}"
        if click_answers:
            box = TreeNodeBox(box_text, self, answers=click_answers, classes=f"{css_class} clickable")
        else:
            box = Static(box_text, classes=css_class)
        return box, view

    def _build_grandchildren(self, parent_view: dict, shown: dict[str, str], first_answer: str) -> list:
        if parent_view["kind"] == "decision":
            yb, _ = self._build_box(
                "Yes", parent_view["yes"], shown, "grandchild-box", click_answers=[first_answer, "yes"]
            )
            nb, _ = self._build_box(
                "No", parent_view["no"], shown, "grandchild-box", click_answers=[first_answer, "no"]
            )
            return [yb, nb]
        if parent_view["kind"] == "diagnosis":
            msg = "— continues to next level, see next screen —" if parent_view.get("next") \
                else "— diagnosis reached, no further branching —"
        elif parent_view["kind"] == "terminal":
            msg = "— pathway ends here —"
        elif parent_view.get("next"):
            msg = "— continues automatically, see next screen —"
        else:
            msg = "—"
        return [Static(msg, classes="pathway-end")]

    @staticmethod
    def _sub_connector(n: int) -> Horizontal:
        lines = [Static("│", classes="connector") for _ in range(n)] or [Static("", classes="connector")]
        return Horizontal(*lines, classes="connector-subrow")

    def _build_family(self, rel_label: str, target_id: str, shown: dict[str, str], first_answer: str) -> Vertical:
        daughter_box, view = self._build_box(
            rel_label, target_id, shown, "daughter-box", click_answers=[first_answer]
        )
        children = self._build_grandchildren(view, shown, first_answer)
        connector = self._sub_connector(2 if view["kind"] == "decision" else 0)
        return Vertical(
            daughter_box, connector, Horizontal(*children, classes="grandchild-group"),
            classes="family-frame",
        )

    # ------------------------------------------------------------------
    # Intro form (p6 chronic pain specifier)
    # ------------------------------------------------------------------

    def _intro_input(self, fid: str, placeholder: str = "") -> Input:
        return Input(
            value=self._workup.intro.get(fid, ""), placeholder=placeholder,
            id=_INTRO_WIDGET_IDS[fid], compact=True,
        )

    @staticmethod
    def _intro_col(label: str, control) -> Vertical:
        return Vertical(Static(label, classes="field-label"), control, classes="intro-col")

    @staticmethod
    def _nrs_placeholder(field: dict) -> str:
        return f"0={field.get('anchor_low', '')}, 10={field.get('anchor_high', '')}"

    def _build_intro_widgets(self) -> list:
        spec = INTRO_FORM.get("chronic_pain_specifier", {})
        fields = {f["id"]: f for f in spec.get("fields", []) if f.get("id")}
        widgets: list = []
        widgets.append(Static("[b]Chronic Pain Specifier[/b] [dim](p.6 — assess separately per pain site)[/dim]"))

        widgets.append(Horizontal(
            self._intro_col(
                "Site label",
                Input(value=self._workup.label, id=_INTRO_WIDGET_IDS["label"], compact=True),
            ),
            self._intro_col("Onset (MM/YYYY)", self._intro_input("onset_date", "MM/YYYY")),
            classes="intro-row",
        ))
        widgets.append(Static(
            "[dim]Pain must be present >3 months to count as chronic.[/dim]", classes="intro-note"
        ))

        nrs_i = fields.get("nrs_intensity", {})
        distress = fields.get("distress", {})
        widgets.append(Horizontal(
            self._intro_col("Intensity, last wk (0-10)", self._intro_input("nrs_intensity", self._nrs_placeholder(nrs_i))),
            self._intro_col("Distress, last wk (0-10)", self._intro_input("distress", self._nrs_placeholder(distress))),
            classes="intro-row",
        ))

        interference = fields.get("interference", {})
        temporal = fields.get("temporal_pattern", {})
        temporal_options = temporal.get("options") or TEMPORAL_PATTERN_OPTIONS
        radio = RadioSet(
            *[
                RadioButton(
                    o["label"], name=o["value"],
                    value=(self._workup.intro.get("temporal_pattern") == o["value"]),
                )
                for o in temporal_options
            ],
            id="dx_intro_temporal", compact=True,
        )
        widgets.append(Horizontal(
            self._intro_col("Interference, last wk (0-10)", self._intro_input("interference", self._nrs_placeholder(interference))),
            self._intro_col("Temporal pattern", radio),
            classes="intro-row",
        ))

        widgets.append(Button("Start decision trunk →", id="dx_intro_start", variant="primary", compact=True))
        return widgets

    # ------------------------------------------------------------------
    # Cross-reference badges — dropped with the CAL-CP rebuild (per user
    # decision). Kept as a no-op so _show_section's generic
    # update_cross_refs() call doesn't error.
    # ------------------------------------------------------------------

    def update_cross_refs(self, assessment: dict | None = None) -> None:
        pass

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def collect(self) -> dict:
        data = {"workups": [self._workup.to_dict()]}
        if self._legacy_dx:
            data["legacy"] = self._legacy_dx
        return data

    def load(self, data: dict) -> None:
        self._loading = True
        try:
            dx = data if isinstance(data, dict) else {}
            workups_data = dx.get("workups")
            if workups_data:
                self._workup = Workup.from_dict(workups_data[0])
            else:
                self._workup = Workup(id="w1", label="Site 1")
            # Preserve any pre-CAL-CP free-form dx data verbatim rather than
            # silently dropping it on next save — never lose data.
            legacy = dx.get("legacy") or {
                k: v for k, v in dx.items() if k not in ("workups", "legacy")
            }
            self._legacy_dx = legacy
            # load() is a sync method (assessment_view.py's contract for all
            # sections) but the rebuild is async — schedule it as a worker.
            # self._workup above is already set correctly regardless of
            # whether #dx_body exists yet (see _rebuild_body's own NoMatches
            # guard for the mount-vs-load race); if it's not composed yet,
            # on_mount() schedules its own rebuild once it fires.
            self._schedule_rebuild()
        finally:
            self._loading = False

    def is_complete(self) -> bool:
        return self._workup.finished

    class FieldChanged(Message):
        pass


_INTRO_FIELD_IDS = {
    "dx_intro_label": "label",
    "dx_intro_onset": "onset_date",
    "dx_intro_intensity": "nrs_intensity",
    "dx_intro_distress": "distress",
    "dx_intro_interference": "interference",
}
_INTRO_WIDGET_IDS = {v: k for k, v in _INTRO_FIELD_IDS.items()}
