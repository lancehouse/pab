"""Load KB YAML files and resolve field IDs to KBEntry objects."""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_KB_DIR = Path(__file__).parent / "kb"

_STRIP_SUFFIXES = ("_l", "_r", "_left", "_right")


@dataclass
class KBEntry:
    label: str = ""
    purpose: str = ""
    position: str = ""
    procedure: str = ""
    assess: str = ""      # decision-criteria entries (non-test KB)
    sn_sp: str = ""
    variants: str = ""
    cluster: str = ""
    note: str = ""

    def render_lines(self) -> list[str]:
        """Return display lines for the KB panel."""
        lines: list[str] = []
        if self.label:
            lines += [f" {self.label}", "─" * 36]
        if self.purpose:
            lines += ["Purpose:", _wrap(self.purpose.strip(), 34), ""]
        if self.position:
            lines += ["Position:", _wrap(self.position.strip(), 34), ""]
        if self.procedure:
            lines += ["Procedure:", _wrap(self.procedure.strip(), 34), ""]
        if self.assess:
            lines += ["Assess:", _wrap(self.assess.strip(), 34), ""]
        if self.variants:
            lines += ["Variants:", _wrap(self.variants.strip(), 34), ""]
        if self.sn_sp:
            lines += ["Sn / Sp:", f"  {self.sn_sp}", ""]
        if self.cluster:
            lines += ["Cluster:", _wrap(self.cluster.strip(), 34), ""]
        if self.note:
            lines += ["Note:", _wrap(self.note.strip(), 34), ""]
        return lines


def _wrap(text: str, width: int) -> str:
    """Simple word-wrap to `width` chars, returns indented block."""
    words = text.split()
    lines: list[str] = []
    current = "  "
    for word in words:
        if len(current) + len(word) + 1 > width:
            lines.append(current)
            current = "  " + word
        else:
            current = current + (" " if len(current) > 2 else "") + word
    if current.strip():
        lines.append(current)
    return "\n".join(lines)


def _load_yaml_file(path: Path) -> dict[str, KBEntry]:
    """Parse one YAML file into a flat dict of id → KBEntry."""
    entries: dict[str, KBEntry] = {}
    try:
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning("KB YAML load failed %s: %s", path, e)
        return entries
    for key, data in raw.items():
        if not isinstance(data, dict):
            continue
        entries[key] = KBEntry(
            label=str(data.get("label", key)),
            purpose=str(data.get("purpose", "")),
            position=str(data.get("position", "")),
            procedure=str(data.get("procedure", "")),
            assess=str(data.get("assess", "")),
            sn_sp=str(data.get("sn_sp", "")),
            variants=str(data.get("variants", "")),
            cluster=str(data.get("cluster", "")),
            note=str(data.get("note", "")),
        )
    return entries


class KBRegistry:
    """Holds all loaded KB entries, keyed by region then field ID."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, KBEntry]] = {}

    def load_all(self) -> None:
        """Load all YAML files found in the kb/ directory."""
        for yaml_path in sorted(_KB_DIR.glob("*.yaml")):
            region = yaml_path.stem
            self._data[region] = _load_yaml_file(yaml_path)
            logger.debug("KB loaded %s: %d entries", region, len(self._data[region]))

    def resolve_any(self, field_id: str) -> tuple[str, KBEntry] | None:
        """Search all loaded regions for field_id. Returns (region, entry) or None."""
        for region, data in self._data.items():
            if field_id in data:
                return region, data[field_id]
            for suffix in _STRIP_SUFFIXES:
                if field_id.endswith(suffix):
                    stem = field_id[: -len(suffix)]
                    if stem in data:
                        return region, data[stem]
        return None

    def resolve(self, region: str, field_id: str) -> KBEntry | None:
        """Resolve a field_id to a KBEntry for the given region.

        Tries exact match first, then strips _l/_r suffixes.
        """
        region_data = self._data.get(region, {})
        if not region_data:
            return None
        if field_id in region_data:
            return region_data[field_id]
        for suffix in _STRIP_SUFFIXES:
            if field_id.endswith(suffix):
                stem = field_id[: -len(suffix)]
                if stem in region_data:
                    return region_data[stem]
        return None


# Module-level singleton — loaded once at startup
_registry: KBRegistry | None = None


def get_registry() -> KBRegistry:
    global _registry
    if _registry is None:
        _registry = KBRegistry()
        _registry.load_all()
    return _registry
