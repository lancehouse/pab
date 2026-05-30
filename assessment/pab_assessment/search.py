"""Search index builder and fuzzy scorer for the jump-search (ctrl+.) feature."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from textual.app import App

# ---------------------------------------------------------------------------
# Data type
# ---------------------------------------------------------------------------

@dataclass
class SearchEntry:
    display: str         # shown in the dropdown row
    match_text: str      # text fuzzy-matched against the query
    section_id: str      # section to navigate to
    anchor_id: str | None   # subsection anchor ID (or None)
    widget_id: str | None   # specific widget to focus (or None)
    kind: Literal["section", "subsection", "field", "content"]


# ---------------------------------------------------------------------------
# Static tables
# ---------------------------------------------------------------------------

_SECTION_SHORT: dict[str, str] = {
    "01_consent":             "Consent",
    "02_subjective":          "Subj",
    "03_medical":             "Medical",
    "04_pain_classification": "Pain",
    "05_outcome_measures":    "Outcomes",
    "06_diagnosis":           "Diagnosis",
    "07_barriers":            "Barriers",
    "08_rx_plan":             "Rx Plan",
    "scratchpad":             "Notes",
    "obj:01_general":         "Obj:General",
    "obj:02_active":          "Obj:Active",
    "obj:03_passive":         "Obj:Passive",
    "obj:04_neurological":    "Obj:Neuro",
    "obj:05_sensory":         "Obj:Sensory",
    "obj:06_muscle":          "Obj:Muscle",
    "obj:07_functional":      "Obj:Functional",
    "obj:08_special":         "Obj:Special",
}

_SECTION_LABELS: dict[str, str] = {
    "01_consent":             "01 Consent",
    "02_subjective":          "02 Subjective",
    "03_medical":             "03 Medical",
    "04_pain_classification": "04 Pain Classification",
    "05_outcome_measures":    "05 Outcome Measures",
    "06_diagnosis":           "06 Diagnosis",
    "07_barriers":            "07 Barriers",
    "08_rx_plan":             "08 Rx & Plan",
    "scratchpad":             "Notes / Scratchpad",
    "obj:01_general":         "Obj 01 General",
    "obj:02_active":          "Obj 02 Active Movement",
    "obj:03_passive":         "Obj 03 Passive Movement",
    "obj:04_neurological":    "Obj 04 Neurological",
    "obj:05_sensory":         "Obj 05 Sensory",
    "obj:06_muscle":          "Obj 06 Muscle Testing",
    "obj:07_functional":      "Obj 07 Functional",
    "obj:08_special":         "Obj 08 Special Tests",
}

# (section_id, anchor_id, display_label)
_SUBSECTIONS: list[tuple[str, str, str]] = [
    # 02 Subjective
    ("02_subjective", "subj_symptoms",     "Body Chart Symptoms"),
    ("02_subjective", "subj_history",      "History"),
    ("02_subjective", "subj_flareups",     "Flare-ups"),
    ("02_subjective", "subj_management",   "Self-Management"),
    ("02_subjective", "subj_activity",     "Activity & Exercise"),
    ("02_subjective", "subj_work",         "Work"),
    ("02_subjective", "subj_sleep",        "Sleep"),
    ("02_subjective", "subj_24hr",         "24Hr Pattern"),
    ("02_subjective", "subj_psychosocial", "Psychosocial"),
    ("02_subjective", "subj_goals",        "SMART Goals"),
    ("02_subjective", "subj_suicide",      "Suicide / Self-Harm Risk"),
    # 03 Medical
    ("03_medical", "med_comorbidities",    "Comorbidities / PMH"),
    ("03_medical", "med_cardiovascular",   "Cardiovascular Risk"),
    ("03_medical", "med_red_flags",        "Red Flags"),
    ("03_medical", "rf_malignancy",        "Red Flag: Malignancy"),
    ("03_medical", "rf_fracture",          "Red Flag: Fracture"),
    ("03_medical", "rf_infection",         "Red Flag: Infection"),
    ("03_medical", "rf_cauda_equina",      "Red Flag: Cauda Equina Compression"),
    ("03_medical", "rf_spinal_cord",       "Red Flag: Spinal Cord Compression"),
    ("03_medical", "rf_umn_signs",         "Red Flag: Upper Motor Neurone Signs"),
    ("03_medical", "med_differential",     "Differential Diagnosis"),
    ("03_medical", "diff_as",              "Differential: Ankylosing Spondylitis"),
    ("03_medical", "diff_aaa",             "Differential: Aortic Aneurysm"),
    ("03_medical", "diff_vc",              "Differential: Vascular Claudication"),
    ("03_medical", "med_medications",      "Medications"),
    # 04 Pain Classification
    ("04_pain_classification", "pc_inflammatory", "Inflammatory"),
    ("04_pain_classification", "pc_nociceptive",  "Nociceptive"),
    ("04_pain_classification", "pc_neuropathic",  "Neuropathic"),
    ("04_pain_classification", "pc_nociplastic",  "Nociplastic"),
    ("04_pain_classification", "pc_central",      "Central Sensitisation"),
    ("04_pain_classification", "pc_summary",      "Pain Classification Summary"),
    # 05 Outcome Measures
    ("05_outcome_measures", "om_psfs",       "PSFS"),
    ("05_outcome_measures", "om_bpi",        "BPI"),
    ("05_outcome_measures", "om_dass",       "DASS"),
    ("05_outcome_measures", "om_pcs",        "PCS"),
    ("05_outcome_measures", "om_pseq",       "PSEQ / PCL-5"),
    ("05_outcome_measures", "om_sleep",      "ISI / Sleep"),
    ("05_outcome_measures", "om_additional", "Additional Measures"),
    ("05_outcome_measures", "om_hypothesis", "Outcome Hypothesis"),
    # 06 Diagnosis
    ("06_diagnosis", "dx_overview",    "Overview"),
    ("06_diagnosis", "dx_primary",     "Primary Diagnosis"),
    ("06_diagnosis", "dx_surgical",    "Post-Surgical"),
    ("06_diagnosis", "dx_traumatic",   "Post-Traumatic"),
    ("06_diagnosis", "dx_msk",         "MSK"),
    ("06_diagnosis", "dx_neuropathic", "Neuropathic Diagnosis"),
    ("06_diagnosis", "dx_mixed",       "Mixed"),
    # 07 Barriers
    ("07_barriers", "br_physical",     "Physical Barriers"),
    ("07_barriers", "br_neuro",        "Neurological Barriers"),
    ("07_barriers", "br_nocip",        "Nociplastic Barriers"),
    ("07_barriers", "br_psych",        "Psychological Barriers"),
    ("07_barriers", "br_sleep",        "Sleep & Social Barriers"),
    ("07_barriers", "br_medical",      "Medical Barriers"),
    ("07_barriers", "br_custom",       "Custom Barriers"),
    # 08 Rx Plan
    ("08_rx_plan", "rp_treatment",     "Treatment Plan"),
    ("08_rx_plan", "rp_session1",      "Session 1"),
    ("08_rx_plan", "rp_day1",          "Day 1 Programme"),
    ("08_rx_plan", "rp_followup",      "Follow-Up"),
    # Objective subsections
    ("obj:01_general", "go_physical",            "General: Physical"),
    ("obj:01_general", "go_posture",             "General: Posture"),
    ("obj:01_general", "go_functional_movement", "General: Functional Movement"),
    ("obj:02_active",  "am_lumbar",              "Active: Lumbar ROM"),
    ("obj:02_active",  "am_thoracic",            "Active: Thoracic ROM"),
    ("obj:02_active",  "am_cx_lumbar",           "Active: Cervical ROM"),
    ("obj:02_active",  "am_shoulder",            "Active: Shoulder ROM"),
    ("obj:03_passive", "pm_overpressure",        "Passive: Overpressure"),
    ("obj:03_passive", "pm_paivms",              "Passive: PAIVMs"),
    ("obj:03_passive", "pm_cx_overpressure",     "Passive: Cervical OP"),
    ("obj:03_passive", "pm_cx_paivms",           "Passive: Cervical PAIVMs"),
    ("obj:03_passive", "pm_sh_overpressure",     "Passive: Shoulder OP"),
    ("obj:03_passive", "pm_sh_accessory",        "Passive: GH Accessory Glides"),
    ("obj:03_passive", "pm_sh_acsc",             "Passive: AC/SC Joint"),
    ("obj:04_neurological", "nr_reflexes",       "Neuro: Reflexes"),
    ("obj:04_neurological", "nr_myotomes",       "Neuro: Myotomes"),
    ("obj:04_neurological", "nr_dermatomes",     "Neuro: Dermatomes"),
    ("obj:04_neurological", "nr_neurodynamics",  "Neuro: Neurodynamics"),
    ("obj:04_neurological", "nr_umn",            "Neuro: UMN Signs"),
    ("obj:05_sensory",  "sn_hyposensitivity",    "Sensory: Hyposensitivity"),
    ("obj:05_sensory",  "sn_hypersensitivity",   "Sensory: Hypersensitivity"),
    ("obj:06_muscle",   "ml_length",             "Muscle: Length"),
    ("obj:06_muscle",   "ml_activation",         "Muscle: Activation"),
    ("obj:06_muscle",   "ml_strength_trunk",     "Muscle: Strength (Trunk)"),
    ("obj:06_muscle",   "ml_strength_hip",       "Muscle: Strength (Hip)"),
    ("obj:06_muscle",   "ml_sij",                "Muscle: SIJ Provocation"),
    ("obj:06_muscle",   "ml_cx_neck",            "Muscle: Neck Strength"),
    ("obj:06_muscle",   "ml_sh_length",          "Muscle: Shoulder Length"),
    ("obj:06_muscle",   "ml_sh_activation",      "Muscle: Shoulder Activation"),
    ("obj:06_muscle",   "ml_sh_strength",        "Muscle: Shoulder Strength"),
    ("obj:07_functional", "fn_movement",         "Functional: Movement"),
    ("obj:07_functional", "fn_balance",          "Functional: Balance"),
    ("obj:07_functional", "fn_timed",            "Functional: Timed Capability"),
    ("obj:08_special",  "st_cervical",           "Special Tests: Cervical"),
    ("obj:08_special",  "st_lumbar",             "Special Tests: Lumbar"),
    ("obj:08_special",  "st_shoulder",           "Special Tests: Shoulder"),
]

# Pre-built lookup: (section_id, anchor_id) -> subsection label
_SUBSECTION_LABEL: dict[tuple[str, str], str] = {
    (s, a): lbl for s, a, lbl in _SUBSECTIONS
}

# widget_id -> (section_id, anchor_id_or_None, human_name)
_FIELD_LABELS: dict[str, tuple[str, str | None, str]] = {
    # 01 Consent
    "preferred_name_input":       ("01_consent", None, "Preferred name"),
    "patient_expectations":       ("01_consent", None, "Patient expectations"),
    "reason_for_attending":       ("01_consent", None, "Reason for attending"),
    "cause_understanding_detail": ("01_consent", None, "Cause understanding"),
    "prognosis_expectations":     ("01_consent", None, "Prognosis expectations"),
    "treatment_preference":       ("01_consent", None, "Treatment preference"),
    # 02 Subjective — History
    "onset":              ("02_subjective", "subj_history",    "Onset"),
    "duration":           ("02_subjective", "subj_history",    "Duration"),
    "context_at_onset":   ("02_subjective", "subj_history",    "Context at onset"),
    "previous_episodes":  ("02_subjective", "subj_history",    "Previous episodes"),
    "previous_treatment": ("02_subjective", "subj_history",    "Previous treatment"),
    # 02 Subjective — Flare-ups
    "flareup_triggers":       ("02_subjective", "subj_flareups", "Flare-up triggers"),
    "flareup_predictability": ("02_subjective", "subj_flareups", "Flare-up predictability"),
    "flareup_duration":       ("02_subjective", "subj_flareups", "Flare-up duration"),
    # 02 Subjective — Management
    "pain_control_score":    ("02_subjective", "subj_management", "Pain control score"),
    "flareup_prevention":    ("02_subjective", "subj_management", "Flare-up prevention"),
    "management_strategies": ("02_subjective", "subj_management", "Management strategies"),
    "confidence_score":      ("02_subjective", "subj_management", "Confidence score"),
    # 02 Subjective — Activity
    "pre_activity_level":     ("02_subjective", "subj_activity", "Pre-injury activity"),
    "current_activity_level": ("02_subjective", "subj_activity", "Current activity"),
    "exercise_type":          ("02_subjective", "subj_activity", "Exercise type"),
    "exercise_dose":          ("02_subjective", "subj_activity", "Exercise dose"),
    "exercise_response":      ("02_subjective", "subj_activity", "Exercise response"),
    # 02 Subjective — Work
    "pre_injury_role":    ("02_subjective", "subj_work", "Pre-injury role"),
    "pre_injury_hours":   ("02_subjective", "subj_work", "Pre-injury hours"),
    "pre_injury_duties":  ("02_subjective", "subj_work", "Pre-injury duties"),
    "current_work_status":("02_subjective", "subj_work", "Current work status"),
    "current_hours":      ("02_subjective", "subj_work", "Current hours"),
    "current_duties":     ("02_subjective", "subj_work", "Current duties"),
    # 02 Subjective — Sleep (YAML pilot)
    "sleep_overall_rating":    ("02_subjective", "subj_sleep", "Sleep quality rating"),
    "sleep_feels_rested":      ("02_subjective", "subj_sleep", "Feels rested"),
    "sleep_time_to_bed":       ("02_subjective", "subj_sleep", "Time to bed"),
    "sleep_time_attempt":      ("02_subjective", "subj_sleep", "Time attempting sleep"),
    "sleep_onset_time":        ("02_subjective", "subj_sleep", "Time to actual sleep (SOL)"),
    "sleep_waso_clock":        ("02_subjective", "subj_sleep", "Wake after sleep onset — time"),
    "sleep_waso_duration":     ("02_subjective", "subj_sleep", "Wake after sleep onset — length"),
    "sleep_awake_in_bed":      ("02_subjective", "subj_sleep", "Time awake in bed"),
    "sleep_awake_out_bed":     ("02_subjective", "subj_sleep", "Time awake out of bed"),
    "sleep_final_wakeup":      ("02_subjective", "subj_sleep", "Final wake up"),
    "sleep_time_out_of_bed":   ("02_subjective", "subj_sleep", "Time out of bed"),
    "sleep_postural_factors":  ("02_subjective", "subj_sleep", "Sleep postural factors"),
    "sleep_environment_quality":("02_subjective","subj_sleep", "Sleep environment quality"),
    "sleep_daytime_naps":      ("02_subjective", "subj_sleep", "Daytime naps"),
    "sleep_overall_comments":  ("02_subjective", "subj_sleep", "Sleep overall comments"),
    # 02 Subjective — 24hr
    "hr24_am":               ("02_subjective", "subj_24hr", "AM pattern"),
    "hr24_day":              ("02_subjective", "subj_24hr", "Daytime pattern"),
    "hr24_pm":               ("02_subjective", "subj_24hr", "PM pattern"),
    "hr24_nocte":            ("02_subjective", "subj_24hr", "Night (nocte) pattern"),
    "energy_levels":         ("02_subjective", "subj_24hr", "Energy levels"),
    "daily_pattern_comments":("02_subjective", "subj_24hr", "Daily pattern comments"),
    # 02 Subjective — Psychosocial
    "mood_text":               ("02_subjective", "subj_psychosocial", "Mood (text)"),
    "social_situation":        ("02_subjective", "subj_psychosocial", "Social situation"),
    "financial_status":        ("02_subjective", "subj_psychosocial", "Financial status"),
    "cultural_considerations": ("02_subjective", "subj_psychosocial", "Cultural considerations"),
    "psychological_distress":  ("02_subjective", "subj_psychosocial", "Psychological distress"),
    "screening_tool":          ("02_subjective", "subj_psychosocial", "Screening tool"),
    # 02 Subjective — Suicide risk
    "harm_plan":   ("02_subjective", "subj_suicide", "Self-harm plan"),
    "harm_means":  ("02_subjective", "subj_suicide", "Self-harm means"),
    "harm_intent": ("02_subjective", "subj_suicide", "Self-harm intent"),
    "harm_action": ("02_subjective", "subj_suicide", "Self-harm action taken"),
    # 03 Medical
    "previous_injuries":     ("03_medical", "med_comorbidities",  "Previous injuries"),
    "comorbid_other":        ("03_medical", "med_comorbidities",  "Other comorbidities"),
    "rf_malignancy_comment": ("03_medical", "med_red_flags",      "Malignancy comment"),
    "rf_fracture_comment":   ("03_medical", "med_red_flags",      "Fracture comment"),
    "rf_infection_comment":  ("03_medical", "med_red_flags",      "Infection comment"),
    "cauda_equina_action":   ("03_medical", "med_red_flags",      "Cauda equina action"),
    "spinal_cord_action":    ("03_medical", "med_red_flags",      "Spinal cord action"),
    "umn_interpretation":    ("03_medical", "med_red_flags",      "UMN interpretation"),
    "diff_as_action":        ("03_medical", "med_differential",   "Ankylosing spondylitis action"),
    "diff_aaa_action":       ("03_medical", "med_differential",   "AAA action"),
    "diff_vc_action":        ("03_medical", "med_differential",   "Vascular claudication action"),
    # 04 Pain Classification
    "noci_interpretation":  ("04_pain_classification", "pc_nociceptive", "Nociceptive interpretation"),
    "neuro_interpretation": ("04_pain_classification", "pc_neuropathic", "Neuropathic interpretation"),
    "nocip_interpretation": ("04_pain_classification", "pc_nociplastic", "Nociplastic interpretation"),
    "csi_score":            ("04_pain_classification", "pc_nociplastic", "CSI score"),
    "summary_contributing": ("04_pain_classification", "pc_summary",     "Contributing factors"),
    "summary_reasoning":    ("04_pain_classification", "pc_summary",     "Classification reasoning"),
    # 05 Outcome Measures
    "psfs_act_1":    ("05_outcome_measures", "om_psfs",       "PSFS activity 1"),
    "psfs_act_2":    ("05_outcome_measures", "om_psfs",       "PSFS activity 2"),
    "psfs_act_3":    ("05_outcome_measures", "om_psfs",       "PSFS activity 3"),
    "bpi_activity":  ("05_outcome_measures", "om_bpi",        "BPI: Activity"),
    "bpi_mood":      ("05_outcome_measures", "om_bpi",        "BPI: Mood"),
    "bpi_walking":   ("05_outcome_measures", "om_bpi",        "BPI: Walking"),
    "bpi_work":      ("05_outcome_measures", "om_bpi",        "BPI: Work"),
    "bpi_relations": ("05_outcome_measures", "om_bpi",        "BPI: Relations"),
    "bpi_sleep":     ("05_outcome_measures", "om_bpi",        "BPI: Sleep"),
    "bpi_enjoyment": ("05_outcome_measures", "om_bpi",        "BPI: Enjoyment"),
    "dass_dep_score": ("05_outcome_measures", "om_dass",      "DASS: Depression"),
    "dass_anx_score": ("05_outcome_measures", "om_dass",      "DASS: Anxiety"),
    "dass_str_score": ("05_outcome_measures", "om_dass",      "DASS: Stress"),
    "pcs_rum_score":  ("05_outcome_measures", "om_pcs",       "PCS: Rumination"),
    "pcs_mag_score":  ("05_outcome_measures", "om_pcs",       "PCS: Magnification"),
    "pcs_help_score": ("05_outcome_measures", "om_pcs",       "PCS: Helplessness"),
    "pcs_total_score":("05_outcome_measures", "om_pcs",       "PCS: Total"),
    "pseq_score":    ("05_outcome_measures", "om_pseq",       "PSEQ score"),
    "pseq_interp":   ("05_outcome_measures", "om_pseq",       "PSEQ interpretation"),
    "pcl5_score":    ("05_outcome_measures", "om_pseq",       "PCL-5 score"),
    "pcl5_action":   ("05_outcome_measures", "om_pseq",       "PCL-5 action"),
    "isi_score":     ("05_outcome_measures", "om_sleep",      "ISI score"),
    "pbas_score":    ("05_outcome_measures", "om_sleep",      "PBAS score"),
    "add_audit":     ("05_outcome_measures", "om_additional", "AUDIT administered"),
    "add_dudit":     ("05_outcome_measures", "om_additional", "DUDIT administered"),
    "add_epoc":      ("05_outcome_measures", "om_additional", "EPOC notes"),
    "add_other":     ("05_outcome_measures", "om_additional", "Other measures notes"),
    "plan_psfs":     ("05_outcome_measures", "om_psfs",       "Plan: PSFS"),
    "plan_bpi":      ("05_outcome_measures", "om_bpi",        "Plan: BPI"),
    "plan_dass":     ("05_outcome_measures", "om_dass",       "Plan: DASS-21"),
    "plan_pcs":      ("05_outcome_measures", "om_pcs",        "Plan: PCS"),
    "plan_pseq":     ("05_outcome_measures", "om_pseq",       "Plan: PSEQ"),
    "plan_pcl5":     ("05_outcome_measures", "om_pseq",       "Plan: PCL-5"),
    "plan_sleep":    ("05_outcome_measures", "om_sleep",      "Plan: Sleep measures"),
    "plan_additional":("05_outcome_measures","om_additional", "Plan: Additional measures"),
    # 06 Diagnosis
    "surgical_procedure": ("06_diagnosis", "dx_surgical",    "Surgical procedure"),
    "surgical_source":    ("06_diagnosis", "dx_surgical",    "Surgical source"),
    "traumatic_event":    ("06_diagnosis", "dx_traumatic",   "Traumatic event"),
    "traumatic_source":   ("06_diagnosis", "dx_traumatic",   "Traumatic source"),
    "msk_pathology":      ("06_diagnosis", "dx_msk",         "MSK pathology"),
    "msk_source":         ("06_diagnosis", "dx_msk",         "MSK source"),
    "neuro_lesion":       ("06_diagnosis", "dx_neuropathic", "Neurological lesion"),
    "mixed_reasoning":    ("06_diagnosis", "dx_mixed",       "Mixed reasoning"),
    "goal_1":             ("02_subjective", "subj_goals",     "Goal 1"),
    "goal_2":             ("02_subjective", "subj_goals",     "Goal 2"),
    "goal_3":             ("02_subjective", "subj_goals",     "Goal 3"),
    "goal_4":             ("02_subjective", "subj_goals",     "Goal 4"),
    # 07 Barriers
    "bi_movement_region": ("07_barriers", "br_physical",  "Movement region"),
    "bi_strength_other":  ("07_barriers", "br_physical",  "Other strength deficit"),
    "bi_deep_other":      ("07_barriers", "br_physical",  "Other deep stability deficit"),
    "bi_over_other":      ("07_barriers", "br_physical",  "Other overactivity"),
    "bi_nerve_region":    ("07_barriers", "br_neuro",     "Nerve region"),
    "bi_red_flag_detail": ("07_barriers", "br_medical",   "Red flag detail"),
    "bi_substance_detail":("07_barriers", "br_medical",   "Substance detail"),
    "custom_1_barrier":   ("07_barriers", "br_custom",    "Custom barrier 1"),
    "custom_1_strategy":  ("07_barriers", "br_custom",    "Custom strategy 1"),
    "custom_2_barrier":   ("07_barriers", "br_custom",    "Custom barrier 2"),
    "custom_2_strategy":  ("07_barriers", "br_custom",    "Custom strategy 2"),
    # 08 Rx Plan
    "tx_goal_orientation":("08_rx_plan", "rp_treatment",  "Goal orientation"),
    "tx_formulation":     ("08_rx_plan", "rp_treatment",  "Treatment formulation"),
    "tx_program":         ("08_rx_plan", "rp_treatment",  "Treatment program"),
    "tx_home_program":    ("08_rx_plan", "rp_treatment",  "Home program"),
    "tx_psychosocial":    ("08_rx_plan", "rp_treatment",  "Psychosocial treatment"),
    "tx_medical":         ("08_rx_plan", "rp_treatment",  "Medical treatment"),
    "tx_rtw":             ("08_rx_plan", "rp_treatment",  "Return to work plan"),
    "s1_education":       ("08_rx_plan", "rp_session1",   "Session 1: Education"),
    "s1_experiential":    ("08_rx_plan", "rp_session1",   "Session 1: Experiential"),
    "s1_confidence_nrs":  ("08_rx_plan", "rp_session1",   "Session 1: Confidence NRS"),
    "s1_hw_other":        ("08_rx_plan", "rp_session1",   "Session 1: HW other"),
    "fu_next_focus":      ("08_rx_plan", "rp_followup",   "Follow-up: Next focus"),
    "fu_monitoring":      ("08_rx_plan", "rp_followup",   "Follow-up: Monitoring"),
    "fu_om_schedule":     ("08_rx_plan", "rp_followup",   "Follow-up: OM schedule"),
    # Scratchpad
    "scratchpad_text": ("scratchpad", None, "Scratchpad notes"),
}

# Assessment sections to harvest button widgets from (objective excluded)
_ASSESSMENT_SECTION_IDS = [
    "01_consent", "02_subjective", "03_medical", "04_pain_classification",
    "05_outcome_measures", "06_diagnosis", "07_barriers", "08_rx_plan", "scratchpad",
]

# Objective special test KB fields — (widget_id, region, section_id, human_name, extra_match)
# widget_id uses st_ prefix (SpecialTestsWidget._rg_id pattern)
_OBJ_KB_FIELDS: list[tuple[str, str, str, str, str]] = [
    # ── Cervical ──────────────────────────────────────────────────────────────
    ("st_spurling_l",      "cervical", "obj:08_special", "Spurling's Left",           "foraminal compression radiculopathy arm pain"),
    ("st_spurling_r",      "cervical", "obj:08_special", "Spurling's Right",          "foraminal compression radiculopathy arm pain"),
    ("st_distraction_l",   "cervical", "obj:08_special", "Cervical Distraction L",    "radiculopathy IVF foraminal relief"),
    ("st_distraction_r",   "cervical", "obj:08_special", "Cervical Distraction R",    "radiculopathy IVF foraminal relief"),
    ("st_ulnt1_l",         "cervical", "obj:08_special", "ULNT1 Left",                "upper limb tension median nerve neurodynamic"),
    ("st_ulnt1_r",         "cervical", "obj:08_special", "ULNT1 Right",               "upper limb tension median nerve neurodynamic"),
    ("st_ulnt2a_l",        "cervical", "obj:08_special", "ULNT2a Left",               "radial nerve neurodynamic upper limb tension"),
    ("st_ulnt2a_r",        "cervical", "obj:08_special", "ULNT2a Right",              "radial nerve neurodynamic upper limb tension"),
    ("st_ulnt3_l",         "cervical", "obj:08_special", "ULNT3 Left",                "ulnar nerve neurodynamic upper limb tension"),
    ("st_ulnt3_r",         "cervical", "obj:08_special", "ULNT3 Right",               "ulnar nerve neurodynamic upper limb tension"),
    ("st_frt_l",           "cervical", "obj:08_special", "FRT Left",                  "flexion rotation test cervicogenic headache CGH C1 C2"),
    ("st_frt_r",           "cervical", "obj:08_special", "FRT Right",                 "flexion rotation test cervicogenic headache CGH"),
    ("st_sharp_purser_l",  "cervical", "obj:08_special", "Sharp-Purser L",            "upper cervical instability atlantoaxial"),
    ("st_sharp_purser_r",  "cervical", "obj:08_special", "Sharp-Purser R",            "upper cervical instability atlantoaxial"),
    ("st_ant_shear_l",     "cervical", "obj:08_special", "Anterior Shear L",          "upper cervical instability transverse ligament"),
    ("st_ant_shear_r",     "cervical", "obj:08_special", "Anterior Shear R",          "upper cervical instability transverse ligament"),
    ("st_alar_sf_l",       "cervical", "obj:08_special", "Alar Ligament SF L",        "upper cervical instability alar"),
    ("st_alar_sf_r",       "cervical", "obj:08_special", "Alar Ligament SF R",        "upper cervical instability alar"),
    ("st_lat_trans_l",     "cervical", "obj:08_special", "Lateral Translation L",     "upper cervical instability lateral stability"),
    ("st_lat_trans_r",     "cervical", "obj:08_special", "Lateral Translation R",     "upper cervical instability lateral stability"),
    ("st_vbi_sus_rot_l",   "cervical", "obj:08_special", "VBI Sustained Rotation L",  "vertebrobasilar insufficiency pre-manipulation screen"),
    ("st_vbi_sus_rot_r",   "cervical", "obj:08_special", "VBI Sustained Rotation R",  "vertebrobasilar insufficiency pre-manipulation screen"),
    ("st_hoffman_l",       "cervical", "obj:08_special", "Hoffman's Left",            "myelopathy UMN upper motor neuron corticospinal"),
    ("st_hoffman_r",       "cervical", "obj:08_special", "Hoffman's Right",           "myelopathy UMN upper motor neuron corticospinal"),
    # ── Lumbar ────────────────────────────────────────────────────────────────
    ("st_slr_l",         "lumbar",   "obj:08_special", "SLR Left",                  "straight leg raise sciatic radiculopathy disc herniation"),
    ("st_slr_r",         "lumbar",   "obj:08_special", "SLR Right",                 "straight leg raise sciatic radiculopathy disc herniation"),
    ("st_slump_l",       "lumbar",   "obj:08_special", "Slump Left",                "neurodynamic sciatic lumbar radiculopathy"),
    ("st_slump_r",       "lumbar",   "obj:08_special", "Slump Right",               "neurodynamic sciatic lumbar radiculopathy"),
    ("st_femoral_l",     "lumbar",   "obj:08_special", "Femoral Stretch Left",      "femoral nerve L2 L3 L4 radiculopathy"),
    ("st_femoral_r",     "lumbar",   "obj:08_special", "Femoral Stretch Right",     "femoral nerve L2 L3 L4 radiculopathy"),
    ("st_faber_l",       "lumbar",   "obj:08_special", "FABER Left",                "Patrick hip SIJ sacroiliac joint"),
    ("st_faber_r",       "lumbar",   "obj:08_special", "FABER Right",               "Patrick hip SIJ sacroiliac joint"),
    ("st_fadir_l",       "lumbar",   "obj:08_special", "FADIR Left",                "hip impingement FAI labral acetabular"),
    ("st_fadir_r",       "lumbar",   "obj:08_special", "FADIR Right",               "hip impingement FAI labral acetabular"),
    ("st_prone_inst_l",  "lumbar",   "obj:08_special", "Prone Instability Left",    "lumbar instability segmental"),
    ("st_prone_inst_r",  "lumbar",   "obj:08_special", "Prone Instability Right",   "lumbar instability segmental"),
    ("st_crossed_slr_l", "lumbar",   "obj:08_special", "Crossed SLR Left",          "disc herniation central paracentral contralateral"),
    ("st_crossed_slr_r", "lumbar",   "obj:08_special", "Crossed SLR Right",         "disc herniation central paracentral contralateral"),
    # ── Shoulder ─────────────────────────────────────────────────────────────
    ("st_hawkins_l",      "shoulder", "obj:08_special", "Hawkins-Kennedy Left",      "impingement subacromial coracoacromial supraspinatus"),
    ("st_hawkins_r",      "shoulder", "obj:08_special", "Hawkins-Kennedy Right",     "impingement subacromial coracoacromial supraspinatus"),
    ("st_neer_l",         "shoulder", "obj:08_special", "Neer Sign Left",            "impingement subacromial acromion supraspinatus"),
    ("st_neer_r",         "shoulder", "obj:08_special", "Neer Sign Right",           "impingement subacromial acromion supraspinatus"),
    ("st_painful_arc_l",  "shoulder", "obj:08_special", "Painful Arc Left",          "impingement subacromial 60 120 abduction"),
    ("st_painful_arc_r",  "shoulder", "obj:08_special", "Painful Arc Right",         "impingement subacromial 60 120 abduction"),
    ("st_empty_can_l",    "shoulder", "obj:08_special", "Empty Can Left",            "supraspinatus rotator cuff tear Jobe scapular plane"),
    ("st_empty_can_r",    "shoulder", "obj:08_special", "Empty Can Right",           "supraspinatus rotator cuff tear Jobe scapular plane"),
    ("st_full_can_l",     "shoulder", "obj:08_special", "Full Can Left",             "supraspinatus rotator cuff strength scapular plane"),
    ("st_full_can_r",     "shoulder", "obj:08_special", "Full Can Right",            "supraspinatus rotator cuff strength scapular plane"),
    ("st_er_lag_l",       "shoulder", "obj:08_special", "ER Lag Sign Left",          "infraspinatus external rotation lag full thickness tear"),
    ("st_er_lag_r",       "shoulder", "obj:08_special", "ER Lag Sign Right",         "infraspinatus external rotation lag full thickness tear"),
    ("st_lift_off_l",     "shoulder", "obj:08_special", "Lift-off Left",             "subscapularis Gerber internal rotation behind back"),
    ("st_lift_off_r",     "shoulder", "obj:08_special", "Lift-off Right",            "subscapularis Gerber internal rotation behind back"),
    ("st_belly_press_l",  "shoulder", "obj:08_special", "Belly Press Left",          "subscapularis Napoleon internal rotation wrist"),
    ("st_belly_press_r",  "shoulder", "obj:08_special", "Belly Press Right",         "subscapularis Napoleon internal rotation wrist"),
    ("st_drop_arm_l",     "shoulder", "obj:08_special", "Drop Arm Left",             "full thickness rotator cuff tear supraspinatus eccentric"),
    ("st_drop_arm_r",     "shoulder", "obj:08_special", "Drop Arm Right",            "full thickness rotator cuff tear supraspinatus eccentric"),
    ("st_cross_body_l",   "shoulder", "obj:08_special", "Cross-body Adduction Left", "AC joint acromioclavicular horizontal adduction"),
    ("st_cross_body_r",   "shoulder", "obj:08_special", "Cross-body Adduction Right","AC joint acromioclavicular horizontal adduction"),
    ("st_ac_stress_l",    "shoulder", "obj:08_special", "AC Stress Left",            "acromioclavicular joint stress compression shear"),
    ("st_ac_stress_r",    "shoulder", "obj:08_special", "AC Stress Right",           "acromioclavicular joint stress compression shear"),
    ("st_speeds_l",       "shoulder", "obj:08_special", "Speed's Left",              "biceps tendinopathy SLAP long head bicipital groove"),
    ("st_speeds_r",       "shoulder", "obj:08_special", "Speed's Right",             "biceps tendinopathy SLAP long head bicipital groove"),
    ("st_yergason_l",     "shoulder", "obj:08_special", "Yergason's Left",           "bicipital tendinopathy groove instability supination"),
    ("st_yergason_r",     "shoulder", "obj:08_special", "Yergason's Right",          "bicipital tendinopathy groove instability supination"),
    ("st_obrien_l",       "shoulder", "obj:08_special", "O'Brien Left",              "SLAP tear active compression AC joint deep pain"),
    ("st_obrien_r",       "shoulder", "obj:08_special", "O'Brien Right",             "SLAP tear active compression AC joint deep pain"),
    ("st_apprehension_l", "shoulder", "obj:08_special", "Apprehension Left",         "anterior instability glenohumeral dislocation ER"),
    ("st_apprehension_r", "shoulder", "obj:08_special", "Apprehension Right",        "anterior instability glenohumeral dislocation ER"),
    ("st_relocation_l",   "shoulder", "obj:08_special", "Relocation Left",           "anterior instability Jobe posterior force humeral head"),
    ("st_relocation_r",   "shoulder", "obj:08_special", "Relocation Right",          "anterior instability Jobe posterior force humeral head"),
    ("st_sulcus_l",       "shoulder", "obj:08_special", "Sulcus Sign Left",          "inferior instability MDI multidirectional traction"),
    ("st_sulcus_r",       "shoulder", "obj:08_special", "Sulcus Sign Right",         "inferior instability MDI multidirectional traction"),
    ("st_scap_assist_l",  "shoulder", "obj:08_special", "Scap Assist Left",          "scapular dyskinesis upward rotation posterior tilt SA LT"),
    ("st_scap_assist_r",  "shoulder", "obj:08_special", "Scap Assist Right",         "scapular dyskinesis upward rotation posterior tilt SA LT"),
    ("st_wall_pushup_l",  "shoulder", "obj:08_special", "Wall Push-up Left",         "serratus anterior winging long thoracic nerve"),
    ("st_wall_pushup_r",  "shoulder", "obj:08_special", "Wall Push-up Right",        "serratus anterior winging long thoracic nerve"),
]


# ---------------------------------------------------------------------------
# Fuzzy scoring
# ---------------------------------------------------------------------------

def fuzzy_score(query: str, target: str) -> int:
    """Return match score > 0 if query fuzzy-matches target. Higher = better."""
    if not query:
        return 0
    q, t = query.lower(), target.lower()
    if q == t:
        return 1000
    if t.startswith(q):
        return 900
    if q in t:
        return 800 - t.index(q)
    # Character subsequence
    idx = 0
    gaps = 0
    for ch in q:
        pos = t.find(ch, idx)
        if pos == -1:
            return 0
        gaps += pos - idx
        idx = pos + 1
    return max(1, 200 - gaps)


def _snippet(text: str, max_len: int = 48) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line[:max_len] + ("…" if len(line) > max_len else "")
    return ""


# ---------------------------------------------------------------------------
# Index builder
# ---------------------------------------------------------------------------

def build_index(app: "App") -> list[SearchEntry]:
    """Build a fresh search index from live app state."""
    from .assessment_view import AssessmentView
    from .widgets import CheckButton
    from textual.widgets import TextArea, Input as TInput

    entries: list[SearchEntry] = []

    # 1 — Sections
    for sec_id, label in _SECTION_LABELS.items():
        entries.append(SearchEntry(
            display=label,
            match_text=label,
            section_id=sec_id,
            anchor_id=None,
            widget_id=None,
            kind="section",
        ))

    # 2 — Subsections
    for sec_id, anchor_id, label in _SUBSECTIONS:
        short = _SECTION_SHORT.get(sec_id, sec_id)
        entries.append(SearchEntry(
            display=f"{short} › {label}",
            match_text=f"{label} {short}",
            section_id=sec_id,
            anchor_id=anchor_id,
            widget_id=None,
            kind="subsection",
        ))

    try:
        av = app.query_one("#assessment_view", AssessmentView)
    except Exception:
        return entries

    # 3 — CheckButton / FlagButton labels (assessment sections only)
    for sec_id in _ASSESSMENT_SECTION_IDS:
        section = av.sections.get(sec_id)
        if section is None:
            continue
        short = _SECTION_SHORT.get(sec_id, sec_id)
        try:
            for btn in section.query(CheckButton):
                if not btn.id:
                    continue
                name = getattr(btn, "base_name", None) or str(btn.label)
                entries.append(SearchEntry(
                    display=f"{short} › {name}",
                    match_text=f"{name} {short}",
                    section_id=sec_id,
                    anchor_id=None,
                    widget_id=btn.id,
                    kind="field",
                ))
        except Exception:
            pass

    # 4 — Named text field entries (from _FIELD_LABELS)
    for widget_id, (sec_id, anchor_id, human_name) in _FIELD_LABELS.items():
        short = _SECTION_SHORT.get(sec_id, sec_id)
        subsec = _SUBSECTION_LABEL.get((sec_id, anchor_id), "") if anchor_id else ""
        if subsec:
            display = f"{short} › {subsec} › {human_name}"
        else:
            display = f"{short} › {human_name}"
        entries.append(SearchEntry(
            display=display,
            match_text=f"{human_name} {short}",
            section_id=sec_id,
            anchor_id=anchor_id,
            widget_id=widget_id,
            kind="field",
        ))

    # 5 — Content entries (non-empty TextArea / Input values)
    for widget_id, (sec_id, anchor_id, human_name) in _FIELD_LABELS.items():
        section = av.sections.get(sec_id)
        if section is None:
            continue
        short = _SECTION_SHORT.get(sec_id, sec_id)
        try:
            widget = section.query_one(f"#{widget_id}")
        except Exception:
            continue
        if isinstance(widget, TextArea):
            text = widget.text
        elif isinstance(widget, TInput):
            text = widget.value
        else:
            continue
        if not text.strip():
            continue
        snip = _snippet(text)
        entries.append(SearchEntry(
            display=f"{short} › {human_name}: '{snip}'",
            match_text=text,
            section_id=sec_id,
            anchor_id=anchor_id,
            widget_id=widget_id,
            kind="content",
        ))

    # 6 — Objective KB special test fields
    for widget_id, region, sec_id, human_name, extra in _OBJ_KB_FIELDS:
        short = _SECTION_SHORT.get(sec_id, "Obj:Special")
        entries.append(SearchEntry(
            display=f"{short} › {region.title()} › {human_name}",
            match_text=f"{human_name} {extra} {region}",
            section_id=sec_id,
            anchor_id=None,
            widget_id=widget_id,
            kind="field",
        ))

    return entries


# ---------------------------------------------------------------------------
# Filter
# ---------------------------------------------------------------------------

def filter_entries(
    query: str,
    index: list[SearchEntry],
    max_results: int = 10,
) -> list[SearchEntry]:
    """Return up to max_results best-scoring entries for query."""
    if not query.strip():
        return []
    scored: list[tuple[int, int, SearchEntry]] = []
    for i, entry in enumerate(index):
        score = fuzzy_score(query, entry.match_text)
        if score > 0:
            scored.append((score, -i, entry))
    scored.sort(reverse=True)
    return [e for _, _, e in scored[:max_results]]
