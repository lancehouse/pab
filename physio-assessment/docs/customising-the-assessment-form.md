# Customising the Assessment Form

This guide explains how to add, remove, or modify fields in the TUI assessment form without AI assistance. It covers the full data flow from UI widget → JSON storage → session file.

---

## Overview: How a Field Works

Every field follows this cycle:

```
compose()          → widget appears on screen
FieldChanged msg   → triggers auto-save (2s debounce in assessment_view.py)
collect()          → gathers all field values into a dict
save_X()           → writes dict to session JSON under assessment.section_key
load()             → on session open, reads dict back and populates widgets
```

---

## Field Types

### YesNoField — toggle button (Yes / No / unset)

Defined in `sections/consent.py`. Import it in any section:

```python
from .consent import YesNoField
```

Usage in `compose()`:
```python
yield Label("Is this present?")
yield YesNoField(id="my_field_id")
```

Reading the value in `collect()`:
```python
data["my_field_id"] = self.query_one("#my_field_id", YesNoField).get_value()
# Returns: True, False, or None (not yet answered)
```

Loading it back in `load()`:
```python
self.query_one("#my_field_id", YesNoField).set_value(data.get("my_field_id"))
```

### CycleField — multi-option cycling button

Defined in `sections/outcome_measures.py`. Import it:

```python
from .outcome_measures import CycleField
```

Usage:
```python
yield CycleField(["Option A", "Option B", "Option C"], id="my_cycle_field")
```

Reading/loading: same pattern as YesNoField — `get_value()` returns the selected string or None, `set_value(val)` sets it.

### LikelihoodField — Low / Moderate / High cycling

Defined in `sections/medical.py`:

```python
from .medical import LikelihoodField
```

Usage: same as CycleField, pre-configured to cycle Low → Moderate → High.

### Input — single line text

Standard Textual widget. Always include `id=`:

```python
yield Input(placeholder="Enter value...", id="my_input_id")
```

Collect: `self.query_one("#my_input_id", Input).value`  
Load: `self.query_one("#my_input_id", Input).value = data.get("my_input_id", "")`

### TextArea — multi-line text (auto-expanding)

Always use this instead of Input for anything that might be multiple sentences:

```python
yield TextArea(id="my_text_id")
```

Collect: `self.query_one("#my_text_id", TextArea).text`  
Load: `self.query_one("#my_text_id", TextArea).load_text(data.get("my_text_id", ""))`

In CSS, set:
```css
#my_text_id { height: auto; min-height: 1; }
```

---

## Registering Fields in collect() / load()

Every section has these two methods. They iterate over lists of field IDs to avoid repetition.

**Pattern used in diagnosis.py and barriers.py:**

```python
_TOGGLE_FIELDS = ["field_a", "field_b", "field_c"]
_INPUT_FIELDS  = ["input_a", "input_b"]
_TEXT_FIELDS   = ["text_a", "text_b"]

def collect(self) -> dict:
    data = {}
    for fid in _TOGGLE_FIELDS:
        data[fid] = self.query_one(f"#{fid}", YesNoField).get_value()
    for fid in _INPUT_FIELDS:
        data[fid] = self.query_one(f"#{fid}", Input).value
    for fid in _TEXT_FIELDS:
        data[fid] = self.query_one(f"#{fid}", TextArea).text
    return data

def load(self, data: dict) -> None:
    for fid in _TOGGLE_FIELDS:
        self.query_one(f"#{fid}", YesNoField).set_value(data.get(fid))
    for fid in _INPUT_FIELDS:
        self.query_one(f"#{fid}", Input).value = data.get(fid, "")
    for fid in _TEXT_FIELDS:
        self.query_one(f"#{fid}", TextArea).load_text(data.get(fid, ""))
```

**To add a new field:** add its ID to the appropriate list AND add the widget in `compose()`.

---

## Adding a New Field to an Existing Section

Example: adding a new toggle to the Barriers section.

**Step 1** — open `sections/barriers.py`, add the ID to the right list:
```python
_TOGGLE_FIELDS = [
    ...existing fields...,
    "b_new_barrier",   # ← add here
]
```

**Step 2** — add the widget in `compose()` at the right place in the layout:
```python
yield Label("New barrier description")
yield YesNoField(id="b_new_barrier")
```

That's it. `collect()` and `load()` are driven by the lists, so they pick it up automatically.

**Step 3** — test the import before launching:
```bash
cd ~/Projects/physio-bodychart/physio-assessment
.venv/bin/python3 -c "from physio_assessment.sections.barriers import BarriersSection; print('OK')"
```

---

## Field ID Naming Conventions

| Prefix | Meaning |
|--------|---------|
| `b_`   | Main barrier (boolean) |
| `bx_`  | Barrier sub-item |
| `bi_`  | Barrier input (text/NRS) |
| `tx_`  | Treatment plan item |
| `s1_`  | Session 1 checklist item |
| `hw_`  | Homework item |
| `d1_`  | Day 1 item |
| `ps_`  | Post-session item |
| `fu_`  | Follow-up item |
| `dx_`  | Diagnosis field |

Keep IDs lowercase with underscores. IDs **must be unique across the entire mounted widget tree** — if you get a "duplicate ID" error at runtime, a field in another section already uses that name.

---

## Adding a New Section

1. **Create** `sections/my_section.py` — copy `sections/diagnosis.py` as a template.  
   Change the class name, field lists, and `compose()` content.

2. **Add storage functions** in `storage.py`:
```python
def load_my_section(session_file: str) -> dict:
    data = _load_session(session_file)
    return data.get("assessment", {}).get("my_section", {})

def save_my_section(session_file: str, section_data: dict) -> bool:
    return _save_assessment_section(session_file, "my_section", section_data)
```

3. **Wire into `assessment_view.py`**:

   a. Import at top:
   ```python
   from .sections.my_section import MySection
   from .storage import load_my_section, save_my_section
   ```

   b. Add to `self.sections` dict in `__init__` or wherever sections are defined:
   ```python
   "08_my_section": MySection(id="section_08_my_section"),
   ```

   c. Add to `load_session()`:
   ```python
   section_data = data.get("assessment", {}).get("my_section", {})
   if "08_my_section" in self.sections:
       sec = self.sections["08_my_section"]
       sec.session_file = session_file
       sec.load(section_data)
   ```

   d. Add to `_do_save()`:
   ```python
   elif section_id == "08_my_section":
       sec = self.sections[section_id]
       save_my_section(self.session_file, sec.collect())
   ```

   e. Add a cross-ref refresh call in `_show_section()` if the section has badges:
   ```python
   elif section_id == "08_my_section":
       self.sections["08_my_section"].update_cross_refs(self.session_file)
   ```

4. **Add to the nav** — in `assessment_view.py`, find the section tab/button list and add an entry for the new section.

---

## Cross-Reference Badges

Cross-ref badges are `Static` widgets that show data from other sections:

```python
yield Static("", id="xref_my_badge", classes="xref_badge")
# or for urgent/red:
yield Static("", id="xref_my_badge", classes="xref_badge_urgent")
```

Update them in `update_cross_refs(self, session_file: str)`:

```python
def update_cross_refs(self, session_file: str) -> None:
    med = load_medical(session_file)  # load another section
    val = med.get("some_field")
    badge = self.query_one("#xref_my_badge", Static)
    if val:
        badge.update(f"Medical → {val}")
    else:
        badge.update("")
```

`update_cross_refs()` is called from `assessment_view.py`'s `_show_section()` each time the user navigates to this section, so badges are always fresh.

---

## Auto-Save Trigger

Every interactive widget must emit `FieldChanged` when its value changes, so the parent can debounce and save. Check the widget class — most already do this. If you add a raw `Input` widget, you need to handle its `Changed` event:

```python
@on(Input.Changed, "#my_input_id")
def _on_my_input_changed(self, event: Input.Changed) -> None:
    self.post_message(self.FieldChanged())
```

For `YesNoField` and `CycleField`, this is already built in — their button presses post `FieldChanged` automatically.

---

## is_complete()

Each section implements `is_complete() -> bool`. This drives the `●/○` indicator in the session list. Define a sensible threshold:

```python
def is_complete(self) -> bool:
    # Example: complete when the first required field is filled
    return self.query_one("#required_field", YesNoField).get_value() is not None
```

The result is stored in `sections_complete` in the session JSON.

---

## CycleField Options

When defining a `CycleField`, pass a list of strings. The first click sets the first option, subsequent clicks cycle through. Clicking again after the last option returns to `None` (unset).

```python
yield CycleField(["Nociceptive", "Neuropathic", "Nociplastic", "Mixed"], id="dx_mechanism")
```

Add the field ID to `_CYCLE_FIELDS` in your section so `collect()` and `load()` handle it:

```python
_CYCLE_FIELDS = ["dx_mechanism", "dx_type"]

# In collect():
for fid in _CYCLE_FIELDS:
    data[fid] = self.query_one(f"#{fid}", CycleField).get_value()

# In load():
for fid in _CYCLE_FIELDS:
    self.query_one(f"#{fid}", CycleField).set_value(data.get(fid))
```

---

## Quick Reference: Test Before Launch

Always run an import test after editing a section file:

```bash
cd ~/Projects/physio-bodychart/physio-assessment
.venv/bin/python3 -c "from physio_assessment.sections.barriers import BarriersSection; print('OK')"
```

Replace `barriers` / `BarriersSection` with your section. If this prints `OK`, the file is syntactically valid and imports cleanly. If it errors, fix before launching the full app.
