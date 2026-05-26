"""Regional differential panel for Pain Classification (section 05)."""

from __future__ import annotations
import re
import logging
from pathlib import Path

import yaml
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
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
    m = re.search(r"Sn\s+(?:\d+[\u2013-])?(\d+)%\s*/\s*Sp\s+(?:\d+[\u2013-])?(\d+)%", raw)
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

class _TestRow(Vertical):
    """One test: compact header row + collapsible KB detail."""

    DEFAULT_CSS = """
    _TestRow {
        height: auto; width: 100%;
        margin-bottom: 0;
    }
    _TestRow .tr_header {
        height: 1; width: 100%;
        layout: horizontal;
        align: left middle;
    }
    _TestRow .tr_label {
        width: 1fr; height: 1;
        padding: 0 1 0 0;
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
    _TestRow Collapsible {
        height: auto;
        border: none;
        padding: 0; margin: 0 0 0 2;
    }
    _TestRow .tr_kb_detail {
        color: $text-muted;
        height: auto;
        padding: 0;
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
        with Horizontal(classes="tr_header"):
            yield Static(self._label, classes="tr_label")
            yield Static(sn_sp, classes="tr_snsp")
            yield Static("L", classes="tr_side_label")
            yield _ResultBadge(self._badge_l_id)
            yield Static("R", classes="tr_side_label")
            yield _ResultBadge(self._badge_r_id)
        if self._kb:
            detail = "\n".join(self._kb.render_lines())
            with Collapsible(title=f"  {self._label} details", collapsed=True):
                yield Static(detail, classes="tr_kb_detail")

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
    """One cluster group: header, test rows, cluster note."""

    DEFAULT_CSS = """
    _ClusterBlock {
        height: auto; width: 100%;
        margin-bottom: 1;
        padding: 0 0 0 1;
        border-left: solid $primary;
    }
    _ClusterBlock .cb_header {
        height: 1; width: 100%;
        layout: horizontal;
    }
    _ClusterBlock .cb_title {
        width: 1fr; height: 1;
        text-style: bold;
    }
    _ClusterBlock .cb_count {
        width: auto; height: 1;
        color: $text-muted;
    }
    _ClusterBlock .cb_cluster_note {
        width: 100%; height: auto;
        color: $accent;
        padding: 0 0 0 1;
        margin-top: 0;
    }
    """

    def __init__(self, group_def: dict, kb: dict, region_id: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._group_def = group_def
        self._kb = kb
        self._region_id = region_id
        self._stems = [row["id"] for row in group_def.get("rows", [])]
        cid = group_def.get("cluster_id", "")
        self._count_id = f"rdp_count_{region_id}_{cid}"

    def compose(self) -> ComposeResult:
        group_label = self._group_def.get("label", "")
        cluster_note = _cluster_note_for(self._group_def, self._kb)
        with Horizontal(classes="cb_header"):
            yield Static(group_label, classes="cb_title")
            total = len(self._stems)
            yield Static(f"0/{total}", id=self._count_id, classes="cb_count")
        for row in self._group_def.get("rows", []):
            stem = row["id"]
            label = row.get("label", stem)
            kb_entry = self._kb.get(stem)
            yield _TestRow(stem, label, kb_entry, self._region_id)
        if cluster_note:
            yield Static(cluster_note, classes="cb_cluster_note")

    def set_tests(self, tests: dict) -> None:
        pos_count = 0
        total = len(self._stems)
        for row_widget in self.query(_TestRow):
            stem = row_widget._stem
            l_val = tests.get(f"st_{stem}_l")
            r_val = tests.get(f"st_{stem}_r")
            row_widget.set_results(l_val, r_val)
            if l_val == "Yes" or r_val == "Yes":
                pos_count += 1
        try:
            self.query_one(f"#{self._count_id}", Static).update(f"{pos_count}/{total}")
        except Exception:
            pass


# ── Regional panel ────────────────────────────────────────────────────────────

class RegionalDifferentialPanel(Vertical):
    """Cluster groups with live test results for one active region."""

    DEFAULT_CSS = """
    RegionalDifferentialPanel {
        height: auto; width: 100%;
        margin-bottom: 1;
        border: solid $primary;
        padding: 0 1;
    }
    RegionalDifferentialPanel .rdp_region_title {
        height: 1; width: 100%;
        text-style: bold;
        color: $primary;
        margin-bottom: 0;
    }
    """

    def __init__(self, region_id: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._region_id = region_id
        self._pending_tests: dict = {}
        self._structure = _load_region_structure(region_id)
        self._kb: dict = dict(get_registry()._data.get(region_id, {}))
        logger.debug("RDP panel: created for region=%s groups=%d kb_entries=%d",
                     region_id, len(self._structure.get("groups", [])), len(self._kb))

    def compose(self) -> ComposeResult:
        region_label = self._region_id.capitalize()
        logger.debug("RDP panel: compose() for %s", self._region_id)
        yield Static(f"◆ {region_label} — Special Test Summary", classes="rdp_region_title")
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
        for block in blocks:
            block.set_tests(tests)
