"""Clinical Impression & ICD-11 Diagnosis section (core/06).

CAL-CP (ICD-11 Chronic Pain Classification Algorithm) walker — replaces the
old free-form mechanism/subtype/severity picker. See ../cal_cp_model.py for
the graph model and cal_cp/cal-cp-history.md for the algorithm's build history.

Phase 4 of the pabd integration: multi-workup tabs (one independent walk per
pain site, mirroring the prototype's "sites" concept). Intro form (p6
specifier), two-generation lookahead tree, and KB-panel notes (Ctrl+K) were
built in Phase 3.

Rendering model: each workup's body is fully rebuilt (remove_children +
mount_all) on every state change rather than patching individual widgets in
place, since the lookahead tree's shape varies with the current node's type.
Rebuilds are serialized per workup (never cancelled mid-mutation — see
_schedule_rebuild's docstring for why that matters) and coalesced if a new
one is requested while one is in flight.

Multi-workup ID namespacing: Textual's TabbedContent keeps every TabPane's
content mounted simultaneously (only the active one is visually shown), so
a plain id like "dx_node_box" would collide across tabs the instant a second
workup exists. Every queryable widget id is namespaced "<base>__<workup_id>".
"""

from __future__ import annotations

import asyncio
import logging

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.message import Message
from textual.widgets import (
    Button, Input, Label, RadioButton, RadioSet, Static, TabbedContent, TabPane,
)

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


_logger = logging.getLogger(__name__)


def _id_for(base: str, wid: str) -> str:
    return f"{base}__{wid}"


class CalCpNodeBox(Static, can_focus=True):
    """Focusable display of the current CAL-CP node for one workup. Y/N/Enter/
    F/Backspace are scoped to this widget's focus (Textual's key_<key>
    convention — same pattern as widgets.CheckButton's key_y/key_n), never
    App-level bindings, so they don't collide with any other section's keys,
    or with another workup's tab. Rebuilt fresh on every state change, so it
    takes its owning section + workup id directly rather than via a bind step."""

    DEFAULT_CSS = """
    CalCpNodeBox {
        height: auto; min-height: 3; width: 100%;
        background: $warning 35%; color: $text; text-style: bold;
        border: round $warning; padding: 0 1; margin-bottom: 1;
    }
    CalCpNodeBox:focus { border: round $accent; }
    """

    def __init__(self, text: str, section: "DiagnosisSection", wid: str, **kwargs) -> None:
        super().__init__(text, **kwargs)
        self._section = section
        self._wid = wid

    async def key_y(self) -> None:
        self._section.workup_answer(self._wid, "yes")

    async def key_n(self) -> None:
        self._section.workup_answer(self._wid, "no")

    async def key_enter(self) -> None:
        self._section.workup_confirm(self._wid)

    async def key_f(self) -> None:
        self._section.workup_stop_as_level(self._wid)

    async def key_backspace(self) -> None:
        self._section.workup_go_back(self._wid)


class TreeNodeBox(Static):
    """A daughter or grandchild box in the lookahead-tree preview. Clicking it
    jumps straight to that node by applying its chain of Yes/No answers from
    the current node — one answer for a daughter, two for a grandchild. Not
    part of the tab/focus order (mouse/tap only, matching the prototype)."""

    def __init__(
        self, content: str, section: "DiagnosisSection", wid: str,
        answers: list[str], classes: str = "",
    ) -> None:
        super().__init__(content, classes=classes)
        self._section = section
        self._wid = wid
        self._click_answers = answers

    def on_click(self, event) -> None:
        event.stop()
        self._section.apply_click_answers(self._wid, self._click_answers)


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
    #dx_add_workup_row Button { width: auto; min-width: 18; }

    #dx_tabs { height: auto; }

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
        with Horizontal(id="dx_add_workup_row", classes="btn_row"):
            yield Button("+ New workup", id="dx_add_workup")
        # Left empty — TabPane content is added programmatically in
        # on_mount()/load() via _schedule_tab_sync(). Composing panes here
        # too would register their ids, then the sync's add_pane() calls
        # would collide with them (same class of bug documented at
        # tui.py's NavChips.set_context: compose-time ids + later
        # remount-time ids with the same value silently collide).
        yield TabbedContent(id="dx_tabs")

    def on_mount(self) -> None:
        super().on_mount()
        # assessment_view.py mounts all sections then calls load_session()
        # synchronously in the same on_mount — load() can run and set
        # self._workups *before* this callback fires (compose()'s widgets
        # exist immediately on mount(), but on_mount itself is dispatched
        # later via the message queue). Only set defaults if load() hasn't
        # already run, so a restored session isn't clobbered.
        if not hasattr(self, "_workups"):
            self._workups: dict[str, Workup] = {}
            self._counter = 0
            self._legacy_dx: dict = {}
        if not self._workups:
            self._add_workup_model()
        self._schedule_tab_sync()

    def _add_workup_model(self) -> str:
        self._counter += 1
        wid = f"w{self._counter}"
        self._workups[wid] = Workup(id=wid, label=f"Site {self._counter}")
        return wid

    def _active_workup_id(self) -> str | None:
        try:
            return self.query_one("#dx_tabs", TabbedContent).active or None
        except NoMatches:
            return None

    # ------------------------------------------------------------------
    # Workup control — called from CalCpNodeBox/TreeNodeBox and the
    # Restart/Start/Add-workup buttons
    # ------------------------------------------------------------------

    def workup_answer(self, wid: str, ans: str) -> None:
        w = self._workups.get(wid)
        if w is None or w.finished or not is_answerable(w.current_node()):
            return
        w.answer(ans)
        self._after_state_change(wid)

    def workup_confirm(self, wid: str) -> None:
        w = self._workups.get(wid)
        if w is None or w.finished or is_answerable(w.current_node()):
            return
        if w.can_continue():
            w.continue_step()
        elif w.can_finish():
            w.finish()
        else:
            return
        self._after_state_change(wid)

    def workup_stop_as_level(self, wid: str) -> None:
        w = self._workups.get(wid)
        if w is None or w.finished:
            return
        if not (w.can_continue() and w.can_finish()):
            return
        w.finish()
        self._after_state_change(wid)

    def workup_go_back(self, wid: str) -> None:
        w = self._workups.get(wid)
        if w is None:
            return
        w.go_back()
        self._after_state_change(wid)

    def apply_click_answers(self, wid: str, answers: list[str]) -> None:
        w = self._workups.get(wid)
        if w is None or w.finished:
            return
        for ans in answers:
            if not is_answerable(w.current_node()):
                return
            w.answer(ans)
        self._after_state_change(wid)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid == "dx_add_workup":
            wid = self._add_workup_model()
            self._pending_active_wid = wid
            if not self._loading:
                self.post_message(self.FieldChanged())
            self._schedule_tab_sync()
            return
        for prefix, handler in (
            ("dx_restart__", self._handle_restart),
            ("dx_intro_start__", self._handle_intro_start),
        ):
            if bid.startswith(prefix):
                handler(bid[len(prefix):])
                return

    def _handle_restart(self, wid: str) -> None:
        w = self._workups.get(wid)
        if w is None:
            return
        w.restart()
        self._after_state_change(wid)

    def _handle_intro_start(self, wid: str) -> None:
        w = self._workups.get(wid)
        if w is None:
            return
        w.intro_done = True
        self._after_state_change(wid)

    def _on_intro_field_changed(self, wid: str, field_id: str, value) -> None:
        w = self._workups.get(wid)
        if w is None:
            return
        if field_id == "label":
            w.label = value or w.label
            self._update_tab_label(wid)
        else:
            w.intro[field_id] = value
        self._after_data_change()

    def on_input_changed(self, event: Input.Changed) -> None:
        parsed = _parse_intro_widget_id(event.input.id)
        if parsed:
            field_id, wid = parsed
            self._on_intro_field_changed(wid, field_id, event.value)

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        rid = event.radio_set.id or ""
        if rid.startswith("dx_intro_temporal__") and event.pressed is not None:
            wid = rid[len("dx_intro_temporal__"):]
            self._on_intro_field_changed(wid, "temporal_pattern", event.pressed.name)

    def _update_tab_label(self, wid: str) -> None:
        w = self._workups.get(wid)
        if w is None:
            return
        try:
            tab = self.query_one("#dx_tabs", TabbedContent).get_tab(wid)
        except Exception:
            return
        tab.label = f"{w.label} · {w.result_summary}" if w.finished else w.label

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        wid = event.pane.id
        w = self._workups.get(wid)
        if w is None:
            return
        self._push_kb_notes(wid)
        if w.intro_done and not w.finished:
            self.call_after_refresh(lambda: self._focus_node_box(wid))

    def _after_state_change(self, wid: str) -> None:
        # State mutation (above) is synchronous and already committed by the
        # time this runs — collect()/autosave can happen immediately. The DOM
        # rebuild itself is deferred past the current event via
        # call_after_refresh: rebuilding synchronously (or even awaiting it
        # inline) while still inside a click/key handler on a widget that the
        # rebuild is about to remove deadlocks Textual's message pump —
        # removing an *ancestor* of the widget still handling its own event
        # never resolves. Confirmed via a minimal repro during Phase 3.
        self._update_tab_label(wid)
        if not self._loading:
            self.post_message(self.FieldChanged())
        self.call_after_refresh(lambda: self._schedule_rebuild(wid))

    def _after_data_change(self) -> None:
        # Field-by-field intro edits (every keystroke) autosave but must NOT
        # rebuild the body — that would destroy the Input's focus/cursor.
        if not self._loading:
            self.post_message(self.FieldChanged())

    # ------------------------------------------------------------------
    # Tab creation — same "never cancel mid-mutation" discipline as body
    # rebuilds (see _schedule_rebuild). TabbedContent.add_pane() is async;
    # cancelling it partway through would leave a half-registered pane, the
    # same class of corruption that caused the Phase 3 crash.
    # ------------------------------------------------------------------

    def _schedule_tab_sync(self) -> None:
        if getattr(self, "_tab_sync_running", False):
            self._tab_sync_dirty = True
            return
        self._tab_sync_running = True
        self._tab_sync_dirty = False
        self.run_worker(self._tab_sync_loop(), group="dx_tab_sync")

    async def _tab_sync_loop(self) -> None:
        try:
            while True:
                try:
                    await self._sync_tabs_once()
                except Exception:
                    # Defense in depth beyond the specific NoMatches race
                    # handled inside _sync_tabs_once: ANY exception escaping
                    # a run_worker coroutine crashes the whole app (see
                    # _schedule_rebuild's docstring), so an unanticipated
                    # failure here must never propagate — log and stop this
                    # pass rather than take the whole TUI down with it.
                    _logger.error("dx tab sync failed", exc_info=True)
                if not self._tab_sync_dirty:
                    break
                self._tab_sync_dirty = False
        finally:
            self._tab_sync_running = False

    async def _sync_tabs_once(self) -> None:
        try:
            tabs = self.query_one("#dx_tabs", TabbedContent)
        except NoMatches:
            return
        existing_ids = {pane.id for pane in tabs.query(TabPane)}
        for wid, w in self._workups.items():
            if wid in existing_ids:
                continue
            pane = TabPane(w.label, Vertical(id=_id_for("dx_body", wid)), id=wid)
            try:
                await tabs.add_pane(pane)
            except NoMatches:
                # TabbedContent's own internal ContentTabs child isn't
                # mounted yet — a deeper version of the same mount-vs-load
                # race as everywhere else in this file (#dx_tabs itself is
                # queryable, but add_pane() needs ITS OWN nested compose()
                # to have completed too). Retry on the next pass rather than
                # let this escape the worker: ANY exception escaping a
                # run_worker coroutine crashes the WHOLE APP, not just this
                # section — confirmed the hard way (Textual's
                # _handle_exception "always results in the app exiting",
                # and it kills pending on_mount()/Mount-message processing
                # for everything else too, so there's no later retry once
                # that happens). A single asyncio.sleep(0) yields to the
                # event loop so the pending compose work can actually run.
                self._tab_sync_dirty = True
                await asyncio.sleep(0)
                return
            self._schedule_rebuild(wid)
        pending = getattr(self, "_pending_active_wid", None)
        if pending and pending in self._workups:
            tabs.active = pending
            self._pending_active_wid = None

    # ------------------------------------------------------------------
    # Body rendering — full rebuild on every state change (see module
    # docstring). remove_children()/mount_all() MUST be awaited in
    # sequence and never cancelled mid-flight — see _schedule_rebuild.
    # ------------------------------------------------------------------

    def _schedule_rebuild(self, wid: str) -> None:
        # ROOT CAUSE of a real pabd-only crash found during Phase 3 (see git
        # history): on_mount(), load(), and the file watcher's session-switch
        # reload could each trigger a rebuild in quick succession. An earlier
        # exclusive=True approach CANCELLED an in-flight rebuild
        # mid-mutation — cancelling a Textual remove_children()/mount_all()
        # sequence partway through leaves the DOM/compositor in a state
        # Textual doesn't expect: a crash with no catchable Python
        # exception, no segfault, and total silence. Fix, extended here to
        # per-workup scope: never cancel an in-flight rebuild. Coalesce
        # instead — if a rebuild is requested for a workup that's already
        # rebuilding, just mark it dirty and let the running one loop once
        # more with the latest state once it finishes cleanly. Tracked
        # per-workup so one tab's rapid changes can't stall another's.
        running = getattr(self, "_rebuild_running", None)
        if running is None:
            running = self._rebuild_running = {}
        dirty = getattr(self, "_rebuild_dirty", None)
        if dirty is None:
            dirty = self._rebuild_dirty = {}
        if running.get(wid):
            dirty[wid] = True
            return
        running[wid] = True
        dirty[wid] = False
        self.run_worker(self._rebuild_loop(wid), group=f"dx_rebuild__{wid}")

    async def _rebuild_loop(self, wid: str) -> None:
        try:
            while True:
                try:
                    await self._rebuild_body_once(wid)
                except Exception:
                    # Defense in depth: ANY exception escaping a run_worker
                    # coroutine crashes the whole app, not just this section
                    # (see _schedule_rebuild's docstring — confirmed the
                    # hard way). Log and stop this pass rather than take
                    # the whole TUI down over an unanticipated failure here.
                    _logger.error("dx rebuild failed for workup=%s", wid, exc_info=True)
                if not self._rebuild_dirty.get(wid):
                    break
                self._rebuild_dirty[wid] = False
        finally:
            self._rebuild_running[wid] = False

    async def _rebuild_body_once(self, wid: str) -> None:
        w = self._workups.get(wid)
        if w is None:
            return
        try:
            body = self.query_one(f"#{_id_for('dx_body', wid)}", Vertical)
        except NoMatches:
            # The tab for this workup isn't mounted yet — _sync_tabs_once
            # schedules a rebuild right after mounting it, so this is only
            # reachable if called before that, which doesn't happen given
            # the call sites here, but stay defensive regardless.
            return
        await body.remove_children()
        await body.mount_all(self._build_body_widgets(wid))
        if wid == self._active_workup_id():
            self._push_kb_notes(wid)
            if w.intro_done and not w.finished:
                self.call_after_refresh(lambda: self._focus_node_box(wid))

    def _focus_node_box(self, wid: str) -> None:
        try:
            self.query_one(f"#{_id_for('dx_node_box', wid)}", CalCpNodeBox).focus()
        except NoMatches:
            pass

    def _push_kb_notes(self, wid: str) -> None:
        w = self._workups.get(wid)
        if w is None:
            return
        try:
            from ..objective.kb_panel import KBPanel
            self.app.query_one(KBPanel).show_raw(render_notes_panel(w))
        except Exception:
            pass

    def _build_body_widgets(self, wid: str) -> list:
        w = self._workups[wid]
        if not w.intro_done:
            return self._build_intro_widgets(wid)

        widgets: list = []
        if w.path:
            widgets.append(Static(w.breadcrumb(), classes="breadcrumb"))
        if w.finished:
            widgets.append(Static(f"  Result: {w.result_summary}  ", classes="result-banner"))

        view = effective_view(w.current_node_id)
        current_text = "\n".join(view["texts"])
        if view.get("criteria"):
            current_text += "\n" + "\n".join(f"  • {c}" for c in view["criteria"])
        widgets.append(CalCpNodeBox(current_text, self, wid, id=_id_for("dx_node_box", wid)))

        if not w.finished and view["kind"] == "decision":
            shown: dict[str, str] = {rid: "current" for rid in view["raw_ids"]}
            widgets.append(Horizontal(
                Static("│", classes="connector"), Static("│", classes="connector"),
                classes="connector-row",
            ))
            yes_family = self._build_family(wid, "Yes", view["yes"], shown, "yes")
            no_family = self._build_family(wid, "No", view["no"], shown, "no")
            widgets.append(Horizontal(yes_family, no_family, classes="families-row"))

        widgets.append(Static(render_hint(w), classes="hint"))
        widgets.append(Horizontal(
            Button("Restart", id=_id_for("dx_restart", wid)), classes="btn_row",
        ))
        return widgets

    # ------------------------------------------------------------------
    # Lookahead tree builders (ported from cal_cp/cal-cp-tui/app.py)
    # ------------------------------------------------------------------

    def _build_box(
        self, wid: str, rel_label: str, target_id: str, shown: dict[str, str], css_class: str,
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
            box = TreeNodeBox(box_text, self, wid, answers=click_answers, classes=f"{css_class} clickable")
        else:
            box = Static(box_text, classes=css_class)
        return box, view

    def _build_grandchildren(self, wid: str, parent_view: dict, shown: dict[str, str], first_answer: str) -> list:
        if parent_view["kind"] == "decision":
            yb, _ = self._build_box(
                wid, "Yes", parent_view["yes"], shown, "grandchild-box", click_answers=[first_answer, "yes"]
            )
            nb, _ = self._build_box(
                wid, "No", parent_view["no"], shown, "grandchild-box", click_answers=[first_answer, "no"]
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

    def _build_family(self, wid: str, rel_label: str, target_id: str, shown: dict[str, str], first_answer: str) -> Vertical:
        daughter_box, view = self._build_box(
            wid, rel_label, target_id, shown, "daughter-box", click_answers=[first_answer]
        )
        children = self._build_grandchildren(wid, view, shown, first_answer)
        connector = self._sub_connector(2 if view["kind"] == "decision" else 0)
        return Vertical(
            daughter_box, connector, Horizontal(*children, classes="grandchild-group"),
            classes="family-frame",
        )

    # ------------------------------------------------------------------
    # Intro form (p6 chronic pain specifier)
    # ------------------------------------------------------------------

    def _intro_input(self, wid: str, fid: str, placeholder: str = "") -> Input:
        w = self._workups[wid]
        return Input(
            value=w.intro.get(fid, ""), placeholder=placeholder,
            id=_id_for(f"dx_intro_{fid}", wid), compact=True,
        )

    @staticmethod
    def _intro_col(label: str, control) -> Vertical:
        return Vertical(Static(label, classes="field-label"), control, classes="intro-col")

    @staticmethod
    def _nrs_placeholder(field: dict) -> str:
        return f"0={field.get('anchor_low', '')}, 10={field.get('anchor_high', '')}"

    def _build_intro_widgets(self, wid: str) -> list:
        w = self._workups[wid]
        spec = INTRO_FORM.get("chronic_pain_specifier", {})
        fields = {f["id"]: f for f in spec.get("fields", []) if f.get("id")}
        widgets: list = []
        widgets.append(Static("[b]Chronic Pain Specifier[/b] [dim](p.6 — assess separately per pain site)[/dim]"))

        widgets.append(Horizontal(
            self._intro_col(
                "Site label",
                Input(value=w.label, id=_id_for("dx_intro_label", wid), compact=True),
            ),
            self._intro_col("Onset (MM/YYYY)", self._intro_input(wid, "onset_date", "MM/YYYY")),
            classes="intro-row",
        ))
        widgets.append(Static(
            "[dim]Pain must be present >3 months to count as chronic.[/dim]", classes="intro-note"
        ))

        nrs_i = fields.get("nrs_intensity", {})
        distress = fields.get("distress", {})
        widgets.append(Horizontal(
            self._intro_col("Intensity, last wk (0-10)", self._intro_input(wid, "nrs_intensity", self._nrs_placeholder(nrs_i))),
            self._intro_col("Distress, last wk (0-10)", self._intro_input(wid, "distress", self._nrs_placeholder(distress))),
            classes="intro-row",
        ))

        interference = fields.get("interference", {})
        temporal = fields.get("temporal_pattern", {})
        temporal_options = temporal.get("options") or TEMPORAL_PATTERN_OPTIONS
        radio = RadioSet(
            *[
                RadioButton(
                    o["label"], name=o["value"],
                    value=(w.intro.get("temporal_pattern") == o["value"]),
                )
                for o in temporal_options
            ],
            id=_id_for("dx_intro_temporal", wid), compact=True,
        )
        widgets.append(Horizontal(
            self._intro_col("Interference, last wk (0-10)", self._intro_input(wid, "interference", self._nrs_placeholder(interference))),
            self._intro_col("Temporal pattern", radio),
            classes="intro-row",
        ))

        widgets.append(Button(
            "Start decision trunk →", id=_id_for("dx_intro_start", wid), variant="primary", compact=True,
        ))
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
        data = {"workups": [w.to_dict() for w in self._workups.values()]}
        if self._legacy_dx:
            data["legacy"] = self._legacy_dx
        return data

    def load(self, data: dict) -> None:
        self._loading = True
        try:
            dx = data if isinstance(data, dict) else {}
            workups_data = dx.get("workups")
            if workups_data:
                self._workups = {}
                max_n = 0
                for wd in workups_data:
                    w = Workup.from_dict(wd)
                    self._workups[w.id] = w
                    if w.id.startswith("w") and w.id[1:].isdigit():
                        max_n = max(max_n, int(w.id[1:]))
                self._counter = max_n
            else:
                self._workups = {}
                self._counter = 0
                self._add_workup_model()
            # Preserve any pre-CAL-CP free-form dx data verbatim rather than
            # silently dropping it on next save — never lose data.
            legacy = dx.get("legacy") or {
                k: v for k, v in dx.items() if k not in ("workups", "legacy")
            }
            self._legacy_dx = legacy
            # load() is a sync method (assessment_view.py's contract for all
            # sections) but tab creation/rebuilds are async — scheduled as
            # workers. self._workups above is already set correctly
            # regardless of whether #dx_tabs is composed yet (see
            # _sync_tabs_once's own NoMatches guard for the mount-vs-load
            # race); if it's not composed yet, on_mount() schedules its own
            # sync once it fires.
            self._schedule_tab_sync()
        finally:
            self._loading = False

    def is_complete(self) -> bool:
        return any(w.finished for w in self._workups.values())

    class FieldChanged(Message):
        pass


def _parse_intro_widget_id(widget_id: str | None) -> tuple[str, str] | None:
    """Split "dx_intro_<field>__<wid>" into (field, wid), or None if it
    doesn't match — split from the right since field names themselves
    contain underscores (e.g. "onset_date", "nrs_intensity")."""
    if not widget_id or not widget_id.startswith("dx_intro_"):
        return None
    if "__" not in widget_id:
        return None
    prefix, wid = widget_id.rsplit("__", 1)
    field = prefix[len("dx_intro_"):]
    return (field, wid) if field else None
