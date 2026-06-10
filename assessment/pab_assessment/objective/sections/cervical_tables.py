"""Cervical Python table widgets — OP/PAIVM (passive) and neck strength (muscle).

CervicalPassiveTables  — Overpressure Normal+text + PAIVM grid C0/1–T4
CervicalMuscleTables   — Neck strength bilateral grid (kg)

Both post CervicalTables.Changed when any field changes, which RegionContainer
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

class CervicalTables:
    """Namespace for messages shared by both cervical table widgets."""
    class Changed(Message):
        pass


# ── Normal toggle state ───────────────────────────────────────────────────────

_NORM_STATE = [("Norm", "success")]


# ── Row / level definitions ───────────────────────────────────────────────────

# (label, prefix, bilateral) — bilateral rows show L | R columns in one row
_CX_OP_ROWS: list[tuple[str, str, bool]] = [
    ("Cx Flexion",   "cx_op_flex",  False),
    ("Cx Extension", "cx_op_ext",   False),
    ("Cx Lat Flex",  "cx_op_lf",    True),
    ("Cx Rotation",  "cx_op_rot",   True),
    ("Cx Quadrant",  "cx_op_quad",  True),
]

# (display_label, id_key) — id_key avoids slashes for use in field IDs
_CX_PAIVM_LEVELS: list[tuple[str, str]] = [
    ("C0/1", "C0_1"),
    ("C1/2", "C1_2"),
    ("C2",   "C2"),
    ("C3",   "C3"),
    ("C4",   "C4"),
    ("C5",   "C5"),
    ("C6",   "C6"),
    ("C7",   "C7"),
    ("T1",   "T1"),
    ("T2",   "T2"),
    ("T3",   "T3"),
    ("T4",   "T4"),
]

_CX_NECK_ROWS: list[tuple[str, str]] = [
    ("Neck flexion",   "cx_neck_flex"),
    ("Neck extension", "cx_neck_ext"),
    ("Neck lat flex",  "cx_neck_lf"),
    ("Neck rotation",  "cx_neck_rot"),
]


# ── CervicalPassiveTables ─────────────────────────────────────────────────────

class CervicalPassiveTables(Static):
    """Overpressure Normal+text table + PAIVM grid C0/1–T4 for cervical passive tab."""

    DEFAULT_CSS = """
    CervicalPassiveTables { width: 100%; height: auto; }
    CervicalPassiveTables CycleButton { width: 6; height: 3; }

    CervicalPassiveTables .op_hdr      { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    CervicalPassiveTables .op_hdr_lbl  { width: 16; }
    CervicalPassiveTables .op_hdr_norm { width: 6; text-align: center; }
    CervicalPassiveTables .op_hdr_txt  { width: 1fr; }
    CervicalPassiveTables .op_row      { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    CervicalPassiveTables .op_row_lbl  { width: 16; height: 3; content-align: left middle; }
    CervicalPassiveTables .op_side     { width: 2; height: 3; content-align: left middle; color: $text-muted; }
    CervicalPassiveTables .op_txt      { width: 1fr; height: 3; padding: 0 1; }

    CervicalPassiveTables .paivm_hdr      { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    CervicalPassiveTables .paivm_hdr_lbl  { width: 6; }
    CervicalPassiveTables .paivm_hdr_norm { width: 6; text-align: center; }
    CervicalPassiveTables .paivm_hdr_txt  { width: 1fr; }
    CervicalPassiveTables .paivm_row      { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    CervicalPassiveTables .paivm_row_lbl  { width: 6; height: 3; content-align: left middle; }
    CervicalPassiveTables .paivm_txt      { width: 1fr; height: 3; padding: 0 1; }

    CervicalPassiveTables TextArea { height: auto; min-height: 2; padding: 0 1; }
    CervicalPassiveTables Label    { height: auto; margin-top: 0; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._op_grid:     list[list[str]] = []
        self._op_grid_pos: dict[str, tuple[int, int]] = {}
        self._pm_grid:     list[list[str]] = []
        self._pm_grid_pos: dict[str, tuple[int, int]] = {}

    def compose(self) -> ComposeResult:
        # ── Overpressure ──────────────────────────────────────────────────────
        yield Label("Overpressure", classes="subsection_header")
        with Horizontal(classes="op_hdr"):
            yield Static("",       classes="op_hdr_lbl")
            yield Static("Norm",   classes="op_hdr_norm")
            yield Static("Notes",  classes="op_hdr_txt")
        for label, prefix, bilateral in _CX_OP_ROWS:
            with Horizontal(classes="op_row"):
                yield Static(label, classes="op_row_lbl")
                if bilateral:
                    yield Static("L", classes="op_side")
                    yield CycleButton(_NORM_STATE, id=f"{prefix}_l_norm")
                    yield GridInput(placeholder="findings / //",
                                    id=f"{prefix}_l_txt", classes="op_txt")
                    yield Static("R", classes="op_side")
                    yield CycleButton(_NORM_STATE, id=f"{prefix}_r_norm")
                    yield GridInput(placeholder="findings / //",
                                    id=f"{prefix}_r_txt", classes="op_txt")
                else:
                    yield CycleButton(_NORM_STATE, id=f"{prefix}_norm")
                    yield GridInput(placeholder="findings / // reassessment",
                                    id=f"{prefix}_txt", classes="op_txt")
        yield Label("OP notes:")
        yield TextArea(id="cx_pm_op_notes", language="plain")

        # ── PAIVMs ────────────────────────────────────────────────────────────
        yield Label("PAIVMs", classes="subsection_header")
        with Horizontal(classes="paivm_hdr"):
            yield Static("",       classes="paivm_hdr_lbl")
            yield Static("L",      classes="paivm_hdr_norm")
            yield Static("C",      classes="paivm_hdr_norm")
            yield Static("R",      classes="paivm_hdr_norm")
            yield Static("Notes",  classes="paivm_hdr_txt")
        for display, key in _CX_PAIVM_LEVELS:
            with Horizontal(classes="paivm_row"):
                yield Static(display, classes="paivm_row_lbl")
                yield CycleButton(_NORM_STATE, id=f"cx_pm_{key}_l_norm")
                yield CycleButton(_NORM_STATE, id=f"cx_pm_{key}_c_norm")
                yield CycleButton(_NORM_STATE, id=f"cx_pm_{key}_r_norm")
                yield GridInput(placeholder="grade / findings",
                                id=f"cx_pm_{key}_txt", classes="paivm_txt")
        yield Label("PAIVM notes:")
        yield TextArea(id="cx_pm_paivm_notes", language="plain")

    def on_mount(self) -> None:
        for row_idx, (_, prefix, bilateral) in enumerate(_CX_OP_ROWS):
            if bilateral:
                row = [f"{prefix}_l_norm_btn", f"{prefix}_l_txt",
                       f"{prefix}_r_norm_btn", f"{prefix}_r_txt"]
            else:
                row = [f"{prefix}_norm_btn", f"{prefix}_txt"]
            self._op_grid.append(row)
            for col_idx, wid in enumerate(row):
                self._op_grid_pos[wid] = (row_idx, col_idx)
        for row_idx, (_, key) in enumerate(_CX_PAIVM_LEVELS):
            row = [f"cx_pm_{key}_l_norm_btn", f"cx_pm_{key}_c_norm_btn",
                   f"cx_pm_{key}_r_norm_btn", f"cx_pm_{key}_txt"]
            self._pm_grid.append(row)
            for col_idx, wid in enumerate(row):
                self._pm_grid_pos[wid] = (row_idx, col_idx)

    def _nav(self, grid: list[list[str]], grid_pos: dict[str, tuple[int, int]],
             fid: str, direction: str) -> bool:
        if fid not in grid_pos:
            return False
        row, col = grid_pos[fid]
        target_id = None
        if direction == "up" and row > 0:
            tc = min(col, len(grid[row - 1]) - 1)
            target_id = grid[row - 1][tc]
        elif direction == "down" and row < len(grid) - 1:
            tc = min(col, len(grid[row + 1]) - 1)
            target_id = grid[row + 1][tc]
        elif direction == "left" and col > 0:
            target_id = grid[row][col - 1]
        elif direction == "right" and col < len(grid[row]) - 1:
            target_id = grid[row][col + 1]
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
        for grid, grid_pos in [
            (self._op_grid, self._op_grid_pos),
            (self._pm_grid, self._pm_grid_pos),
        ]:
            if fid in grid_pos:
                if self._nav(grid, grid_pos, fid, event.key):
                    event.stop()
                return

    @on(GridInput.Navigate)
    def _on_grid_navigate(self, event: GridInput.Navigate) -> None:
        focused = self.app.focused
        if focused is None:
            return
        fid = focused.id or ""
        for grid, grid_pos in [
            (self._op_grid, self._op_grid_pos),
            (self._pm_grid, self._pm_grid_pos),
        ]:
            if fid in grid_pos:
                self._nav(grid, grid_pos, fid, event.direction)
                event.stop()
                return
        event.stop()

    @on(CycleButton.Changed)
    @on(GridInput.Changed)
    @on(TextArea.Changed, selector="TextArea")
    def _on_field_changed(self) -> None:
        self.post_message(CervicalTables.Changed())

    def collect(self) -> dict:
        data: dict = {}
        for cb in self.query(CycleButton):
            data[cb.id] = cb.value
        for gi in self.query(GridInput):
            data[gi.id] = gi.value.strip()
        for tid in ("cx_pm_op_notes", "cx_pm_paivm_notes"):
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
        for tid in ("cx_pm_op_notes", "cx_pm_paivm_notes"):
            try:
                self.query_one(f"#{tid}", TextArea).text = data.get(tid, "")
            except Exception:
                pass


# ── CervicalMuscleTables ──────────────────────────────────────────────────────

class CervicalMuscleTables(Static):
    """Neck strength bilateral grid (kg) for cervical muscle tab."""

    DEFAULT_CSS = """
    CervicalMuscleTables {
        width: 100%;
        height: auto;
    }
    CervicalMuscleTables .neck_hdr     { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    CervicalMuscleTables .neck_hdr_lbl { width: 18; }
    CervicalMuscleTables .neck_hdr_col { width: 1fr; text-align: center; }
    CervicalMuscleTables .neck_row     { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    CervicalMuscleTables .neck_lbl     { width: 18; height: 3; content-align: left middle; }
    CervicalMuscleTables .neck_inp     { width: 1fr; height: 3; padding: 0 1; }
    CervicalMuscleTables Label { height: auto; margin-top: 0; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._neck_grid:     list[list[str]] = []
        self._neck_grid_pos: dict[str, tuple[int, int]] = {}

    def compose(self) -> ComposeResult:
        yield Label("Strength — Neck  (kg)", classes="subsection_header")
        with Horizontal(classes="neck_hdr"):
            yield Static("",      classes="neck_hdr_lbl")
            yield Static("Left",  classes="neck_hdr_col")
            yield Static("Right", classes="neck_hdr_col")
        for label, prefix in _CX_NECK_ROWS:
            with Horizontal(classes="neck_row"):
                yield Static(label, classes="neck_lbl")
                yield GridInput(placeholder="kg", id=f"{prefix}_l", classes="neck_inp")
                yield GridInput(placeholder="kg", id=f"{prefix}_r", classes="neck_inp")

    def on_mount(self) -> None:
        for _, prefix in _CX_NECK_ROWS:
            row_idx = len(self._neck_grid)
            row = [f"{prefix}_l", f"{prefix}_r"]
            self._neck_grid.append(row)
            for col_idx, wid in enumerate(row):
                self._neck_grid_pos[wid] = (row_idx, col_idx)

    @on(GridInput.Navigate)
    def _on_grid_navigate(self, event: GridInput.Navigate) -> None:
        focused = self.app.focused
        if focused is None or focused.id not in self._neck_grid_pos:
            return
        row, col = self._neck_grid_pos[focused.id]
        navigated = False
        if event.direction == "up":
            target = row - 1
            if 0 <= target < len(self._neck_grid):
                try:
                    self.query_one(f"#{self._neck_grid[target][col]}").focus()
                    navigated = True
                except Exception:
                    pass
        elif event.direction == "down":
            target = row + 1
            if 0 <= target < len(self._neck_grid):
                try:
                    self.query_one(f"#{self._neck_grid[target][col]}").focus()
                    navigated = True
                except Exception:
                    pass
        elif event.direction == "left" and col > 0:
            try:
                self.query_one(f"#{self._neck_grid[row][col - 1]}").focus()
                navigated = True
            except Exception:
                pass
        elif event.direction == "right" and col < len(self._neck_grid[row]) - 1:
            try:
                self.query_one(f"#{self._neck_grid[row][col + 1]}").focus()
                navigated = True
            except Exception:
                pass
        event.stop()
        if not navigated:
            pass

    @on(GridInput.Changed)
    def _on_field_changed(self) -> None:
        self.post_message(CervicalTables.Changed())

    def collect(self) -> dict:
        data: dict = {}
        for _, prefix in _CX_NECK_ROWS:
            for side in ("l", "r"):
                fid = f"{prefix}_{side}"
                try:
                    data[fid] = self.query_one(f"#{fid}", GridInput).value.strip()
                except Exception:
                    data[fid] = ""
        return data

    def load(self, data: dict) -> None:
        for _, prefix in _CX_NECK_ROWS:
            for side in ("l", "r"):
                fid = f"{prefix}_{side}"
                try:
                    self.query_one(f"#{fid}", GridInput).value = data.get(fid, "")
                except Exception:
                    pass
