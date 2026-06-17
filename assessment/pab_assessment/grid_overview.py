"""Ctrl+G grid overview — full heading map for rapid section/subsection navigation."""

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer
from textual.message import Message
from textual.widgets import Static


# ── Heading data ─────────────────────────────────────────────────────────────
# Each entry: (section_id, display_label, [(heading_label, anchor_id), ...])

SUBJ_GRID_DATA: list[tuple[str, str, list[tuple[str, str]]]] = [
    ("01_consent", "01 Consent", [
        ("Consent",  "cs_consent"),
        ("Framing",  "cs_framing"),
        ("ICE+",     "cs_ice"),
        ("Goals",    "consent_goals"),
        ("Beliefs",  "cs_beliefs"),
    ]),
    ("02_subjective", "02 Subjective", [
        ("Symptoms",     "subj_symptoms"),
        ("History",      "subj_history"),
        ("Flare-ups",    "subj_flareups"),
        ("Mgmt",         "subj_management"),
        ("Activity",     "subj_activity"),
        ("Work",         "subj_work"),
        ("Sleep",        "subj_sleep"),
        ("24Hr",         "subj_24hr"),
        ("Psychosocial", "subj_psychosocial"),
        ("Goals",        "subj_goals"),
        ("Risk",         "subj_suicide"),
    ]),
    ("03_medical", "03 Medical", [
        ("Comorbid",     "med_comorbidities"),
        ("CVD Risk",     "med_cardiovascular"),
        ("Red Flags",    "med_red_flags"),
        ("Differential", "med_differential"),
        ("Medications",  "med_medications"),
    ]),
    ("04_objective", "04 Objective →", [
        ("General Obs",  "01_general"),
        ("Active",       "02_active"),
        ("Passive",      "03_passive"),
        ("Neurological", "04_neurological"),
        ("Sensory",      "05_sensory"),
        ("Muscle",       "06_muscle"),
        ("Functional",   "07_functional"),  # internal ID unchanged
        ("Special",      "08_special"),
    ]),
    ("04_pain_classification", "04 Pain Class", [
        ("Inflamm",      "pc_inflammatory"),
        ("Nociceptive",  "pc_nociceptive"),
        ("Neuropathic",  "pc_neuropathic"),
        ("Nociplastic",  "pc_nociplastic"),
        ("Central",      "pc_central"),
        ("Fibro",        "pc_fibromyalgia"),
        ("BACPAP",       "pc_bacpap"),
        ("Summary",      "pc_summary"),
    ]),
    ("05_outcome_measures", "05 Outcomes", [
        ("PSFS",       "om_psfs"),
        ("BPI",        "om_bpi"),
        ("DASS",       "om_dass"),
        ("PCS",        "om_pcs"),
        ("PSEQ/PCL",   "om_pseq"),
        ("Sleep",      "om_sleep"),
        ("Additional", "om_additional"),
        ("Hypothesis", "om_hypothesis"),
    ]),
    ("06_diagnosis", "06 Diagnosis", [
        ("Overview",    "dx_overview"),
        ("Primary",     "dx_primary"),
        ("Post-Surg",   "dx_surgical"),
        ("Post-Trauma", "dx_traumatic"),
        ("MSK",         "dx_msk"),
        ("Neuro",       "dx_neuropathic"),
        ("Mixed",       "dx_mixed"),
    ]),
    ("07_barriers", "07 Barriers", [
        ("Physical",  "br_physical"),
        ("Neuro",     "br_neuro"),
        ("Nocip",     "br_nocip"),
        ("Psych",     "br_psych"),
        ("Sleep/Soc", "br_sleep"),
        ("Medical",   "br_medical"),
        ("Custom",    "br_custom"),
    ]),
    ("08_rx_plan", "08 Rx Plan", [
        ("Treatment", "rp_treatment"),
        ("Session 1", "rp_session1"),
        ("Day 1",     "rp_day1"),
        ("Follow-Up", "rp_followup"),
    ]),
]

OBJ_GRID_DATA: list[tuple[str, str, list[tuple[str, str]]]] = [
    ("01_general", "01 General", [
        ("Physical",   "go_physical"),
        ("Posture",    "go_posture"),
        ("Functional", "go_functional_movement"),
    ]),
    ("07_functional", "02 Functional", [
        ("Goals",          "fn_goals"),
        ("Functional Mvt", "fn_movement"),
        ("Balance",        "fn_balance"),
        ("Timed",          "fn_timed"),
    ]),
    ("02_active", "03 Active Mvt", [
        ("Lumbar",   "am_lumbar"),
        ("Thoracic", "am_thoracic"),
    ]),
    ("03_passive", "04 Passive/OP", [
        ("Overpressure", "pm_overpressure"),
        ("PAIVMs",       "pm_paivms"),
    ]),
    ("04_neurological", "05 Neurology", [
        ("UL Reflex",       "nr_ul_reflexes"),
        ("UL Myotomes",     "nr_ul_myotomes"),
        ("UL Dermatomes",   "nr_ul_dermatomes"),
        ("UL Neurodynamics","nr_ul_neurodynamics"),
        ("LL Reflex",       "nr_reflexes"),
        ("LL Myotomes",     "nr_myotomes"),
        ("LL Dermatomes",   "nr_dermatomes"),
        ("LL Neurodynamics","nr_neurodynamics"),
        ("UMN",             "nr_umn"),
    ]),
    ("05_sensory", "06 Sensory", [
        ("Hyposensitivity",  "sn_hyposensitivity"),
        ("Hypersensitivity", "sn_hypersensitivity"),
    ]),
    ("06_muscle", "07 Muscle", [
        ("Length",       "ml_length"),
        ("Activation",   "ml_activation"),
        ("Trunk Str",    "ml_strength_trunk"),
        ("Hip Str",      "ml_strength_hip"),
        ("SIJ",          "ml_sij"),
    ]),
]


# ── Cursor helpers ───────────────────────────────────────────────────────────

def section_to_cursor(section_id: str, grid_data: list) -> tuple[int, int]:
    """Return (row, 0) for the first grid row matching section_id, else (0, 0)."""
    for row_idx, (sid, _, headings) in enumerate(grid_data):
        if sid == section_id and headings:
            return (row_idx, 0)
    return (0, 0)


# ── Tick helper ───────────────────────────────────────────────────────────────

def _section_has_data(data: dict) -> bool:
    """True if any field in collected section data has a meaningful value."""
    for v in data.values():
        if v is True:
            return True
        if isinstance(v, str) and v.strip():
            return True
        if isinstance(v, dict) and _section_has_data(v):
            return True
    return False


# ── Heading button ────────────────────────────────────────────────────────────

class _HeadingButton(Static):
    """Single clickable/focusable cell in the grid."""

    can_focus = True

    class Pressed(Message):
        def __init__(self, row: int, col: int) -> None:
            super().__init__()
            self.row = row
            self.col = col

    DEFAULT_CSS = """
    _HeadingButton {
        height: 3;
        width: auto;
        padding: 1 1;
        margin: 0 1 0 0;
        background: $panel;
        color: $text;
        content-align: center middle;
    }
    _HeadingButton:focus {
        background: $accent;
        color: $background;
        text-style: bold;
    }
    _HeadingButton:hover {
        background: $boost;
        color: $text;
    }
    """

    def __init__(self, label: str, row: int, col: int, **kwargs) -> None:
        super().__init__(label, **kwargs)
        self._row = row
        self._col = col
        self._base_label = label

    def on_click(self) -> None:
        self.post_message(self.Pressed(self._row, self._col))

    def on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            self.post_message(self.Pressed(self._row, self._col))
            event.stop()

    def set_tick(self, has_data: bool) -> None:
        self.update(f"✓ {self._base_label}" if has_data else self._base_label)


# ── Grid overview widget ──────────────────────────────────────────────────────

class GridOverview(ScrollableContainer):
    """Full-content-area heading map. Ctrl+G or Escape dismisses."""

    BINDINGS = [
        Binding("escape", "dismiss",    show=False, priority=True),
        Binding("up",     "nav_up",     show=False, priority=True),
        Binding("down",   "nav_down",   show=False, priority=True),
        Binding("left",   "nav_left",   show=False, priority=True),
        Binding("right",  "nav_right",  show=False, priority=True),
    ]

    DEFAULT_CSS = """
    GridOverview {
        width: 1fr;
        height: 100%;
        background: $surface;
        padding: 1 0 0 0;
        display: none;
    }

    .grid-row {
        height: 3;
        width: 100%;
        margin-bottom: 0;
        padding: 0 1;
    }
    """

    class HeadingSelected(Message):
        def __init__(self, section_id: str, anchor_id: str) -> None:
            super().__init__()
            self.section_id = section_id
            self.anchor_id  = anchor_id

    class Dismissed(Message):
        pass

    def __init__(self, grid_data: list, **kwargs) -> None:
        super().__init__(**kwargs)
        self._grid_data = grid_data
        self._buttons: list[list[_HeadingButton]] = []
        self._cursor: tuple[int, int] = (0, 0)

    def compose(self) -> ComposeResult:
        for row_idx, (_, _, headings) in enumerate(self._grid_data):
            with Horizontal(classes="grid-row"):
                for col_idx, (h_label, _) in enumerate(headings):
                    yield _HeadingButton(
                        h_label, row_idx, col_idx,
                        id=f"gh_{row_idx}_{col_idx}",
                    )

    def on_mount(self) -> None:
        self._buttons = []
        for row_idx, (_, _, headings) in enumerate(self._grid_data):
            row: list[_HeadingButton] = []
            for col_idx in range(len(headings)):
                try:
                    row.append(self.query_one(f"#gh_{row_idx}_{col_idx}", _HeadingButton))
                except Exception:
                    pass
            self._buttons.append(row)

    # ── Public API ────────────────────────────────────────────────────────────

    def open(self, has_data: dict[str, bool], cursor: tuple[int, int]) -> None:
        """Show grid, update ticks, restore cursor."""
        self._cursor = cursor
        self._refresh_ticks(has_data)
        self.display = True
        self._focus_cursor()

    def close(self) -> None:
        self.display = False

    def current_cursor(self) -> tuple[int, int]:
        return self._cursor

    # ── Internal ─────────────────────────────────────────────────────────────

    def _refresh_ticks(self, has_data: dict[str, bool]) -> None:
        for row_idx, (section_id, _, _) in enumerate(self._grid_data):
            tick = has_data.get(section_id, False)
            for btn in self._buttons[row_idx]:
                btn.set_tick(tick)

    def _focus_cursor(self) -> None:
        row, col = self._cursor
        # Skip empty rows (e.g. objective placeholder)
        for r in range(row, len(self._buttons)):
            if self._buttons[r]:
                try:
                    self._buttons[r][min(col, len(self._buttons[r]) - 1)].focus()
                except Exception:
                    pass
                return
        if self._buttons:
            for r, row_btns in enumerate(self._buttons):
                if row_btns:
                    row_btns[0].focus()
                    return

    def _move_cursor(self, row: int, col: int) -> None:
        self._cursor = (row, col)
        try:
            self._buttons[row][col].focus()
        except Exception:
            pass

    def _next_non_empty(self, start: int, direction: int) -> int:
        """Return nearest non-empty row index in direction (+1/-1), or start."""
        r = start + direction
        while 0 <= r < len(self._buttons):
            if self._buttons[r]:
                return r
            r += direction
        return start

    # ── Navigation actions ────────────────────────────────────────────────────

    def action_nav_up(self) -> None:
        row, col = self._cursor
        new_row = self._next_non_empty(row, -1)
        new_col = min(col, len(self._buttons[new_row]) - 1)
        self._move_cursor(new_row, new_col)

    def action_nav_down(self) -> None:
        row, col = self._cursor
        new_row = self._next_non_empty(row, +1)
        new_col = min(col, len(self._buttons[new_row]) - 1)
        self._move_cursor(new_row, new_col)

    def action_nav_left(self) -> None:
        row, col = self._cursor
        self._move_cursor(row, max(0, col - 1))

    def action_nav_right(self) -> None:
        row, col = self._cursor
        self._move_cursor(row, min(len(self._buttons[row]) - 1, col + 1))

    def action_dismiss(self) -> None:
        self.post_message(self.Dismissed())

    # ── Button press ──────────────────────────────────────────────────────────

    def on__heading_button_pressed(self, event: _HeadingButton.Pressed) -> None:
        row, col = event.row, event.col
        self._cursor = (row, col)
        section_id, _, headings = self._grid_data[row]
        _, anchor_id = headings[col]
        self.post_message(self.HeadingSelected(section_id, anchor_id))
