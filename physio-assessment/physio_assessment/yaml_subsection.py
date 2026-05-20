"""YamlSubsection — a subsection widget built dynamically from a SubsectionDef."""

from __future__ import annotations
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Label, Input, TextArea

from .form_schema import SubsectionDef, FieldDef, load_subsection_yaml
from .widgets import RadioGroup


class YamlSubsection(Container):
    """Renders one subsection (header + fields) from a SubsectionDef.

    All widget events (Input.Changed, TextArea.Changed, RadioGroup.Changed)
    bubble up naturally to the parent section's _on_field_changed handler.
    The parent must include RadioGroup.Changed in its @on decorators.

    collect() returns a flat dict of {field_id: value}.
    load(data) sets every widget from a flat dict.
    calculated fields are never persisted — always recomputed (TODO).
    """

    DEFAULT_CSS = """
    YamlSubsection {
        height: auto;
        width: 100%;
    }
    """

    def __init__(self, defn: SubsectionDef, **kwargs) -> None:
        super().__init__(**kwargs)
        self._def = defn
        self._loading = False

        # value↔label translation for radio fields
        # RadioGroup stores/returns the label string; YAML gives a stable value token.
        self._v2l: dict[str, dict[str, str]] = {}   # field_id → {value: label}
        self._l2v: dict[str, dict[str, str]] = {}   # field_id → {label: value}
        for f in defn.fields:
            if f.type == "radio" and f.options:
                self._v2l[f.id] = {o.value: o.label for o in f.options}
                self._l2v[f.id] = {o.label: o.value for o in f.options}

    @classmethod
    def from_yaml(cls, path: Path | str, **kwargs) -> "YamlSubsection":
        return cls(load_subsection_yaml(path), **kwargs)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        f: FieldDef
        yield Label(
            f"— {self._def.label} —",
            classes="subsection_header",
            id=self._def.id,
        )
        for f in self._def.fields:
            if f.type == "text_area":
                with Horizontal(classes="field_row"):
                    yield Label(f"{f.label}:")
                    yield TextArea(id=f.id, language="plain")

            elif f.type == "input":
                lbl = f.label + ("\n(duration)" if f.time_kind == "duration" else "")
                with Horizontal(classes="field_row"):
                    yield Label(f"{lbl}:")
                    yield Input(id=f.id, placeholder=f.placeholder)

            elif f.type == "radio":
                opts = [(o.label, o.variant) for o in f.options]
                with Horizontal(classes="field_row"):
                    yield Label(f"{f.label}:")
                    yield RadioGroup(options=opts, id=f.id)

            elif f.type == "calculated":
                ph = f"— {f.unit}" if f.unit else "—"
                with Horizontal(classes="field_row"):
                    yield Label(f"{f.label}:")
                    yield Input(id=f.id, placeholder=ph, disabled=True)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def collect(self) -> dict:
        data: dict = {}
        for f in self._def.fields:
            if f.type == "calculated":
                continue  # derived — never persisted
            try:
                if f.type == "text_area":
                    data[f.id] = self.query_one(f"#{f.id}", TextArea).text
                elif f.type == "input":
                    data[f.id] = self.query_one(f"#{f.id}", Input).value
                elif f.type == "radio":
                    lbl = self.query_one(f"#{f.id}", RadioGroup).value
                    data[f.id] = self._l2v[f.id].get(lbl) if lbl else None
            except Exception:
                data[f.id] = None if f.type == "radio" else ""
        return data

    def load(self, data: dict) -> None:
        self._loading = True
        try:
            for f in self._def.fields:
                if f.type == "calculated":
                    continue
                val = data.get(f.id)
                try:
                    if f.type == "text_area":
                        self.query_one(f"#{f.id}", TextArea).text = val or ""
                    elif f.type == "input":
                        self.query_one(f"#{f.id}", Input).value = val or ""
                    elif f.type == "radio":
                        lbl = self._v2l[f.id].get(val) if val else None
                        self.query_one(f"#{f.id}", RadioGroup).set_value(lbl)
                except Exception:
                    pass
        finally:
            self._loading = False
