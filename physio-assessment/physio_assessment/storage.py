"""
Session storage — read/write assessment data to session JSON files.

Handles atomic writes via temp file + rename to prevent JSON corruption.
Preserves GTK-owned sections (subjective, objective) while updating
Python-owned assessment block.
"""

import json
import time
import logging
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)


def load_assessment(session_file: str) -> dict:
    """
    Load assessment block from session JSON file.

    Returns empty dict if file doesn't exist or can't be parsed.
    """
    path = Path(session_file)
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text())
        return data.get("assessment", {})
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse session file {session_file}: {e}")
        return {}


def save_assessment(session_file: str, assessment: dict) -> bool:
    """
    Merge assessment block into session JSON, preserving all GTK sections.

    Uses atomic write (temp file + rename) to prevent corruption.
    Returns True on success, False on error.
    """
    path = Path(session_file)

    try:
        # Read current file if it exists
        if path.exists():
            data = json.loads(path.read_text())
        else:
            data = {}

        # Update assessment block with timestamp
        if "assessment" not in data:
            data["assessment"] = {}

        data["assessment"].update(assessment)
        data["assessment"]["modified"] = int(time.time())

        # Atomic write: temp file, then rename
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)  # atomic on POSIX

        logger.debug(f"Saved assessment to {session_file}")
        return True

    except Exception as e:
        logger.error(f"Failed to save assessment to {session_file}: {e}")
        return False


def load_session_current() -> Optional[dict]:
    """
    Load the active session pointer from session_current.json.

    Returns None if file doesn't exist or can't be parsed.
    """
    session_current = Path.home() / ".local/share/physio-bodychart/session_current.json"

    if not session_current.exists():
        return None

    try:
        return json.loads(session_current.read_text())
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse session_current.json: {e}")
        return None


def list_sessions() -> list[dict]:
    """
    List all assessment sessions from GTK storage directory.

    Returns list of session dicts with: path, patient_id, session_label,
    date, regions, body_chart_data, sections_complete
    """
    sessions = []
    physio_root = Path.home() / "Physio-Bodychart"

    if not physio_root.exists():
        return sessions

    # Scan all session directories
    for session_dir in sorted(physio_root.iterdir(), reverse=True):
        if not session_dir.is_dir():
            continue

        # Look for session.json in this directory
        session_file = session_dir / f"{session_dir.name}_session.json"
        if not session_file.exists():
            continue

        try:
            data = json.loads(session_file.read_text())

            # Extract session metadata
            session = {
                "path": str(session_file),
                "patient_id": data.get("patient_id", "XX"),
                "session_label": data.get("session_label", ""),
                "date": data.get("date") or data.get("created", 0),
                "regions": data.get("regions", []),
                "body_chart_data": bool(
                    data.get("subjective", {}).get("strokes") or
                    data.get("subjective", {}).get("notes") or
                    data.get("objective", {}).get("zones") or
                    data.get("objective", {}).get("points")
                ),
                "sections_complete": count_complete_sections(data),
            }
            sessions.append(session)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to read session {session_file}: {e}")
            continue

    return sessions


def count_complete_sections(session_data: dict) -> int:
    """Count how many assessment sections have content."""
    sections = get_sections_complete(session_data)
    return sum(1 for v in sections.values() if v)


def get_sections_complete(session_data: dict) -> dict[str, bool]:
    """
    Check completion status of each core section.

    Returns dict mapping section_id to completion status.
    """
    assessment = session_data.get("assessment", {})
    complete_status = {}

    # Special handling for 01_consent (has its own sub-block)
    consent = assessment.get("consent", {})
    complete_status["01_consent"] = (
        consent.get("consent_to_proceed") is True
        and bool(consent.get("preferred_name", "").strip())
    )

    # Define remaining sections and their mandatory fields
    sections = {
        "02_subjective": {
            "assessment_fields": ["history"],
        },
        "03_medical": {
            "assessment_fields": [],  # completion driven by save_medical via sections_complete
        },
        "04_pain_classification": {
            "assessment_fields": [],
        },
        "05_outcome_measures": {
            "assessment_fields": [],
        },
        "06_diagnosis": {
            "assessment_fields": [],
        },
        "07_barriers": {
            "assessment_fields": [],
        },
    }

    # Check all other sections
    for section_id, section_def in sections.items():
        # Check if all mandatory assessment fields have content
        all_filled = True
        for field in section_def["assessment_fields"]:
            if not assessment.get(field, "").strip():
                all_filled = False
                break

        complete_status[section_id] = all_filled

    return complete_status


def is_section_complete(session_data: dict, section_id: str) -> bool:
    """Check if a specific section is complete."""
    sections = get_sections_complete(session_data)
    return sections.get(section_id, False)


def mark_section_complete(session_file: str, section_id: str) -> bool:
    """
    Mark a section as complete in the session.

    Returns True on success.
    """
    path = Path(session_file)
    if not path.exists():
        return False

    try:
        data = json.loads(path.read_text())

        # Initialize sections_complete if needed
        if "sections_complete" not in data:
            data["sections_complete"] = {}
        if "sections_last_modified" not in data:
            data["sections_last_modified"] = {}

        # Mark this section complete
        data["sections_complete"][section_id] = True
        data["sections_last_modified"][section_id] = int(time.time())

        # Atomic write
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)

        return True
    except Exception as e:
        logger.error(f"Failed to mark section complete: {e}")
        return False


def get_resume_section(session_data: dict) -> str:
    """
    Find the first incomplete section to resume from.

    Returns section ID to open. If all complete, returns last section.
    """
    section_order = [
        "01_consent",
        "02_subjective",
        "03_medical",
        "04_pain_classification",
        "05_outcome_measures",
        "06_diagnosis",
        "07_barriers",
    ]

    # Check sections in order
    for section_id in section_order:
        if not is_section_complete(session_data, section_id):
            return section_id

    # All complete; return last section
    return section_order[-1]


def load_consent(session_file: str) -> dict:
    """
    Load consent data from session JSON file.

    Returns empty dict if file doesn't exist or can't be parsed.
    """
    path = Path(session_file)
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text())
        return data.get("assessment", {}).get("consent", {})
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse session file {session_file}: {e}")
        return {}


def save_consent(session_file: str, consent: dict) -> bool:
    """
    Merge consent data into session JSON, preserving all other sections.

    Updates sections_complete["01_consent"] based on consent data.
    Uses atomic write (temp file + rename) to prevent corruption.
    Returns True on success, False on error.
    """
    path = Path(session_file)

    try:
        # Read current file if it exists
        if path.exists():
            data = json.loads(path.read_text())
        else:
            data = {}

        # Ensure assessment block exists
        if "assessment" not in data:
            data["assessment"] = {}

        # Merge consent into assessment.consent
        if "consent" not in data["assessment"]:
            data["assessment"]["consent"] = {}
        data["assessment"]["consent"].update(consent)

        # Calculate completion for 01_consent
        is_complete = (
            consent.get("consent_to_proceed") is True
            and bool(consent.get("preferred_name", "").strip())
        )

        # Update sections_complete
        if "sections_complete" not in data:
            data["sections_complete"] = {}
        if "sections_last_modified" not in data:
            data["sections_last_modified"] = {}

        data["sections_complete"]["01_consent"] = is_complete
        data["sections_last_modified"]["01_consent"] = int(time.time())

        # Atomic write: temp file, then rename
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)

        logger.debug(f"Saved consent to {session_file}")
        return True

    except Exception as e:
        logger.error(f"Failed to save consent to {session_file}: {e}")
        return False


def load_subjective(session_file: str) -> dict:
    """
    Load subjective assessment data from session JSON file.

    Returns empty dict if file doesn't exist or can't be parsed.
    """
    path = Path(session_file)
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text())
        return data.get("assessment", {}).get("subjective", {})
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse session file {session_file}: {e}")
        return {}


def save_subjective(session_file: str, subjective: dict) -> bool:
    """
    Merge subjective assessment data into session JSON, preserving all other sections.

    Updates sections_complete["02_subjective"] based on subjective data.
    Uses atomic write (temp file + rename) to prevent corruption.
    Returns True on success, False on error.
    """
    path = Path(session_file)

    try:
        # Read current file if it exists
        if path.exists():
            data = json.loads(path.read_text())
        else:
            data = {}

        # Ensure assessment block exists
        if "assessment" not in data:
            data["assessment"] = {}

        # Merge subjective into assessment.subjective
        if "subjective" not in data["assessment"]:
            data["assessment"]["subjective"] = {}
        data["assessment"]["subjective"].update(subjective)

        # Calculate completion for 02_subjective (self-harm risk assessed)
        is_complete = subjective.get("self_harm_risk") is not None

        # Update sections_complete
        if "sections_complete" not in data:
            data["sections_complete"] = {}
        if "sections_last_modified" not in data:
            data["sections_last_modified"] = {}

        data["sections_complete"]["02_subjective"] = is_complete
        data["sections_last_modified"]["02_subjective"] = int(time.time())

        # Atomic write: temp file, then rename
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)

        logger.debug(f"Saved subjective to {session_file}")
        return True

    except Exception as e:
        logger.error(f"Failed to save subjective to {session_file}: {e}")
        return False


def load_medical(session_file: str) -> dict:
    """Load medical screening data from session JSON file."""
    path = Path(session_file)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data.get("assessment", {}).get("medical", {})
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse session file {session_file}: {e}")
        return {}


def save_medical(session_file: str, medical: dict) -> bool:
    """Merge medical screening data into session JSON, preserving all other sections."""
    path = Path(session_file)
    try:
        if path.exists():
            data = json.loads(path.read_text())
        else:
            data = {}
        if "assessment" not in data:
            data["assessment"] = {}
        if "medical" not in data["assessment"]:
            data["assessment"]["medical"] = {}
        data["assessment"]["medical"].update(medical)

        # Complete when all urgent red flag fields have been explicitly reviewed
        urgent = [
            "rf_saddle_anaesthesia", "rf_bladder_disturbance", "rf_bowel_disturbance",
            "rf_bilateral_paraesthesia", "rf_gait_disturbance",
        ]
        is_complete = all(medical.get(fid) is not None for fid in urgent)

        if "sections_complete" not in data:
            data["sections_complete"] = {}
        if "sections_last_modified" not in data:
            data["sections_last_modified"] = {}
        data["sections_complete"]["03_medical"] = is_complete
        data["sections_last_modified"]["03_medical"] = int(time.time())

        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)
        logger.debug(f"Saved medical to {session_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to save medical to {session_file}: {e}")
        return False


def load_pain_classification(session_file: str) -> dict:
    """Load pain classification data from session JSON file."""
    path = Path(session_file)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data.get("assessment", {}).get("pain_classification", {})
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse session file {session_file}: {e}")
        return {}


def save_pain_classification(session_file: str, pain: dict) -> bool:
    """Merge pain classification data into session JSON, preserving all other sections."""
    path = Path(session_file)
    try:
        if path.exists():
            data = json.loads(path.read_text())
        else:
            data = {}
        if "assessment" not in data:
            data["assessment"] = {}
        if "pain_classification" not in data["assessment"]:
            data["assessment"]["pain_classification"] = {}
        data["assessment"]["pain_classification"].update(pain)

        is_complete = pain.get("summary_dominant") is not None

        if "sections_complete" not in data:
            data["sections_complete"] = {}
        if "sections_last_modified" not in data:
            data["sections_last_modified"] = {}
        data["sections_complete"]["04_pain_classification"] = is_complete
        data["sections_last_modified"]["04_pain_classification"] = int(time.time())

        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)
        logger.debug(f"Saved pain_classification to {session_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to save pain_classification to {session_file}: {e}")
        return False


def load_outcome_measures(session_file: str) -> dict:
    """Load outcome measures data from session JSON file."""
    path = Path(session_file)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data.get("assessment", {}).get("outcome_measures", {})
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse session file {session_file}: {e}")
        return {}


def save_outcome_measures(session_file: str, om: dict) -> bool:
    """Merge outcome measures data into session JSON, preserving all other sections."""
    path = Path(session_file)
    try:
        if path.exists():
            data = json.loads(path.read_text())
        else:
            data = {}
        if "assessment" not in data:
            data["assessment"] = {}
        if "outcome_measures" not in data["assessment"]:
            data["assessment"]["outcome_measures"] = {}
        data["assessment"]["outcome_measures"].update(om)

        main_scores = ["psfs_score", "bpi_activity", "dass_dep_score",
                       "pcs_total_score", "pseq_score", "pcl5_score", "isi_score"]
        is_complete = any(om.get(f, "").strip() for f in main_scores)

        if "sections_complete" not in data:
            data["sections_complete"] = {}
        if "sections_last_modified" not in data:
            data["sections_last_modified"] = {}
        data["sections_complete"]["05_outcome_measures"] = is_complete
        data["sections_last_modified"]["05_outcome_measures"] = int(time.time())

        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)
        logger.debug(f"Saved outcome_measures to {session_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to save outcome_measures to {session_file}: {e}")
        return False


def load_diagnosis(session_file: str) -> dict:
    """Load diagnosis data from session JSON file."""
    path = Path(session_file)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data.get("assessment", {}).get("diagnosis", {})
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse session file {session_file}: {e}")
        return {}


def save_diagnosis(session_file: str, dx: dict) -> bool:
    """Merge diagnosis data into session JSON, preserving all other sections."""
    path = Path(session_file)
    try:
        if path.exists():
            data = json.loads(path.read_text())
        else:
            data = {}
        if "assessment" not in data:
            data["assessment"] = {}
        data["assessment"]["diagnosis"] = dx

        is_complete = dx.get("mechanism") is not None

        if "sections_complete" not in data:
            data["sections_complete"] = {}
        if "sections_last_modified" not in data:
            data["sections_last_modified"] = {}
        data["sections_complete"]["06_diagnosis"] = is_complete
        data["sections_last_modified"]["06_diagnosis"] = int(time.time())

        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)
        logger.debug(f"Saved diagnosis to {session_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to save diagnosis to {session_file}: {e}")
        return False


def load_barriers(session_file: str) -> dict:
    """Load barriers and treatment plan data from session JSON file."""
    path = Path(session_file)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
        return data.get("assessment", {}).get("barriers", {})
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse session file {session_file}: {e}")
        return {}


def save_barriers(session_file: str, barriers: dict) -> bool:
    """Merge barriers and treatment plan data into session JSON."""
    path = Path(session_file)
    try:
        if path.exists():
            data = json.loads(path.read_text())
        else:
            data = {}
        if "assessment" not in data:
            data["assessment"] = {}
        data["assessment"]["barriers"] = barriers

        # Complete when any main barrier has been explicitly reviewed (True or False)
        main_barriers = [
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
        is_complete = any(barriers.get(fid) is not None for fid in main_barriers)

        if "sections_complete" not in data:
            data["sections_complete"] = {}
        if "sections_last_modified" not in data:
            data["sections_last_modified"] = {}
        data["sections_complete"]["07_barriers"] = is_complete
        data["sections_last_modified"]["07_barriers"] = int(time.time())

        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)
        logger.debug(f"Saved barriers to {session_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to save barriers to {session_file}: {e}")
        return False


def write_tui_pid(pid: int) -> None:
    """Write the TUI process PID into session_current.json."""
    path = Path.home() / ".local/share/physio-bodychart/session_current.json"
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
        data["tui_pid"] = pid
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(path)
    except Exception as e:
        logger.warning(f"write_tui_pid: {e}")


def read_gtk_pid() -> int | None:
    """Read the GTK process PID from session_current.json. Returns None if absent."""
    path = Path.home() / ".local/share/physio-bodychart/session_current.json"
    try:
        data = json.loads(path.read_text())
        pid = data.get("gtk_pid")
        return int(pid) if pid else None
    except Exception:
        return None


def read_tui_socket() -> str | None:
    """Read the kitty remote-control socket path from session_current.json."""
    path = Path.home() / ".local/share/physio-bodychart/session_current.json"
    try:
        data = json.loads(path.read_text())
        return data.get("tui_socket") or None
    except Exception:
        return None


def focus_signal_path(session_file: str, target: str) -> Path:
    """Return path to a focus signal file (.focus_gtk or .focus_tui) in the session dir."""
    return Path(session_file).parent / f".focus_{target}"


def write_focus_signal(session_file: str, target: str) -> None:
    """Write a focus signal file. The other app watches for this and raises its window."""
    try:
        focus_signal_path(session_file, target).touch()
    except Exception as e:
        logger.warning(f"write_focus_signal({target}): {e}")


# ---------------------------------------------------------------------------
# Session report export
# ---------------------------------------------------------------------------

def _yn(val) -> str:
    if val is True:  return "Yes"
    if val is False: return "No"
    return ""


def _row(*pairs) -> str:
    """Format key-value pairs on one line, skipping empty values."""
    parts = [f"**{k}:** {v}" for k, v in pairs if v not in (None, "", [])]
    return "  ".join(parts) if parts else ""


def export_session_report(session_file: str) -> str:
    """
    Write a compact Markdown assessment report to <session_dir>/<name>_report.md.
    Returns the output path, or empty string on failure.
    """
    try:
        data = json.loads(Path(session_file).read_text())
    except Exception as e:
        logger.error(f"export_session_report: {e}")
        return ""

    session_dir  = Path(session_file).parent
    session_name = data.get("session_name", "session")
    out_path     = session_dir / f"{session_name}_report.md"

    import time as _time
    created = data.get("created", 0)
    date_str = _time.strftime("%d %b %Y", _time.localtime(created)) if created else ""

    lines: list[str] = []

    def h1(text):  lines.append(f"# {text}\n")
    def h2(text):  lines.append(f"## {text}")
    def row(*pairs): r = _row(*pairs); lines.append(r) if r else None
    def text(label, val):
        if val and val.strip():
            lines.append(f"**{label}:** {val.strip()}")
    def gap(): lines.append("")

    a = data.get("assessment", {})

    # ── Title ──────────────────────────────────────────────────────────────
    pid   = data.get("patient_id", "")
    label = data.get("session_label", "")
    h1(f"Physiotherapy Assessment — {pid}")
    row(("Session", label), ("Date", date_str))
    gap()

    # ── 01 Consent ─────────────────────────────────────────────────────────
    c = a.get("consent", {})
    if isinstance(c, dict) and c:
        h2("01 Consent")
        row(("Preferred name", c.get("preferred_name")),
            ("Consent to proceed", _yn(c.get("consent_to_proceed"))),
            ("Consent (sensitive topics)", _yn(c.get("consent_sensitive_topics"))))
        row(("Pain multifactorial explained", _yn(c.get("pain_multifactorial_explained"))),
            ("Education as treatment explained", _yn(c.get("education_as_treatment_explained"))))
        text("Reason for attending", c.get("reason_for_attending"))
        text("Patient expectations", c.get("patient_expectations"))
        row(("Cause understanding", _yn(c.get("cause_understanding"))),
            ("Detail", c.get("cause_understanding_detail")))
        text("Prognosis expectations", c.get("prognosis_expectations"))
        text("Treatment preference", c.get("treatment_preference"))
        gap()

    # ── 02 Subjective ──────────────────────────────────────────────────────
    s = a.get("subjective", {})
    if isinstance(s, dict) and s:
        h2("02 Subjective Examination")
        text("History", s.get("history"))
        row(("Duration", s.get("duration")), ("Onset", s.get("onset")))
        row(("Current NRS", s.get("nrs_current")),
            ("Best", s.get("nrs_best")), ("Worst", s.get("nrs_worst")))
        row(("24-hr pattern", s.get("behaviour_24hr")))
        row(("Course", s.get("course")),
            ("Improving", _yn(s.get("course_improving"))),
            ("Worsening", _yn(s.get("course_worsening"))))
        text("Context at onset", s.get("context_at_onset"))
        text("Previous treatment", s.get("previous_treatment"))
        row(("Sleep difficulty", _yn(s.get("sleep_difficulty"))),
            ("Night waking", _yn(s.get("night_waking"))),
            ("Total sleep hrs", s.get("total_sleep_hours")))
        row(("Aggravating factors", s.get("aggravating_factors")))
        row(("Easing factors", s.get("easing_factors")))
        row(("Morning stiffness", _yn(s.get("morning_stiffness"))),
            ("Stiffness duration", s.get("morning_stiffness_duration")))
        row(("Mood influences", _yn(s.get("mood_influences"))),
            ("Psychological distress", _yn(s.get("psychological_distress"))))
        row(("Self-harm risk", _yn(s.get("self_harm_risk"))),
            ("Harm plan", _yn(s.get("harm_plan"))))
        row(("PSEQ confidence", s.get("confidence_score")))
        gap()

    # ── 03 Medical ─────────────────────────────────────────────────────────
    m = a.get("medical", {})
    if isinstance(m, dict) and m:
        h2("03 Medical Screening")
        # Red flags
        rf_map = [
            ("rf_saddle_anaesthesia", "Saddle anaesthesia"),
            ("rf_bladder_disturbance", "Bladder disturbance"),
            ("rf_bowel_disturbance", "Bowel disturbance"),
            ("rf_bilateral_paraesthesia", "Bilateral paraesthesia"),
            ("rf_gait_disturbance", "Gait disturbance"),
        ]
        positives = [label for fid, label in rf_map if m.get(fid) is True]
        if positives:
            lines.append(f"**Red flags +ve:** {', '.join(positives)}")
        comorbid_map = [
            ("comorbid_cardiovascular", "Cardiovascular"),
            ("comorbid_diabetes", "Diabetes"),
            ("comorbid_cancer", "Cancer"),
            ("comorbid_inflammatory", "Inflammatory arthritis"),
            ("comorbid_fibromyalgia", "Fibromyalgia"),
            ("comorbid_mental_health", "Mental health"),
            ("comorbid_drug_alcohol", "Drug/alcohol"),
            ("comorbid_whiplash", "Whiplash"),
        ]
        comorbid = [label for fid, label in comorbid_map if m.get(fid) is True]
        if comorbid:
            lines.append(f"**Comorbidities:** {', '.join(comorbid)}")
        meds = [m.get(f"medication_{i}_name", "").strip() for i in range(1, 6)]
        meds = [x for x in meds if x]
        if meds:
            lines.append(f"**Medications:** {', '.join(meds)}")
        gap()

    # ── 04 Pain Classification ─────────────────────────────────────────────
    pc = a.get("pain_classification", {})
    if isinstance(pc, dict) and pc:
        h2("04 Pain Classification")
        row(("Dominant type", pc.get("summary_dominant")),
            ("Secondary", pc.get("summary_secondary")))
        text("Reasoning", pc.get("summary_reasoning"))
        gap()

    # ── 05 Outcome Measures ────────────────────────────────────────────────
    om = a.get("outcome_measures", {})
    if isinstance(om, dict) and om:
        h2("05 Outcome Measures")
        score_map = [
            ("psfs_score", "psfs_interp",    "PSFS"),
            ("bpi_activity","",              "BPI activity"),
            ("dass_dep_score","dass_dep_interp","DASS dep"),
            ("dass_anx_score","dass_anx_interp","DASS anx"),
            ("dass_str_score","dass_str_interp","DASS stress"),
            ("pcs_total_score","pcs_total_risk","PCS total"),
            ("pseq_score","",               "PSEQ"),
            ("pcl5_score","pcl5_interp",    "PCL-5"),
            ("isi_score","isi_interp",      "ISI"),
            ("pbas_score","pbas_interp",    "PBAS"),
        ]
        parts = []
        for sfid, ifid, label in score_map:
            score = om.get(sfid, "").strip()
            if score:
                interp = om.get(ifid, "").strip() if ifid else ""
                parts.append(f"{label} {score}" + (f" ({interp})" if interp else ""))
        if parts:
            lines.append("  ".join(parts))
        goals = [om.get(f"psfs_goal_{i}", "").strip() for i in range(1, 6)]
        goals = [g for g in goals if g]
        if goals:
            lines.append(f"**PSFS goals:** {'; '.join(goals)}")
        gap()

    # ── 06 Diagnosis ──────────────────────────────────────────────────────
    dx = a.get("diagnosis", {})
    if isinstance(dx, dict) and dx:
        h2("06 Diagnosis")
        row(("Duration >3 months", _yn(dx.get("duration_over_3_months"))),
            ("Mechanism", dx.get("mechanism")))
        row(("Primary subtype", dx.get("primary_subtype")),
            ("Severity", dx.get("primary_severity")))
        row(("Surgical subtype", dx.get("surgical_subtype")),
            ("Procedure", dx.get("surgical_procedure")))
        row(("Traumatic subtype", dx.get("traumatic_subtype")),
            ("Event", dx.get("traumatic_event")))
        row(("MSK subtype", dx.get("msk_subtype")),
            ("Pathology", dx.get("msk_pathology")))
        row(("Neuro subtype", dx.get("neuro_subtype")),
            ("Lesion", dx.get("neuro_lesion")))
        row(("Mixed dominant", dx.get("mixed_dominant")))
        text("Mixed reasoning", dx.get("mixed_reasoning"))
        goals = [dx.get(f"goal_{i}", "").strip() for i in range(1, 5)]
        goals = [g for g in goals if g]
        if goals:
            lines.append("**SMART Goals:**")
            for i, g in enumerate(goals, 1):
                lines.append(f"{i}. {g}")
        gap()

    # ── 07 Barriers ────────────────────────────────────────────────────────
    br = a.get("barriers", {})
    if isinstance(br, dict) and br:
        h2("07 Barriers & Treatment Plan")
        barrier_map = [
            ("b_noci_disease",        "Disease/pathology"),
            ("b_noci_pacing",         "Pacing issues"),
            ("b_noci_inflammatory",   "Inflammatory features"),
            ("b_noci_deconditioning", "Deconditioning"),
            ("b_noci_movement",       "Reduced movement"),
            ("b_noci_gait",           "Asymmetrical gait"),
            ("b_noci_strength",       "Strength deficits"),
            ("b_noci_deep_muscle",    "Deep muscle activation"),
            ("b_noci_overactivity",   "Muscle overactivity"),
            ("b_noci_nerve_mech",     "Nerve mechanosensitivity"),
            ("b_noci_diet",           "Diet/weight"),
            ("b_neuro_confirmed",     "Neuropathic (confirmed)"),
            ("b_neuro_unconfirmed",   "Neuropathic (unconfirmed)"),
            ("b_nocip_moderate",      "Nociplastic/CS"),
            ("b_nocip_crps",          "CRPS"),
            ("b_nocip_fnd",           "FND"),
            ("b_psych_depression",    "Depression"),
            ("b_psych_anxiety",       "Anxiety"),
            ("b_psych_stress",        "Stress"),
            ("b_psych_catastrophising","Catastrophising"),
            ("b_psych_self_efficacy", "Reduced self-efficacy"),
            ("b_psych_unhelpful_beliefs","Unhelpful beliefs"),
            ("b_psych_ptsd",          "PTSD symptoms"),
            ("b_psych_readiness",     "Unclear readiness"),
            ("b_sleep_disturbed",     "Disturbed sleep"),
            ("b_social_home",         "Home/social barriers"),
            ("b_social_rtw",          "RTW barriers"),
            ("b_med_red_flag",        "Red flag"),
            ("b_med_substance",       "Substance use"),
            ("b_med_as",              "Possible AS"),
            ("b_med_aaa",             "Possible AAA"),
            ("b_med_vascular",        "Vascular claudication"),
            ("b_med_cervical_ha",     "Cervical headache"),
            ("b_med_medico_legal",    "Medico-legal"),
        ]
        present = [label for fid, label in barrier_map if br.get(fid) is True]
        if present:
            lines.append(f"**Barriers identified:** {', '.join(present)}")
        # Treatment plan
        text("Goal orientation", br.get("tx_goal_orientation"))
        text("Formulation", br.get("tx_formulation"))
        text("Program", br.get("tx_program"))
        text("Home program", br.get("tx_home_program"))
        text("Psychosocial strategies", br.get("tx_psychosocial"))
        text("Medical/referral", br.get("tx_medical"))
        text("RTW plan", br.get("tx_rtw"))
        # Follow-up
        text("Next session focus", br.get("fu_next_focus"))
        text("Monitoring", br.get("fu_monitoring"))
        gap()

    # ── Write ──────────────────────────────────────────────────────────────
    try:
        out_path.write_text("\n".join(lines))
        logger.info(f"Report written to {out_path}")
        return str(out_path)
    except Exception as e:
        logger.error(f"export_session_report write failed: {e}")
        return ""


def create_new_session(patient_id: str, regions: list[str]) -> dict:
    """
    Create a new assessment session (JSON scaffold).

    Returns session dict with initialized fields ready to save.
    """
    from datetime import datetime
    now = int(time.time())
    iso_date = datetime.fromtimestamp(now).isoformat() + "Z"

    return {
        "version": 2,
        "patient_id": patient_id,
        "session_label": f"Assessment - {regions[0] if regions else 'General'}" if regions else "Assessment",
        "session_name": f"{patient_id}_{datetime.now().strftime('%d_%m_%Y_%H%M')}",
        "created": now,
        "modified": now,
        "regions": regions,
        "launched_by": "tui",
        "workflow_stage": "01_consent",
        "body_chart_requested": False,
        "body_chart_complete": False,
        "ui": {
            "layout_mode": 0,
            "right_slot_views": [0, 1],
        },
        "subjective": {
            "strokes": [],
            "notes": [],
            "arrows": [],
            "link_matrix": [],
            "link_relations": [],
            "link_summary_active": False,
            "link_summary_view": 0,
            "link_summary_bx": 12.0,
            "link_summary_by": 378.0,
        },
        "objective": {
            "zones": [],
            "points": [],
        },
        "neuro": {},
        "assessment": {
            "consent": {
                "consent_to_proceed": None,
                "consent_sensitive_topics": None,
                "preferred_name": "",
                "pain_multifactorial_explained": None,
                "education_as_treatment_explained": None,
                "patient_expectations": "",
                "reason_for_attending": "",
                "cause_understanding": None,
                "cause_understanding_detail": "",
                "prognosis_expectations": "",
                "treatment_preference": "",
            },
            "history": "",
            "agg_factors": "",
            "ease_factors": "",
            "behaviour_24hr": "",
            "diagnosis": "",
            "plan": "",
            "clinical_notes": "",
            "modified": now,
        },
        "report": {
            "assessment": "",
            "plan": "",
            "clinical_notes": "",
            "note_subj": [],
        },
    }
