"""Dataclasses and YAML loader for YAML-driven form sections."""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class OptionDef:
    value: str
    label: str
    variant: str = "default"


@dataclass
class FieldDef:
    id: str
    type: str       # text_area | input | radio | calculated | check | flag
    label: str
    placeholder: str = ""
    time_format: str = ""
    time_kind: str = ""     # clock | duration
    unit: str = ""
    note: str = ""
    readonly: bool = False
    options: list[OptionDef] = field(default_factory=list)
    formula_fn: str = ""
    inputs: list[str] = field(default_factory=list)


@dataclass
class SubsectionDef:
    id: str
    label: str
    fields: list[FieldDef] = field(default_factory=list)


def load_subsection_yaml(path: Path | str) -> SubsectionDef:
    """Parse a subsection-pilot YAML file and return its first SubsectionDef."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"YAML subsection file not found: {p.resolve()}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    sub = raw["subsections"][0]
    return SubsectionDef(
        id=sub["id"],
        label=sub["label"],
        fields=[_parse_field(f) for f in sub.get("fields", [])],
    )


def _parse_field(raw: dict) -> FieldDef:
    opts = [
        OptionDef(
            value=str(o["value"]),
            label=o["label"],
            variant=o.get("variant", "default"),
        )
        for o in raw.get("options", [])
    ]
    return FieldDef(
        id=raw["id"],
        type=raw["type"],
        label=raw["label"],
        placeholder=raw.get("placeholder", ""),
        time_format=raw.get("time_format", ""),
        time_kind=raw.get("time_kind", ""),
        unit=raw.get("unit", ""),
        note=raw.get("note", ""),
        readonly=raw.get("readonly", False),
        options=opts,
        formula_fn=raw.get("formula_fn", ""),
        inputs=list(raw.get("inputs", [])),
    )
