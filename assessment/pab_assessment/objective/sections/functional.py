"""Functional Assessment — 07 Objective Examination."""

from textual.app import ComposeResult, on
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Input, Label, Static, TextArea

from ...nav import escape_to_neighbor
from ...sections.base import BaseSection
from ...widgets import GridInput, RadioGroup


# ---------------------------------------------------------------------------
# Gang option sets
# ---------------------------------------------------------------------------

_GAIT2  = [("Norm", "success"), ("Antlgc", "warning")]
_STS3   = [("Norm", "success"), ("Hands",  "warning"), ("Asymm", "default")]
_SQ3    = [("Norm", "success"), ("Antlgc", "warning"), ("Asymm", "default")]
_LFT3   = [("Norm", "success"), ("Antlgc", "warning"), ("Asymm", "default")]
_CARRY2 = [("Norm", "success"), ("Antlgc", "warning")]
_REACH2 = [("Norm", "success"), ("Antlgc", "warning")]


# ---------------------------------------------------------------------------
# Row definitions
# ---------------------------------------------------------------------------

# Functional movement rows: (display label, radio id, radio options, input id)
_FM_ROWS: list[tuple[str, str, list, str]] = [
    ("Gait",         "ft_gait",  _GAIT2,  "ft_gait_obs"),
    ("Sit-to-stand", "ft_sts_q", _STS3,   "ft_sts_obs"),
    ("Squat",        "ft_squat", _SQ3,    "ft_squat_obs"),
    ("Lunge",        "ft_lunge", _SQ3,    "ft_lunge_obs"),
    ("Lifting",      "ft_lift",  _LFT3,   "ft_lift_obs"),
    ("Carrying",     "ft_carry", _CARRY2, "ft_carry_obs"),
    ("Reaching",     "ft_reach", _REACH2, "ft_reach_obs"),
]

_FM_INPUT_IDS = [r[3] for r in _FM_ROWS]

# Balance rows: (label, [input ids])
_BAL_ROWS: list[tuple[str, list]] = [
    ("Both legs",       ["ft_bal_both"]),
    ("Feet together",   ["ft_bal_feet"]),
    ("Tandem",          ["ft_bal_tandem"]),
    ("SLS eyes open",   ["ft_sls_eo_l",   "ft_sls_eo_r"]),
    ("SLS eyes closed", ["ft_sls_ec_l",   "ft_sls_ec_r"]),
    ("SLS foam 10cm",   ["ft_sls_foam_l", "ft_sls_foam_r"]),
]

# Timed capability measures: (label, id, unit)
_CAP_ROWS: list[tuple[str, str, str]] = [
    ("TUG  (3m chair→chair)", "ft_tug",   "s"),
    ("5× Sit-to-Stand",       "ft_sts5",  "s"),
    ("10m walk comfortable",  "ft_10m_e", "m/s"),
    ("10m walk fast",         "ft_10m_f", "m/s"),
    ("2 min walk",            "ft_2mw",   "m"),
]


# ---------------------------------------------------------------------------
# FunctionalSection
# ---------------------------------------------------------------------------

class FunctionalSection(BaseSection):
    """02 Functional — SMART Goals mirror + movement obs, balance, timed capability."""

    _nav_include_inputs = True  # include GridInput (balance/timed rows) in arrow-key nav

    class FieldChanged(Message):
        pass

    class GoalsChanged(Message):
        def __init__(self, goals: dict) -> None:
            super().__init__()
            self.goals = goals

    DEFAULT_CSS = """
    FunctionalSection {
        width: 100%;
        height: auto;
        padding: 0 1 2 1;
    }
    FunctionalSection .section_title { text-style: bold; margin-bottom: 0; }

    /* Functional movement rows — label + gang + input */
    FunctionalSection .obs_row { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    FunctionalSection .obs_lbl { width: 16; height: 3; content-align: left middle; }
    FunctionalSection .obs_inp { width: 1fr; height: 3; padding: 0 1; }

    /* Inline TextArea rows — label beside text area */
    FunctionalSection .fm_ta_row { layout: horizontal; height: auto; width: 100%; margin-bottom: 1; }
    FunctionalSection .fm_ta_lbl { width: auto; padding-right: 1; height: auto; content-align: left top; }
    FunctionalSection .fm_ta     { width: 1fr; height: auto; min-height: 3; max-height: 12; padding: 0 1; }

    /* Balance / capability table */
    FunctionalSection .tbl_hdr     { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    FunctionalSection .tbl_hdr_lbl { width: 22; }
    FunctionalSection .tbl_hdr_col { width: 1fr; text-align: center; }
    FunctionalSection .tbl_row     { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    FunctionalSection .tbl_lbl     { width: 22; height: 3; content-align: left middle; }
    FunctionalSection .tbl_inp     { width: 1fr; height: 3; padding: 0 1; }
    FunctionalSection .tbl_empty   { width: 1fr; height: 3; }

    FunctionalSection TextArea { height: auto; min-height: 2; padding: 0 1; }
    FunctionalSection Label    { height: auto; margin-top: 0; }

    FunctionalSection .goal_row { layout: horizontal; height: auto; width: 100%; }
    FunctionalSection .goal_lbl { width: 4; height: auto; content-align: left top; padding-top: 0; }
    FunctionalSection .goal_ta  { width: 1fr; height: auto; min-height: 2; padding: 0 1; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._grid:     list[list[str]] = []
        self._grid_pos: dict[str, tuple[int, int]] = {}

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Label("02 Functional", classes="section_title")

        # ── SMART Goals (mirror of Consent / Subjective) ──────────────────────
        yield Label("— SMART Goals —", classes="subsection_header", id="fn_goals")
        yield Label("Shared with 01 Consent and 02 Subjective — edit in any section:",
                    classes="reference_note")
        for i in range(1, 5):
            with Horizontal(classes="goal_row"):
                yield Static(f"{i}.", classes="goal_lbl")
                yield TextArea(id=f"ft_goal_{i}", language="plain", classes="goal_ta")

        # ── Functional Movement Observation ───────────────────────────────────
        yield Label("Functional Movement", classes="subsection_header", id="fn_movement")
        for label, rid, opts, iid in _FM_ROWS:
            with Horizontal(classes="obs_row"):
                yield Static(label, classes="obs_lbl")
                yield RadioGroup(opts, id=rid)
                yield Input(placeholder="…", id=iid, classes="obs_inp")

        # Functional obs — inline TextArea
        with Horizontal(classes="fm_ta_row"):
            yield Static("Functional obs", classes="fm_ta_lbl")
            yield TextArea(id="ft_fm_obs", language="plain", classes="fm_ta")

        # Custom Functional test — inline TextArea
        with Horizontal(classes="fm_ta_row"):
            yield Static("Custom Functional test", classes="fm_ta_lbl")
            yield TextArea(id="ft_fm_custom", language="plain", classes="fm_ta")

        # ── Balance (Steffen 2002) ────────────────────────────────────────────
        yield Label("Balance  (Steffen 2002)", classes="subsection_header", id="fn_balance")
        with Horizontal(classes="tbl_hdr"):
            yield Static("",         classes="tbl_hdr_lbl")
            yield Static("Left  s",  classes="tbl_hdr_col")
            yield Static("Right  s", classes="tbl_hdr_col")
        for label, ids in _BAL_ROWS:
            with Horizontal(classes="tbl_row"):
                yield Static(label, classes="tbl_lbl")
                yield GridInput(placeholder="s", id=ids[0], classes="tbl_inp")
                if len(ids) == 2:
                    yield GridInput(placeholder="s", id=ids[1], classes="tbl_inp")
                else:
                    yield Static("", classes="tbl_empty")

        # ── Timed Capability Measures ─────────────────────────────────────────
        yield Label("Timed Capability Measures", classes="subsection_header", id="fn_timed")
        for label, fid, unit in _CAP_ROWS:
            with Horizontal(classes="tbl_row"):
                yield Static(label, classes="tbl_lbl")
                yield GridInput(placeholder=unit, id=fid, classes="tbl_inp")
                yield Static("", classes="tbl_empty")

        # ── Notes / Special Tests ─────────────────────────────────────────────
        yield Label("Special tests / notes:")
        yield TextArea(id="ft_notes", language="plain")

    # ------------------------------------------------------------------
    # Grid navigation — balance + capability rows
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        for _, ids in _BAL_ROWS:
            row_idx = len(self._grid)
            self._grid.append(ids[:])
            for col_idx, wid in enumerate(ids):
                self._grid_pos[wid] = (row_idx, col_idx)
        for _, fid, _ in _CAP_ROWS:
            row_idx = len(self._grid)
            self._grid.append([fid])
            self._grid_pos[fid] = (row_idx, 0)

    def _focus_nearest(self, row: int, col: int) -> bool:
        if row < 0 or row >= len(self._grid):
            return False
        grid_row = self._grid[row]
        col = max(0, min(col, len(grid_row) - 1))
        try:
            self.query_one(f"#{grid_row[col]}").focus()
            return True
        except Exception:
            return False

    @on(GridInput.Navigate)
    def _on_grid_navigate(self, event: GridInput.Navigate) -> None:
        focused = self.app.focused
        if focused is None or focused.id not in self._grid_pos:
            return
        row, col = self._grid_pos[focused.id]
        navigated = False
        if event.direction == "up":
            navigated = self._focus_nearest(row - 1, col)
        elif event.direction == "down":
            navigated = self._focus_nearest(row + 1, col)
        elif event.direction == "left" and col > 0:
            navigated = self._focus_nearest(row, col - 1)
        elif event.direction == "right" and col < len(self._grid[row]) - 1:
            navigated = self._focus_nearest(row, col + 1)
        if not navigated:
            escape_to_neighbor(self, focused, event.direction)
        event.stop()

    # ------------------------------------------------------------------
    # Field change → autosave
    # ------------------------------------------------------------------

    @on(RadioGroup.Changed)
    @on(GridInput.Changed)
    @on(Input.Changed)
    def _on_field_changed(self) -> None:
        if not self._loading:
            self.post_message(self.FieldChanged())

    @on(TextArea.Changed, selector="TextArea")
    def _on_textarea_changed(self, event: TextArea.Changed) -> None:
        if self._loading:
            return
        wid = getattr(event.text_area, "id", "") or ""
        if wid.startswith("ft_goal_"):
            goals = {}
            for i in range(1, 5):
                try:
                    goals[f"goal_{i}"] = self.query_one(f"#ft_goal_{i}", TextArea).text
                except Exception:
                    goals[f"goal_{i}"] = ""
            self.post_message(self.GoalsChanged(goals))
        else:
            self.post_message(self.FieldChanged())

    # ------------------------------------------------------------------
    # collect / load / is_complete
    # ------------------------------------------------------------------

    def collect(self) -> dict:
        data: dict = {}
        for rg in self.query(RadioGroup):
            data[rg.id] = rg.value
        for iid in _FM_INPUT_IDS:
            try:
                data[iid] = self.query_one(f"#{iid}", Input).value.strip()
            except Exception:
                data[iid] = ""
        for _, ids in _BAL_ROWS:
            for fid in ids:
                try:
                    data[fid] = self.query_one(f"#{fid}", GridInput).value.strip()
                except Exception:
                    data[fid] = ""
        for _, fid, _ in _CAP_ROWS:
            try:
                data[fid] = self.query_one(f"#{fid}", GridInput).value.strip()
            except Exception:
                data[fid] = ""
        for tid in ("ft_fm_obs", "ft_fm_custom", "ft_notes"):
            try:
                data[tid] = self.query_one(f"#{tid}", TextArea).text
            except Exception:
                data[tid] = ""
        return data

    def load(self, data: dict) -> None:
        self._loading = True
        try:
            for rg in self.query(RadioGroup):
                rg.set_value(data.get(rg.id))
            for iid in _FM_INPUT_IDS:
                try:
                    self.query_one(f"#{iid}", Input).value = data.get(iid, "")
                except Exception:
                    pass
            for _, ids in _BAL_ROWS:
                for fid in ids:
                    try:
                        self.query_one(f"#{fid}", GridInput).value = data.get(fid, "")
                    except Exception:
                        pass
            for _, fid, _ in _CAP_ROWS:
                try:
                    self.query_one(f"#{fid}", GridInput).value = data.get(fid, "")
                except Exception:
                    pass
            for tid in ("ft_fm_obs", "ft_fm_custom", "ft_notes"):
                try:
                    self.query_one(f"#{tid}", TextArea).text = data.get(tid, "")
                except Exception:
                    pass
        finally:
            self._loading = False

    def load_goals(self, data: dict) -> None:
        """Populate the SMART Goals mirror from subjective data (goal_1..4)."""
        self._loading = True
        try:
            for i in range(1, 5):
                try:
                    self.query_one(f"#ft_goal_{i}", TextArea).text = data.get(f"goal_{i}", "")
                except Exception:
                    pass
        finally:
            self._loading = False

    def is_complete(self) -> bool:
        try:
            return self.query_one("#ft_tug", GridInput).value.strip() != ""
        except Exception:
            return False
