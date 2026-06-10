"""Shoulder Python table widgets — OP/accessory/AC-SC (passive) and strength (muscle).

ShoulderPassiveTables  — Overpressure bilateral (L/R) + GH accessory glides + AC/SC joint
ShoulderMuscleTables   — Shoulder strength bilateral grid (kg or 0–5)

Both post ShoulderTables.Changed when any field changes, which RegionContainer
catches and converts to RegionContainer.FieldChanged for autosave.
"""

from __future__ import annotations

from textual import events
from textual.app import ComposeResult, on
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button, Label, Static, TextArea

from ...widgets import CycleButton, GridInput


# ── Shared changed message ────────────────────────────────────────────────────

class ShoulderTables:
    """Namespace for messages shared by both shoulder table widgets."""
    class Changed(Message):
        pass


# ── Normal toggle state ───────────────────────────────────────────────────────

_NORM_STATE = [("Norm", "success")]


# ── Row definitions ───────────────────────────────────────────────────────────

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
    """Overpressure bilateral + GH accessory glides + AC/SC joint for shoulder passive tab."""

    DEFAULT_CSS = """
    ShoulderPassiveTables { width: 100%; height: auto; }
    ShoulderPassiveTables CycleButton { width: 6; height: 3; }

    /* Overpressure — bilateral L/R */
    ShoulderPassiveTables .op_hdr      { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    ShoulderPassiveTables .op_hdr_lbl  { width: 12; }
    ShoulderPassiveTables .op_hdr_side { width: 1fr; text-align: center; }
    ShoulderPassiveTables .op_subhdr   { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    ShoulderPassiveTables .op_subhdr_lbl  { width: 12; }
    ShoulderPassiveTables .op_subhdr_norm { width: 6; text-align: center; }
    ShoulderPassiveTables .op_subhdr_txt  { width: 1fr; }
    ShoulderPassiveTables .op_row      { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    ShoulderPassiveTables .op_row_lbl  { width: 12; height: 3; content-align: left middle; }
    ShoulderPassiveTables .op_txt      { width: 1fr; height: 3; padding: 0 1; }

    /* GH accessory glides */
    ShoulderPassiveTables .acc_hdr         { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    ShoulderPassiveTables .acc_hdr_lbl     { width: 12; }
    ShoulderPassiveTables .acc_hdr_side    { width: 1fr; text-align: center; }
    ShoulderPassiveTables .acc_subhdr      { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    ShoulderPassiveTables .acc_subhdr_lbl  { width: 12; }
    ShoulderPassiveTables .acc_subhdr_norm { width: 6; text-align: center; }
    ShoulderPassiveTables .acc_subhdr_txt  { width: 1fr; }
    ShoulderPassiveTables .acc_row         { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    ShoulderPassiveTables .acc_row_lbl     { width: 12; height: 3; content-align: left middle; }
    ShoulderPassiveTables .acc_txt         { width: 1fr; height: 3; padding: 0 1; }

    /* AC / SC joint — bilateral */
    ShoulderPassiveTables .acsc_hdr      { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    ShoulderPassiveTables .acsc_hdr_lbl  { width: 12; }
    ShoulderPassiveTables .acsc_hdr_side { width: 1fr; text-align: center; }
    ShoulderPassiveTables .acsc_subhdr   { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    ShoulderPassiveTables .acsc_subhdr_lbl  { width: 12; }
    ShoulderPassiveTables .acsc_subhdr_norm { width: 6; text-align: center; }
    ShoulderPassiveTables .acsc_subhdr_txt  { width: 1fr; }
    ShoulderPassiveTables .acsc_row      { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    ShoulderPassiveTables .acsc_row_lbl  { width: 12; height: 3; content-align: left middle; }
    ShoulderPassiveTables .acsc_txt      { width: 1fr; height: 3; padding: 0 1; }

    ShoulderPassiveTables TextArea { height: auto; min-height: 2; padding: 0 1; }
    ShoulderPassiveTables Label    { height: auto; margin-top: 0; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._grid:     list[list[str]] = []
        self._grid_pos: dict[str, tuple[int, int]] = {}

    def compose(self) -> ComposeResult:
        # ── Overpressure (bilateral) ──────────────────────────────────────────
        yield Label("Overpressure", classes="subsection_header")
        with Horizontal(classes="op_hdr"):
            yield Static("",       classes="op_hdr_lbl")
            yield Static("Left",   classes="op_hdr_side")
            yield Static("Right",  classes="op_hdr_side")
        with Horizontal(classes="op_subhdr"):
            yield Static("",       classes="op_subhdr_lbl")
            yield Static("Norm",   classes="op_subhdr_norm")
            yield Static("Notes",  classes="op_subhdr_txt")
            yield Static("Norm",   classes="op_subhdr_norm")
            yield Static("Notes",  classes="op_subhdr_txt")
        for label, prefix in _OP_ROWS:
            with Horizontal(classes="op_row"):
                yield Static(label, classes="op_row_lbl")
                yield CycleButton(_NORM_STATE, id=f"{prefix}_l_norm")
                yield GridInput(placeholder="findings", id=f"{prefix}_l_txt", classes="op_txt")
                yield CycleButton(_NORM_STATE, id=f"{prefix}_r_norm")
                yield GridInput(placeholder="findings", id=f"{prefix}_r_txt", classes="op_txt")
        yield Label("OP notes:")
        yield TextArea(id="sh_pm_op_notes", language="plain")

        # ── GH Accessory glides ───────────────────────────────────────────────
        yield Label("GH Accessory Glides", classes="subsection_header")
        with Horizontal(classes="acc_hdr"):
            yield Static("",       classes="acc_hdr_lbl")
            yield Static("Left",   classes="acc_hdr_side")
            yield Static("Right",  classes="acc_hdr_side")
        with Horizontal(classes="acc_subhdr"):
            yield Static("",       classes="acc_subhdr_lbl")
            yield Static("Norm",   classes="acc_subhdr_norm")
            yield Static("Notes",  classes="acc_subhdr_txt")
            yield Static("Norm",   classes="acc_subhdr_norm")
            yield Static("Notes",  classes="acc_subhdr_txt")
        for dir_label, dir_key in _ACC_DIRS:
            with Horizontal(classes="acc_row"):
                yield Static(dir_label, classes="acc_row_lbl")
                yield CycleButton(_NORM_STATE, id=f"sh_acc_{dir_key}_l_norm")
                yield GridInput(placeholder="grade / findings",
                                id=f"sh_acc_{dir_key}_l_txt", classes="acc_txt")
                yield CycleButton(_NORM_STATE, id=f"sh_acc_{dir_key}_r_norm")
                yield GridInput(placeholder="grade / findings",
                                id=f"sh_acc_{dir_key}_r_txt", classes="acc_txt")
        yield Label("Accessory notes:")
        yield TextArea(id="sh_pm_acc_notes", language="plain")

        # ── AC / SC joint (bilateral) ─────────────────────────────────────────
        yield Label("AC / SC Joint", classes="subsection_header")
        with Horizontal(classes="acsc_hdr"):
            yield Static("",       classes="acsc_hdr_lbl")
            yield Static("Left",   classes="acsc_hdr_side")
            yield Static("Right",  classes="acsc_hdr_side")
        with Horizontal(classes="acsc_subhdr"):
            yield Static("",       classes="acsc_subhdr_lbl")
            yield Static("Norm",   classes="acsc_subhdr_norm")
            yield Static("Notes",  classes="acsc_subhdr_txt")
            yield Static("Norm",   classes="acsc_subhdr_norm")
            yield Static("Notes",  classes="acsc_subhdr_txt")
        for label, prefix in _AC_SC_ROWS:
            with Horizontal(classes="acsc_row"):
                yield Static(label, classes="acsc_row_lbl")
                yield CycleButton(_NORM_STATE, id=f"{prefix}_l_norm")
                yield GridInput(placeholder="findings", id=f"{prefix}_l_txt", classes="acsc_txt")
                yield CycleButton(_NORM_STATE, id=f"{prefix}_r_norm")
                yield GridInput(placeholder="findings", id=f"{prefix}_r_txt", classes="acsc_txt")

    def on_mount(self) -> None:
        # OP bilateral rows (4 cols each)
        for _, prefix in _OP_ROWS:
            row = [f"{prefix}_l_norm_btn", f"{prefix}_l_txt",
                   f"{prefix}_r_norm_btn", f"{prefix}_r_txt"]
            row_idx = len(self._grid)
            self._grid.append(row)
            for col_idx, wid in enumerate(row):
                self._grid_pos[wid] = (row_idx, col_idx)
        # GH Acc (4 cols, one row per direction)
        for _, dir_key in _ACC_DIRS:
            row = [f"sh_acc_{dir_key}_l_norm_btn", f"sh_acc_{dir_key}_l_txt",
                   f"sh_acc_{dir_key}_r_norm_btn", f"sh_acc_{dir_key}_r_txt"]
            row_idx = len(self._grid)
            self._grid.append(row)
            for col_idx, wid in enumerate(row):
                self._grid_pos[wid] = (row_idx, col_idx)
        # AC/SC bilateral rows (4 cols)
        for _, prefix in _AC_SC_ROWS:
            row = [f"{prefix}_l_norm_btn", f"{prefix}_l_txt",
                   f"{prefix}_r_norm_btn", f"{prefix}_r_txt"]
            row_idx = len(self._grid)
            self._grid.append(row)
            for col_idx, wid in enumerate(row):
                self._grid_pos[wid] = (row_idx, col_idx)

    def _nav(self, fid: str, direction: str) -> bool:
        if fid not in self._grid_pos:
            return False
        row, col = self._grid_pos[fid]
        target_id = None
        if direction == "up" and row > 0:
            tc = min(col, len(self._grid[row - 1]) - 1)
            target_id = self._grid[row - 1][tc]
        elif direction == "down" and row < len(self._grid) - 1:
            tc = min(col, len(self._grid[row + 1]) - 1)
            target_id = self._grid[row + 1][tc]
        elif direction == "left" and col > 0:
            target_id = self._grid[row][col - 1]
        elif direction == "right" and col < len(self._grid[row]) - 1:
            target_id = self._grid[row][col + 1]
        if target_id is None:
            return False
        try:
            self.query_one(f"#{target_id}").focus()
            return True
        except Exception:
            return False

    def on_key(self, event: events.Key) -> None:
        focused = self.app.focused
        if not isinstance(focused, Button):
            return
        fid = focused.id or ""
        if event.key not in ("up", "down", "left", "right"):
            return
        if fid in self._grid_pos:
            if self._nav(fid, event.key):
                event.stop()

    @on(GridInput.Navigate)
    def _on_grid_navigate(self, event: GridInput.Navigate) -> None:
        focused = self.app.focused
        if focused is None:
            return
        fid = focused.id or ""
        if fid in self._grid_pos:
            self._nav(fid, event.direction)
        event.stop()

    @on(CycleButton.Changed)
    @on(GridInput.Changed)
    @on(TextArea.Changed, selector="TextArea")
    def _on_field_changed(self) -> None:
        self.post_message(ShoulderTables.Changed())

    def collect(self) -> dict:
        data: dict = {}
        for cb in self.query(CycleButton):
            data[cb.id] = cb.value
        for gi in self.query(GridInput):
            data[gi.id] = gi.value.strip()
        for tid in ("sh_pm_op_notes", "sh_pm_acc_notes"):
            try:
                data[tid] = self.query_one(f"#{tid}", TextArea).text
            except Exception:
                data[tid] = ""
        return data

    def load(self, data: dict) -> None:
        for cb in self.query(CycleButton):
            cb.set_value(data.get(cb.id))
        for gi in self.query(GridInput):
            gi.value = data.get(gi.id, "")
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
