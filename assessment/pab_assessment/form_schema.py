"""Dataclasses, YAML loader, and report renderers for YAML-driven form sections.

Report rendering
----------------
render_subsection_md(defn, data, clean)  → list[str]  markdown content lines
render_subsection_raw(defn, data, clean) → list[str]  plain-text content lines

Both return *content only* — the caller is responsible for emitting the
subsection header before calling these.  Empty list means nothing to show.

clean=True omits empty fields and suppresses headers with no content.
clean=False renders every field, including unanswered ones.

Clustering (controlled by SubsectionDef.report):
  cluster_checks=True  →  all `check` fields grouped as PRESENT / ABSENT
  cluster_flags=True   →  all `flag` fields grouped as NIL REPORTED / raised
Non-clustered fields render individually in YAML declaration order.
"""

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
class ReportHint:
    """Controls how a subsection renders in the full and clean reports."""
    omit_empty: bool = True       # hide empty fields in clean mode (always true for clean)
    cluster_checks: bool = False  # group check fields as PRESENT / ABSENT block
    cluster_flags: bool = False   # group flag fields as NIL REPORTED / raised block


@dataclass
class SubsectionDef:
    id: str
    label: str
    fields: list[FieldDef] = field(default_factory=list)
    report: ReportHint = field(default_factory=ReportHint)


def load_subsection_yaml(path: Path | str) -> SubsectionDef:
    """Parse a subsection YAML file and return its first SubsectionDef."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"YAML subsection file not found: {p.resolve()}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    sub = raw["subsections"][0]
    rh_raw = sub.get("report", {}) or {}
    report = ReportHint(
        omit_empty=rh_raw.get("omit_empty", True),
        cluster_checks=rh_raw.get("cluster_checks", False),
        cluster_flags=rh_raw.get("cluster_flags", False),
    )
    return SubsectionDef(
        id=sub["id"],
        label=sub["label"],
        fields=[_parse_field(f) for f in sub.get("fields", [])],
        report=report,
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


# ---------------------------------------------------------------------------
# Report rendering helpers
# ---------------------------------------------------------------------------

def _is_empty(val) -> bool:
    if val is None:
        return True
    if isinstance(val, str) and not val.strip():
        return True
    return False


def _md_val(val) -> str:
    if val is None:
        return "—"
    if val is True:
        return "Yes"
    if val is False:
        return "No"
    return str(val).strip() or "—"


def _raw_val(val) -> str:
    if val is True:
        return "✓ Yes"
    if val is False:
        return "✗ No"
    if val is None:
        return "(not answered)"
    if isinstance(val, str):
        s = val.strip()
        return s if s else "(empty)"
    return str(val)


def _resolve_radio(f: FieldDef, raw_val) -> str | None:
    """Translate a stored radio value token to its display label."""
    if raw_val is None:
        return None
    v2l = {o.value: o.label for o in f.options}
    return v2l.get(str(raw_val), str(raw_val))


def render_subsection_md(defn: SubsectionDef, data: dict, clean: bool) -> list[str]:
    """Render a SubsectionDef to markdown content lines.

    Returns content lines only — no subsection header.
    Returns an empty list when all fields are empty and clean=True.
    """
    out: list[str] = []
    hint = defn.report

    # Partition fields by type for optional clustering
    check_fields = [f for f in defn.fields if f.type == "check"]
    flag_fields  = [f for f in defn.fields if f.type == "flag"]
    other_fields = [f for f in defn.fields
                    if not (hint.cluster_checks and f.type == "check")
                    and not (hint.cluster_flags  and f.type == "flag")]

    # ── Non-clustered fields (text_area, input, radio, calculated, plus any
    #    check/flag when clustering is off) ──────────────────────────────────
    for fd in other_fields:
        raw = data.get(fd.id)

        if fd.type == "radio":
            val = _resolve_radio(fd, raw)
        else:
            val = raw

        if fd.type == "text_area":
            txt = (val or "").strip() if isinstance(val, str) else ""
            if clean and not txt:
                continue
            if txt and "\n" in txt:
                out.append(f"**{fd.label}:**  ")
                for row in txt.split("\n"):
                    out.append((row + "  ") if (clean and row.strip()) else row)
                out.append("")
            elif txt:
                out.append(f"**{fd.label}:** {txt}")
            else:
                out.append(f"**{fd.label}:** *(empty)*")
        else:
            if clean and _is_empty(val):
                continue
            out.append(f"**{fd.label}:** {_md_val(val)}")

    # ── Clustered check fields (PRESENT / ABSENT) ───────────────────────────
    if hint.cluster_checks and check_fields:
        present = [fd.label for fd in check_fields if data.get(fd.id) is True]
        absent  = [fd.label for fd in check_fields if data.get(fd.id) is False]
        if present:
            out.append("**PRESENT:** " + "; ".join(f"**{l}:** Yes" for l in present))
        if absent:
            out.append("**ABSENT:** " + "; ".join(absent))
        if not present and not absent and not clean:
            out.append("**PRESENT:** —")

    # ── Clustered flag fields (NIL REPORTED / raised) ───────────────────────
    if hint.cluster_flags and flag_fields:
        raised     = [fd.label for fd in flag_fields if data.get(fd.id) is True]
        not_raised = [fd.label for fd in flag_fields if data.get(fd.id) is False]
        if raised:
            out.append("**⚠️ FLAGS RAISED:** " + "; ".join(f"**{l}**" for l in raised))
            if not_raised:
                out.append("**Not reported:** " + "; ".join(not_raised))
        else:
            not_clean_empty = not clean or not_raised or raised
            if not_clean_empty:
                suffix = ""
                out.append(f"**NIL REPORTED**{suffix}")

    return out


def render_subsection_raw(defn: SubsectionDef, data: dict, clean: bool) -> list[str]:
    """Render a SubsectionDef to plain-text content lines.

    Returns content lines only — no subsection header.
    Returns an empty list when all fields are empty and clean=True.
    """
    out: list[str] = []
    hint = defn.report

    check_fields = [f for f in defn.fields if f.type == "check"]
    flag_fields  = [f for f in defn.fields if f.type == "flag"]
    other_fields = [f for f in defn.fields
                    if not (hint.cluster_checks and f.type == "check")
                    and not (hint.cluster_flags  and f.type == "flag")]

    for fd in other_fields:
        raw = data.get(fd.id)

        if fd.type == "radio":
            val = _resolve_radio(fd, raw)
        else:
            val = raw

        if fd.type == "text_area":
            txt = (val or "").strip() if isinstance(val, str) else ""
            if clean and not txt:
                continue
            out.append(f"  {fd.label}:")
            if txt:
                for row in txt.split("\n"):
                    out.append(f"    {row}" if row.strip() else "")
            else:
                out.append("    (empty)")
        else:
            if clean and _is_empty(val):
                continue
            out.append(f"  {fd.label}: {_raw_val(val)}")

    if hint.cluster_checks and check_fields:
        present = [fd.label for fd in check_fields if data.get(fd.id) is True]
        absent  = [fd.label for fd in check_fields if data.get(fd.id) is False]
        if present:
            out.append("  PRESENT: " + "; ".join(present))
        if absent:
            out.append("  ABSENT: " + "; ".join(absent))
        if not present and not absent and not clean:
            out.append("  PRESENT: (none answered)")

    if hint.cluster_flags and flag_fields:
        raised     = [fd.label for fd in flag_fields if data.get(fd.id) is True]
        not_raised = [fd.label for fd in flag_fields if data.get(fd.id) is False]
        if raised:
            out.append("  FLAGS RAISED: " + "; ".join(raised))
            if not_raised:
                out.append("  Not reported: " + "; ".join(not_raised))
        else:
            if not clean or not_raised:
                out.append("  NIL REPORTED")

    return out
