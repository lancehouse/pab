"""Pain Type Classification section (core/04)."""

import json
from pathlib import Path

from textual.app import ComposeResult, on
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import Button, Label, Input, TextArea, Static
from textual.message import Message

from .base import BaseSection
from ..widgets import CheckButton
from .medical import LikelihoodField
from .regional_differential import RegionalDifferentialPanel


class PainTypeSelector(Static):
    """Cycling selector for dominant pain type."""

    DEFAULT_CSS = """
    PainTypeSelector {
        height: 3;
        width: 100%;
        layout: horizontal;
        margin-bottom: 0;
        padding: 0;
    }
    PainTypeSelector Label {
        width: 1fr;
        height: auto;
        padding: 0 1 0 0;
    }
    PainTypeSelector Button {
        width: auto;
        height: 3;
        margin: 0;
        padding: 0 2;
    }
    """

    _CYCLE = [None, "Nociceptive", "Neuropathic", "Nociplastic", "Mixed — unable to determine"]
    _VARIANTS = {
        None: "primary",
        "Nociceptive": "success",
        "Neuropathic": "warning",
        "Nociplastic": "error",
        "Mixed — unable to determine": "default",
    }

    def __init__(self, label: str, field_id: str, **kwargs):
        super().__init__(**kwargs)
        self.id = field_id
        self._label = label
        self._field_id = field_id
        self._value = None

    def compose(self) -> ComposeResult:
        yield Label(self._label)
        yield Button("?", id=f"{self._field_id}_btn", variant="primary")

    def get_value(self) -> str | None:
        return self._value

    def set_value(self, value: str | None) -> None:
        self._value = value
        try:
            btn = self.query_one(f"#{self._field_id}_btn", Button)
            btn.label = value if value else "?"
            btn.variant = self._VARIANTS.get(value, "primary")
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == f"{self._field_id}_btn":
            idx = self._CYCLE.index(self._value)
            self.set_value(self._CYCLE[(idx + 1) % len(self._CYCLE)])
            self.post_message(PainTypeSelector.Changed())
            event.stop()

    class Changed(Message):
        pass


# ---------------------------------------------------------------------------
# PainClassificationSection
# ---------------------------------------------------------------------------

class PainClassificationSection(BaseSection):
    """Pain Type Classification section (core/04)."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._diff_panels: dict[str, RegionalDifferentialPanel] = {}

    DEFAULT_CSS = """
    PainClassificationSection {
        width: 100%;
        height: auto;
        padding: 0 1;
    }
    .section_title { text-style: bold; color: $text; margin-bottom: 0; }
    .subgroup_header { color: $text-muted; margin-top: 0; margin-bottom: 0; text-style: bold italic; }
    .reference_note  { color: $text-muted; margin-bottom: 0; }

    .btn_row { height: auto; width: 100%; margin-bottom: 0; }

    CheckButton { width: auto; height: 3; min-width: 16; margin: 0 1 0 0; }

    /* Label + field row */
    .field_row { height: auto; width: 100%; margin: 0; padding: 0; }
    .field_row Label { width: 28; height: auto; padding: 0 1 0 0; }
    .field_row Input { width: 1fr; height: auto; padding: 0 1; }
    .field_row TextArea { width: 1fr; height: auto; min-height: 2; padding: 0 1; }

    TextArea { height: auto; min-height: 2; padding: 0 1; }
    Input    { height: auto; padding: 0 1; }

    #pc_infl_score {
        color: $primary; text-style: bold; margin-bottom: 0;
    }
    #pc_infl_alert, #pc_csi_alert {
        width: 100%; padding: 0 1; text-style: bold;
        color: $warning; background: $warning 20%; margin-bottom: 0;
    }
    #pc_mixed_reminder {
        width: 100%; padding: 0 1; color: $warning; margin-bottom: 0;
    }
    .xref_badge {
        width: 100%; height: auto; padding: 0 1; margin-bottom: 0;
        color: $accent; background: $accent 12%;
    }
    """

    _INFL_FIELDS = ["infl_constant", "infl_morning", "infl_sleep", "infl_activity"]

    _TOGGLE_FIELDS = [
        "infl_constant", "infl_morning", "infl_sleep", "infl_activity",
        "noci_subj_mechanical", "noci_subj_trauma", "noci_subj_localised",
        "noci_subj_resolving", "noci_subj_analgesia", "noci_subj_no_constant",
        "noci_subj_inflammation", "noci_subj_recent",
        "noci_exam_mechanical", "noci_exam_palpation",
        "noci_exam_hyperalgesia", "noci_exam_antalgic",
        "neuro_subj_quality", "neuro_subj_nerve_injury", "neuro_subj_neurological",
        "neuro_subj_dermatomal", "neuro_subj_medication", "neuro_subj_severity",
        "neuro_subj_neural_loading", "neuro_subj_dysaesthesia", "neuro_subj_spontaneous",
        "neuro_exam_neurodynamic", "neuro_exam_neural_palpation",
        "neuro_exam_neurology", "neuro_exam_antalgic", "neuro_exam_hyperalgesia",
        "nocip_subj_disproportionate", "nocip_subj_persistent",
        "nocip_subj_disproportionate2", "nocip_subj_widespread",
        "nocip_subj_failed", "nocip_subj_psychosocial", "nocip_subj_medication",
        "nocip_subj_spontaneous", "nocip_subj_disability", "nocip_subj_constant",
        "nocip_subj_night_pain", "nocip_subj_dysaesthesia", "nocip_subj_severity",
        "nocip_exam_disproportionate", "nocip_exam_hyperalgesia",
        "nocip_exam_diffuse", "nocip_exam_psychosocial",
        "cs_light", "cs_touch", "cs_noise", "cs_pesticides", "cs_temperature",
        "cs_fatigue", "cs_sleep", "cs_concentration", "cs_swelling", "cs_tingling",
    ]

    _LIKELIHOOD_FIELDS = [
        "infl_likelihood", "noci_likelihood", "neuro_likelihood", "nocip_likelihood",
    ]

    _TEXT_FIELDS = [
        "noci_interpretation", "neuro_interpretation",
        "nocip_interpretation", "summary_contributing", "summary_reasoning",
    ]

    # ------------------------------------------------------------------
    # compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:  # noqa: C901
        yield Label("Pain Type Classification", classes="section_title")

        # ── Inflammatory ────────────────────────────────────────────────
        yield Label("— Inflammatory Pain —", classes="subsection_header", id="pc_inflammatory")
        yield Label("Walker & Williamson 2008", classes="reference_note")
        with Horizontal(classes="btn_row"):
            yield CheckButton("Constant symptoms", id="infl_constant")
            yield CheckButton("Morning pain/stiffness >30 min", id="infl_morning")
        yield Static("", id="xref_infl_morning", classes="xref_badge")
        with Horizontal(classes="btn_row"):
            yield CheckButton("Sleep disturbance (moderate+)", id="infl_sleep")
            yield CheckButton("Better with activity", id="infl_activity")
        yield Static("", id="xref_infl_sleep", classes="xref_badge")
        yield Static("Score: 0/4", id="pc_infl_score")
        yield Static("", id="pc_infl_alert")
        yield LikelihoodField("Inflammatory likelihood:", field_id="infl_likelihood")
        yield Static("", id="xref_infl_dx", classes="xref_badge")

        # ── Nociceptive ─────────────────────────────────────────────────
        yield Label("— Nociceptive Pain —", classes="subsection_header", id="pc_nociceptive")
        yield Label("Smart et al 2010 — pain from actual or threatened non-neural tissue damage", classes="reference_note")
        yield Label("Subjective:", classes="subgroup_header")
        with Horizontal(classes="btn_row"):
            yield CheckButton("Mechanical agg/ease factors", id="noci_subj_mechanical")
            yield CheckButton("Proportionate to trauma/pathology", id="noci_subj_trauma")
            yield CheckButton("Localised ±somatic referral", id="noci_subj_localised")
        with Horizontal(classes="btn_row"):
            yield CheckButton("Resolves in healing timeframes", id="noci_subj_resolving")
            yield CheckButton("Responsive to analgesia/NSAIDs", id="noci_subj_analgesia")
            yield CheckButton("No constant/unremitting pain", id="noci_subj_no_constant")
        yield Static("", id="xref_noci_resolving", classes="xref_badge")
        with Horizontal(classes="btn_row"):
            yield CheckButton("Associated with inflammation", id="noci_subj_inflammation")
            yield CheckButton("Recent onset", id="noci_subj_recent")
        yield Label("Examination:", classes="subgroup_header")
        with Horizontal(classes="btn_row"):
            yield CheckButton("Mechanical pattern on testing", id="noci_exam_mechanical")
            yield CheckButton("Localised on palpation", id="noci_exam_palpation")
            yield CheckButton("Proportionate hyperalgesia", id="noci_exam_hyperalgesia")
            yield CheckButton("Antalgic posture/movement", id="noci_exam_antalgic")
        yield LikelihoodField("Nociceptive likelihood:", field_id="noci_likelihood")
        yield Label("Interpretation:")
        yield TextArea(id="noci_interpretation", language="plain")

        # ── Neuropathic ─────────────────────────────────────────────────
        yield Label("— Neuropathic Pain —", classes="subsection_header", id="pc_neuropathic")
        yield Label("Smart et al 2010 — pain from somatosensory nervous system lesion/disease", classes="reference_note")
        yield Label("Subjective:", classes="subgroup_header")
        with Horizontal(classes="btn_row"):
            yield CheckButton("Burning/shooting/electric quality", id="neuro_subj_quality")
            yield CheckButton("Hx of nerve injury", id="neuro_subj_nerve_injury")
            yield CheckButton("Neurological Sx/paraesthesia", id="neuro_subj_neurological")
        yield Static("", id="xref_neuro_neurological", classes="xref_badge")
        with Horizontal(classes="btn_row"):
            yield CheckButton("Dermatomal distribution", id="neuro_subj_dermatomal")
            yield CheckButton("Anti-epileptic/AD responsive", id="neuro_subj_medication")
            yield CheckButton("High severity/irritability", id="neuro_subj_severity")
        with Horizontal(classes="btn_row"):
            yield CheckButton("Neural tissue loading pattern", id="neuro_subj_neural_loading")
            yield CheckButton("Dysaesthesias (burn/cold/crawl)", id="neuro_subj_dysaesthesia")
            yield CheckButton("Spontaneous/paroxysmal pain", id="neuro_subj_spontaneous")
        yield Label("Examination:", classes="subgroup_header")
        with Horizontal(classes="btn_row"):
            yield CheckButton("Provoc neurodynamic tests", id="neuro_exam_neurodynamic")
            yield CheckButton("Neural tissue palpation +", id="neuro_exam_neural_palpation")
            yield CheckButton("Positive neurological findings", id="neuro_exam_neurology")
            yield CheckButton("Antalgic limb posture", id="neuro_exam_antalgic")
        yield CheckButton("Hyperalgesia/allodynia in distribution", id="neuro_exam_hyperalgesia")
        yield LikelihoodField("Neuropathic likelihood:", field_id="neuro_likelihood")
        yield Label("Interpretation:")
        yield TextArea(id="neuro_interpretation", language="plain")

        # ── Nociplastic ─────────────────────────────────────────────────
        yield Label("— Nociplastic Pain —", classes="subsection_header", id="pc_nociplastic")
        yield Label("IASP — pain from altered nociception, no clear nociceptive/neuropathic cause", classes="reference_note")
        yield Label("Subjective:", classes="subgroup_header")
        with Horizontal(classes="btn_row"):
            yield CheckButton("Disproportionate/unpredictable", id="nocip_subj_disproportionate")
            yield CheckButton("Beyond healing timeframes", id="nocip_subj_persistent")
            yield CheckButton("Disproportionate to pathology", id="nocip_subj_disproportionate2")
        with Horizontal(classes="btn_row"):
            yield CheckButton("Widespread/non-anatomical", id="nocip_subj_widespread")
            yield CheckButton("Failed interventions", id="nocip_subj_failed")
            yield CheckButton("Psychosocial association", id="nocip_subj_psychosocial")
        yield Static("", id="xref_nocip_failed", classes="xref_badge")
        yield Static("", id="xref_nocip_psych", classes="xref_badge")
        with Horizontal(classes="btn_row"):
            yield CheckButton("Anti-epileptic/AD responsive", id="nocip_subj_medication")
            yield CheckButton("Spontaneous/paroxysmal pain", id="nocip_subj_spontaneous")
            yield CheckButton("High functional disability", id="nocip_subj_disability")
        with Horizontal(classes="btn_row"):
            yield CheckButton("Constant/unremitting pain", id="nocip_subj_constant")
            yield CheckButton("Night pain/disturbed sleep", id="nocip_subj_night_pain")
            yield CheckButton("Dysaesthesias (burn/cold/crawl)", id="nocip_subj_dysaesthesia")
        yield Static("", id="xref_nocip_night", classes="xref_badge")
        yield CheckButton("High severity/irritability", id="nocip_subj_severity")
        yield Label("Examination:", classes="subgroup_header")
        with Horizontal(classes="btn_row"):
            yield CheckButton("Disproportionate provocation", id="nocip_exam_disproportionate")
            yield CheckButton("Hyperalgesia/allodynia", id="nocip_exam_hyperalgesia")
            yield CheckButton("Diffuse non-anatomic tenderness", id="nocip_exam_diffuse")
            yield CheckButton("Psychosocial (catastroph/FA)", id="nocip_exam_psychosocial")
        yield LikelihoodField("Nociplastic likelihood:", field_id="nocip_likelihood")
        yield Static("", id="xref_nocip_dx", classes="xref_badge")
        yield Label("Interpretation:")
        yield TextArea(id="nocip_interpretation", language="plain")

        # ── Central Sensitisation ────────────────────────────────────────
        yield Label("— Central Sensitisation —", classes="subsection_header", id="pc_central")
        yield Label("Nijs et al 2010, Neblett et al 2013", classes="reference_note")
        yield Label("CSI score (0–100):")
        yield Input(id="csi_score", placeholder="0–100")
        yield Static("", id="pc_csi_alert")
        yield Label("Additional CS features:", classes="subgroup_header")
        with Horizontal(classes="btn_row"):
            yield CheckButton("Light sensitivity", id="cs_light")
            yield CheckButton("Touch sensitivity", id="cs_touch")
            yield CheckButton("Noise sensitivity", id="cs_noise")
            yield CheckButton("Chemical sensitivity", id="cs_pesticides")
        with Horizontal(classes="btn_row"):
            yield CheckButton("Temperature sensitivity", id="cs_temperature")
            yield CheckButton("Fatigue", id="cs_fatigue")
            yield CheckButton("Sleep disturbance", id="cs_sleep")
            yield CheckButton("Concentration difficulty", id="cs_concentration")
        yield Static("", id="xref_cs_fatigue", classes="xref_badge")
        yield Static("", id="xref_cs_sleep", classes="xref_badge")
        yield Static("", id="xref_cs_concentration", classes="xref_badge")
        with Horizontal(classes="btn_row"):
            yield CheckButton("Limb swelling sensation", id="cs_swelling")
            yield CheckButton("Tingling/numbness", id="cs_tingling")
        yield Static("", id="xref_cs_tingling", classes="xref_badge")

        # ── Regional Differential ───────────────────────────────────────
        yield Vertical(id="pc_diff_region")

        # ── Summary ──────────────────────────────────────────────────────
        yield Label("— Pain Type Summary —", classes="subsection_header", id="pc_summary")
        yield PainTypeSelector("Dominant pain type:", field_id="summary_dominant")
        yield Static("", id="pc_mixed_reminder")
        yield Label("Contributing pain type(s):")
        yield TextArea(id="summary_contributing", language="plain")
        yield Label("Clinical reasoning:")
        yield TextArea(id="summary_reasoning", language="plain")

    # ------------------------------------------------------------------
    # Regional differential panel management
    # ------------------------------------------------------------------

    def set_active_regions(self, regions: list[str]) -> None:
        """Mount/unmount regional differential panels to match active regions."""
        try:
            container = self.query_one("#pc_diff_region", Vertical)
        except Exception:
            return
        current = set(self._diff_panels.keys())
        for rid in current - set(regions):
            panel = self._diff_panels.pop(rid)
            panel.remove()
        for rid in set(regions) - current:
            panel = RegionalDifferentialPanel(rid, id=f"pc_diff_{rid}")
            self._diff_panels[rid] = panel
            container.mount(panel)

    def set_region_test_data(self, region_id: str, tests: dict) -> None:
        """Push latest special test results to the matching regional panel."""
        panel = self._diff_panels.get(region_id)
        if panel:
            panel.set_tests(tests)

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

        med = _sec("medical")
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
        if subj.get("morning_stiffness", "").strip():
            lines.append("Subj: morning stiffness recorded")
        _set("xref_infl_morning", lines)

        lines = []
        if subj.get("sleep_difficulty") is True:
            lines.append("Subj: sleep difficulty")
        if subj.get("night_waking") is True:
            lines.append("Subj: night waking")
        _set("xref_infl_sleep", lines)

        lines = []
        if med.get("comorbid_inflammatory") is True:
            lines.append("Med: systemic inflammatory condition")
        if med.get("diff_as_inflammatory") is True:
            lines.append("Med: inflammatory pattern (diff. AS)")
        _set("xref_infl_dx", lines)

        lines = []
        if subj.get("course_improving") is True:
            lines.append("Subj: course improving")
        if subj.get("course_worsening") is True:
            lines.append("Subj: course worsening")
        _set("xref_noci_resolving", lines)

        lines = []
        if med.get("rf_bilateral_paraesthesia") is True:
            lines.append("Med: bilateral paraesthesia (red flag +ve)")
        if med.get("rf_saddle_anaesthesia") is True:
            lines.append("Med: saddle anaesthesia (red flag +ve)")
        _set("xref_neuro_neurological", lines)

        lines = []
        if subj.get("previous_treatment", "").strip():
            lines.append("Subj: previous treatment recorded")
        _set("xref_nocip_failed", lines)

        lines = []
        if subj.get("mood_influences") is True:
            lines.append("Subj: mood influences pain")
        _set("xref_nocip_psych", lines)

        lines = []
        if subj.get("night_waking") is True:
            lines.append("Subj: night waking")
        _set("xref_nocip_night", lines)

        lines = []
        if med.get("comorbid_fibromyalgia") is True:
            lines.append("Med: fibromyalgia")
        if med.get("comorbid_whiplash") is True:
            lines.append("Med: chronic whiplash")
        _set("xref_nocip_dx", lines)

        lines = []
        if med.get("comorbid_cfs") is True:
            lines.append("Med: chronic fatigue syndrome")
        if med.get("comorbid_fatigue_memory") is True:
            lines.append("Med: fatigue/concentration/memory issues")
        _set("xref_cs_fatigue", lines)

        lines = []
        if subj.get("sleep_difficulty") is True:
            lines.append("Subj: sleep difficulty")
        if subj.get("night_waking") is True:
            lines.append("Subj: night waking")
        if med.get("comorbid_cfs") is True:
            lines.append("Med: CFS")
        _set("xref_cs_sleep", lines)

        lines = []
        if med.get("comorbid_fatigue_memory") is True:
            lines.append("Med: fatigue/concentration/memory issues")
        if med.get("comorbid_cfs") is True:
            lines.append("Med: CFS")
        _set("xref_cs_concentration", lines)

        lines = []
        if med.get("rf_bilateral_paraesthesia") is True:
            lines.append("Med: bilateral paraesthesia (red flag +ve)")
        _set("xref_cs_tingling", lines)

    # ------------------------------------------------------------------
    # Auto-update display widgets
    # ------------------------------------------------------------------

    def _update_infl_score(self) -> None:
        try:
            score = sum(
                1 for fid in self._INFL_FIELDS
                if self.query_one(f"#{fid}", CheckButton).value is True
            )
            self.query_one("#pc_infl_score", Static).update(f"Score: {score}/4")
            alert = self.query_one("#pc_infl_alert", Static)
            if score >= 2:
                alert.update(
                    "⚠ Score ≥2 — moderate likelihood of inflammatory processes "
                    "as significant barrier to recovery"
                )
                alert.display = True
            else:
                alert.display = False
        except Exception:
            pass

    def _update_csi_alert(self) -> None:
        try:
            score_str = self.query_one("#csi_score", Input).value.strip()
            alert = self.query_one("#pc_csi_alert", Static)
            if score_str.isdigit() and int(score_str) >= 40:
                alert.update(f"⚠ CSI score {score_str} ≥ 40 — suggestive of central sensitisation")
                alert.display = True
            else:
                alert.display = False
        except Exception:
            pass

    def _update_mixed_reminder(self) -> None:
        try:
            val = self.query_one("#summary_dominant", PainTypeSelector).get_value()
            reminder = self.query_one("#pc_mixed_reminder", Static)
            if val == "Mixed — unable to determine":
                reminder.update(
                    "Reminder: document plan to determine dominant pain type "
                    "during the preparation phase"
                )
                reminder.display = True
            else:
                reminder.display = False
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def collect(self) -> dict:
        data = {}
        for fid in self._TOGGLE_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", CheckButton).value
            except Exception:
                data[fid] = None
        for fid in self._LIKELIHOOD_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", LikelihoodField).get_value()
            except Exception:
                data[fid] = None
        for fid in self._TEXT_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", TextArea).text
            except Exception:
                data[fid] = ""
        try:
            data["csi_score"] = self.query_one("#csi_score", Input).value
        except Exception:
            data["csi_score"] = ""
        try:
            data["summary_dominant"] = self.query_one("#summary_dominant", PainTypeSelector).get_value()
        except Exception:
            data["summary_dominant"] = None
        return data

    def load(self, data: dict) -> None:
        self._loading = True
        try:
            pain = data if isinstance(data, dict) else {}
            for fid in self._TOGGLE_FIELDS:
                if fid in pain:
                    try:
                        self.query_one(f"#{fid}", CheckButton).set_value(pain[fid])
                    except Exception:
                        pass
            for fid in self._LIKELIHOOD_FIELDS:
                if fid in pain:
                    try:
                        self.query_one(f"#{fid}", LikelihoodField).set_value(pain[fid])
                    except Exception:
                        pass
            for fid in self._TEXT_FIELDS:
                if fid in pain:
                    try:
                        self.query_one(f"#{fid}", TextArea).text = pain[fid]
                    except Exception:
                        pass
            if "csi_score" in pain:
                try:
                    self.query_one("#csi_score", Input).value = pain["csi_score"]
                except Exception:
                    pass
            if "summary_dominant" in pain:
                try:
                    self.query_one("#summary_dominant", PainTypeSelector).set_value(
                        pain["summary_dominant"]
                    )
                except Exception:
                    pass
        finally:
            self._loading = False
            self._update_infl_score()
            self._update_csi_alert()
            self._update_mixed_reminder()
            self.update_cross_refs()

    def is_complete(self) -> bool:
        return self.collect().get("summary_dominant") is not None

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    @on(CheckButton.Changed)
    @on(LikelihoodField.Changed)
    @on(PainTypeSelector.Changed)
    @on(Input.Changed, selector="Input")
    @on(TextArea.Changed, selector="TextArea")
    def _on_field_changed(self) -> None:
        if self._loading:
            return
        self._update_infl_score()
        self._update_csi_alert()
        self._update_mixed_reminder()
        self.post_message(self.FieldChanged())

    class FieldChanged(Message):
        pass
