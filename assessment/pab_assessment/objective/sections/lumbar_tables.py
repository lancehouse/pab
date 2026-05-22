"""Lumbar Python table widgets — OP/PAIVM (passive) and hip strength/SIJ (muscle).

These are the structured grids that cannot be expressed as flat YAML rows:
  LumbarPassiveTables  — Overpressure end-feel/response + PAIVM grid
  LumbarMuscleTables   — Hip strength (Wagner FPX) + SIJ provocation signs

Both post LumbarTables.Changed when any field changes, which RegionContainer
catches and converts to RegionContainer.FieldChanged for autosave.
"""

from __future__ import annotations

from textual import events
from textual.app import ComposeResult, on
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Label, Static, TextArea

from ...widgets import CheckButton, GridInput, RadioGroup


# ── Shared changed message ────────────────────────────────────────────────────

class LumbarTables:
    """Namespace for messages shared by both lumbar table widgets."""
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

_OP_ROWS: list[tuple[str, str]] = [
    ("Tx Flexion",   "op_tx_flex"),
    ("Tx Extension", "op_tx_ext"),
    ("Tx Rot L",     "op_tx_rot_l"),
    ("Tx Rot R",     "op_tx_rot_r"),
    ("Lx Flexion",   "op_lx_flex"),
    ("Lx Extension", "op_lx_ext"),
    ("Lx Lat Fl L",  "op_lx_lf_l"),
    ("Lx Lat Fl R",  "op_lx_lf_r"),
]

_PAIVM_LEVELS: list[str] = [
    "T8", "T9", "T10", "T11", "T12",
    "L1", "L2", "L3",  "L4",  "L5",
]

_PAIVM_DIRS = ("ul_l", "c", "ul_r")

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


def _paivm_id(level: str, direction: str) -> str:
    return f"pm_{level}_{direction}"


# ── LumbarPassiveTables ───────────────────────────────────────────────────────

class LumbarPassiveTables(Static):
    """Overpressure end-feel/response table + PAIVM grid for Lumbar passive tab."""

    DEFAULT_CSS = """
    LumbarPassiveTables {
        width: 100%;
        height: auto;
    }
    LumbarPassiveTables .op_hdr      { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    LumbarPassiveTables .op_hdr_lbl  { width: 16; }
    LumbarPassiveTables .op_hdr_ef   { width: 24; text-align: center; }
    LumbarPassiveTables .op_hdr_gap  { width: 2; }
    LumbarPassiveTables .op_hdr_resp { width: 24; text-align: center; }
    LumbarPassiveTables .op_row      { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    LumbarPassiveTables .op_row_lbl  { width: 16; height: 3; content-align: left middle; }
    LumbarPassiveTables .op_gap      { width: 2; height: 3; }
    LumbarPassiveTables .paivm_hdr     { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    LumbarPassiveTables .paivm_hdr_lbl { width: 6; }
    LumbarPassiveTables .paivm_hdr_col { width: 30; text-align: center; }
    LumbarPassiveTables .paivm_hdr_gap { width: 2; }
    LumbarPassiveTables .paivm_row     { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    LumbarPassiveTables .paivm_row_lbl { width: 6; height: 3; content-align: left middle; }
    LumbarPassiveTables .paivm_gap     { width: 2; height: 3; }
    LumbarPassiveTables TextArea { height: auto; min-height: 2; padding: 0 1; }
    LumbarPassiveTables Label    { height: auto; margin-top: 0; }
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
        for label, prefix in _OP_ROWS:
            with Horizontal(classes="op_row"):
                yield Static(label, classes="op_row_lbl")
                yield RadioGroup(_END_FEEL, id=f"{prefix}_ef")
                yield Static("",    classes="op_gap")
                yield RadioGroup(_OP_RESP,  id=f"{prefix}_resp")
        yield Label("OP notes:")
        yield TextArea(id="pm_op_notes", language="plain")

        yield Label("PAIVMs", classes="subsection_header")
        with Horizontal(classes="paivm_hdr"):
            yield Static("",        classes="paivm_hdr_lbl")
            yield Static("Left",    classes="paivm_hdr_col")
            yield Static("",        classes="paivm_hdr_gap")
            yield Static("Central", classes="paivm_hdr_col")
            yield Static("",        classes="paivm_hdr_gap")
            yield Static("Right",   classes="paivm_hdr_col")
        for level in _PAIVM_LEVELS:
            with Horizontal(classes="paivm_row"):
                yield Static(level, classes="paivm_row_lbl")
                yield RadioGroup(_PAIVM, id=_paivm_id(level, "ul_l"))
                yield Static("",    classes="paivm_gap")
                yield RadioGroup(_PAIVM, id=_paivm_id(level, "c"))
                yield Static("",    classes="paivm_gap")
                yield RadioGroup(_PAIVM, id=_paivm_id(level, "ul_r"))
        yield Label("PAIVM notes:")
        yield TextArea(id="pm_paivm_notes", language="plain")

    def on_mount(self) -> None:
        for row_idx, level in enumerate(_PAIVM_LEVELS):
            row = [_paivm_id(level, d) for d in _PAIVM_DIRS]
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
        self.post_message(LumbarTables.Changed())

    def collect(self) -> dict:
        data: dict = {}
        for rg in self.query(RadioGroup):
            data[rg.id] = rg.value
        for tid in ("pm_op_notes", "pm_paivm_notes"):
            try:
                data[tid] = self.query_one(f"#{tid}", TextArea).text
            except Exception:
                data[tid] = ""
        return data

    def load(self, data: dict) -> None:
        for rg in self.query(RadioGroup):
            rg.set_value(data.get(rg.id))
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
