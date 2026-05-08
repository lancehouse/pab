"""Assessment view with section navigation."""

import asyncio
import json
import logging
from pathlib import Path

from textual.app import ComposeResult, on
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Button, Label, Static

from .sections.consent import ConsentSection
from .sections.subjective import SubjectiveSection
from .sections.medical import MedicalSection
from .sections.pain_classification import PainClassificationSection
from .sections.outcome_measures import OutcomeMeasuresSection
from .sections.diagnosis import DiagnosisSection
from .sections.barriers import BarriersSection
from .sections.placeholder import PlaceholderSection
from .storage import (
    save_consent, load_consent,
    save_subjective, load_subjective,
    save_medical, load_medical,
    save_pain_classification, load_pain_classification,
    save_outcome_measures, load_outcome_measures,
    save_diagnosis, load_diagnosis,
    save_barriers, load_barriers,
)


logger = logging.getLogger(__name__)


class SectionNav(Static):
    """Left sidebar with section navigation buttons."""

    DEFAULT_CSS = """
    SectionNav {
        width: 20;
        height: 100%;
        border-right: solid $border;
        background: $panel;
        layout: vertical;
        padding: 1 0;
    }

    SectionNav Button {
        width: 100%;
        height: auto;
        border: none;
        background: $panel;
        margin: 0;
        padding: 0 1;
    }

    SectionNav Button:hover {
        background: $boost;
    }

    SectionNav Button.active {
        background: $accent;
        text-style: bold;
    }

    """

    SECTION_LABELS = {
        "01_consent": "01 Consent",
        "02_subjective": "02 Subjective",
        "03_medical": "03 Medical",
        "04_pain_classification": "04 Classification",
        "05_outcome_measures": "05 Outcomes",
        "06_diagnosis": "06 Diagnosis",
        "07_barriers": "07 Barriers",
    }

    def __init__(self, on_section_selected: callable, **kwargs):
        super().__init__(**kwargs)
        self.on_section_selected = on_section_selected
        self.active_section = "01_consent"
        self.section_indicators = {}  # section_id -> completion bool

    def compose(self) -> ComposeResult:
        """Create navigation buttons for all 7 sections."""
        for section_id in [
            "01_consent",
            "02_subjective",
            "03_medical",
            "04_pain_classification",
            "05_outcome_measures",
            "06_diagnosis",
            "07_barriers",
        ]:
            label = self.SECTION_LABELS.get(section_id, section_id)
            btn = Button(label, id=f"nav_{section_id}")
            if section_id == "01_consent":
                btn.add_class("active")
            yield btn

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle section button clicks."""
        button_id = event.button.id
        if button_id.startswith("nav_"):
            section_id = button_id[4:]  # Remove "nav_" prefix
            self.set_active(section_id)
            self.on_section_selected(section_id)

    def set_active(self, section_id: str) -> None:
        """Highlight the active section button."""
        # Remove active class from all buttons
        for btn in self.query(Button):
            btn.remove_class("active")

        # Add active class to the selected button
        try:
            active_btn = self.query_one(f"#nav_{section_id}", Button)
            active_btn.add_class("active")
            self.active_section = section_id
        except:
            pass

    def set_indicator(self, section_id: str, complete: bool) -> None:
        """Update the completion indicator (●/○) for a section.

        Currently just marks in our dict; rendering happens via button label.
        """
        self.section_indicators[section_id] = complete

    def refresh_indicators(self, sections: dict[str, bool]) -> None:
        """Update all section indicators based on completion dict."""
        for section_id, complete in sections.items():
            self.set_indicator(section_id, complete)

    def set_tab_status(self, section_id: str, status: str) -> None:
        """Set visual status on a section button via variant: 'pending', 'clear', or 'positive'."""
        variant_map = {"pending": "warning", "positive": "error", "clear": "success"}
        try:
            btn = self.query_one(f"#nav_{section_id}", Button)
            btn.variant = variant_map.get(status, "default")
        except Exception:
            pass


class AssessmentView(Container):
    """Main assessment view with section navigation and content area."""

    DEFAULT_CSS = """
    AssessmentView {
        width: 100%;
        height: 100%;
        layout: horizontal;
    }

    #section_content {
        width: 1fr;
        height: 100%;
    }

    #section_content_inner {
        width: 100%;
        height: 100%;
    }
    """

    def __init__(self, session_file: str = "", **kwargs):
        super().__init__(**kwargs)
        self.session_file = session_file
        self.sections = {}
        self.active_section_id = "01_consent"
        self._save_task: asyncio.Task | None = None
        self._mounted = False
        self._pending_load: dict | None = None

    def compose(self) -> ComposeResult:
        """Create sidebar nav + content area."""
        # Navigation sidebar
        yield SectionNav(on_section_selected=self._show_section, id="section_nav")

        # Content area (sections will be mounted in on_mount)
        yield ScrollableContainer(Vertical(id="section_content_inner"), id="section_content")

    def on_mount(self) -> None:
        """Initialize after mounting."""
        # Create all 7 section instances
        self.sections = {
            "01_consent": ConsentSection(id="section_01_consent"),
            "02_subjective": SubjectiveSection(id="section_02_subjective"),
            "03_medical": MedicalSection(id="section_03_medical"),
            "04_pain_classification": PainClassificationSection(id="section_04_pain_classification"),
            "05_outcome_measures": OutcomeMeasuresSection(id="section_05_outcome_measures"),
            "06_diagnosis": DiagnosisSection(id="section_06_diagnosis"),
            "07_barriers": BarriersSection(id="section_07_barriers"),
        }

        # Mount all sections to content area
        content = self.query_one("#section_content_inner", Vertical)
        for section_id, section in self.sections.items():
            if section_id != self.active_section_id:
                section.display = False
            content.mount(section)

        # Mark as mounted and process any pending load
        self._mounted = True
        if self._pending_load:
            data = self._pending_load
            self._pending_load = None
            self.load_session(self.session_file, data)

    def load_session(self, session_file: str, data: dict) -> None:
        """Load session data into all sections."""
        if not self._mounted:
            # Defer load until mounted
            self._pending_load = data
            self.session_file = session_file
            return

        self.session_file = session_file

        # Load consent section
        consent_data = data.get("assessment", {}).get("consent", {})
        if "01_consent" in self.sections:
            consent_section = self.sections["01_consent"]
            consent_section.session_file = session_file
            consent_section.load(consent_data)

        # Load subjective section
        subjective_data = data.get("assessment", {}).get("subjective", {})
        if "02_subjective" in self.sections:
            subjective_section = self.sections["02_subjective"]
            subjective_section.session_file = session_file
            subjective_section.load(subjective_data)

        # Load medical section
        medical_data = data.get("assessment", {}).get("medical", {})
        if "03_medical" in self.sections:
            medical_section = self.sections["03_medical"]
            medical_section.session_file = session_file
            medical_section.load(medical_data)

        # Load pain classification section
        pain_data = data.get("assessment", {}).get("pain_classification", {})
        if "04_pain_classification" in self.sections:
            pain_section = self.sections["04_pain_classification"]
            pain_section.session_file = session_file
            pain_section.load(pain_data)

        # Load outcome measures section
        om_data = data.get("assessment", {}).get("outcome_measures", {})
        if "05_outcome_measures" in self.sections:
            om_section = self.sections["05_outcome_measures"]
            om_section.session_file = session_file
            om_section.load(om_data)

        # Load barriers section
        br_data = data.get("assessment", {}).get("barriers", {})
        if "07_barriers" in self.sections:
            br_section = self.sections["07_barriers"]
            br_section.session_file = session_file
            if isinstance(br_data, dict):
                br_section.load(br_data)

        # Load diagnosis section
        dx_data = data.get("assessment", {}).get("diagnosis", {})
        if "06_diagnosis" in self.sections:
            dx_section = self.sections["06_diagnosis"]
            dx_section.session_file = session_file
            if isinstance(dx_data, dict):
                dx_section.load(dx_data)

        # Update nav indicators and medical tab color
        self._refresh_nav_indicators(data)
        self._update_medical_tab_color()

    def _show_section(self, section_id: str) -> None:
        """Switch to a different section."""
        if section_id == self.active_section_id:
            return

        # Capture medical tab status when leaving the medical section
        if self.active_section_id == "03_medical":
            self._update_medical_tab_color()

        # Hide current section
        current = self.sections.get(self.active_section_id)
        if current:
            current.display = False

        # Show new section
        new = self.sections.get(section_id)
        if new:
            new.display = True
            self.active_section_id = section_id

        # Refresh cross-reference badges when entering pain classification or outcome measures
        if section_id == "04_pain_classification":
            pain_section = self.sections.get("04_pain_classification")
            if pain_section:
                pain_section.update_cross_refs()
        elif section_id == "05_outcome_measures":
            om_section = self.sections.get("05_outcome_measures")
            if om_section:
                om_section.update_cross_refs()
        elif section_id == "06_diagnosis":
            dx_section = self.sections.get("06_diagnosis")
            if dx_section:
                dx_section.update_cross_refs()
        elif section_id == "07_barriers":
            br_section = self.sections.get("07_barriers")
            if br_section:
                br_section.update_cross_refs()

        # Update nav highlight
        nav = self.query_one("#section_nav", SectionNav)
        nav.set_active(section_id)

    def _update_medical_tab_color(self) -> None:
        """Update the 03 Medical nav button to orange/green/red based on urgent red flag review."""
        try:
            medical_section = self.sections.get("03_medical")
            if medical_section is None:
                return
            status = medical_section.urgent_red_flag_status()
            nav = self.query_one("#section_nav", SectionNav)
            nav.set_tab_status("03_medical", status)
        except Exception:
            pass

    def _refresh_nav_indicators(self, data: dict) -> None:
        """Update all section completion indicators."""
        from .storage import get_sections_complete

        sections_complete = get_sections_complete(data)

        nav = self.query_one("#section_nav", SectionNav)
        nav.refresh_indicators(sections_complete)

    def _schedule_save(self) -> None:
        """Schedule a debounced save after 2 seconds of inactivity."""
        if self._save_task:
            self._save_task.cancel()

        async def delayed_save():
            await asyncio.sleep(2.0)
            await self._do_save()

        self._save_task = asyncio.create_task(delayed_save())

    async def _do_save(self) -> None:
        """Execute the save for the active section."""
        if not self.session_file:
            return

        if self.active_section_id == "01_consent":
            consent_section = self.sections["01_consent"]
            consent_data = consent_section.collect()
            save_consent(self.session_file, consent_data)

            # Reload section indicators
            data = json.loads(Path(self.session_file).read_text())
            self._refresh_nav_indicators(data)

        elif self.active_section_id == "02_subjective":
            subjective_section = self.sections["02_subjective"]
            subjective_data = subjective_section.collect()
            save_subjective(self.session_file, subjective_data)

            data = json.loads(Path(self.session_file).read_text())
            self._refresh_nav_indicators(data)

        elif self.active_section_id == "03_medical":
            medical_section = self.sections["03_medical"]
            medical_data = medical_section.collect()
            save_medical(self.session_file, medical_data)

            data = json.loads(Path(self.session_file).read_text())
            self._refresh_nav_indicators(data)
            self._update_medical_tab_color()

        elif self.active_section_id == "04_pain_classification":
            pain_section = self.sections["04_pain_classification"]
            pain_data = pain_section.collect()
            save_pain_classification(self.session_file, pain_data)

            data = json.loads(Path(self.session_file).read_text())
            self._refresh_nav_indicators(data)

        elif self.active_section_id == "05_outcome_measures":
            om_section = self.sections["05_outcome_measures"]
            om_data = om_section.collect()
            save_outcome_measures(self.session_file, om_data)

            data = json.loads(Path(self.session_file).read_text())
            self._refresh_nav_indicators(data)

        elif self.active_section_id == "06_diagnosis":
            dx_section = self.sections["06_diagnosis"]
            dx_data = dx_section.collect()
            save_diagnosis(self.session_file, dx_data)

            data = json.loads(Path(self.session_file).read_text())
            self._refresh_nav_indicators(data)

        elif self.active_section_id == "07_barriers":
            br_section = self.sections["07_barriers"]
            br_data = br_section.collect()
            save_barriers(self.session_file, br_data)

            data = json.loads(Path(self.session_file).read_text())
            self._refresh_nav_indicators(data)

    def on_section_01_consent_field_changed(self) -> None:
        """Handle field changes from ConsentSection."""
        self._schedule_save()

    def on_section_02_subjective_field_changed(self) -> None:
        """Handle field changes from SubjectiveSection."""
        self._schedule_save()

    def on_section_03_medical_field_changed(self) -> None:
        """Handle field changes from MedicalSection."""
        self._schedule_save()
        self._update_medical_tab_color()

    def on_section_04_pain_classification_field_changed(self) -> None:
        """Handle field changes from PainClassificationSection."""
        self._schedule_save()

    def on_section_05_outcome_measures_field_changed(self) -> None:
        """Handle field changes from OutcomeMeasuresSection."""
        self._schedule_save()

    def on_section_06_diagnosis_field_changed(self) -> None:
        """Handle field changes from DiagnosisSection."""
        self._schedule_save()

    def on_section_07_barriers_field_changed(self) -> None:
        """Handle field changes from BarriersSection."""
        self._schedule_save()
