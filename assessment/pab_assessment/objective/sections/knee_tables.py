"""Knee Python table widgets — passive OP/accessory and knee strength.

KneePassiveTables  — bilateral OP Normal+text rows + patellar accessory + notes
KneeMuscleTables   — knee/calf strength bilateral numeric grid (kg or 0–5)

Both post KneeTables.Changed when any field changes.
"""

from __future__ import annotations

from textual import events
from textual.app import ComposeResult, on
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button, Label, Static, TextArea

from ...widgets import CycleButton, GridInput


class KneeTables:
    """Namespace for messages shared by both knee table widgets."""
    class Changed(Message):
        pass


_NORM_STATE = [("Norm", "success")]

_KN_OP_ROWS: list[tuple[str, str]] = [
    ("Flexion",    "kn_op_flex"),
    ("Extension",  "kn_op_ext"),
]

_KN_ACC_ROWS: list[tuple[str, str]] = [
    ("AP Glide",      "kn_acc_ap"),
    ("Patella Med",   "kn_acc_pmed"),
    ("Patella Lat",   "kn_acc_plat"),
]

_KN_STR_ROWS: list[tuple[str, str]] = [
    ("Extension (quads)",  "kn_str_ext"),
    ("Flexion (hamstring)","kn_str_flex"),
    ("Calf (heel raise)",  "kn_str_calf"),
]


class KneePassiveTables(Static):
    """Bilateral OP Normal+text table + patellar accessory for knee passive tab."""

    DEFAULT_CSS = """
    KneePassiveTables { width: 100%; height: auto; }
    KneePassiveTables CycleButton { width: 6; height: 3; }

    KneePassiveTables .op_hdr         { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    KneePassiveTables .op_hdr_lbl     { width: 18; }
    KneePassiveTables .op_hdr_side    { width: 1fr; text-align: center; }
    KneePassiveTables .op_subhdr      { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    KneePassiveTables .op_subhdr_lbl  { width: 18; }
    KneePassiveTables .op_subhdr_norm { width: 6; text-align: center; }
    KneePassiveTables .op_subhdr_txt  { width: 1fr; }
    KneePassiveTables .op_row         { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    KneePassiveTables .op_row_lbl     { width: 18; height: 3; content-align: left middle; }
    KneePassiveTables .op_txt         { width: 1fr; height: 3; padding: 0 1; }

    KneePassiveTables TextArea { height: auto; min-height: 3; max-height: 12; padding: 0 1; }
    KneePassiveTables Label    { height: auto; margin-top: 0; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._op_grid:     list[list[str]] = []
        self._op_grid_pos: dict[str, tuple[int, int]] = {}

    def compose(self) -> ComposeResult:
        yield Label("Overpressure", classes="subsection_header")
        with Horizontal(classes="op_hdr"):
            yield Static("",      classes="op_hdr_lbl")
            yield Static("Left",  classes="op_hdr_side")
            yield Static("Right", classes="op_hdr_side")
        with Horizontal(classes="op_subhdr"):
            yield Static("",      classes="op_subhdr_lbl")
            yield Static("Norm",  classes="op_subhdr_norm")
            yield Static("Notes", classes="op_subhdr_txt")
            yield Static("Norm",  classes="op_subhdr_norm")
            yield Static("Notes", classes="op_subhdr_txt")
        for label, prefix in _KN_OP_ROWS:
            with Horizontal(classes="op_row"):
                yield Static(label, classes="op_row_lbl")
                yield CycleButton(_NORM_STATE, id=f"{prefix}_l_norm")
                yield GridInput(placeholder="findings / //",
                                id=f"{prefix}_l_txt", classes="op_txt")
                yield CycleButton(_NORM_STATE, id=f"{prefix}_r_norm")
                yield GridInput(placeholder="findings / //",
                                id=f"{prefix}_r_txt", classes="op_txt")

        yield Label("Accessory Glides", classes="subsection_header")
        with Horizontal(classes="op_hdr"):
            yield Static("",      classes="op_hdr_lbl")
            yield Static("Left",  classes="op_hdr_side")
            yield Static("Right", classes="op_hdr_side")
        with Horizontal(classes="op_subhdr"):
            yield Static("",      classes="op_subhdr_lbl")
            yield Static("Norm",  classes="op_subhdr_norm")
            yield Static("Notes", classes="op_subhdr_txt")
            yield Static("Norm",  classes="op_subhdr_norm")
            yield Static("Notes", classes="op_subhdr_txt")
        for label, prefix in _KN_ACC_ROWS:
            with Horizontal(classes="op_row"):
                yield Static(label, classes="op_row_lbl")
                yield CycleButton(_NORM_STATE, id=f"{prefix}_l_norm")
                yield GridInput(placeholder="grade / findings",
                                id=f"{prefix}_l_txt", classes="op_txt")
                yield CycleButton(_NORM_STATE, id=f"{prefix}_r_norm")
                yield GridInput(placeholder="grade / findings",
                                id=f"{prefix}_r_txt", classes="op_txt")

        yield Label("OP notes:")
        yield TextArea(id="kn_op_notes", language="plain")

    def on_mount(self) -> None:
        for _, prefix in _KN_OP_ROWS:
            row = [f"{prefix}_l_norm_btn", f"{prefix}_l_txt",
                   f"{prefix}_r_norm_btn", f"{prefix}_r_txt"]
            row_idx = len(self._op_grid)
            self._op_grid.append(row)
            for col_idx, wid in enumerate(row):
                self._op_grid_pos[wid] = (row_idx, col_idx)
        for _, prefix in _KN_ACC_ROWS:
            row = [f"{prefix}_l_norm_btn", f"{prefix}_l_txt",
                   f"{prefix}_r_norm_btn", f"{prefix}_r_txt"]
            row_idx = len(self._op_grid)
            self._op_grid.append(row)
            for col_idx, wid in enumerate(row):
                self._op_grid_pos[wid] = (row_idx, col_idx)

    def _nav(self, fid: str, direction: str) -> bool:
        if fid not in self._op_grid_pos:
            return False
        row, col = self._op_grid_pos[fid]
        target_id = None
        if direction == "up" and row > 0:
            tc = min(col, len(self._op_grid[row - 1]) - 1)
            target_id = self._op_grid[row - 1][tc]
        elif direction == "down" and row < len(self._op_grid) - 1:
            tc = min(col, len(self._op_grid[row + 1]) - 1)
            target_id = self._op_grid[row + 1][tc]
        elif direction == "left" and col > 0:
            target_id = self._op_grid[row][col - 1]
        elif direction == "right" and col < len(self._op_grid[row]) - 1:
            target_id = self._op_grid[row][col + 1]
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
        if fid in self._op_grid_pos:
            if self._nav(fid, event.key):
                event.stop()

    @on(GridInput.Navigate)
    def _on_grid_navigate(self, event: GridInput.Navigate) -> None:
        focused = self.app.focused
        if focused is None:
            return
        fid = focused.id or ""
        if fid in self._op_grid_pos:
            self._nav(fid, event.direction)
            event.stop()

    @on(CycleButton.Changed)
    @on(GridInput.Changed)
    @on(TextArea.Changed, selector="TextArea")
    def _on_field_changed(self) -> None:
        self.post_message(KneeTables.Changed())

    def collect(self) -> dict:
        data: dict = {}
        for cb in self.query(CycleButton):
            data[cb.id] = cb.value
        for gi in self.query(GridInput):
            data[gi.id] = gi.value.strip()
        try:
            data["kn_op_notes"] = self.query_one("#kn_op_notes", TextArea).text
        except Exception:
            data["kn_op_notes"] = ""
        return data

    def load(self, data: dict) -> None:
        for cb in self.query(CycleButton):
            cb.set_value(data.get(cb.id))
        for gi in self.query(GridInput):
            gi.value = data.get(gi.id, "")
        try:
            self.query_one("#kn_op_notes", TextArea).text = data.get("kn_op_notes", "")
        except Exception:
            pass


class KneeMuscleTables(Static):
    """Knee/calf strength bilateral grid for knee muscle tab."""

    DEFAULT_CSS = """
    KneeMuscleTables { width: 100%; height: auto; }
    KneeMuscleTables .str_hdr     { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    KneeMuscleTables .str_hdr_lbl { width: 22; }
    KneeMuscleTables .str_hdr_col { width: 1fr; text-align: center; }
    KneeMuscleTables .str_row     { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    KneeMuscleTables .str_lbl     { width: 22; height: 3; content-align: left middle; }
    KneeMuscleTables .str_inp     { width: 1fr; height: 3; padding: 0 1; }
    KneeMuscleTables Label        { height: auto; margin-top: 0; }
    KneeMuscleTables TextArea     { height: auto; min-height: 3; max-height: 12; padding: 0 1; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._str_grid:     list[list[str]] = []
        self._str_grid_pos: dict[str, tuple[int, int]] = {}

    def compose(self) -> ComposeResult:
        yield Label("Strength — Knee / Calf  (kg or 0–5)", classes="subsection_header")
        with Horizontal(classes="str_hdr"):
            yield Static("",      classes="str_hdr_lbl")
            yield Static("Left",  classes="str_hdr_col")
            yield Static("Right", classes="str_hdr_col")
        for label, prefix in _KN_STR_ROWS:
            with Horizontal(classes="str_row"):
                yield Static(label, classes="str_lbl")
                yield GridInput(placeholder="kg / grade", id=f"{prefix}_l", classes="str_inp")
                yield GridInput(placeholder="kg / grade", id=f"{prefix}_r", classes="str_inp")
        yield Label("Notes:")
        yield TextArea(id="mu_kn_notes", language="plain")

    def on_mount(self) -> None:
        for _, prefix in _KN_STR_ROWS:
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
        if event.direction == "up" and row > 0:
            try:
                self.query_one(f"#{self._str_grid[row - 1][col]}").focus()
            except Exception:
                pass
        elif event.direction == "down" and row < len(self._str_grid) - 1:
            try:
                self.query_one(f"#{self._str_grid[row + 1][col]}").focus()
            except Exception:
                pass
        elif event.direction == "left" and col > 0:
            try:
                self.query_one(f"#{self._str_grid[row][col - 1]}").focus()
            except Exception:
                pass
        elif event.direction == "right" and col < len(self._str_grid[row]) - 1:
            try:
                self.query_one(f"#{self._str_grid[row][col + 1]}").focus()
            except Exception:
                pass
        event.stop()

    @on(GridInput.Changed)
    @on(TextArea.Changed, selector="TextArea")
    def _on_field_changed(self) -> None:
        self.post_message(KneeTables.Changed())

    def collect(self) -> dict:
        data: dict = {}
        for _, prefix in _KN_STR_ROWS:
            for side in ("l", "r"):
                fid = f"{prefix}_{side}"
                try:
                    data[fid] = self.query_one(f"#{fid}", GridInput).value.strip()
                except Exception:
                    data[fid] = ""
        try:
            data["mu_kn_notes"] = self.query_one("#mu_kn_notes", TextArea).text
        except Exception:
            data["mu_kn_notes"] = ""
        return data

    def load(self, data: dict) -> None:
        for _, prefix in _KN_STR_ROWS:
            for side in ("l", "r"):
                fid = f"{prefix}_{side}"
                try:
                    self.query_one(f"#{fid}", GridInput).value = data.get(fid, "")
                except Exception:
                    pass
        try:
            self.query_one("#mu_kn_notes", TextArea).text = data.get("mu_kn_notes", "")
        except Exception:
            pass
