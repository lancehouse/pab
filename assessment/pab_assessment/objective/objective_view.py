"""Objective TUI: region topbar + sidebar navigation + section content area."""

import asyncio
import logging

from textual.app import ComposeResult, on
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.message import Message
from textual.widgets import Button, Static

from .sections.general import GeneralSection
from .sections.neurological import NeurologicalSection
from .sections.sensory import SensorySection
from .sections.functional import FunctionalSection
from .sections.region_section import RegionTabContent
from ..storage import objective_path, save_objective, save_raw_report, export_session_report


logger = logging.getLogger(__name__)

# ── Region toggle chip ───────────────────────────────────────────────────────

class _RegionButton(Static):
    """Region toggle chip — plain Static avoids Button's unoverrideable text-color CSS."""

    class Toggled(Message):
        def __init__(self, region_id: str) -> None:
            super().__init__()
            self.region_id = region_id

    DEFAULT_CSS = """
    _RegionButton {
        width: auto; height: 1; padding: 0 1; margin: 0 1 0 0;
        background: $panel; color: $text-muted;
    }
    _RegionButton.active-region {
        background: #2a5080; color: white; text-style: bold;
    }
    _RegionButton:hover { background: $boost; color: white; }
    """

    def __init__(self, label: str, region_id: str, **kwargs) -> None:
        super().__init__(label, **kwargs)
        self._region_id = region_id

    def on_click(self) -> None:
        self.post_message(self.Toggled(self._region_id))


# All available regions (topbar order). Phase 3A: only lumbar is shown.
_ALL_REGIONS: list[tuple[str, str]] = [
    ("lumbar",    "Lumbar"),
    ("cervical",  "Cervical"),
    ("shoulder",  "Shoulder"),
    ("thoracic",  "Thoracic"),
    ("hip",       "Hip"),
    ("knee",      "Knee"),
    ("elbow",     "Elbow"),
    ("ankle",     "Ankle"),
]

# Tabs that show per-region stacked blocks
_VARIABLE_TABS: list[tuple[str, str, str]] = [
    # (section_id,   section_key, display_label)
    ("02_active",  "active",  "02 Active Movement"),
    ("03_passive", "passive", "03 Passive / OP"),
    ("06_muscle",  "muscle",  "06 Muscle Testing"),
    ("08_special", "special", "08 Special Tests"),
]

# Generic fixed-content tabs
_GENERIC_TABS: list[tuple[str, str]] = [
    # (section_id, json_key)
    ("01_general",      "general"),
    ("04_neurological", "neurological"),
    ("05_sensory",      "sensory"),
    ("07_functional",   "functional"),
]


def _migrate_objective(old: dict) -> dict:
    """Migrate flat objective schema → region-based schema (lumbar auto-detected)."""
    new: dict = {}
    for key in ("general", "neurological", "sensory", "functional"):
        if key in old:
            new[key] = old[key]
    lumbar: dict = {}
    for old_key, new_key in (("active", "active"), ("passive", "passive"), ("muscle", "muscle")):
        if old_key in old:
            lumbar[new_key] = old[old_key]
    new["active_regions"] = ["lumbar"]
    new["lumbar"] = lumbar
    logger.info("Migrated flat objective schema → region schema (lumbar)")
    return new


# ── Region topbar ─────────────────────────────────────────────────────────────

class RegionTopbar(Static):
    """Horizontal strip of region toggle buttons above the objective content area."""

    class RegionToggled(Message):
        def __init__(self, region_id: str, active: bool) -> None:
            super().__init__()
            self.region_id = region_id
            self.active = active

    DEFAULT_CSS = """
    RegionTopbar {
        height: 3;
        width: 100%;
        layout: horizontal;
        align: left middle;
        padding: 0 1;
        border-bottom: solid $border;
        background: $panel-darken-1;
    }
    RegionTopbar .region_label {
        width: auto;
        height: 1;
        margin-right: 1;
        color: $text-muted;
    }
    """

    def __init__(self, active_regions: list[str], **kwargs) -> None:
        super().__init__(**kwargs)
        self._active_regions = list(active_regions)

    def compose(self) -> ComposeResult:
        yield Static("Regions:", classes="region_label")
        for region_id, label in _ALL_REGIONS:
            chip = _RegionButton(label, region_id, id=f"rgn_{region_id}")
            if region_id in self._active_regions:
                chip.add_class("active-region")
            yield chip

    @on(_RegionButton.Toggled)
    def _on_region_chip_toggled(self, event: _RegionButton.Toggled) -> None:
        region_id = event.region_id
        try:
            chip = self.query_one(f"#rgn_{region_id}", _RegionButton)
        except Exception:
            return
        active = chip.has_class("active-region")
        if active:
            chip.remove_class("active-region")
            self._active_regions = [r for r in self._active_regions if r != region_id]
        else:
            chip.add_class("active-region")
            self._active_regions.append(region_id)
        self.post_message(self.RegionToggled(region_id, not active))

    def set_active_regions(self, regions: list[str]) -> None:
        self._active_regions = list(regions)
        for region_id, _ in _ALL_REGIONS:
            try:
                chip = self.query_one(f"#rgn_{region_id}", _RegionButton)
                if region_id in regions:
                    chip.add_class("active-region")
                else:
                    chip.remove_class("active-region")
            except Exception:
                pass


# ── Sidebar ───────────────────────────────────────────────────────────────────

class ObjectiveSidebar(Static):
    """Left sidebar navigation for Objective TUI."""

    DEFAULT_CSS = """
    ObjectiveSidebar {
        width: 22;
        height: 100%;
        border-right: solid $border;
        background: $panel;
        layout: vertical;
        padding: 1 0;
    }
    ObjectiveSidebar Button {
        width: 100%;
        height: auto;
        border: none;
        background: $panel;
        margin: 0;
        padding: 0 1;
    }
    ObjectiveSidebar Button:hover { background: $boost; }
    ObjectiveSidebar Button.active { background: $accent; text-style: bold; }
    ObjectiveSidebar .back {
        background: $panel-darken-1;
        color: $text-muted;
        margin-top: 1;
    }
    ObjectiveSidebar .back:hover { background: $boost; color: $text; }
    """

    SECTION_LABELS = {
        "01_general":      "01 General Obs",
        "02_active":       "02 Active Mvmt",
        "03_passive":      "03 Passive/OP",
        "04_neurological": "04 Neurological",
        "05_sensory":      "05 Sensory",
        "06_muscle":       "06 Muscle Test",
        "07_functional":   "07 Functional",
        "08_special":      "08 Special Tests",
    }

    def __init__(self, on_section_selected: callable, on_back: callable, **kwargs):
        super().__init__(**kwargs)
        self._on_section_selected = on_section_selected
        self._on_back = on_back
        self.active_section = "01_general"

    def compose(self) -> ComposeResult:
        for section_id, label in self.SECTION_LABELS.items():
            btn = Button(label, id=f"objnav_{section_id}")
            if section_id == "01_general":
                btn.add_class("active")
            yield btn
        yield Button("← Subjective", id="objnav_back", classes="back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "objnav_back":
            self._on_back()
        elif bid and bid.startswith("objnav_"):
            section_id = bid[7:]
            self.set_active(section_id)
            self._on_section_selected(section_id)

    def set_active(self, section_id: str) -> None:
        for btn in self.query(Button):
            btn.remove_class("active")
        try:
            self.query_one(f"#objnav_{section_id}", Button).add_class("active")
            self.active_section = section_id
        except Exception:
            pass


# ── Main view ─────────────────────────────────────────────────────────────────

class ObjectiveAssessmentView(Container):
    """Main content area for Objective TUI: region topbar + sidebar + section panels."""

    DEFAULT_CSS = """
    ObjectiveAssessmentView {
        width: 100%;
        height: 100%;
        layout: vertical;
    }
    #obj_main_area {
        width: 100%;
        height: 1fr;
        layout: horizontal;
    }
    #obj_section_content {
        width: 1fr;
        height: 100%;
    }
    #obj_section_content_inner {
        width: 100%;
        height: auto;
    }
    """

    class SaveStateChanged(Message):
        def __init__(self, state: str) -> None:
            super().__init__()
            self.state = state

    class ExitRequested(Message):
        """Posted when the ← back button is pressed."""

    def __init__(self, session_file: str = "", **kwargs):
        super().__init__(**kwargs)
        self.session_file = session_file
        self.sections: dict = {}
        self.active_section_id = "01_general"
        self._active_regions: list[str] = ["lumbar"]
        self._save_task: asyncio.Task | None = None
        self._mounted = False
        self._pending_load: dict | None = None

    def compose(self) -> ComposeResult:
        yield RegionTopbar(self._active_regions, id="obj_region_topbar")
        with Container(id="obj_main_area"):
            yield ObjectiveSidebar(
                on_section_selected=self._show_section,
                on_back=self._go_back,
                id="obj_sidebar",
            )
            yield ScrollableContainer(
                Vertical(id="obj_section_content_inner"),
                id="obj_section_content",
            )

    def on_mount(self) -> None:
        # Build generic sections
        generic_instances = {
            "01_general":      GeneralSection(id="obj_section_01_general"),
            "04_neurological": NeurologicalSection(id="obj_section_04_neurological"),
            "05_sensory":      SensorySection(id="obj_section_05_sensory"),
            "07_functional":   FunctionalSection(id="obj_section_07_functional"),
        }
        # Build variable (region-based) tab containers
        variable_instances = {
            section_id: RegionTabContent(
                section_key, tab_label,
                id=f"obj_section_{section_id}",
            )
            for section_id, section_key, tab_label in _VARIABLE_TABS
        }
        self.sections = {**generic_instances, **variable_instances}

        content = self.query_one("#obj_section_content_inner", Vertical)
        for section_id, section in self.sections.items():
            if section_id != self.active_section_id:
                section.display = False
            content.mount(section)

        # Pre-activate default regions into variable tabs
        for region_id in self._active_regions:
            self._mount_region(region_id)

        self._mounted = True
        if self._pending_load is not None:
            data = self._pending_load
            self._pending_load = None
            self.load_session(self.session_file, data)

    def on_unmount(self) -> None:
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()

    # ── Region management ─────────────────────────────────────────────────────

    def _mount_region(self, region_id: str) -> None:
        """Mount a region into all variable tabs."""
        for section_id, _, _ in _VARIABLE_TABS:
            tab = self.sections.get(section_id)
            if isinstance(tab, RegionTabContent):
                tab.mount_region(region_id)

    def _unmount_region(self, region_id: str) -> None:
        """Remove a region from all variable tabs."""
        for section_id, _, _ in _VARIABLE_TABS:
            tab = self.sections.get(section_id)
            if isinstance(tab, RegionTabContent):
                tab.unmount_region(region_id)

    def _sync_active_regions(self, regions: list[str]) -> None:
        """Sync variable tabs and topbar to match regions list."""
        current = set(self._active_regions)
        target = set(regions)
        for rid in current - target:
            self._unmount_region(rid)
        for rid in target - current:
            self._mount_region(rid)
        self._active_regions = list(regions)
        try:
            self.query_one("#obj_region_topbar", RegionTopbar).set_active_regions(regions)
        except Exception:
            pass

    @on(RegionTopbar.RegionToggled)
    def _on_region_toggled(self, event: RegionTopbar.RegionToggled) -> None:
        if event.active:
            if event.region_id not in self._active_regions:
                self._active_regions.append(event.region_id)
                self._mount_region(event.region_id)
        else:
            self._active_regions = [r for r in self._active_regions if r != event.region_id]
            self._unmount_region(event.region_id)
        self._schedule_save()

    # ── Session load ──────────────────────────────────────────────────────────

    def load_session(self, session_file: str, data: dict) -> None:
        if not self._mounted:
            self._pending_load = data
            self.session_file = session_file
            return

        self.session_file = session_file
        assessment = data.get("assessment", {})

        # Migrate old flat schema if needed
        if "active_regions" not in assessment and any(
            k in assessment for k in ("active", "passive", "muscle")
        ):
            assessment = _migrate_objective(assessment)

        # Sync regions
        regions = assessment.get("active_regions", ["lumbar"])
        self._sync_active_regions(regions)

        # Load generic sections
        for section_id, json_key in _GENERIC_TABS:
            section = self.sections.get(section_id)
            if section is None:
                continue
            section.session_file = session_file
            section.load(assessment.get(json_key, {}))

        # Load per-region data into variable tabs
        for region_id in self._active_regions:
            region_data = assessment.get(region_id, {})
            for section_id, section_key, _ in _VARIABLE_TABS:
                tab = self.sections.get(section_id)
                if not isinstance(tab, RegionTabContent):
                    continue
                container = tab.get_container(region_id)
                if container:
                    container.load(region_data.get(section_key, {}))

    # ── Section visibility ────────────────────────────────────────────────────

    def _show_section(self, section_id: str) -> None:
        if section_id == self.active_section_id:
            return
        current = self.sections.get(self.active_section_id)
        if current:
            current.display = False
        new = self.sections.get(section_id)
        if new:
            new.display = True
            self.active_section_id = section_id
        try:
            self.query_one("#obj_sidebar", ObjectiveSidebar).set_active(section_id)
        except Exception:
            pass

    def _go_back(self) -> None:
        self.post_message(self.ExitRequested())

    # ── Autosave ──────────────────────────────────────────────────────────────

    @on(GeneralSection.FieldChanged)
    @on(NeurologicalSection.FieldChanged)
    @on(SensorySection.FieldChanged)
    @on(FunctionalSection.FieldChanged)
    @on(RegionTabContent.FieldChanged)
    def _on_section_field_changed(self) -> None:
        self._schedule_save()

    def _schedule_save(self) -> None:
        if self._save_task:
            self._save_task.cancel()
        self.post_message(self.SaveStateChanged("pending"))

        async def delayed_save():
            await asyncio.sleep(2.0)
            await self._do_save()

        self._save_task = asyncio.create_task(delayed_save())

    async def _do_save(self) -> None:
        if not self.session_file:
            return
        self.post_message(self.SaveStateChanged("saving"))

        assessment_data: dict = {}
        sections_complete: dict[str, bool] = {}

        # Generic sections
        for section_id, json_key in _GENERIC_TABS:
            section = self.sections.get(section_id)
            if section is None:
                continue
            assessment_data[json_key] = section.collect()
            sections_complete[section_id] = section.is_complete()

        # Active regions list
        assessment_data["active_regions"] = list(self._active_regions)

        # Per-region data from variable tabs
        for region_id in self._active_regions:
            region_data: dict = {}
            for section_id, section_key, _ in _VARIABLE_TABS:
                tab = self.sections.get(section_id)
                if not isinstance(tab, RegionTabContent):
                    continue
                container = tab.get_container(region_id)
                if container:
                    region_data[section_key] = container.collect()
                sections_complete[section_id] = tab.is_complete()
            assessment_data[region_id] = region_data

        save_objective(self.session_file, assessment_data, sections_complete)
        save_raw_report(self.session_file)
        export_session_report(self.session_file)
        self.post_message(self.SaveStateChanged("saved"))
