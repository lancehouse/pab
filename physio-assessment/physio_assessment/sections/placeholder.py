"""Placeholder sections for future implementation (02-07)."""

from textual.app import ComposeResult
from textual.widgets import Label

from .base import BaseSection


class PlaceholderSection(BaseSection):
    """Placeholder section for sections not yet implemented."""

    SECTION_NAMES = {
        "02_subjective": "Subjective History",
        "03_medical": "Medical Screening",
        "04_pain_classification": "Pain Classification",
        "05_outcome_measures": "Outcome Measures",
        "06_diagnosis": "Diagnosis & Goals",
        "07_barriers": "Barriers & Treatment",
    }

    def __init__(self, section_id: str, **kwargs):
        super().__init__(**kwargs)
        self.section_id = section_id
        self.section_name = self.SECTION_NAMES.get(section_id, "Unknown Section")

    def compose(self) -> ComposeResult:
        yield Label(f"Coming soon — {self.section_name}")

    def load(self, data: dict) -> None:
        """Placeholder: no-op."""
        pass

    def collect(self) -> dict:
        """Placeholder: return empty dict."""
        return {}

    def is_complete(self) -> bool:
        """Placeholder: always incomplete."""
        return False
