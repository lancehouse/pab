"""Cervical Python table widgets — OP/PAIVM (passive) and neck strength (muscle).

CervicalPassiveTables  — Overpressure end-feel/response + PAIVM grid C0/1–T4
CervicalMuscleTables   — Neck strength bilateral grid (kg)

Both post CervicalTables.Changed when any field changes, which RegionContainer
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

class CervicalTables:
    """Namespace for messages shared by both cervical table widgets."""
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

_PAIVM = [
    ("Norm",  "success"),
    ("↑R",    "warning"),
    ("↑R+P",  "error"),
    ("Pain",  "error"),
    ("↓R",    "default"),
]

_CX_OP_ROWS: list[tuple[str, str]] = [
    ("Cx Flexion",    "cx_op_flex"),
    ("Cx Extension",  "cx_op_ext"),
    ("Cx Lat Fl L",   "cx_op_lf_l"),
    ("Cx Lat Fl R",   "cx_op_lf_r"),
    ("Cx Rotation L", "cx_op_rot_l"),
    ("Cx Rotation R", "cx_op_rot_r"),
    ("Cx Quadrant L", "cx_op_quad_l"),
    ("Cx Quadrant R", "cx_op_quad_r"),
]

# (display_label, id_key) — id_key is used in field IDs (no slashes)
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

_CX_PAIVM_DIRS = ("ul_l", "c", "ul_r")

_CX_NECK_ROWS: list[tuple[str, str]] = [
    ("Neck flexion",   "cx_neck_flex"),
    ("Neck extension", "cx_neck_ext"),
    ("Neck lat flex",  "cx_neck_lf"),
    ("Neck rotation",  "cx_neck_rot"),
]


def _cx_paivm_id(level_key: str, direction: str) -> str:
    return f"cx_pm_{level_key}_{direction}"


# ── CervicalPassiveTables ─────────────────────────────────────────────────────

class CervicalPassiveTables(Static):
    """Overpressure end-feel/response table + PAIVM grid C0/1–T4 for cervical passive tab."""

    DEFAULT_CSS = """
    CervicalPassiveTables {
        width: 100%;
        height: auto;
    }
    CervicalPassiveTables .op_hdr      { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    CervicalPassiveTables .op_hdr_lbl  { width: 16; }
    CervicalPassiveTables .op_hdr_ef   { width: 24; text-align: center; }
    CervicalPassiveTables .op_hdr_gap  { width: 2; }
    CervicalPassiveTables .op_hdr_resp { width: 24; text-align: center; }
    CervicalPassiveTables .op_row      { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    CervicalPassiveTables .op_row_lbl  { width: 16; height: 3; content-align: left middle; }
    CervicalPassiveTables .op_gap      { width: 2; height: 3; }
    CervicalPassiveTables .paivm_hdr     { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    CervicalPassiveTables .paivm_hdr_lbl { width: 6; }
    CervicalPassiveTables .paivm_hdr_col { width: 30; text-align: center; }
    CervicalPassiveTables .paivm_hdr_gap { width: 2; }
    CervicalPassiveTables .paivm_row     { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    CervicalPassiveTables .paivm_row_lbl { width: 6; height: 3; content-align: left middle; }
    CervicalPassiveTables .paivm_gap     { width: 2; height: 3; }
    CervicalPassiveTables TextArea { height: auto; min-height: 2; padding: 0 1; }
    CervicalPassiveTables Label    { height: auto; margin-top: 0; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._grid:     list[list[str]] = []
        self._grid_pos: dict[str, tuple[int, int]] = {}

    def compose(self) -> ComposeResult:
        yield Label("Overpressure", classes="subsection_header")
        with Horizontal(classes="op_hdr"):
            yield Static("",          classes="op_hdr_lbl")
            yield Static("End-feel",  classes="op_hdr_ef")
            yield Static("",          classes="op_hdr_gap")
            yield Static("Response",  classes="op_hdr_resp")
        for label, prefix in _CX_OP_ROWS:
            with Horizontal(classes="op_row"):
                yield Static(label, classes="op_row_lbl")
                yield RadioGroup(_END_FEEL, id=f"{prefix}_ef")
                yield Static("",    classes="op_gap")
                yield RadioGroup(_OP_RESP,  id=f"{prefix}_resp")
        yield Label("OP notes:")
        yield TextArea(id="cx_pm_op_notes", language="plain")

        yield Label("PAIVMs", classes="subsection_header")
        with Horizontal(classes="paivm_hdr"):
            yield Static("",        classes="paivm_hdr_lbl")
            yield Static("Left",    classes="paivm_hdr_col")
            yield Static("",        classes="paivm_hdr_gap")
            yield Static("Central", classes="paivm_hdr_col")
            yield Static("",        classes="paivm_hdr_gap")
            yield Static("Right",   classes="paivm_hdr_col")
        for display, key in _CX_PAIVM_LEVELS:
            with Horizontal(classes="paivm_row"):
                yield Static(display, classes="paivm_row_lbl")
                yield RadioGroup(_PAIVM, id=_cx_paivm_id(key, "ul_l"))
                yield Static("",        classes="paivm_gap")
                yield RadioGroup(_PAIVM, id=_cx_paivm_id(key, "c"))
                yield Static("",        classes="paivm_gap")
                yield RadioGroup(_PAIVM, id=_cx_paivm_id(key, "ul_r"))
        yield Label("PAIVM notes:")
        yield TextArea(id="cx_pm_paivm_notes", language="plain")

    def on_mount(self) -> None:
        for row_idx, (_, key) in enumerate(_CX_PAIVM_LEVELS):
            row = [_cx_paivm_id(key, d) for d in _CX_PAIVM_DIRS]
            self._grid.append(row)
            for col_idx, rg_id in enumerate(row):
                self._grid_pos[rg_id] = (row_idx, col_idx)

    def on_key(self, event: events.Key) -> None:
        focused = self.app.focused
        if not isinstance(focused, RadioGroup):
            return
        fid = focused.id or ""
        if fid not in self._grid_pos:
            return
        if event.key not in ("up", "down"):
            return
        row, col = self._grid_pos[fid]
        target_row = row - 1 if event.key == "up" else row + 1
        if 0 <= target_row < len(self._grid):
            try:
                self.query_one(f"#{self._grid[target_row][col]}", RadioGroup).focus()
                event.stop()
            except Exception:
                pass

    @on(RadioGroup.Changed)
    @on(TextArea.Changed, selector="TextArea")
    def _on_field_changed(self) -> None:
        self.post_message(CervicalTables.Changed())

    def collect(self) -> dict:
        data: dict = {}
        for rg in self.query(RadioGroup):
            data[rg.id] = rg.value
        for tid in ("cx_pm_op_notes", "cx_pm_paivm_notes"):
            try:
                data[tid] = self.query_one(f"#{tid}", TextArea).text
            except Exception:
                data[tid] = ""
        return data

    def load(self, data: dict) -> None:
        for rg in self.query(RadioGroup):
            rg.set_value(data.get(rg.id))
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
