"""Lumbar Python table widgets — OP/PAIVM (passive) and hip strength/SIJ (muscle).

These are the structured grids that cannot be expressed as flat YAML rows:
  LumbarPassiveTables  — Overpressure Normal+text + PAIVM grid
  LumbarMuscleTables   — Hip strength (Wagner FPX) + SIJ provocation signs

Both post LumbarTables.Changed when any field changes, which RegionContainer
catches and converts to RegionContainer.FieldChanged for autosave.
"""

from __future__ import annotations

from textual import events
from textual.app import ComposeResult, on
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button, Label, Static, TextArea

from ...widgets import CheckButton, CycleButton, GridInput


# ── Shared changed message ────────────────────────────────────────────────────

class LumbarTables:
    """Namespace for messages shared by both lumbar table widgets."""
    class Changed(Message):
        pass


# ── Normal toggle state ───────────────────────────────────────────────────────

_NORM_STATE = [("Norm", "success")]


# ── Row / level definitions ───────────────────────────────────────────────────

# (label, prefix, bilateral) — bilateral rows show L | R columns in one row
_OP_ROWS: list[tuple[str, str, bool]] = [
    ("Tx Flexion",   "op_tx_flex",  False),
    ("Tx Extension", "op_tx_ext",   False),
    ("Tx Rotation",  "op_tx_rot",   True),
    ("Lx Flexion",   "op_lx_flex",  False),
    ("Lx Extension", "op_lx_ext",   False),
    ("Lx Lat Flex",  "op_lx_lf",    True),
]

_PAIVM_LEVELS: list[str] = [
    "T8", "T9", "T10", "T11", "T12",
    "L1", "L2", "L3",  "L4",  "L5",
]

_HIP_ROWS: list[tuple[str, str]] = [
    ("Hip flexion",      "sh_hip_flex"),
    ("Hip extension",    "sh_hip_ext"),
    ("Hip abduction",    "sh_hip_abd"),
    ("Hip adduction",    "sh_hip_add"),
    ("Hip int rotation", "sh_hip_ir"),
    ("Hip ext rotation", "sh_hip_er"),
]

_SIJ_ITEMS: list[tuple[str, str]] = [
    ("Sacral thrust",      "sij_sacral"),
    ("Post thigh thrust",  "sij_ptt"),
    ("Distraction supine", "sij_dist"),
    ("Compression s/l",    "sij_comp"),
    ("Gaenslen",           "sij_gaenslen"),
    ("ASLR compression",   "sij_aslr"),
]


# ── LumbarPassiveTables ───────────────────────────────────────────────────────

class LumbarPassiveTables(Static):
    """Overpressure Normal+text table + PAIVM grid for Lumbar passive tab."""

    DEFAULT_CSS = """
    LumbarPassiveTables { width: 100%; height: auto; }
    LumbarPassiveTables CycleButton { width: 6; height: 3; }

    LumbarPassiveTables .op_hdr      { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    LumbarPassiveTables .op_hdr_lbl  { width: 16; }
    LumbarPassiveTables .op_hdr_norm { width: 6; text-align: center; }
    LumbarPassiveTables .op_hdr_txt  { width: 1fr; }
    LumbarPassiveTables .op_row      { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    LumbarPassiveTables .op_row_lbl  { width: 16; height: 3; content-align: left middle; }
    LumbarPassiveTables .op_side     { width: 2; height: 3; content-align: left middle; color: $text-muted; }
    LumbarPassiveTables .op_txt      { width: 1fr; height: 3; padding: 0 1; }

    LumbarPassiveTables .paivm_hdr      { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    LumbarPassiveTables .paivm_hdr_lbl  { width: 6; }
    LumbarPassiveTables .paivm_hdr_norm { width: 6; text-align: center; }
    LumbarPassiveTables .paivm_hdr_txt  { width: 1fr; }
    LumbarPassiveTables .paivm_row      { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    LumbarPassiveTables .paivm_row_lbl  { width: 6; height: 3; content-align: left middle; }
    LumbarPassiveTables .paivm_txt      { width: 1fr; height: 3; padding: 0 1; }

    LumbarPassiveTables TextArea { height: auto; min-height: 2; padding: 0 1; }
    LumbarPassiveTables Label    { height: auto; margin-top: 0; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._op_grid:      list[list[str]] = []
        self._op_grid_pos:  dict[str, tuple[int, int]] = {}
        self._pm_grid:      list[list[str]] = []
        self._pm_grid_pos:  dict[str, tuple[int, int]] = {}

    def compose(self) -> ComposeResult:
        # ── Overpressure ──────────────────────────────────────────────────────
        yield Label("Overpressure", classes="subsection_header")
        with Horizontal(classes="op_hdr"):
            yield Static("",       classes="op_hdr_lbl")
            yield Static("Norm",   classes="op_hdr_norm")
            yield Static("Notes",  classes="op_hdr_txt")
        for label, prefix, bilateral in _OP_ROWS:
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
        yield TextArea(id="pm_op_notes", language="plain")

        # ── PAIVMs ────────────────────────────────────────────────────────────
        yield Label("PAIVMs", classes="subsection_header")
        with Horizontal(classes="paivm_hdr"):
            yield Static("",       classes="paivm_hdr_lbl")
            yield Static("L",      classes="paivm_hdr_norm")
            yield Static("C",      classes="paivm_hdr_norm")
            yield Static("R",      classes="paivm_hdr_norm")
            yield Static("Notes",  classes="paivm_hdr_txt")
        for level in _PAIVM_LEVELS:
            with Horizontal(classes="paivm_row"):
                yield Static(level, classes="paivm_row_lbl")
                yield CycleButton(_NORM_STATE, id=f"pm_{level}_l_norm")
                yield CycleButton(_NORM_STATE, id=f"pm_{level}_c_norm")
                yield CycleButton(_NORM_STATE, id=f"pm_{level}_r_norm")
                yield GridInput(placeholder="grade / findings",
                                id=f"pm_{level}_txt", classes="paivm_txt")
        yield Label("PAIVM notes:")
        yield TextArea(id="pm_paivm_notes", language="plain")

    def on_mount(self) -> None:
        for row_idx, (_, prefix, bilateral) in enumerate(_OP_ROWS):
            if bilateral:
                row = [f"{prefix}_l_norm_btn", f"{prefix}_l_txt",
                       f"{prefix}_r_norm_btn", f"{prefix}_r_txt"]
            else:
                row = [f"{prefix}_norm_btn", f"{prefix}_txt"]
            self._op_grid.append(row)
            for col_idx, wid in enumerate(row):
                self._op_grid_pos[wid] = (row_idx, col_idx)
        for row_idx, level in enumerate(_PAIVM_LEVELS):
            row = [f"pm_{level}_l_norm_btn", f"pm_{level}_c_norm_btn",
                   f"pm_{level}_r_norm_btn", f"pm_{level}_txt"]
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
        self.post_message(LumbarTables.Changed())

    def collect(self) -> dict:
        data: dict = {}
        for cb in self.query(CycleButton):
            data[cb.id] = cb.value
        for gi in self.query(GridInput):
            data[gi.id] = gi.value.strip()
        for tid in ("pm_op_notes", "pm_paivm_notes"):
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
        for tid in ("pm_op_notes", "pm_paivm_notes"):
            try:
                self.query_one(f"#{tid}", TextArea).text = data.get(tid, "")
            except Exception:
                pass


# ── LumbarMuscleTables ────────────────────────────────────────────────────────

class LumbarMuscleTables(Static):
    """Hip strength grid (Wagner FPX kg) + SIJ provocation signs for Lumbar muscle tab."""

    DEFAULT_CSS = """
    LumbarMuscleTables {
        width: 100%;
        height: auto;
    }
    LumbarMuscleTables .hip_hdr     { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    LumbarMuscleTables .hip_hdr_lbl { width: 18; }
    LumbarMuscleTables .hip_hdr_col { width: 1fr; text-align: center; }
    LumbarMuscleTables .hip_row     { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    LumbarMuscleTables .hip_lbl     { width: 18; height: 3; content-align: left middle; }
    LumbarMuscleTables .hip_inp     { width: 1fr; height: 3; padding: 0 1; }
    LumbarMuscleTables .sij_row { layout: horizontal; height: 3; width: 100%; }
    LumbarMuscleTables .sij_row CheckButton {
        width: 1fr; height: 3; min-width: 0; margin: 0 1 0 0;
    }
    LumbarMuscleTables .sij_row CheckButton:last-of-type { margin: 0; }
    LumbarMuscleTables Label { height: auto; margin-top: 0; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._hip_grid:     list[list[str]] = []
        self._hip_grid_pos: dict[str, tuple[int, int]] = {}

    def compose(self) -> ComposeResult:
        yield Label("Strength — Hip  (Wagner FPX kg)", classes="subsection_header")
        with Horizontal(classes="hip_hdr"):
            yield Static("",      classes="hip_hdr_lbl")
            yield Static("Left",  classes="hip_hdr_col")
            yield Static("Right", classes="hip_hdr_col")
        for label, prefix in _HIP_ROWS:
            with Horizontal(classes="hip_row"):
                yield Static(label, classes="hip_lbl")
                yield GridInput(placeholder="kg", id=f"{prefix}_l", classes="hip_inp")
                yield GridInput(placeholder="kg", id=f"{prefix}_r", classes="hip_inp")

        yield Label("SIJ Provocation Signs", classes="subsection_header")
        with Horizontal(classes="sij_row"):
            for label, sid in _SIJ_ITEMS:
                yield CheckButton(label, id=sid)

    def on_mount(self) -> None:
        for _, prefix in _HIP_ROWS:
            row_idx = len(self._hip_grid)
            row = [f"{prefix}_l", f"{prefix}_r"]
            self._hip_grid.append(row)
            for col_idx, wid in enumerate(row):
                self._hip_grid_pos[wid] = (row_idx, col_idx)

    @on(GridInput.Navigate)
    def _on_grid_navigate(self, event: GridInput.Navigate) -> None:
        focused = self.app.focused
        if focused is None or focused.id not in self._hip_grid_pos:
            return
        row, col = self._hip_grid_pos[focused.id]
        navigated = False
        if event.direction == "up":
            target = row - 1
            if 0 <= target < len(self._hip_grid):
                try:
                    self.query_one(f"#{self._hip_grid[target][col]}").focus()
                    navigated = True
                except Exception:
                    pass
        elif event.direction == "down":
            target = row + 1
            if 0 <= target < len(self._hip_grid):
                try:
                    self.query_one(f"#{self._hip_grid[target][col]}").focus()
                    navigated = True
                except Exception:
                    pass
        elif event.direction == "left" and col > 0:
            try:
                self.query_one(f"#{self._hip_grid[row][col - 1]}").focus()
                navigated = True
            except Exception:
                pass
        elif event.direction == "right" and col < len(self._hip_grid[row]) - 1:
            try:
                self.query_one(f"#{self._hip_grid[row][col + 1]}").focus()
                navigated = True
            except Exception:
                pass
        event.stop()
        if not navigated:
            pass  # boundary — let focus stay

    @on(GridInput.Changed)
    @on(CheckButton.Changed)
    def _on_field_changed(self) -> None:
        self.post_message(LumbarTables.Changed())

    def collect(self) -> dict:
        data: dict = {}
        for _, prefix in _HIP_ROWS:
            for side in ("l", "r"):
                fid = f"{prefix}_{side}"
                try:
                    data[fid] = self.query_one(f"#{fid}", GridInput).value.strip()
                except Exception:
                    data[fid] = ""
        for _, sid in _SIJ_ITEMS:
            try:
                data[sid] = self.query_one(f"#{sid}", CheckButton).value
            except Exception:
                data[sid] = None
        return data

    def load(self, data: dict) -> None:
        for _, prefix in _HIP_ROWS:
            for side in ("l", "r"):
                fid = f"{prefix}_{side}"
                try:
                    self.query_one(f"#{fid}", GridInput).value = data.get(fid, "")
                except Exception:
                    pass
        for _, sid in _SIJ_ITEMS:
            try:
                self.query_one(f"#{sid}", CheckButton).set_value(data.get(sid))
            except Exception:
                pass
