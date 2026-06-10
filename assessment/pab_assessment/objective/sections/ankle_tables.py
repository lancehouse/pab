"""Ankle Python table widgets — passive OP/accessory and ankle strength.

AnklePassiveTables  — bilateral OP Normal+text rows + subtalar accessory + notes
AnkleMuscleTables   — ankle strength bilateral numeric grid (kg or 0–5)

Both post AnkleTables.Changed when any field changes.
"""

from __future__ import annotations

from textual import events
from textual.app import ComposeResult, on
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button, Label, Static, TextArea

from ...widgets import CycleButton, GridInput


class AnkleTables:
    """Namespace for messages shared by both ankle table widgets."""
    class Changed(Message):
        pass


_NORM_STATE = [("Norm", "success")]

_AK_OP_ROWS: list[tuple[str, str]] = [
    ("Dorsiflexion",   "ak_op_df"),
    ("Plantarflexion", "ak_op_pf"),
    ("Inversion",      "ak_op_inv"),
    ("Eversion",       "ak_op_ev"),
]

_AK_ACC_ROWS: list[tuple[str, str]] = [
    ("AP Glide",   "ak_acc_ap"),
    ("Subtalar",   "ak_acc_st"),
]

_AK_STR_ROWS: list[tuple[str, str]] = [
    ("Dorsiflexion (TA)",   "ak_str_df"),
    ("Plantarflexion (GS)", "ak_str_pf"),
    ("Eversion (peroneals)","ak_str_ev"),
]


class AnklePassiveTables(Static):
    """Bilateral OP Normal+text table + subtalar accessory for ankle passive tab."""

    DEFAULT_CSS = """
    AnklePassiveTables { width: 100%; height: auto; }
    AnklePassiveTables CycleButton { width: 6; height: 3; }

    AnklePassiveTables .op_hdr      { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    AnklePassiveTables .op_hdr_lbl  { width: 18; }
    AnklePassiveTables .op_hdr_side { width: 3; text-align: center; }
    AnklePassiveTables .op_hdr_norm { width: 6; text-align: center; }
    AnklePassiveTables .op_hdr_txt  { width: 1fr; }
    AnklePassiveTables .op_row      { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    AnklePassiveTables .op_row_lbl  { width: 18; height: 3; content-align: left middle; }
    AnklePassiveTables .op_side     { width: 3; height: 3; content-align: center middle; color: $text-muted; }
    AnklePassiveTables .op_txt      { width: 1fr; height: 3; padding: 0 1; }

    AnklePassiveTables TextArea { height: auto; min-height: 3; max-height: 12; padding: 0 1; }
    AnklePassiveTables Label    { height: auto; margin-top: 0; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._op_grid:     list[list[str]] = []
        self._op_grid_pos: dict[str, tuple[int, int]] = {}

    def compose(self) -> ComposeResult:
        yield Label("Overpressure", classes="subsection_header")
        with Horizontal(classes="op_hdr"):
            yield Static("",      classes="op_hdr_lbl")
            yield Static("",      classes="op_hdr_side")
            yield Static("Norm",  classes="op_hdr_norm")
            yield Static("Notes", classes="op_hdr_txt")
        for label, prefix in _AK_OP_ROWS:
            for side in ("l", "r"):
                with Horizontal(classes="op_row"):
                    yield Static(label if side == "l" else "", classes="op_row_lbl")
                    yield Static(side.upper(), classes="op_side")
                    yield CycleButton(_NORM_STATE, id=f"{prefix}_{side}_norm")
                    yield GridInput(placeholder="findings / //",
                                    id=f"{prefix}_{side}_txt", classes="op_txt")

        yield Label("Accessory Glides", classes="subsection_header")
        for label, prefix in _AK_ACC_ROWS:
            for side in ("l", "r"):
                with Horizontal(classes="op_row"):
                    yield Static(label if side == "l" else "", classes="op_row_lbl")
                    yield Static(side.upper(), classes="op_side")
                    yield CycleButton(_NORM_STATE, id=f"{prefix}_{side}_norm")
                    yield GridInput(placeholder="grade / findings",
                                    id=f"{prefix}_{side}_txt", classes="op_txt")

        yield Label("OP notes:")
        yield TextArea(id="ak_op_notes", language="plain")

    def on_mount(self) -> None:
        row_idx = 0
        for _, prefix in _AK_OP_ROWS:
            for side in ("l", "r"):
                row = [f"{prefix}_{side}_norm_btn", f"{prefix}_{side}_txt"]
                self._op_grid.append(row)
                for col_idx, wid in enumerate(row):
                    self._op_grid_pos[wid] = (row_idx, col_idx)
                row_idx += 1
        for _, prefix in _AK_ACC_ROWS:
            for side in ("l", "r"):
                row = [f"{prefix}_{side}_norm_btn", f"{prefix}_{side}_txt"]
                self._op_grid.append(row)
                for col_idx, wid in enumerate(row):
                    self._op_grid_pos[wid] = (row_idx, col_idx)
                row_idx += 1

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
        self.post_message(AnkleTables.Changed())

    def collect(self) -> dict:
        data: dict = {}
        for cb in self.query(CycleButton):
            data[cb.id] = cb.value
        for gi in self.query(GridInput):
            data[gi.id] = gi.value.strip()
        try:
            data["ak_op_notes"] = self.query_one("#ak_op_notes", TextArea).text
        except Exception:
            data["ak_op_notes"] = ""
        return data

    def load(self, data: dict) -> None:
        for cb in self.query(CycleButton):
            cb.set_value(data.get(cb.id))
        for gi in self.query(GridInput):
            gi.value = data.get(gi.id, "")
        try:
            self.query_one("#ak_op_notes", TextArea).text = data.get("ak_op_notes", "")
        except Exception:
            pass


class AnkleMuscleTables(Static):
    """Ankle strength bilateral grid for ankle muscle tab."""

    DEFAULT_CSS = """
    AnkleMuscleTables { width: 100%; height: auto; }
    AnkleMuscleTables .str_hdr     { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    AnkleMuscleTables .str_hdr_lbl { width: 22; }
    AnkleMuscleTables .str_hdr_col { width: 1fr; text-align: center; }
    AnkleMuscleTables .str_row     { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    AnkleMuscleTables .str_lbl     { width: 22; height: 3; content-align: left middle; }
    AnkleMuscleTables .str_inp     { width: 1fr; height: 3; padding: 0 1; }
    AnkleMuscleTables Label        { height: auto; margin-top: 0; }
    AnkleMuscleTables TextArea     { height: auto; min-height: 3; max-height: 12; padding: 0 1; }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._str_grid:     list[list[str]] = []
        self._str_grid_pos: dict[str, tuple[int, int]] = {}

    def compose(self) -> ComposeResult:
        yield Label("Strength — Ankle  (kg or 0–5)", classes="subsection_header")
        with Horizontal(classes="str_hdr"):
            yield Static("",      classes="str_hdr_lbl")
            yield Static("Left",  classes="str_hdr_col")
            yield Static("Right", classes="str_hdr_col")
        for label, prefix in _AK_STR_ROWS:
            with Horizontal(classes="str_row"):
                yield Static(label, classes="str_lbl")
                yield GridInput(placeholder="kg / grade", id=f"{prefix}_l", classes="str_inp")
                yield GridInput(placeholder="kg / grade", id=f"{prefix}_r", classes="str_inp")
        yield Label("Notes:")
        yield TextArea(id="mu_ak_notes", language="plain")

    def on_mount(self) -> None:
        for _, prefix in _AK_STR_ROWS:
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
        self.post_message(AnkleTables.Changed())

    def collect(self) -> dict:
        data: dict = {}
        for _, prefix in _AK_STR_ROWS:
            for side in ("l", "r"):
                fid = f"{prefix}_{side}"
                try:
                    data[fid] = self.query_one(f"#{fid}", GridInput).value.strip()
                except Exception:
                    data[fid] = ""
        try:
            data["mu_ak_notes"] = self.query_one("#mu_ak_notes", TextArea).text
        except Exception:
            data["mu_ak_notes"] = ""
        return data

    def load(self, data: dict) -> None:
        for _, prefix in _AK_STR_ROWS:
            for side in ("l", "r"):
                fid = f"{prefix}_{side}"
                try:
                    self.query_one(f"#{fid}", GridInput).value = data.get(fid, "")
                except Exception:
                    pass
        try:
            self.query_one("#mu_ak_notes", TextArea).text = data.get("mu_ak_notes", "")
        except Exception:
            pass
