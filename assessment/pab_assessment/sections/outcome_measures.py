"""Outcome Measures section (core/05) — accordion layout with lazy body mounting."""

import json
from pathlib import Path

from textual.app import ComposeResult, on
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.widgets import Label, Input, TextArea, Button, Static
from textual.message import Message

from .base import BaseSection
from ..widgets import CheckButton


# ---------------------------------------------------------------------------
# Shared option lists
# ---------------------------------------------------------------------------

_DASS_OPTIONS = [
    ("Normal",           "success"),
    ("Mild",             "primary"),
    ("Moderate",         "warning"),
    ("Severe",           "error"),
    ("Extremely severe", "error"),
]

_PCS_RISK_OPTIONS = [
    ("Low",       "success"),
    ("Moderate",  "warning"),
    ("High risk", "error"),
]

_PCL5_OPTIONS = [
    ("Negative (<33)",         "success"),
    ("Positive — PTSD likely", "error"),
]

_ISI_OPTIONS = [
    ("No insomnia (<10)",            "success"),
    ("Clinically significant (≥10)", "error"),
]

_PBAS_OPTIONS = [
    ("Normal",   "success"),
    ("Moderate", "warning"),
    ("Severe",   "error"),
]

# ---------------------------------------------------------------------------
# Auto-interpretation functions
# ---------------------------------------------------------------------------

def _interp_dass_dep(score: int) -> str:
    if score < 10: return "Normal"
    if score < 14: return "Mild"
    if score < 21: return "Moderate"
    if score < 28: return "Severe"
    return "Extremely severe"


def _interp_dass_anx(score: int) -> str:
    if score < 8:  return "Normal"
    if score < 10: return "Mild"
    if score < 15: return "Moderate"
    if score < 20: return "Severe"
    return "Extremely severe"


def _interp_dass_str(score: int) -> str:
    if score < 15: return "Normal"
    if score < 19: return "Mild"
    if score < 26: return "Moderate"
    if score < 34: return "Severe"
    return "Extremely severe"


def _interp_pcs_total(score: int) -> str:
    if score < 20: return "Low"
    if score < 30: return "Moderate"
    return "High risk"


def _interp_pcl5(score: int) -> str:
    return "Positive — PTSD likely" if score >= 33 else "Negative (<33)"


def _interp_isi(score: int) -> str:
    return "Clinically significant (≥10)" if score >= 10 else "No insomnia (<10)"


# ---------------------------------------------------------------------------
# CycleField widget
# ---------------------------------------------------------------------------

class CycleField(Static):
    """Button that cycles through a fixed list of labelled options."""

    DEFAULT_CSS = """
    CycleField {
        height: auto;
        width: auto;
        layout: horizontal;
        margin-bottom: 0;
        padding: 0;
    }
    CycleField Button {
        width: auto;
        height: auto;
        margin: 0;
        padding: 0 1;
    }
    """

    def __init__(self, field_id: str, options: list[tuple[str, str]],
                 initial_value: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.id = field_id
        self._field_id = field_id
        self._options = [(None, "default")] + list(options)
        self._idx = 0
        self._initial_value = initial_value

    def compose(self) -> ComposeResult:
        yield Button("?", id=f"{self._field_id}_btn", variant="default")

    def on_mount(self) -> None:
        if self._initial_value is not None:
            self.set_value(self._initial_value)

    def get_value(self) -> str | None:
        return self._options[self._idx][0]

    def set_value(self, value: str | None) -> None:
        for i, (opt, _) in enumerate(self._options):
            if opt == value:
                self._idx = i
                self._refresh()
                return
        self._idx = 0
        self._refresh()

    def _refresh(self) -> None:
        label, variant = self._options[self._idx]
        try:
            btn = self.query_one(Button)
            btn.label = label if label else "?"
            btn.variant = variant
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == f"{self._field_id}_btn":
            self._idx = (self._idx + 1) % len(self._options)
            self._refresh()
            self.post_message(CycleField.Changed())
            event.stop()

    class Changed(Message):
        pass


# ---------------------------------------------------------------------------
# HypRow — one row in the hypothesis testing table
# ---------------------------------------------------------------------------

_HYP_COLS = ["measure", "baseline", "interval", "rationale"]

# Field-key prefixes owned by each block — used to filter _pending_data so
# one block's stale pending data can't overwrite another block's live data.
_BLOCK_PREFIXES: dict[str, list[str]] = {
    "psfs":       ["psfs_"],
    "bpi":        ["bpi_"],
    "dass":       ["dass_"],
    "pcs":        ["pcs_"],
    "pseq":       ["pseq_"],
    "pcl5":       ["pcl5_"],
    "sleep":      ["isi_", "pbas_"],
    "additional": ["add_"],
}


class HypRow(Horizontal):
    """One row in the hypothesis testing table."""

    def __init__(self, row_idx: int, **kwargs):
        kwargs.setdefault("id", f"hyp_row_{row_idx}")
        super().__init__(**kwargs)
        self._row_idx = row_idx

    def compose(self) -> ComposeResult:
        yield Input(id=f"hyp_{self._row_idx}_measure",   classes="hyp_measure",   placeholder="Measure")
        yield Input(id=f"hyp_{self._row_idx}_baseline",  classes="hyp_baseline",  placeholder="Baseline")
        yield Input(id=f"hyp_{self._row_idx}_interval",  classes="hyp_interval",  placeholder="Interval")
        yield Input(id=f"hyp_{self._row_idx}_rationale", classes="hyp_rationale", placeholder="Rationale")


# ---------------------------------------------------------------------------
# OutcomeBlock — collapsible accordion block with lazy body mounting
# ---------------------------------------------------------------------------

class _CollapseBtn(Static):
    """Clickable header label that walks up to OutcomeBlock and toggles it."""

    def on_click(self) -> None:
        node = self.parent
        while node is not None:
            if isinstance(node, OutcomeBlock):
                node._toggle()
                return
            node = getattr(node, "parent", None)


class OutcomeBlock(Vertical):
    """
    Accordion block for one outcome measure.

    Always-visible header contains the plan checkbox + clickable title.
    Body is empty until first expand — widgets mounted lazily via mount_fn.
    """

    class Toggled(Message):
        def __init__(self, block: "OutcomeBlock", expanded: bool) -> None:
            super().__init__()
            self.block = block
            self.expanded = expanded

    DEFAULT_CSS = """
    OutcomeBlock {
        height: auto; width: 100%;
        border-bottom: tall $surface-lighten-1;
        margin-bottom: 0;
    }
    .ob_header {
        height: auto; width: 100%;
        background: $surface-lighten-1;
        padding: 0;
    }
    .ob_plan_btn {
        width: auto; min-width: 8; height: auto;
        margin: 0; padding: 0 1;
    }
    .ob_label {
        width: 1fr; height: auto;
        color: $accent; text-style: bold;
        padding: 0 1;
    }
    .ob_label:hover { background: $boost; }
    .ob_body {
        height: auto; width: 100%;
        padding: 0 1;
    }
    """

    def __init__(self, measure_id: str, title: str, mount_fn, **kwargs) -> None:
        super().__init__(**kwargs)
        self._measure_id = measure_id
        self._title = title
        self._mount_fn = mount_fn
        self._mounted = False
        self._expanded = False
        self._pending_data: dict = {}

    def compose(self) -> ComposeResult:
        with Horizontal(classes="ob_header"):
            yield CheckButton("Plan", id=f"plan_{self._measure_id}", classes="ob_plan_btn")
            yield _CollapseBtn(
                f"▶ {self._title}",
                id=f"ob_label_{self._measure_id}",
                classes="ob_label",
            )
        yield Vertical(id=f"ob_body_{self._measure_id}", classes="ob_body")

    def on_mount(self) -> None:
        self.query_one(f"#ob_body_{self._measure_id}").display = False

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        body = self.query_one(f"#ob_body_{self._measure_id}")
        if self._expanded and not self._mounted:
            self._mount_fn(body)
            self._mounted = True
        body.display = self._expanded
        self._update_label()
        self.post_message(self.Toggled(self, self._expanded))

    def _update_label(self) -> None:
        arrow = "▼" if self._expanded else "▶"
        try:
            self.query_one(f"#ob_label_{self._measure_id}", _CollapseBtn).update(
                f"{arrow} {self._title}"
            )
        except Exception:
            pass

    def store_data(self, data: dict) -> None:
        """Called by section load() — store plan checkbox always; defer rest if unmounted."""
        plan_key = f"plan_{self._measure_id}"
        if plan_key in data:
            try:
                self.query_one(f"#{plan_key}", CheckButton).set_value(data[plan_key])
            except Exception:
                pass
        if not self._mounted:
            # Only keep fields owned by this block — prevents stale pending data
            # from overwriting another block's freshly-collected live values in collect().
            prefixes = _BLOCK_PREFIXES.get(self._measure_id, [])
            self._pending_data = {
                k: v for k, v in data.items()
                if any(k.startswith(p) for p in prefixes)
            }
        else:
            self._apply_to_body(data)

    def drain_pending(self) -> None:
        """Apply pending data to mounted body widgets. Call under section._loading=True."""
        if self._pending_data:
            self._apply_to_body(self._pending_data)
            self._pending_data = {}

    def _apply_to_body(self, data: dict) -> None:
        try:
            body = self.query_one(f"#ob_body_{self._measure_id}")
        except Exception:
            return
        for inp in body.query(Input):
            if inp.id in data:
                inp.value = data[inp.id]
        for ta in body.query(TextArea):
            if ta.id in data:
                ta.load_text(data[ta.id])
        for cf in body.query(CycleField):
            if cf.id in data:
                cf.set_value(data[cf.id])
        for cb in body.query(CheckButton):
            if cb.id in data:
                cb.set_value(data[cb.id])

    def collect_data(self) -> dict:
        """Return all field values — plan checkbox always, body fields from pending or widgets."""
        data = {}
        plan_key = f"plan_{self._measure_id}"
        try:
            data[plan_key] = self.query_one(f"#{plan_key}", CheckButton).value
        except Exception:
            data[plan_key] = None

        if not self._mounted:
            for k, v in self._pending_data.items():
                if k != plan_key:
                    data[k] = v
        else:
            try:
                body = self.query_one(f"#ob_body_{self._measure_id}")
                for inp in body.query(Input):
                    data[inp.id] = inp.value
                for ta in body.query(TextArea):
                    data[ta.id] = ta.text
                for cf in body.query(CycleField):
                    data[cf.id] = cf.get_value()
                for cb in body.query(CheckButton):
                    data[cb.id] = cb.value
            except Exception:
                pass
        return data


# ---------------------------------------------------------------------------
# Body mount functions — one per measure
# ---------------------------------------------------------------------------

def _mount_psfs(body: Vertical) -> None:
    body.mount(
        Input(id="psfs_act_1", placeholder="Activity 1"),
        Input(id="psfs_act_2", placeholder="Activity 2"),
        Input(id="psfs_act_3", placeholder="Activity 3"),
    )


def _mount_bpi(body: Vertical) -> None:
    # 2-column layout, left-then-right tab order preserved:
    # activity→mood, walking→work, relations→sleep, enjoyment
    body.mount(
        Label("/10 — higher = greater impairment", classes="reference_note"),
        Horizontal(
            Label("Activity:", classes="bpi_lbl2"), Input(id="bpi_activity",  placeholder="/10", classes="bpi_sc2"),
            Label("Mood:",     classes="bpi_lbl2"), Input(id="bpi_mood",      placeholder="/10", classes="bpi_sc2"),
            classes="bpi_row2",
        ),
        Horizontal(
            Label("Walking:", classes="bpi_lbl2"), Input(id="bpi_walking",   placeholder="/10", classes="bpi_sc2"),
            Label("Work:",    classes="bpi_lbl2"), Input(id="bpi_work",      placeholder="/10", classes="bpi_sc2"),
            classes="bpi_row2",
        ),
        Horizontal(
            Label("Relations:", classes="bpi_lbl2"), Input(id="bpi_relations", placeholder="/10", classes="bpi_sc2"),
            Label("Sleep:",     classes="bpi_lbl2"), Input(id="bpi_sleep",     placeholder="/10", classes="bpi_sc2"),
            classes="bpi_row2",
        ),
        Horizontal(
            Label("Enjoyment:", classes="bpi_lbl2"), Input(id="bpi_enjoyment", placeholder="/10", classes="bpi_sc2"),
            classes="bpi_row2",
        ),
    )


def _mount_dass(body: Vertical) -> None:
    body.mount(
        Static("", id="xref_om_dass", classes="xref_badge"),
        Horizontal(
            Label("Dep:", classes="inline_lbl"),
            Input(id="dass_dep_score", placeholder="##", classes="inline_score"),
            CycleField("dass_dep_interp", _DASS_OPTIONS),
            Label("Anx:", classes="inline_lbl"),
            Input(id="dass_anx_score", placeholder="##", classes="inline_score"),
            CycleField("dass_anx_interp", _DASS_OPTIONS),
            Label("Str:", classes="inline_lbl"),
            Input(id="dass_str_score", placeholder="##", classes="inline_score"),
            CycleField("dass_str_interp", _DASS_OPTIONS),
            classes="inline_row",
        ),
    )


def _mount_pcs(body: Vertical) -> None:
    body.mount(
        Static("", id="xref_om_pcs", classes="xref_badge"),
        Horizontal(
            Label("Rum:", classes="inline_lbl"),
            Input(id="pcs_rum_score",  placeholder="##", classes="inline_score"),
            CycleField("pcs_rum_risk",  _PCS_RISK_OPTIONS),
            Label("Mag:", classes="inline_lbl"),
            Input(id="pcs_mag_score",  placeholder="##", classes="inline_score"),
            CycleField("pcs_mag_risk",  _PCS_RISK_OPTIONS),
            Label("Help:", classes="inline_lbl"),
            Input(id="pcs_help_score", placeholder="##", classes="inline_score"),
            CycleField("pcs_help_risk", _PCS_RISK_OPTIONS),
            Label("Total:", classes="inline_lbl"),
            Input(id="pcs_total_score", placeholder="##", classes="inline_score"),
            CycleField("pcs_total_risk", _PCS_RISK_OPTIONS),
            classes="inline_row",
        ),
        Static("", id="om_pcs_alert", classes="om_alert"),
    )


def _mount_pseq(body: Vertical) -> None:
    body.mount(
        Label("Score /60 — higher = stronger self-efficacy", classes="reference_note"),
        Input(id="pseq_score", placeholder="/60"),
        Static("", id="xref_om_pseq", classes="xref_badge"),
    )


def _mount_pcl5(body: Vertical) -> None:
    body.mount(
        Label("Score /80:"),
        Horizontal(
            Input(id="pcl5_score", placeholder="/80", classes="om_score"),
            CycleField("pcl5_interp", _PCL5_OPTIONS),
            classes="om_row",
        ),
        Static("", id="om_pcl5_alert", classes="om_alert"),
        Static("", id="xref_om_pcl5", classes="xref_badge_urgent"),
        Label("Action if positive:"),
        TextArea(id="pcl5_action", language="plain"),
    )


def _mount_sleep(body: Vertical) -> None:
    body.mount(
        Static("", id="xref_om_sleep", classes="xref_badge"),
        Label("Insomnia Severity Index (ISI) — score /28:"),
        Horizontal(
            Input(id="isi_score", placeholder="/28", classes="om_score"),
            CycleField("isi_interp", _ISI_OPTIONS),
            classes="om_row",
        ),
        Static("", id="om_isi_alert", classes="om_alert"),
        Label("Pain-Related Beliefs and Attitudes About Sleep (PBAS) — score /10:"),
        Horizontal(
            Input(id="pbas_score", placeholder="/10", classes="om_score"),
            CycleField("pbas_interp", _PBAS_OPTIONS),
            classes="om_row",
        ),
    )


def _mount_additional(body: Vertical) -> None:
    body.mount(
        CheckButton("AUDIT (alcohol use) — administered?", id="add_audit", classes="add_btn"),
        Static("", id="xref_om_audit", classes="xref_badge"),
        CheckButton("DUDIT (drug use) — administered?", id="add_dudit", classes="add_btn"),
        Label("ePPOC components (specify):"),
        TextArea(id="add_epoc", language="plain"),
        Label("Other:"),
        TextArea(id="add_other", language="plain"),
    )


# ---------------------------------------------------------------------------
# OutcomeMeasuresSection
# ---------------------------------------------------------------------------

class OutcomeMeasuresSection(BaseSection):
    """Outcome Measures section (core/05)."""

    DEFAULT_CSS = """
    OutcomeMeasuresSection {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    .section_title  { text-style: bold; margin-bottom: 0; }
    .reference_note { color: $text-muted; margin-bottom: 0; }

    Label { margin-bottom: 0; }

    TextArea, Input { height: auto; min-height: 1; margin-bottom: 0; }

    /* OutcomeBlock header — 2 rows deep for larger click target */
    .ob_header { min-height: 2; }
    .ob_label  { height: 1fr; }

    /* Dense single-row layout (DASS, PCS) */
    .inline_row   { height: auto; margin-bottom: 0; }
    .inline_lbl   { width: auto; padding: 0 1; margin-bottom: 0; }
    .inline_score { width: 5; margin-bottom: 0; }

    /* BPI 2-column pairs */
    .bpi_row2  { height: auto; margin-bottom: 0; }
    .bpi_lbl2  { width: 1fr; margin-bottom: 0; }
    .bpi_sc2   { width: 6; margin-bottom: 0; }

    /* Compact score row (PCL-5, PSEQ, Sleep) */
    .om_row   { height: auto; margin-bottom: 0; }
    .om_score { width: 10; margin-bottom: 0; }

    /* Hypothesis testing table */
    .hyp_header_row { height: auto; margin-bottom: 0; }
    .hyp_header     { text-style: bold; color: $text-muted; margin-bottom: 0; }
    .hyp_measure    { width: 2fr; }
    .hyp_baseline   { width: 2fr; }
    .hyp_interval   { width: 2fr; }
    .hyp_rationale  { width: 3fr; }
    HypRow          { height: auto; margin-bottom: 0; }

    /* Alert banners */
    .om_alert {
        width: 100%; padding: 0 1; text-style: bold;
        color: $warning; background: $warning 20%;
        margin-bottom: 0; display: none;
    }

    /* Cross-ref badges */
    .xref_badge {
        width: 100%; height: auto; padding: 0 1;
        margin-bottom: 0; color: $accent; background: $accent 12%;
        display: none;
    }
    .xref_badge_urgent {
        width: 100%; height: auto; padding: 0 1;
        margin-bottom: 0; color: $warning; background: $warning 20%;
        text-style: bold; display: none;
    }

    /* Additional measures toggle buttons */
    .add_btn { width: 100%; height: 3; margin-bottom: 0; }
    """

    # ------------------------------------------------------------------
    # compose / on_mount
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Label("Outcome Measures", classes="section_title")
        yield OutcomeBlock("psfs",       "PSFS — Patient Specific Functional Scale", _mount_psfs)
        yield OutcomeBlock("bpi",        "BPI — Brief Pain Inventory",                _mount_bpi)
        yield OutcomeBlock("dass",       "DASS-21",                                   _mount_dass)
        yield OutcomeBlock("pcs",        "PCS — Pain Catastrophising Scale",          _mount_pcs)
        yield OutcomeBlock("pseq",       "PSEQ — Pain Self-Efficacy Questionnaire",   _mount_pseq)
        yield OutcomeBlock("pcl5",       "PCL-5 — PTSD Checklist",                   _mount_pcl5)
        yield OutcomeBlock("sleep",      "Sleep Outcome Measures",                    _mount_sleep)
        yield OutcomeBlock("additional", "Additional Measures",                       _mount_additional)

        yield Label("— Measures Selected for Ongoing Hypothesis Testing —",
                    classes="subsection_header", id="om_hypothesis")
        with Horizontal(classes="hyp_header_row"):
            yield Label("Measure",   classes="hyp_measure hyp_header")
            yield Label("Baseline",  classes="hyp_baseline hyp_header")
            yield Label("Interval",  classes="hyp_interval hyp_header")
            yield Label("Rationale", classes="hyp_rationale hyp_header")
        with Vertical(id="hyp_table"):
            yield HypRow(0)
        yield Label("Administer questionnaires same day where possible. Score before next session.",
                    classes="reference_note")

    def on_mount(self) -> None:
        self._hyp_row_count: int = 1
        self._hyp_pending: dict = {}

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _jump_to(self, anchor_id: str) -> None:
        try:
            target = self.query_one(f"#{anchor_id}")
            self.app.query_one("#section_content", ScrollableContainer).scroll_to_widget(
                target, top=True, animate=False
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Auto-interpretation and alerts
    # ------------------------------------------------------------------

    def _update_auto_interp(self) -> None:
        _auto = [
            ("dass_dep_score", "dass_dep_interp", _interp_dass_dep),
            ("dass_anx_score", "dass_anx_interp", _interp_dass_anx),
            ("dass_str_score", "dass_str_interp", _interp_dass_str),
            ("pcs_total_score", "pcs_total_risk",  _interp_pcs_total),
            ("pcl5_score",      "pcl5_interp",     _interp_pcl5),
            ("isi_score",       "isi_interp",      _interp_isi),
        ]
        for score_id, interp_id, fn in _auto:
            try:
                raw = self.query_one(f"#{score_id}", Input).value.strip()
                if raw.lstrip("-").isdigit():
                    self.query_one(f"#{interp_id}", CycleField).set_value(fn(int(raw)))
            except Exception:
                pass

    def _update_alerts(self) -> None:
        _checks = [
            ("pcs_total_score", 30, "om_pcs_alert",  "⚠ PCS total ≥30 — high catastrophising: consider psychology referral"),
            ("pcl5_score",      33, "om_pcl5_alert", "⚠ PCL-5 ≥33 — PTSD likely: document action above"),
            ("isi_score",       10, "om_isi_alert",  "⚠ ISI ≥10 — clinically significant insomnia"),
        ]
        for score_id, threshold, alert_id, msg in _checks:
            try:
                raw = self.query_one(f"#{score_id}", Input).value.strip()
                alert = self.query_one(f"#{alert_id}", Static)
                if raw.lstrip("-").isdigit() and int(raw) >= threshold:
                    alert.update(msg)
                    alert.display = True
                else:
                    alert.display = False
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Cross-reference badges
    # ------------------------------------------------------------------

    def update_cross_refs(self) -> None:
        if not self.session_file:
            return
        try:
            data = json.loads(Path(self.session_file).read_text())
        except Exception:
            return

        def _sec(key):
            v = data.get("assessment", {}).get(key)
            return v if isinstance(v, dict) else {}

        med  = _sec("medical")
        subj = _sec("subjective")

        def _set(badge_id: str, lines: list[str]) -> None:
            try:
                w = self.query_one(f"#{badge_id}", Static)
                if lines:
                    w.update("  ".join(f"◀ {l}" for l in lines))
                    w.display = True
                else:
                    w.display = False
            except Exception:
                pass

        lines = []
        if med.get("comorbid_mental_health") is True:
            lines.append("Med: mental health condition (comorbidity)")
        if subj.get("psychological_distress", "").strip():
            lines.append("Subj: psychological distress recorded")
        if subj.get("mood_influences") is True:
            lines.append("Subj: mood influences pain")
        if subj.get("screening_tool", "").strip():
            lines.append("Subj: screening tool recorded")
        _set("xref_om_dass", lines)

        lines = []
        if subj.get("psychological_distress", "").strip():
            lines.append("Subj: psychological distress recorded")
        _set("xref_om_pcs", lines)

        lines = []
        conf = subj.get("confidence_score", "").strip()
        if conf:
            lines.append(f"Subj: confidence score = {conf}/10")
        _set("xref_om_pseq", lines)

        lines = []
        if subj.get("self_harm_risk") is True:
            lines.append("Subj: self-harm/suicide risk — POSITIVE")
        elif subj.get("self_harm_risk") is False:
            lines.append("Subj: self-harm/suicide risk — cleared")
        if subj.get("harm_plan", "").strip():
            lines.append("Subj: harm plan documented")
        _set("xref_om_pcl5", lines)

        lines = []
        if subj.get("sleep_difficulty") is True:
            lines.append("Subj: sleep difficulty")
        if subj.get("night_waking") is True:
            lines.append("Subj: night waking")
        total_sleep = subj.get("total_sleep_hours", "").strip()
        if total_sleep:
            lines.append(f"Subj: {total_sleep} hrs/night")
        _set("xref_om_sleep", lines)

        lines = []
        if med.get("comorbid_drug_alcohol") is True:
            lines.append("Med: drug/alcohol issues (comorbidity)")
        _set("xref_om_audit", lines)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def collect(self) -> dict:
        data = {}
        for block in self.query(OutcomeBlock):
            data.update(block.collect_data())
        for i in range(self._hyp_row_count):
            for col in _HYP_COLS:
                fid = f"hyp_{i}_{col}"
                try:
                    data[fid] = self.query_one(f"#{fid}", Input).value
                except Exception:
                    data[fid] = ""
        return data

    def load(self, data: dict) -> None:
        self._loading = True
        try:
            om = data if isinstance(data, dict) else {}
            for block in self.query(OutcomeBlock):
                block.store_data(om)
            # Mount additional hyp rows needed for this session's data
            max_hyp = -1
            for k in om:
                if k.startswith("hyp_"):
                    parts = k.split("_")
                    if len(parts) >= 3 and parts[1].isdigit():
                        max_hyp = max(max_hyp, int(parts[1]))
            if max_hyp >= self._hyp_row_count:
                try:
                    hyp_table = self.query_one("#hyp_table")
                    for i in range(self._hyp_row_count, max_hyp + 1):
                        hyp_table.mount(HypRow(i))
                        self._hyp_row_count += 1
                except Exception:
                    pass
            self._hyp_pending = {k: v for k, v in om.items() if k.startswith("hyp_")}
        finally:
            self._loading = False
            self.update_cross_refs()
        if self._hyp_pending:
            self.call_after_refresh(self._drain_hyp)

    def _drain_hyp(self) -> None:
        self._loading = True
        try:
            for i in range(self._hyp_row_count):
                for col in _HYP_COLS:
                    fid = f"hyp_{i}_{col}"
                    val = self._hyp_pending.get(fid, "")
                    if val:
                        try:
                            self.query_one(f"#{fid}", Input).value = val
                        except Exception:
                            pass
        finally:
            self._loading = False
        self._hyp_pending = {}

    def _maybe_add_hyp_row(self) -> None:
        last_idx = self._hyp_row_count - 1
        try:
            has_content = any(
                (self.query_one(f"#hyp_{last_idx}_{col}", Input).value or "").strip()
                for col in _HYP_COLS
            )
            if has_content:
                self.query_one("#hyp_table").mount(HypRow(self._hyp_row_count))
                self._hyp_row_count += 1
        except Exception:
            pass

    def is_complete(self) -> bool:
        d = self.collect()
        indicators = ["psfs_act_1", "bpi_activity", "dass_dep_score",
                      "pcs_total_score", "pseq_score", "pcl5_score", "isi_score"]
        return any(d.get(f, "").strip() for f in indicators if isinstance(d.get(f), str))

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def on_outcome_block_toggled(self, event: OutcomeBlock.Toggled) -> None:
        if event.expanded:
            block = event.block
            def _drain():
                self._loading = True
                try:
                    block.drain_pending()
                finally:
                    self._loading = False
                self._update_auto_interp()
                self._update_alerts()
                self.update_cross_refs()
            block.call_after_refresh(_drain)

    @on(CheckButton.Changed)
    @on(CycleField.Changed)
    @on(Input.Changed, selector="Input")
    @on(TextArea.Changed, selector="TextArea")
    def _on_field_changed(self, event: Message = None) -> None:
        if self._loading:
            return
        self._update_auto_interp()
        self._update_alerts()
        if isinstance(event, Input.Changed) and getattr(event.input, "id", "").startswith("hyp_"):
            self._maybe_add_hyp_row()
        self.post_message(self.FieldChanged())

    class FieldChanged(Message):
        pass
