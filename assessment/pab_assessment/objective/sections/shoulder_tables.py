"""Shoulder Python table widgets — OP/accessory/AC-SC (passive) and strength (muscle).

ShoulderPassiveTables  — Overpressure end-feel/response + GH accessory glides + AC/SC joint
ShoulderMuscleTables   — Shoulder strength bilateral grid (kg or 0–5)

Both post ShoulderTables.Changed when any field changes, which RegionContainer
catches and converts to RegionContainer.FieldChanged for autosave.
"""

from __future__ import annotations

from textual import events
from textual.app import ComposeResult, on
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Label, Static, TextArea

from ...widgets import GridInput, RadioGroup


# ── Shared changed message ────────────────────────────────────────────────────

class ShoulderTables:
    """Namespace for messages shared by both shoulder table widgets."""
    class Changed(Message):
        pass


# ── Gang option sets ──────────────────────────────────────────────────────────

_END_FEEL = [
    ("Norm",  "success"),
    ("Hard",  "default"),
    ("Sprng", "warning"),
    ("Spasm", "error"),
]

_OP_RESP = [
    ("NoChg", "success"),
    ("Repro", "warning"),
    ("Incrs", "error"),
    ("Decrs", "default"),
]

_MAITLAND = [
    ("I",   "success"),
    ("II",  "success"),
    ("III", "warning"),
    ("IV",  "warning"),
    ("V",   "error"),
]

_ACC_RESP = [
    ("NoChg", "success"),
    ("Repro", "warning"),
    ("Incrs", "error"),
    ("Decrs", "default"),
]

_AC_SC = [
    ("Neg", "success"),
    ("Tnd", "warning"),
    ("Pos", "error"),
]


# ── Row / level definitions ───────────────────────────────────────────────────

_OP_ROWS: list[tuple[str, str]] = [
    ("Flexion",     "sh_op_flex"),
    ("Extension",   "sh_op_ext"),
    ("Abduction",   "sh_op_abd"),
    ("Int Rot",     "sh_op_ir"),
    ("Ext Rot",     "sh_op_er"),
    ("Horiz Add",   "sh_op_hadd"),
    ("Horiz Abd",   "sh_op_habd"),
]

_ACC_DIRS: list[tuple[str, str]] = [
    ("Inferior",  "inf"),
    ("Posterior", "post"),
    ("Anterior",  "ant"),
]

_AC_SC_ROWS: list[tuple[str, str]] = [
    ("AC Stress",  "sh_ac_pm_stress"),
    ("AC Palp",    "sh_ac_pm_palp"),
    ("SC Stress",  "sh_sc_pm_stress"),
]

_SH_STR_ROWS: list[tuple[str, str]] = [
    ("Flexion",     "sh_str_flex"),
    ("Abduction",   "sh_str_abd"),
    ("Int Rot",     "sh_str_ir"),
    ("Ext Rot",     "sh_str_er"),
    ("Scaption",    "sh_str_scap"),
]


# ── ShoulderPassiveTables ─────────────────────────────────────────────────────

class ShoulderPassiveTables(Static):
    """Overpressure + GH accessory glides + AC/SC joint for shoulder passive tab."""

    DEFAULT_CSS = """
    ShoulderPassiveTables { width: 100%; height: auto; }

    /* Overpressure */
    ShoulderPassiveTables .op_hdr      { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    ShoulderPassiveTables .op_hdr_lbl  { width: 14; }
    ShoulderPassiveTables .op_hdr_ef   { width: 24; text-align: center; }
    ShoulderPassiveTables .op_hdr_gap  { width: 2; }
    ShoulderPassiveTables .op_hdr_resp { width: 24; text-align: center; }
    ShoulderPassiveTables .op_row      { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    ShoulderPassiveTables .op_row_lbl  { width: 14; height: 3; content-align: left middle; }
    ShoulderPassiveTables .op_gap      { width: 2; height: 3; }

    /* GH accessory glides */
    ShoulderPassiveTables .acc_hdr      { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    ShoulderPassiveTables .acc_hdr_lbl  { width: 12; }
    ShoulderPassiveTables .acc_hdr_grde { width: 30; text-align: center; }
    ShoulderPassiveTables .acc_hdr_gap  { width: 2; }
    ShoulderPassiveTables .acc_hdr_resp { width: 24; text-align: center; }
    ShoulderPassiveTables .acc_row      { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    ShoulderPassiveTables .acc_row_lbl  { width: 12; height: 3; content-align: left middle; }
    ShoulderPassiveTables .acc_gap      { width: 2; height: 3; }

    /* AC / SC joint */
    ShoulderPassiveTables .acsc_hdr      { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    ShoulderPassiveTables .acsc_hdr_lbl  { width: 14; }
    ShoulderPassiveTables .acsc_hdr_col  { width: 18; text-align: center; }
    ShoulderPassiveTables .acsc_hdr_gap  { width: 2; }
    ShoulderPassiveTables .acsc_row      { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    ShoulderPassiveTables .acsc_row_lbl  { width: 14; height: 3; content-align: left middle; }
    ShoulderPassiveTables .acsc_gap      { width: 2; height: 3; }

    ShoulderPassiveTables TextArea { height: auto; min-height: 2; padding: 0 1; }
    ShoulderPassiveTables Label    { height: auto; margin-top: 0; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._op_grid:     list[list[str]] = []
        self._op_grid_pos: dict[str, tuple[int, int]] = {}

    def compose(self) -> ComposeResult:
        # ── Overpressure ──────────────────────────────────────────────────────
        yield Label("Overpressure", classes="subsection_header")
        with Horizontal(classes="op_hdr"):
            yield Static("",          classes="op_hdr_lbl")
            yield Static("End-feel",  classes="op_hdr_ef")
            yield Static("",          classes="op_hdr_gap")
            yield Static("Response",  classes="op_hdr_resp")
        for label, prefix in _OP_ROWS:
            with Horizontal(classes="op_row"):
                yield Static(label, classes="op_row_lbl")
                yield RadioGroup(_END_FEEL, id=f"{prefix}_ef")
                yield Static("",           classes="op_gap")
                yield RadioGroup(_OP_RESP,  id=f"{prefix}_resp")
        yield Label("OP notes:")
        yield TextArea(id="sh_pm_op_notes", language="plain")

        # ── GH Accessory glides ───────────────────────────────────────────────
        for side, side_label in (("l", "Left"), ("r", "Right")):
            yield Label(f"GH Accessory — {side_label}", classes="subsection_header")
            with Horizontal(classes="acc_hdr"):
                yield Static("",          classes="acc_hdr_lbl")
                yield Static("Grade",     classes="acc_hdr_grde")
                yield Static("",          classes="acc_hdr_gap")
                yield Static("Response",  classes="acc_hdr_resp")
            for dir_label, dir_key in _ACC_DIRS:
                with Horizontal(classes="acc_row"):
                    yield Static(dir_label, classes="acc_row_lbl")
                    yield RadioGroup(_MAITLAND, id=f"sh_acc_{dir_key}_{side}_grade")
                    yield Static("",           classes="acc_gap")
                    yield RadioGroup(_ACC_RESP, id=f"sh_acc_{dir_key}_{side}_resp")
        yield Label("Accessory notes:")
        yield TextArea(id="sh_pm_acc_notes", language="plain")

        # ── AC / SC joint ─────────────────────────────────────────────────────
        yield Label("AC / SC Joint", classes="subsection_header")
        with Horizontal(classes="acsc_hdr"):
            yield Static("",       classes="acsc_hdr_lbl")
            yield Static("Left",   classes="acsc_hdr_col")
            yield Static("",       classes="acsc_hdr_gap")
            yield Static("Right",  classes="acsc_hdr_col")
        for label, prefix in _AC_SC_ROWS:
            with Horizontal(classes="acsc_row"):
                yield Static(label, classes="acsc_row_lbl")
                yield RadioGroup(_AC_SC, id=f"{prefix}_l")
                yield Static("",        classes="acsc_gap")
                yield RadioGroup(_AC_SC, id=f"{prefix}_r")

    def on_mount(self) -> None:
        for row_idx, (_, prefix) in enumerate(_OP_ROWS):
            row = [f"{prefix}_ef", f"{prefix}_resp"]
            self._op_grid.append(row)
            for col_idx, rg_id in enumerate(row):
                self._op_grid_pos[rg_id] = (row_idx, col_idx)

    def on_key(self, event: events.Key) -> None:
        focused = self.app.focused
        if not isinstance(focused, RadioGroup):
            return
        fid = focused.id or ""
        if fid not in self._op_grid_pos:
            return
        if event.key not in ("up", "down"):
            return
        row, col = self._op_grid_pos[fid]
        target_row = row - 1 if event.key == "up" else row + 1
        if 0 <= target_row < len(self._op_grid):
            try:
                self.query_one(f"#{self._op_grid[target_row][col]}", RadioGroup).focus()
                event.stop()
            except Exception:
                pass

    @on(RadioGroup.Changed)
    @on(TextArea.Changed, selector="TextArea")
    def _on_field_changed(self) -> None:
        self.post_message(ShoulderTables.Changed())

    def collect(self) -> dict:
        data: dict = {}
        for rg in self.query(RadioGroup):
            data[rg.id] = rg.value
        for tid in ("sh_pm_op_notes", "sh_pm_acc_notes"):
            try:
                data[tid] = self.query_one(f"#{tid}", TextArea).text
            except Exception:
                data[tid] = ""
        return data

    def load(self, data: dict) -> None:
        for rg in self.query(RadioGroup):
            rg.set_value(data.get(rg.id))
        for tid in ("sh_pm_op_notes", "sh_pm_acc_notes"):
            try:
                self.query_one(f"#{tid}", TextArea).text = data.get(tid, "")
            except Exception:
                pass


# ── ShoulderMuscleTables ──────────────────────────────────────────────────────

class ShoulderMuscleTables(Static):
    """Shoulder strength bilateral grid (kg or 0–5) for shoulder muscle tab."""

    DEFAULT_CSS = """
    ShoulderMuscleTables { width: 100%; height: auto; }
    ShoulderMuscleTables .str_hdr     { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    ShoulderMuscleTables .str_hdr_lbl { width: 18; }
    ShoulderMuscleTables .str_hdr_col { width: 1fr; text-align: center; }
    ShoulderMuscleTables .str_row     { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    ShoulderMuscleTables .str_lbl     { width: 18; height: 3; content-align: left middle; }
    ShoulderMuscleTables .str_inp     { width: 1fr; height: 3; padding: 0 1; }
    ShoulderMuscleTables Label { height: auto; margin-top: 0; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._str_grid:     list[list[str]] = []
        self._str_grid_pos: dict[str, tuple[int, int]] = {}

    def compose(self) -> ComposeResult:
        yield Label("Strength — Shoulder  (kg or 0–5)", classes="subsection_header")
        with Horizontal(classes="str_hdr"):
            yield Static("",      classes="str_hdr_lbl")
            yield Static("Left",  classes="str_hdr_col")
            yield Static("Right", classes="str_hdr_col")
        for label, prefix in _SH_STR_ROWS:
            with Horizontal(classes="str_row"):
                yield Static(label, classes="str_lbl")
                yield GridInput(placeholder="kg / 0–5", id=f"{prefix}_l", classes="str_inp")
                yield GridInput(placeholder="kg / 0–5", id=f"{prefix}_r", classes="str_inp")

    def on_mount(self) -> None:
        for _, prefix in _SH_STR_ROWS:
            row_idx = len(self._str_grid)
            row = [f"{prefix}_l", f"{prefix}_r"]
            self._str_grid.append(row)
            for col_idx, wid in enumerate(row):
                self._str_grid_pos[wid] = (row_idx, col_idx)

    @on(GridInput.Navigate)
    def _on_grid_navigate(self, event: GridInput.Navigate) -> None:
        focused = self.app.focused
        if focused is None or focused.id not in self._str_grid_pos:
            return
        row, col = self._str_grid_pos[focused.id]
        navigated = False
        if event.direction == "up":
            target = row - 1
            if 0 <= target < len(self._str_grid):
                try:
                    self.query_one(f"#{self._str_grid[target][col]}").focus()
                    navigated = True
                except Exception:
                    pass
        elif event.direction == "down":
            target = row + 1
            if 0 <= target < len(self._str_grid):
                try:
                    self.query_one(f"#{self._str_grid[target][col]}").focus()
                    navigated = True
                except Exception:
                    pass
        elif event.direction == "left" and col > 0:
            try:
                self.query_one(f"#{self._str_grid[row][col - 1]}").focus()
                navigated = True
            except Exception:
                pass
        elif event.direction == "right" and col < len(self._str_grid[row]) - 1:
            try:
                self.query_one(f"#{self._str_grid[row][col + 1]}").focus()
                navigated = True
            except Exception:
                pass
        event.stop()

    @on(GridInput.Changed)
    def _on_field_changed(self) -> None:
        self.post_message(ShoulderTables.Changed())

    def collect(self) -> dict:
        data: dict = {}
        for _, prefix in _SH_STR_ROWS:
            for side in ("l", "r"):
                fid = f"{prefix}_{side}"
                try:
                    data[fid] = self.query_one(f"#{fid}", GridInput).value.strip()
                except Exception:
                    data[fid] = ""
        return data

    def load(self, data: dict) -> None:
        for _, prefix in _SH_STR_ROWS:
            for side in ("l", "r"):
                fid = f"{prefix}_{side}"
                try:
                    self.query_one(f"#{fid}", GridInput).value = data.get(fid, "")
                except Exception:
                    pass
