# Assessment App — Architecture Overview

This document explains how the different YAML and Python files relate to each
other, what is user-editable without code changes, and how the knowledge base
connects to the assessment form.

---

## The Three YAML Layers

There are three distinct YAML layers in the app. They look similar but serve
completely different purposes.

```
pab/assessment/
│
├── pab_assessment/sections/yaml/
│   └── subj_sleep_pilot.yaml        ← SUBJECTIVE form driver
│
├── pab_assessment/objective/sections/yaml/
│   ├── cervical.yaml                ← OBJECTIVE form driver (cervical)
│   └── lumbar.yaml                  ← OBJECTIVE form driver (lumbar)
│
├── pab_assessment/objective/kb/
│   ├── cervical.yaml                ← KNOWLEDGE BASE content (cervical)
│   └── lumbar.yaml                  ← KNOWLEDGE BASE content (lumbar)
│
└── regions/
    ├── cervical_physical_examination.md   ← clinical REFERENCE (not read by app)
    └── lumbar_physical_examination.md     ← clinical REFERENCE (not read by app)
```

---

## Layer 1 — Form Driver YAML (drives what fields appear in the TUI)

**Files:** `sections/yaml/subj_sleep_pilot.yaml`,
           `objective/sections/yaml/cervical.yaml`,
           `objective/sections/yaml/lumbar.yaml`

These files define the **structure of the form** — which rows exist, what their
labels are, what RadioGroup options are available. The Python rendering code
reads them and builds the TUI from them. If you add a row here, it appears in
the form. If you rename a label, the label changes on screen.

**CRITICAL: never rename a field `id`.** The `id` is the JSON storage key.
Renaming it silently drops all historical data for that field. Labels, options,
and notes can be changed freely.

### What is and isn't YAML-driven yet

| Section | Status |
|---|---|
| Objective: Active Movement | YAML-driven ✓ |
| Objective: Muscle Testing | YAML-driven ✓ |
| Objective: Special Tests | YAML-driven ✓ |
| Subjective: Sleep | YAML-driven ✓ (pilot) |
| Objective: Neurological, Sensory, Functional, General | Hardcoded Python |
| All other Subjective sections | Hardcoded Python |

---

## Layer 2 — Knowledge Base YAML (populates the KB panel on field focus)

**Files:** `objective/kb/cervical.yaml`, `objective/kb/lumbar.yaml`

These files supply the text shown in the Ctrl+K KB panel when you focus a
special test field. Each entry contains: label, purpose, position, procedure,
Sn/Sp, cluster note.

**How KB entries link to form fields:**

The key in the KB YAML must match the row `id` in the form driver YAML.
Bilateral tests (left/right) use the stem only — the loader automatically
resolves `spurling_l` → `spurling` by stripping the `_l`/`_r` suffix.

```
Form YAML row:      {id: spurling_l, label: "Spurling Left", ...}
KB YAML entry key:  spurling:
                      label: "Spurling's Test"
                      ...
```

**How to update KB content:**
1. Open `objective/kb/cervical.yaml` or `lumbar.yaml`
2. Find the entry by its key (= the row `id` from the form YAML, without `_l`/`_r`)
3. Edit any field — label, purpose, position, procedure, sn_sp, cluster, note
4. Restart the app — the KB registry loads once at startup

**How to add a new KB entry:**
1. Find the field's row `id` in the relevant form YAML (see `docs/field-key-reference.md`)
2. Add an entry to the matching KB YAML with that key
3. Restart the app

Currently the KB only covers objective **special tests** for cervical and lumbar.
Adding KB entries for muscle tests, neurological fields, or subjective fields is
straightforward — see `docs/field-key-reference.md` for all available keys.

---

## Layer 3 — Reference Documents (human-readable clinical spec, not read by app)

**Files:** `regions/cervical_physical_examination.md`,
           `regions/lumbar_physical_examination.md`

These are clinical documentation — the full physical examination spec including
tests, normal values, Sn/Sp, and clinical patterns. The app does **not** read
these files. They exist as the authoritative clinical reference behind the app
design and as a source for KB content when writing or updating KB YAML entries.

You can edit them freely.

---

## Data Flow (end-to-end)

```
Form driver YAML
      │ read once at startup
      ▼
Python section renders widgets (each widget gets an id)
      │ user interacts
      ▼
FieldChanged message → 2s debounce → collect() → storage.py
      │ atomic write
      ▼
~/Physio-Bodychart/<session>/_objective.json   (objective)
~/Physio-Bodychart/<session>/_assessment.json  (subjective)

KB YAML
      │ read once at startup → KBRegistry (dict in memory)
      ▼
on_descendant_focus → resolve(region, widget_id) → KBPanel.update()
```

---

## Adding a New Region (e.g. Shoulder)

1. Create `objective/sections/yaml/shoulder.yaml` — define active_movement,
   muscle_testing, special_tests sections following the cervical/lumbar pattern
2. Create `objective/kb/shoulder.yaml` — add KB entries for the special tests
3. Add `("shoulder", "Shoulder")` to `_ALL_REGIONS` in `objective_view.py`
4. Add shoulder field IDs to `docs/field-key-reference.md`

No other Python changes needed for the YAML-driven sections.

---

## Separation of Concerns — enforced rules

| Layer | Location | Contains | Must NOT contain |
|---|---|---|---|
| Form structure | `sections/yaml/*.yaml` | Field IDs, labels, options | Clinical logic, storage |
| KB content | `kb/*.yaml` | Test descriptions, Sn/Sp | UI code, storage calls |
| Rendering | Python section files | Widget composition, CSS | Storage I/O, clinical decisions |
| Persistence | `storage.py` | JSON read/write | Textual imports, clinical logic |
| Search index | `search.py` | Static field tables | UI state, storage |
