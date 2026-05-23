"""YAML-driven region block renderer for Objective TUI.

RegionContainer  — collapsible per-region block for one objective tab.
                   Renders YAML-defined flat fields + optional Python extras.
RegionTabContent — the full tab container; manages one RegionContainer per
                   active region, stacked vertically.

Supported YAML field group types (in lumbar.yaml):
  active_movement  → ROMGroupWidget (RangeCell/ROMRow tables)
  muscle_testing   → GradeGroupWidget (bilateral/unilateral RadioGroup rows)
                   + TrunkStrengthWidget (numeric GridInput rows)
  special_tests    → SpecialTestsWidget (RadioGroup rows)

Python extras (OP/PAIVM/hip/SIJ) registered per (region_id, section_key)
in REGION_EXTRAS at the bottom of this file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Type

import yaml

from textual.app import ComposeResult, on
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import Label, Static, TextArea

from ...widgets import GridInput, RadioGroup
from .active_movement import RangeCell, ROMRow
from .cervical_tables import CervicalMuscleTables, CervicalPassiveTables, CervicalTables
from .lumbar_tables import LumbarMuscleTables, LumbarPassiveTables, LumbarTables


_YAML_DIR = Path(__file__).parent / "yaml"

# Maps section_key ("active", "passive", "muscle", "special") → yaml top-level key
_YAML_KEY: dict[str, str] = {
    "active":  "active_movement",
    "muscle":  "muscle_testing",
    "special": "special_tests",
}


def _load_yaml(region_id: str) -> dict:
    path = _YAML_DIR / f"{region_id}.yaml"
    return yaml.safe_load(path.read_text()) if path.exists() else {}


def _infer_variant(idx: int, total: int) -> str:
    if idx == 0:
        return "success"
    if total == 2 or idx == total - 1:
        return "error"
    return "warning"


def _build_gang(options: list[str]) -> list[tuple[str, str]]:
    total = len(options)
    return [(label, _infer_variant(i, total)) for i, label in enumerate(options)]


# ── ROM group widget ──────────────────────────────────────────────────────────

class ROMGroupWidget(Static):
    """One named group of ROM rows (Ax/ReAx L/R) from YAML active_movement.groups."""

    DEFAULT_CSS = """
    ROMGroupWidget { width: 100%; height: auto; }
    ROMGroupWidget .hdr_major  { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    ROMGroupWidget .hdr_spacer { width: 12; }
    ROMGroupWidget .hdr_group  { width: 2fr; text-align: center; text-style: bold; }
    ROMGroupWidget .hdr_sub    { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    ROMGroupWidget .hdr_lr     { width: 1fr; text-align: center; }
    ROMGroupWidget TextArea    { height: auto; min-height: 2; padding: 0 1; }
    ROMGroupWidget Label       { height: auto; margin-top: 0; }
    """

    def __init__(self, group_def: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self._group = group_def
        self._notes_id: str | None = group_def.get("notes_id")
        self._row_ids: list[str] = [r["id"] for r in group_def.get("rows", [])]

    def compose(self) -> ComposeResult:
        label = self._group.get("label", "")
        yield Label(label, classes="subsection_header")
        with Horizontal(classes="hdr_major"):
            yield Static("",     classes="hdr_spacer")
            yield Static("Ax",   classes="hdr_group")
            yield Static("ReAx", classes="hdr_group")
        with Horizontal(classes="hdr_sub"):
            yield Static("",      classes="hdr_spacer")
            yield Static("Left",  classes="hdr_lr")
            yield Static("Right", classes="hdr_lr")
            yield Static("Left",  classes="hdr_lr")
            yield Static("Right", classes="hdr_lr")
        for row in self._group.get("rows", []):
            yield ROMRow(
                row["label"],
                row["id"],
                bilateral=row.get("bilateral", False),
                id=f"romrow_{row['id']}",
            )
        if self._notes_id:
            yield Label("Comment:")
            yield TextArea(id=self._notes_id, language="plain")

    def collect(self) -> dict:
        data: dict = {}
        for rid in self._row_ids:
            try:
                data.update(self.query_one(f"#romrow_{rid}", ROMRow).collect())
            except Exception:
                pass
        if self._notes_id:
            try:
                data[self._notes_id] = self.query_one(f"#{self._notes_id}", TextArea).text
            except Exception:
                data[self._notes_id] = ""
        return data

    def load(self, data: dict) -> None:
        for rid in self._row_ids:
            try:
                self.query_one(f"#romrow_{rid}", ROMRow).load(data)
            except Exception:
                pass
        if self._notes_id:
            try:
                self.query_one(f"#{self._notes_id}", TextArea).text = data.get(self._notes_id, "")
            except Exception:
                pass


# ── Grade group widget (bilateral / unilateral RadioGroup rows) ───────────────

class GradeGroupWidget(Static):
    """One group of RadioGroup rows — bilateral (L/R) or unilateral (single)."""

    DEFAULT_CSS = """
    GradeGroupWidget { width: 100%; height: auto; }
    GradeGroupWidget .hdr  { layout: horizontal; height: 1; width: 100%; color: $text-muted; }
    GradeGroupWidget .hlbl { width: 18; }
    GradeGroupWidget .hcol { width: 24; text-align: center; }
    GradeGroupWidget .hgap { width: 2; }
    GradeGroupWidget .row  { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    GradeGroupWidget .rlbl { width: 18; height: 3; content-align: left middle; }
    GradeGroupWidget .rgap { width: 2; height: 3; }
    GradeGroupWidget Label { height: auto; margin-top: 0; }
    """

    def __init__(self, group_def: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self._group = group_def
        self._bilateral = (group_def.get("type", "bilateral") == "bilateral")
        self._gang = _build_gang(group_def.get("options", []))
        self._rows: list[dict] = group_def.get("rows", [])
        self._grid: list[list[str]] = []
        self._grid_pos: dict[str, tuple[int, int]] = {}

    def _rg_id(self, row_id: str, side: str = "") -> str:
        return f"{row_id}_{side}" if side else row_id

    def compose(self) -> ComposeResult:
        label = self._group.get("label", "")
        yield Label(label, classes="subsection_header")
        if self._bilateral:
            with Horizontal(classes="hdr"):
                yield Static("",      classes="hlbl")
                yield Static("Left",  classes="hcol")
                yield Static("",      classes="hgap")
                yield Static("Right", classes="hcol")
        for row in self._rows:
            with Horizontal(classes="row"):
                yield Static(row["label"], classes="rlbl")
                if self._bilateral:
                    yield RadioGroup(self._gang, id=self._rg_id(row["id"], "l"))
                    yield Static("", classes="rgap")
                    yield RadioGroup(self._gang, id=self._rg_id(row["id"], "r"))
                else:
                    yield RadioGroup(self._gang, id=self._rg_id(row["id"]))

    def on_mount(self) -> None:
        for row_idx, row in enumerate(self._rows):
            if self._bilateral:
                ids = [self._rg_id(row["id"], "l"), self._rg_id(row["id"], "r")]
            else:
                ids = [self._rg_id(row["id"])]
            self._grid.append(ids)
            for col_idx, rg_id in enumerate(ids):
                self._grid_pos[rg_id] = (row_idx, col_idx)

    def on_key(self, event) -> None:
        focused = self.app.focused
        if not isinstance(focused, RadioGroup):
            return
        fid = focused.id or ""
        if fid not in self._grid_pos:
            return
        if event.key not in ("up", "down"):
            return
        row, col = self._grid_pos[fid]
        target = row - 1 if event.key == "up" else row + 1
        if 0 <= target < len(self._grid):
            try:
                self.query_one(f"#{self._grid[target][col]}", RadioGroup).focus()
                event.stop()
            except Exception:
                pass

    def collect(self) -> dict:
        data: dict = {}
        for rg in self.query(RadioGroup):
            data[rg.id] = rg.value
        return data

    def load(self, data: dict) -> None:
        for rg in self.query(RadioGroup):
            rg.set_value(data.get(rg.id))


# ── Trunk strength widget (numeric GridInput rows) ────────────────────────────

class TrunkStrengthWidget(Static):
    """Numeric GridInput rows for trunk strength (reps, raises, etc.)."""

    DEFAULT_CSS = """
    TrunkStrengthWidget { width: 100%; height: auto; }
    TrunkStrengthWidget .row { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    TrunkStrengthWidget .lbl { width: 18; height: 3; content-align: left middle; }
    TrunkStrengthWidget .inp { width: 1fr; height: 3; padding: 0 1; }
    TrunkStrengthWidget Label { height: auto; margin-top: 0; }
    """

    def __init__(self, group_def: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self._rows: list[dict] = group_def.get("rows", [])
        label = group_def.get("label", "Trunk Strength")
        self._label = label

    def compose(self) -> ComposeResult:
        yield Label(self._label, classes="subsection_header")
        for row in self._rows:
            with Horizontal(classes="row"):
                yield Static(row["label"], classes="lbl")
                yield GridInput(
                    placeholder=row.get("placeholder", ""),
                    id=row["id"],
                    classes="inp",
                )

    def collect(self) -> dict:
        data: dict = {}
        for row in self._rows:
            try:
                data[row["id"]] = self.query_one(f"#{row['id']}", GridInput).value.strip()
            except Exception:
                data[row["id"]] = ""
        return data

    def load(self, data: dict) -> None:
        for row in self._rows:
            try:
                self.query_one(f"#{row['id']}", GridInput).value = data.get(row["id"], "")
            except Exception:
                pass


# ── Special tests widget ──────────────────────────────────────────────────────

class SpecialTestsWidget(Static):
    """RadioGroup rows for special tests from YAML special_tests section."""

    DEFAULT_CSS = """
    SpecialTestsWidget { width: 100%; height: auto; }
    SpecialTestsWidget .row  { layout: horizontal; height: 3; width: 100%; margin-bottom: 0; }
    SpecialTestsWidget .rlbl { width: 18; height: 3; content-align: left middle; }
    SpecialTestsWidget TextArea { height: auto; min-height: 2; padding: 0 1; }
    SpecialTestsWidget Label    { height: auto; margin-top: 0; }
    """

    def __init__(self, section_def: dict, **kwargs) -> None:
        super().__init__(**kwargs)
        self._rows: list[dict] = section_def.get("rows", [])
        self._notes_id: str | None = section_def.get("notes_id")
        self._grid: list[str] = []
        self._grid_pos: dict[str, int] = {}

    def _rg_id(self, row_id: str) -> str:
        return f"st_{row_id}"

    def compose(self) -> ComposeResult:
        for row in self._rows:
            gang = _build_gang(row.get("options", ["Negative", "Positive"]))
            with Horizontal(classes="row"):
                yield Static(row["label"], classes="rlbl")
                yield RadioGroup(gang, id=self._rg_id(row["id"]))
        if self._notes_id:
            yield Label("Notes:")
            yield TextArea(id=self._notes_id, language="plain")

    def on_mount(self) -> None:
        for idx, row in enumerate(self._rows):
            rg_id = self._rg_id(row["id"])
            self._grid.append(rg_id)
            self._grid_pos[rg_id] = idx

    def on_key(self, event) -> None:
        focused = self.app.focused
        if not isinstance(focused, RadioGroup):
            return
        fid = focused.id or ""
        if fid not in self._grid_pos:
            return
        if event.key not in ("up", "down"):
            return
        idx = self._grid_pos[fid]
        target = idx - 1 if event.key == "up" else idx + 1
        if 0 <= target < len(self._grid):
            try:
                self.query_one(f"#{self._grid[target]}", RadioGroup).focus()
                event.stop()
            except Exception:
                pass

    def collect(self) -> dict:
        data: dict = {}
        for rg in self.query(RadioGroup):
            data[rg.id] = rg.value
        if self._notes_id:
            try:
                data[self._notes_id] = self.query_one(f"#{self._notes_id}", TextArea).text
            except Exception:
                data[self._notes_id] = ""
        return data

    def load(self, data: dict) -> None:
        for rg in self.query(RadioGroup):
            rg.set_value(data.get(rg.id))
        if self._notes_id:
            try:
                self.query_one(f"#{self._notes_id}", TextArea).text = data.get(self._notes_id, "")
            except Exception:
                pass


# ── RegionContainer ───────────────────────────────────────────────────────────

class RegionContainer(Static):
    """Collapsible block for one region's content within one objective tab.

    Renders YAML-driven flat fields (ROMGroupWidget, GradeGroupWidget, etc.)
    and optionally mounts a Python extras widget (LumbarPassiveTables, etc.)
    registered in REGION_EXTRAS.
    """

    class FieldChanged(Message):
        pass

    DEFAULT_CSS = """
    RegionContainer {
        width: 100%;
        height: auto;
        border: solid $border;
        margin-bottom: 1;
    }
    RegionContainer .region_header {
        background: $panel-darken-1;
        color: $text;
        text-style: bold;
        height: 2;
        padding: 0 1;
        content-align: left middle;
        width: 100%;
    }
    RegionContainer .region_body {
        width: 100%;
        height: auto;
        padding: 0 1 1 1;
    }
    """

    def __init__(self, region_id: str, section_key: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._region_id = region_id
        self._section_key = section_key
        self._yaml = _load_yaml(region_id)
        self._extras_class: Type | None = REGION_EXTRAS.get((region_id, section_key))
        self._loading = False
        self._notes_ids: list[str] = []

    def compose(self) -> ComposeResult:
        label = self._yaml.get("label", self._region_id.upper())
        yield Static(f"▼ {label}", classes="region_header")
        with Vertical(classes="region_body"):
            yield from self._compose_yaml_widgets()
            if self._extras_class is not None:
                yield self._extras_class(
                    id=f"extras_{self._region_id}_{self._section_key}"
                )

    def _compose_yaml_widgets(self) -> ComposeResult:
        yaml_key = _YAML_KEY.get(self._section_key, "")
        if not yaml_key:
            return
        section_def = self._yaml.get(yaml_key, {})
        if not section_def:
            return

        if self._section_key == "active":
            for group in section_def.get("groups", []):
                notes_id = group.get("notes_id", "")
                yield ROMGroupWidget(group, id=f"romgrp_{self._region_id}_{notes_id}")

        elif self._section_key == "muscle":
            for group in section_def.get("groups", []):
                gtype = group.get("type", "bilateral")
                slug = group["label"].lower().replace(" ", "_")
                if gtype in ("bilateral", "unilateral"):
                    yield GradeGroupWidget(group, id=f"grade_{self._region_id}_{slug}")
                elif gtype == "numeric":
                    yield TrunkStrengthWidget(group, id=f"trunk_{self._region_id}_{slug}")
            notes_id = section_def.get("notes_id")
            if notes_id:
                self._notes_ids.append(notes_id)
                yield Label("Notes:")
                yield TextArea(id=notes_id, language="plain")

        elif self._section_key == "special":
            yield SpecialTestsWidget(
                section_def, id=f"sptests_{self._region_id}"
            )

    # ── Event handlers ────────────────────────────────────────────────────────

    @on(RadioGroup.Changed)
    @on(TextArea.Changed)
    @on(GridInput.Changed)
    @on(LumbarTables.Changed)
    @on(CervicalTables.Changed)
    def _on_any_field_changed(self) -> None:
        if not self._loading:
            self.post_message(self.FieldChanged())

    # ── collect / load ────────────────────────────────────────────────────────

    def collect(self) -> dict:
        data: dict = {}
        for cls in (ROMGroupWidget, GradeGroupWidget, TrunkStrengthWidget, SpecialTestsWidget):
            for w in self.query(cls):
                data.update(w.collect())
        for nid in self._notes_ids:
            try:
                data[nid] = self.query_one(f"#{nid}", TextArea).text
            except Exception:
                data[nid] = ""
        if self._extras_class is not None:
            extras_id = f"#extras_{self._region_id}_{self._section_key}"
            try:
                extras = self.query_one(extras_id, self._extras_class)
                data.update(extras.collect())
            except Exception:
                pass
        return data

    def load(self, data: dict) -> None:
        self._loading = True
        try:
            for cls in (ROMGroupWidget, GradeGroupWidget, TrunkStrengthWidget, SpecialTestsWidget):
                for w in self.query(cls):
                    w.load(data)
            for nid in self._notes_ids:
                try:
                    self.query_one(f"#{nid}", TextArea).text = data.get(nid, "")
                except Exception:
                    pass
            if self._extras_class is not None:
                extras_id = f"#extras_{self._region_id}_{self._section_key}"
                try:
                    extras = self.query_one(extras_id, self._extras_class)
                    extras.load(data)
                except Exception:
                    pass
        finally:
            self._loading = False

    def is_complete(self) -> bool:
        return bool(self.collect())


# ── RegionTabContent ──────────────────────────────────────────────────────────

class RegionTabContent(Container):
    """Variable objective tab — shows one collapsible RegionContainer per active region."""

    class FieldChanged(Message):
        pass

    DEFAULT_CSS = """
    RegionTabContent {
        width: 100%;
        height: auto;
        padding: 0 1 2 1;
    }
    RegionTabContent .tab_title { text-style: bold; margin-bottom: 1; }
    RegionTabContent .no_region {
        color: $text-muted;
        margin: 2 1;
    }
    """

    def __init__(self, section_key: str, tab_label: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._section_key = section_key
        self._tab_label = tab_label
        self._containers: dict[str, RegionContainer] = {}
        self.session_file = ""
        self._loading = False

    def compose(self) -> ComposeResult:
        yield Label(self._tab_label, classes="tab_title")
        yield Static("No region selected. Enable a region from the topbar.",
                     id="no_region_msg", classes="no_region")

    def _update_empty_msg(self) -> None:
        try:
            msg = self.query_one("#no_region_msg", Static)
            msg.display = len(self._containers) == 0
        except Exception:
            pass

    def mount_region(self, region_id: str) -> None:
        if region_id in self._containers:
            return
        container = RegionContainer(
            region_id,
            self._section_key,
            id=f"rc_{region_id}_{self._section_key}",
        )
        self._containers[region_id] = container
        self.mount(container)
        self._update_empty_msg()

    def unmount_region(self, region_id: str) -> None:
        container = self._containers.pop(region_id, None)
        if container:
            container.remove()
        self._update_empty_msg()

    def get_container(self, region_id: str) -> RegionContainer | None:
        return self._containers.get(region_id)

    @on(RegionContainer.FieldChanged)
    def _on_region_changed(self) -> None:
        if not self._loading:
            self.post_message(self.FieldChanged())

    def collect(self) -> dict:
        return {rid: c.collect() for rid, c in self._containers.items()}

    def load(self, data: dict) -> None:
        for rid, container in self._containers.items():
            container.load(data.get(rid, {}))

    def is_complete(self) -> bool:
        return any(c.is_complete() for c in self._containers.values())


# ── Region extras registry ────────────────────────────────────────────────────
# Add entries here when new region Python table widgets are created.
# Key: (region_id, section_key)  Value: widget class

REGION_EXTRAS: dict[tuple[str, str], Type] = {
    ("lumbar",    "passive"): LumbarPassiveTables,
    ("lumbar",    "muscle"):  LumbarMuscleTables,
    ("cervical",  "passive"): CervicalPassiveTables,
    ("cervical",  "muscle"):  CervicalMuscleTables,
}
