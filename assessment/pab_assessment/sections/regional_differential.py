"""Regional differential panel for Pain Classification (section 05)."""

from __future__ import annotations
import re
import logging
from pathlib import Path

import yaml
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Collapsible, Static

from ..objective.kb_loader import get_registry, KBEntry

logger = logging.getLogger(__name__)

_YAML_DIR = Path(__file__).parent.parent / "objective" / "sections" / "yaml"

_BADGE_MAP: dict = {
    None:  ("  —  ", "badge_none"),
    "Yes": (" Pos ", "badge_pos"),
    "No":  (" Neg ", "badge_neg"),
}


def _short_sn_sp(raw: str) -> str:
    """Extract compact Sn/Sp: 'Sn 72–79% / Sp 56–66% (...)' → 'Sn 79% Sp 66%'."""
    m = re.search(r"Sn\s+(?:\d+[–-])?(\d+)%\s*/\s*Sp\s+(?:\d+[–-])?(\d+)%", raw)
    if m:
        return f"Sn {m.group(1)}% Sp {m.group(2)}%"
    return "—"


def _load_region_structure(region_id: str) -> dict:
    """Load special_tests groups from the region YAML."""
    yaml_path = _YAML_DIR / f"{region_id}.yaml"
    try:
        with open(yaml_path) as f:
            data = yaml.safe_load(f) or {}
        return data.get("special_tests", {})
    except Exception as e:
        logger.warning("Failed to load region YAML %s: %s", yaml_path, e)
        return {}


def _cluster_note_for(group_def: dict, kb: dict) -> str:
    """Return first non-empty cluster note from this group's KB entries."""
    for row in group_def.get("rows", []):
        entry = kb.get(row["id"])
        if entry and entry.cluster:
            return entry.cluster
    return ""


# ── Message ───────────────────────────────────────────────────────────────────

class RequestKBEntry(Message):
    """Bubbles when user clicks a test row — show its KB entry in the side panel."""
    def __init__(self, region_id: str, stem: str) -> None:
        super().__init__()
        self.region_id = region_id
        self.stem = stem


# ── Badge ─────────────────────────────────────────────────────────────────────

class _ResultBadge(Static):
    """Compact coloured badge: Pos / Neg / —."""

    DEFAULT_CSS = """
    _ResultBadge {
        width: 5; height: 1;
        content-align: center middle;
        text-align: center;
    }
    _ResultBadge.badge_pos  { background: $error;   color: white; }
    _ResultBadge.badge_neg  { background: $success; color: white; }
    _ResultBadge.badge_none { background: $surface; color: $text-muted; }
    """

    def __init__(self, badge_id: str, **kwargs) -> None:
        super().__init__("  —  ", id=badge_id, **kwargs)
        self.add_class("badge_none")

    def set_state(self, value) -> None:
        text, css_class = _BADGE_MAP.get(value, _BADGE_MAP[None])
        self.update(text)
        for cls in ("badge_pos", "badge_neg", "badge_none"):
            self.remove_class(cls)
        self.add_class(css_class)


# ── Test row ──────────────────────────────────────────────────────────────────

class _TestRow(Horizontal):
    """One test: label (click → KB panel) + Sn/Sp + L/R result badges."""

    DEFAULT_CSS = """
    _TestRow {
        height: 1; width: 100%;
    }
    _TestRow:hover { background: $boost; }
    _TestRow .tr_label {
        width: 1fr; height: 1;
        padding: 0 1 0 0;
        color: $text;
    }
    _TestRow .tr_snsp {
        width: 18; height: 1;
        color: $text-muted;
        text-align: right;
    }
    _TestRow .tr_side_label {
        width: 2; height: 1;
        color: $text-muted;
        margin: 0 0 0 1;
    }
    """

    def __init__(self, stem: str, label: str, kb: "KBEntry | None",
                 region_id: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._stem = stem
        self._label = label
        self._kb = kb
        self._region_id = region_id
        self._badge_l_id = f"rdp_{region_id}_{stem}_l"
        self._badge_r_id = f"rdp_{region_id}_{stem}_r"

    def compose(self) -> ComposeResult:
        sn_sp = _short_sn_sp(self._kb.sn_sp) if (self._kb and self._kb.sn_sp) else "—"
        yield Static(self._label, classes="tr_label")
        yield Static(sn_sp, classes="tr_snsp")
        yield Static("L", classes="tr_side_label")
        yield _ResultBadge(self._badge_l_id)
        yield Static("R", classes="tr_side_label")
        yield _ResultBadge(self._badge_r_id)

    def on_click(self) -> None:
        self.post_message(RequestKBEntry(self._region_id, self._stem))

    def set_results(self, l_val, r_val) -> None:
        try:
            self.query_one(f"#{self._badge_l_id}", _ResultBadge).set_state(l_val)
        except Exception:
            pass
        try:
            self.query_one(f"#{self._badge_r_id}", _ResultBadge).set_state(r_val)
        except Exception:
            pass


# ── Cluster block ─────────────────────────────────────────────────────────────

class _ClusterBlock(Vertical):
    """One cluster group wrapped in a collapsible (collapsed by default)."""

    DEFAULT_CSS = """
    _ClusterBlock {
        height: auto; width: 100%;
        margin-bottom: 0;
    }
    _ClusterBlock Collapsible {
        height: auto;
        border: none;
        padding: 0; margin: 0;
    }
    _ClusterBlock .cb_cluster_note {
        width: 100%; height: auto;
        color: $accent;
        padding: 0 0 0 2;
        margin: 0;
    }
    """

    def __init__(self, group_def: dict, kb: dict, region_id: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._group_def = group_def
        self._kb = kb
        self._region_id = region_id
        self._stems = [row["id"] for row in group_def.get("rows", [])]
        self._collapsible: Collapsible | None = None

    def compose(self) -> ComposeResult:
        group_label = self._group_def.get("label", "")
        n = len(self._stems)
        cluster_note = _cluster_note_for(self._group_def, self._kb)
        with Collapsible(title=f"{group_label}  0/{n}", collapsed=True) as c:
            self._collapsible = c
            for row in self._group_def.get("rows", []):
                stem = row["id"]
                label = row.get("label", stem)
                kb_entry = self._kb.get(stem)
                yield _TestRow(stem, label, kb_entry, self._region_id)
            if cluster_note:
                yield Static(cluster_note, classes="cb_cluster_note")

    def set_tests(self, tests: dict) -> tuple[int, int]:
        """Update badges; return (pos_count, total) for parent to sum."""
        pos_count = 0
        total = len(self._stems)
        for row_widget in self.query(_TestRow):
            stem = row_widget._stem
            l_val = tests.get(f"st_{stem}_l")
            r_val = tests.get(f"st_{stem}_r")
            row_widget.set_results(l_val, r_val)
            if l_val == "Yes" or r_val == "Yes":
                pos_count += 1
        if self._collapsible is not None:
            group_label = self._group_def.get("label", "")
            self._collapsible.title = f"{group_label}  {pos_count}/{total}"
        return pos_count, total


# ── Regional panel ────────────────────────────────────────────────────────────

class RegionalDifferentialPanel(Vertical):
    """Region-level collapsible containing cluster-level collapsibles."""

    DEFAULT_CSS = """
    RegionalDifferentialPanel {
        height: auto; width: 100%;
        margin-bottom: 0;
    }
    RegionalDifferentialPanel > Collapsible {
        height: auto;
        border: none;
        padding: 0; margin: 0;
    }
    """

    def __init__(self, region_id: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._region_id = region_id
        self._pending_tests: dict = {}
        self._structure = _load_region_structure(region_id)
        self._kb: dict = dict(get_registry()._data.get(region_id, {}))
        self._collapsible: Collapsible | None = None
        self._total_stems = sum(
            len(g.get("rows", [])) for g in self._structure.get("groups", [])
        )
        logger.debug("RDP panel: created for region=%s groups=%d kb_entries=%d",
                     region_id, len(self._structure.get("groups", [])), len(self._kb))

    def compose(self) -> ComposeResult:
        region_label = self._region_id.capitalize()
        logger.debug("RDP panel: compose() for %s", self._region_id)
        with Collapsible(
            title=f"◆ {region_label}  0/{self._total_stems}", collapsed=True
        ) as c:
            self._collapsible = c
            for group in self._structure.get("groups", []):
                cid = group.get("cluster_id", "")
                yield _ClusterBlock(
                    group, self._kb, self._region_id,
                    id=f"rdp_cb_{self._region_id}_{cid}"
                )

    def on_mount(self) -> None:
        logger.debug("RDP panel: on_mount() for %s pending=%s",
                     self._region_id, bool(self._pending_tests))
        if self._pending_tests:
            self.set_tests(self._pending_tests)
            self._pending_tests = {}

    def set_tests(self, tests: dict) -> None:
        blocks = list(self.query(_ClusterBlock))
        if not blocks:
            self._pending_tests = dict(tests)
            return
        total_pos = 0
        for block in blocks:
            pos, _ = block.set_tests(tests)
            total_pos += pos
        if self._collapsible is not None:
            region_label = self._region_id.capitalize()
            self._collapsible.title = f"◆ {region_label}  {total_pos}/{self._total_stems}"
