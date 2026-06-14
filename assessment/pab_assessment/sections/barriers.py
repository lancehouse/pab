"""Barriers to Recovery — F8.

Treatment Plan, Session 1, Day 1 checklist, and Follow-Up are in RxPlanSection (F9).
"""

import json
from pathlib import Path

from textual.app import ComposeResult, on
from textual.containers import Horizontal, ScrollableContainer
from textual.widgets import Label, Input, TextArea, Static
from textual.message import Message

from .base import BaseSection
from ..widgets import CheckButton, FlagButton
from .outcome_measures import CycleField


# ---------------------------------------------------------------------------
# Option lists
# ---------------------------------------------------------------------------

_DASS_SEVERITY_OPTIONS = [
    ("Mild",             "success"),
    ("Moderate",         "warning"),
    ("Severe",           "error"),
    ("Extremely severe", "error"),
]

_PTSD_MECHANISM_OPTIONS = [
    ("Motor vehicle accident",  "default"),
    ("Traumatic work accident", "default"),
    ("Other",                   "default"),
]


# ---------------------------------------------------------------------------
# Field lists for collect / load
# ---------------------------------------------------------------------------

_TOGGLE_FIELDS = [
    # Physical / Nociceptive barriers
    "b_noci_disease", "b_noci_pacing", "b_noci_inflammatory", "b_noci_deconditioning",
    "b_noci_movement", "b_noci_gait", "b_noci_strength", "b_noci_deep_muscle",
    "b_noci_overactivity", "b_noci_nerve_mech", "b_noci_diet",
    # Strength sub-items
    "bx_strength_glute_max", "bx_strength_glute_med", "bx_strength_iliopsoas", "bx_strength_quads",
    # Deep muscle sub-items
    "bx_deep_multifidus", "bx_deep_ta", "bx_deep_erector",
    # Overactivity sub-items
    "bx_over_erector", "bx_over_ql", "bx_over_ra", "bx_over_obliques",
    "bx_over_piriformis", "bx_over_iliopsoas", "bx_over_hamstrings", "bx_over_adductors",
    # Neuropathic barriers
    "b_neuro_confirmed", "b_neuro_unconfirmed",
    # Nociplastic barriers
    "b_nocip_moderate", "b_nocip_crps", "b_nocip_fnd",
    # Psychological barriers
    "b_psych_depression", "b_psych_anxiety", "b_psych_stress",
    "b_psych_catastrophising", "b_psych_self_efficacy", "b_psych_unhelpful_beliefs",
    "b_psych_ptsd", "b_psych_readiness",
    # Psych sub-items
    "bx_dep_psychiatry", "bx_anx_psychiatry", "bx_stress_psychiatry", "bx_ptsd_psychiatry",
    # Unhelpful beliefs sub-items
    "bx_belief_expectations", "bx_belief_symptom_focus", "bx_belief_cure_focus", "bx_belief_further_tx",
    # Sleep
    "b_sleep_disturbed",
    # Social
    "b_social_home", "b_social_rtw",
    # Social sub-items
    "bx_soc_family_support", "bx_soc_social_support", "bx_soc_relationship",
    "bx_soc_personal_rel", "bx_soc_financial", "bx_soc_residential", "bx_soc_distance",
    # Medical barriers
    "b_med_red_flag", "b_med_substance", "b_med_as", "b_med_aaa",
    "b_med_vascular", "b_med_cervical_ha", "b_med_medico_legal",
]

_CYCLE_FIELDS = [
    "bx_dep_severity", "bx_anx_severity", "bx_stress_severity", "bx_ptsd_mechanism",
]

_INPUT_FIELDS = [
    "bi_movement_region", "bi_strength_other", "bi_deep_other", "bi_over_other",
    "bi_nerve_region",
]

_TEXT_FIELDS = [
    "bi_red_flag_detail", "bi_substance_detail",
    "custom_1_barrier", "custom_1_strategy",
    "custom_2_barrier", "custom_2_strategy",
]

# Barriers used for is_complete (any reviewed = section is started)
_MAIN_BARRIERS = [
    "b_noci_disease", "b_noci_pacing", "b_noci_inflammatory", "b_noci_deconditioning",
    "b_noci_movement", "b_noci_gait", "b_noci_strength", "b_noci_deep_muscle",
    "b_noci_overactivity", "b_noci_nerve_mech", "b_noci_diet",
    "b_neuro_confirmed", "b_neuro_unconfirmed",
    "b_nocip_moderate", "b_nocip_crps", "b_nocip_fnd",
    "b_psych_depression", "b_psych_anxiety", "b_psych_stress",
    "b_psych_catastrophising", "b_psych_self_efficacy", "b_psych_unhelpful_beliefs",
    "b_psych_ptsd", "b_psych_readiness",
    "b_sleep_disturbed",
    "b_social_home", "b_social_rtw",
    "b_med_red_flag", "b_med_substance", "b_med_as", "b_med_aaa",
    "b_med_vascular", "b_med_cervical_ha", "b_med_medico_legal",
]


# ---------------------------------------------------------------------------
# BarriersSection
# ---------------------------------------------------------------------------

class BarriersSection(BaseSection):
    """Barriers to Recovery & Treatment Plan section (core/07)."""

    DEFAULT_CSS = """
    BarriersSection {
        width: 100%;
        height: auto;
        padding: 0 1;
    }

    .section_title  { text-style: bold; margin-bottom: 0; }
    .reference_note { color: $text-muted; margin-bottom: 0; }

    Label    { margin-bottom: 0; }
    Input    { height: auto; min-height: 1; margin-bottom: 0; }
    TextArea { height: auto; min-height: 2; margin-bottom: 0; }

    /* All flag/check buttons compact — width auto so they pack side-by-side */
    CheckButton { width: auto; height: auto; min-width: 16; margin: 0 1 1 0; }

    /* Horizontal rows */
    .btn_row  { height: auto; width: 100%; margin-bottom: 0; }
    .sub_row  { height: auto; width: 100%; margin-left: 4; margin-bottom: 0; }

    /* DASS compact rows */
    .dass_row  { layout: horizontal; height: auto; width: 100%; margin-bottom: 0; }
    .dass_flag { width: 16; }

    .xref_badge {
        width: 100%; height: auto; padding: 0 1;
        margin-bottom: 0; color: $accent; background: $accent 12%;
    }
    .xref_badge_urgent {
        width: 100%; height: auto; padding: 0 1;
        margin-bottom: 0; color: $warning; background: $warning 20%;
        text-style: bold;
    }
    """

    # ------------------------------------------------------------------
    # compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:  # noqa: C901
        yield Label("08 Barriers to Recovery", classes="section_title")

        # ── Physical / Nociceptive ─────────────────────────────
        yield Label("— Physical / Nociceptive Barriers —", classes="subsection_header", id="br_physical")
        yield Static("", id="xref_br_noci", classes="xref_badge")

        yield FlagButton("Significant disease / pathology / physical factors — nociceptive", id="b_noci_disease")
        with Horizontal(classes="btn_row"):
            yield FlagButton("Significant pacing issues — boom-bust pattern", id="b_noci_pacing")
            yield FlagButton("Moderate severity inflammatory features", id="b_noci_inflammatory")
        with Horizontal(classes="btn_row"):
            yield FlagButton("Deconditioning (>50% activity reduction >3 months)", id="b_noci_deconditioning")
            yield FlagButton("Relevant diet and / or weight issues", id="b_noci_diet")

        yield FlagButton("Significant regional reduction in passive movement / resistance", id="b_noci_movement")
        yield Input(id="bi_movement_region", placeholder="region or level")

        yield FlagButton("Asymmetrical gait — moderate severity", id="b_noci_gait")

        yield FlagButton("Significant regional strength deficits", id="b_noci_strength")
        with Horizontal(classes="sub_row"):
            yield FlagButton("Gluteus maximus", id="bx_strength_glute_max")
            yield FlagButton("Gluteus medius / minimus", id="bx_strength_glute_med")
            yield FlagButton("Iliopsoas", id="bx_strength_iliopsoas")
            yield FlagButton("Quadriceps", id="bx_strength_quads")
        yield Input(id="bi_strength_other", placeholder="other muscle(s)")

        yield FlagButton("Reduced functional activation — deep / local / postural muscles", id="b_noci_deep_muscle")
        with Horizontal(classes="sub_row"):
            yield FlagButton("Lumbar multifidus", id="bx_deep_multifidus")
            yield FlagButton("Transversus abdominis", id="bx_deep_ta")
            yield FlagButton("Thoracic erector spinae", id="bx_deep_erector")
        yield Input(id="bi_deep_other", placeholder="other muscle(s)")

        yield FlagButton("Significant overactivity of muscles", id="b_noci_overactivity")
        with Horizontal(classes="sub_row"):
            yield FlagButton("Erector spinae", id="bx_over_erector")
            yield FlagButton("Quadratus lumborum", id="bx_over_ql")
            yield FlagButton("Rectus abdominis", id="bx_over_ra")
            yield FlagButton("External obliques", id="bx_over_obliques")
        with Horizontal(classes="sub_row"):
            yield FlagButton("Piriformis", id="bx_over_piriformis")
            yield FlagButton("Iliopsoas", id="bx_over_iliopsoas")
            yield FlagButton("Hamstrings", id="bx_over_hamstrings")
            yield FlagButton("Short hip adductors", id="bx_over_adductors")
        yield Input(id="bi_over_other", placeholder="other muscle(s)")

        yield FlagButton("Moderately increased nerve mechanosensitivity", id="b_noci_nerve_mech")
        yield Input(id="bi_nerve_region", placeholder="nerve / region")

        # ── Neuropathic ────────────────────────────────────────
        yield Label("— Neuropathic Barriers —", classes="subsection_header", id="br_neuro")
        yield Static("", id="xref_br_neuro", classes="xref_badge")
        with Horizontal(classes="btn_row"):
            yield FlagButton("Moderate neuropathic pain — confirmed nerve injury on investigations", id="b_neuro_confirmed")
            yield FlagButton("Moderate neuropathic pain — without confirmed nerve injury", id="b_neuro_unconfirmed")

        # ── Nociplastic ────────────────────────────────────────
        yield Label("— Nociplastic / Central Sensitisation Barriers —", classes="subsection_header", id="br_nocip")
        yield Static("", id="xref_br_nocip", classes="xref_badge")
        with Horizontal(classes="btn_row"):
            yield FlagButton("Moderate nociplastic pain including central sensitisation", id="b_nocip_moderate")
            yield FlagButton("Confirmed CRPS (Budapest criteria)", id="b_nocip_crps")
            yield FlagButton("Functional neurological disorder", id="b_nocip_fnd")

        # ── Psychological ──────────────────────────────────────
        yield Label("— Psychological Barriers —", classes="subsection_header", id="br_psych")

        yield Static("", id="xref_br_depression", classes="xref_badge")
        yield Static("", id="xref_br_anxiety",    classes="xref_badge")
        yield Static("", id="xref_br_stress",     classes="xref_badge")
        with Horizontal(classes="dass_row"):
            yield FlagButton("Depression", id="b_psych_depression", classes="dass_flag")
            yield CycleField("bx_dep_severity", _DASS_SEVERITY_OPTIONS)
            yield CheckButton("Psychiatry referral", id="bx_dep_psychiatry")
        with Horizontal(classes="dass_row"):
            yield FlagButton("Anxiety", id="b_psych_anxiety", classes="dass_flag")
            yield CycleField("bx_anx_severity", _DASS_SEVERITY_OPTIONS)
            yield CheckButton("Psychiatry referral", id="bx_anx_psychiatry")
        with Horizontal(classes="dass_row"):
            yield FlagButton("Stress", id="b_psych_stress", classes="dass_flag")
            yield CycleField("bx_stress_severity", _DASS_SEVERITY_OPTIONS)
            yield CheckButton("Psychiatry referral", id="bx_stress_psychiatry")

        with Horizontal(classes="btn_row"):
            yield FlagButton("Moderate pain catastrophising (PCS)", id="b_psych_catastrophising")
            yield FlagButton("Reduced pain self-efficacy (PSEQ)", id="b_psych_self_efficacy")
        yield Static("", id="xref_br_catastrophising", classes="xref_badge")
        yield Static("", id="xref_br_self_efficacy", classes="xref_badge")

        yield FlagButton("Moderate unhelpful beliefs impacting pain management", id="b_psych_unhelpful_beliefs")
        with Horizontal(classes="sub_row"):
            yield FlagButton("Unrealistic recovery expectations", id="bx_belief_expectations")
            yield FlagButton("Strong symptom focus", id="bx_belief_symptom_focus")
            yield FlagButton("Strong cure focus", id="bx_belief_cure_focus")
            yield FlagButton("Desire for further treatment / investigations", id="bx_belief_further_tx")

        yield FlagButton("PTSD-type symptoms (PCL-5)", id="b_psych_ptsd")
        yield Static("", id="xref_br_ptsd", classes="xref_badge_urgent")
        yield Label("Mechanism:")
        yield CycleField("bx_ptsd_mechanism", _PTSD_MECHANISM_OPTIONS)
        yield CheckButton("Psychiatry referral", id="bx_ptsd_psychiatry")

        yield FlagButton("Unclear readiness for change", id="b_psych_readiness")

        # ── Sleep & Social ─────────────────────────────────────
        yield Label("— Sleep & Social / Contextual Barriers —", classes="subsection_header", id="br_sleep")

        yield FlagButton("Moderately disturbed sleep due to pain and / or rumination", id="b_sleep_disturbed")
        yield Static("", id="xref_br_sleep", classes="xref_badge")

        yield FlagButton("Moderate home / social barriers", id="b_social_home")
        with Horizontal(classes="sub_row"):
            yield FlagButton("Reduced family support", id="bx_soc_family_support")
            yield FlagButton("Reduced social support", id="bx_soc_social_support")
            yield FlagButton("Relationship issues (immediate family)", id="bx_soc_relationship")
        with Horizontal(classes="sub_row"):
            yield FlagButton("Personal relationship issues", id="bx_soc_personal_rel")
            yield FlagButton("Financial difficulties", id="bx_soc_financial")
            yield FlagButton("Residential instability", id="bx_soc_residential")
            yield FlagButton("Distance from program location", id="bx_soc_distance")

        yield FlagButton("Moderate return-to-work barriers — physical and psychosocial", id="b_social_rtw")

        # ── Medical ────────────────────────────────────────────
        yield Label("— Medical / Systemic Barriers —", classes="subsection_header", id="br_medical")
        yield Static("", id="xref_br_red_flag", classes="xref_badge")

        yield FlagButton("Red flag — requires further investigation", id="b_med_red_flag")
        yield TextArea(id="bi_red_flag_detail", language="plain")

        yield FlagButton("Significant maladaptive use of prescription / non-prescription drugs / alcohol", id="b_med_substance")
        yield Static("", id="xref_br_substance", classes="xref_badge")
        yield TextArea(id="bi_substance_detail", language="plain")

        with Horizontal(classes="btn_row"):
            yield FlagButton("Possible ankylosing spondylitis", id="b_med_as")
            yield FlagButton("Possible lumbar symptoms due to AAA", id="b_med_aaa")
            yield FlagButton("Possible vascular claudication", id="b_med_vascular")
        with Horizontal(classes="btn_row"):
            yield FlagButton("Moderate severity cervical headache", id="b_med_cervical_ha")
            yield FlagButton("Medico-legal / claim issues", id="b_med_medico_legal")

        # ── Custom Barriers ────────────────────────────────────
        yield Label("— Custom Barriers —", classes="subsection_header", id="br_custom")
        yield Label("1. Barrier:")
        yield TextArea(id="custom_1_barrier", language="plain")
        yield Label("   Strategy:")
        yield TextArea(id="custom_1_strategy", language="plain")
        yield Label("2. Barrier:")
        yield TextArea(id="custom_2_barrier", language="plain")
        yield Label("   Strategy:")
        yield TextArea(id="custom_2_strategy", language="plain")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _jump_to(self, anchor_id: str) -> None:
        try:
            target = self.query_one(f"#{anchor_id}")
            self.app.query_one("#section_content", ScrollableContainer).scroll_to_widget(target, top=True, animate=False)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Cross-reference badges
    # ------------------------------------------------------------------

    def update_cross_refs(self, assessment: dict | None = None) -> None:
        """Update inline badges from sibling section data."""
        if assessment is None:
            if not self.session_file:
                return
            try:
                data = json.loads(Path(self.session_file).read_text())
                assessment = data.get("assessment", {})
            except Exception:
                return

        def _sec(key):
            v = assessment.get(key)
            return v if isinstance(v, dict) else {}

        med  = _sec("medical")
        subj = _sec("subjective")
        pc   = _sec("pain_classification")
        om   = _sec("outcome_measures")
        dx   = _sec("diagnosis")

        def _set(badge_id: str, lines: list[str], urgent: bool = False) -> None:
            try:
                w = self.query_one(f"#{badge_id}", Static)
                if lines:
                    w.update("  ".join(f"◀ {l}" for l in lines))
                    w.display = True
                else:
                    w.display = False
            except Exception:
                pass

        # Nociceptive — dominant pain type
        lines = []
        dominant = pc.get("summary_dominant")
        if dominant:
            lines.append(f"PC: dominant type = {dominant}")
        mech = dx.get("mechanism")
        if mech:
            lines.append(f"Dx: mechanism = {mech}")
        _set("xref_br_noci", lines)

        # Neuropathic
        lines = []
        if med.get("rf_bilateral_paraesthesia") is True:
            lines.append("Med: bilateral paraesthesia (red flag +ve)")
        if med.get("rf_saddle_anaesthesia") is True:
            lines.append("Med: saddle anaesthesia (red flag +ve)")
        if dominant:
            lines.append(f"PC: dominant type = {dominant}")
        _set("xref_br_neuro", lines)

        # Nociplastic
        lines = []
        if dominant:
            lines.append(f"PC: dominant type = {dominant}")
        if dx.get("primary_subtype") == "CRPS type I":
            lines.append("Dx: CRPS type I selected")
        _set("xref_br_nocip", lines)

        # Depression
        lines = []
        score = om.get("dass_dep_score", "").strip()
        interp = om.get("dass_dep_interp")
        if score:
            lines.append(f"OM: DASS depression score = {score}" + (f" ({interp})" if interp else ""))
        _set("xref_br_depression", lines)

        # Anxiety
        lines = []
        score = om.get("dass_anx_score", "").strip()
        interp = om.get("dass_anx_interp")
        if score:
            lines.append(f"OM: DASS anxiety score = {score}" + (f" ({interp})" if interp else ""))
        _set("xref_br_anxiety", lines)

        # Stress
        lines = []
        score = om.get("dass_str_score", "").strip()
        interp = om.get("dass_str_interp")
        if score:
            lines.append(f"OM: DASS stress score = {score}" + (f" ({interp})" if interp else ""))
        _set("xref_br_stress", lines)

        # Catastrophising
        lines = []
        score = om.get("pcs_total_score", "").strip()
        risk = om.get("pcs_total_risk")
        if score:
            lines.append(f"OM: PCS total = {score}" + (f" ({risk})" if risk else ""))
        _set("xref_br_catastrophising", lines)

        # Self-efficacy
        lines = []
        score = om.get("pseq_score", "").strip()
        if score:
            lines.append(f"OM: PSEQ score = {score}")
        _set("xref_br_self_efficacy", lines)

        # PTSD (urgent)
        lines = []
        score = om.get("pcl5_score", "").strip()
        interp = om.get("pcl5_interp")
        if score:
            lines.append(f"OM: PCL-5 score = {score}" + (f" ({interp})" if interp else ""))
        if subj.get("self_harm_risk") is True:
            lines.append("Subj: self-harm risk flagged")
        _set("xref_br_ptsd", lines, urgent=True)

        # Sleep
        lines = []
        score = om.get("isi_score", "").strip()
        interp = om.get("isi_interp")
        if score:
            lines.append(f"OM: ISI score = {score}" + (f" ({interp})" if interp else ""))
        if subj.get("sleep_difficulty") is True:
            lines.append("Subj: sleep difficulty reported")
        _set("xref_br_sleep", lines)

        # Red flag
        rf_fields = [
            ("rf_saddle_anaesthesia",    "saddle anaesthesia"),
            ("rf_bladder_disturbance",   "bladder disturbance"),
            ("rf_bowel_disturbance",     "bowel disturbance"),
            ("rf_bilateral_paraesthesia","bilateral paraesthesia"),
            ("rf_gait_disturbance",      "gait disturbance"),
        ]
        lines = [f"Med: {label} +ve" for fid, label in rf_fields if med.get(fid) is True]
        _set("xref_br_red_flag", lines)

        # Substance
        lines = []
        if med.get("comorbid_drug_alcohol") is True:
            lines.append("Med: drug / alcohol comorbidity flagged")
        _set("xref_br_substance", lines)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def collect(self) -> dict:
        data = {}
        for fid in _TOGGLE_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", CheckButton).value
            except Exception:
                data[fid] = None
        for fid in _CYCLE_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", CycleField).get_value()
            except Exception:
                data[fid] = None
        for fid in _INPUT_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", Input).value
            except Exception:
                data[fid] = ""
        for fid in _TEXT_FIELDS:
            try:
                data[fid] = self.query_one(f"#{fid}", TextArea).text
            except Exception:
                data[fid] = ""
        return data

    def load(self, data: dict) -> None:
        self._loading = True
        try:
            br = data if isinstance(data, dict) else {}
            for fid in _TOGGLE_FIELDS:
                try:
                    self.query_one(f"#{fid}", CheckButton).set_value(br.get(fid))
                except Exception:
                    pass
            for fid in _CYCLE_FIELDS:
                try:
                    self.query_one(f"#{fid}", CycleField).set_value(br.get(fid))
                except Exception:
                    pass
            for fid in _INPUT_FIELDS:
                try:
                    self.query_one(f"#{fid}", Input).value = br.get(fid, "")
                except Exception:
                    pass
            for fid in _TEXT_FIELDS:
                try:
                    self.query_one(f"#{fid}", TextArea).text = br.get(fid, "")
                except Exception:
                    pass
        finally:
            self._loading = False
            self.update_cross_refs()

    def is_complete(self) -> bool:
        """Complete when at least one main barrier has been explicitly reviewed (True or False)."""
        for fid in _MAIN_BARRIERS:
            try:
                if self.query_one(f"#{fid}", CheckButton).value is not None:
                    return True
            except Exception:
                pass
        return False

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    @on(CheckButton.Changed)
    @on(CycleField.Changed)
    @on(Input.Changed, selector="Input")
    @on(TextArea.Changed, selector="TextArea")
    def _on_field_changed(self) -> None:
        if self._loading:
            return
        self.post_message(self.FieldChanged())

    class FieldChanged(Message):
        pass
