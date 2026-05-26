# Region Plugin Architecture
## PAB Assessment — Shoulder Build & Multi-Region Expansion Plan

**Status:** Planning phase — nothing built yet  
**Created:** 2026-05-26  
**Governs:** Shoulder region build + KB expansion + subjective region-awareness  
**Target:** A clean plugin pattern that scales to 10–20 regions without breaking existing code

---

## 1. Current State (what already exists)

### What is already pluggable

| Component | Mechanism | Files |
|---|---|---|
| Active movement ROM | `yaml/{region}.yaml` → `ROMGroupWidget` | `sections/yaml/lumbar.yaml`, `cervical.yaml` |
| Passive / OP tables | `REGION_EXTRAS[(region, "passive")]` → Python class | `lumbar_tables.py`, `cervical_tables.py` |
| Muscle testing | `yaml/{region}.yaml` + `REGION_EXTRAS[(region, "muscle")]` | Same |
| Special tests | `yaml/{region}.yaml` → `SpecialTestsWidget` | Same |
| KB panel tooltips | `objective/kb/{region}.yaml` loaded at startup | `kb/lumbar.yaml`, `kb/cervical.yaml` |
| Report rendering | `storage.py` — manual `sh_`/`cx_`/`lx_` blocks | NOT yet pluggable |

### What is NOT pluggable yet

- **`storage.py` report renderer** — every new region requires manual additions to both `_render_objective_md()` and `_render_objective_raw()`. This is currently correct and safe but won't scale to 20 regions without a template-driven approach. Flagged for future phase.
- **Subjective KB panel** — KB tooltips only exist for objective fields. The KB panel widget (Ctrl+K) is accessible from all sections but only wired to objective `on_descendant_focus`.
- **Region-conditional subjective fields** — no mechanism yet to show/hide subjective fields based on active region.

### Region state persistence

`active_regions` is stored in `_objective.json` (key: `active_regions`, list of strings). It is:
- Set and saved by `ObjectiveAssessmentView` on region tab toggle
- Read back on session load
- Read by `storage.py` for both report renderers
- **Accessible read-only to the subjective side** by reading `_objective.json` — no architectural change needed

### Neurological section — already always-on

`neurological.py` shows ALL content unconditionally: full UL (C5–T1) reflexes, myotomes, dermatomes, ULNT1/2a/3 + full LL (L2–S1) reflexes, myotomes, dermatomes, SLR/slump/PKF + UMN signs. No region checks, no conditional rendering. Shoulder will get a complete neurological section automatically with no changes required.

---

## 2. Architecture Principles (the plugin contract)

Every region is a self-contained module. Adding a new region must never require changes to core TUI files outside of specific registration points. The contract:

```
For each new region {name}:

  REQUIRED files (create):
    objective/sections/yaml/{name}.yaml        — ROM, muscle length/activation, special tests
    objective/kb/{name}.yaml                   — KB panel field tooltips (Sn/Sp, procedure, cluster)

  OPTIONAL files (create if complex passive/muscle tables needed):
    objective/sections/{name}_tables.py        — Python widget classes for PAIVM/OP/strength grids

  REQUIRED registration (edit — single location each):
    objective/sections/region_section.py       — add to REGION_EXTRAS if tables file created
    storage.py                                 — add rendering block to both renderers
    docs/field-key-reference.md                — add all new field IDs
    pab_assessment/search.py                   — add new fields to search index

  FUTURE (not yet built — see Phase 4):
    sections/kb/{name}.yaml                    — subjective KB tooltips for this region
```

The YAML format is the schema. If a region needs a field not supportable in YAML, it gets a Python tables class. Everything else is data, not code.

---

## 3. Knowledge Base Sources

### ~/Projects/kb/ — Clinical reference library (read-only, never modified by TUI)

| File | Relevance |
|---|---|
| `Shoulder Pain Differentiation_*.md` | Shoulder differentials, special tests, red flags |
| `Scapular Pain Differentiation_*.md` | Scapular dyskinesis, winging, nerve entrapment |
| `Clinical Special Tests _ Complete Re_2026.md` | All tests with Sn/Sp — primary KB source |
| `Clinical Special Tests - Pitfalls*.md` | False positive/negative warnings |
| `Upper Limb Neural Assessment_*.md` | C5–T1 myotomes, reflexes, dermatomes |
| `Differential diagnosis for common MSK presentations.pdf` | 16 body regions — structured DDx tables, subjective features, imaging decision rules |
| All other region files | Future region builds (elbow, hip, knee, ankle, etc.) |

These files are the authoritative clinical reference. Content is extracted and condensed into TUI KB YAML entries — the source files are never modified, never loaded at runtime.

### pab_assessment/objective/kb/ — TUI field-level tooltips (the "pab/kb")

Small YAML files, one per region, keyed to field IDs. Loaded once at startup, O(1) lookup per field focus. No performance concern. Fields covered: special tests only (currently). Future: muscle tests, passive tests, neurodynamic tests.

---

## 4. Phased Build Plan

### Phase 1 — Shoulder objective form (immediate next build)

**Status:** Ready to build once this plan is confirmed.

#### 1a. `objective/sections/yaml/shoulder.yaml`

**Active Movement** — all movements `bilateral: false` (full L/R, shoulder problems are typically asymmetric):

| Field prefix | Movement |
|---|---|
| `sh_flex` | Flexion |
| `sh_ext` | Extension |
| `sh_abd` | Abduction |
| `sh_ir` | Internal rotation (at side) |
| `sh_er` | External rotation (at side) |
| `sh_hadd` | Horizontal adduction |
| `sh_hbb` | Hand behind back |

Notes: `am_sh_notes`

**Muscle Length** (RadioGroup bilateral, options: Norm / ↓Mild / ↓Mod / ↓Mrkd):

| Field | Muscle |
|---|---|
| `ml_pec_min` | Pectoralis minor |
| `ml_pec_st` | Pec major sternal |
| `ml_pec_cl` | Pec major clavicular |
| `ml_lat` | Latissimus dorsi |
| `ml_post_cap` | Posterior capsule |

**Muscle Activation** (RadioGroup bilateral, options: Norm / ↓Mild / ↓Mod / Absent):

| Field | Muscle |
|---|---|
| `ma_lt` | Lower trapezius |
| `ma_sa` | Serratus anterior |
| `ma_er_fc` | ER force couple |

**Special Tests** (RadioGroup, bilateral L/R per test, options: Neg / +ve):

| Group | Fields |
|---|---|
| Impingement | `hawkins_l/r`, `neer_l/r`, `painful_arc_l/r` |
| Rotator cuff integrity | `empty_can_l/r`, `full_can_l/r`, `er_lag_l/r`, `lift_off_l/r`, `belly_press_l/r`, `drop_arm_l/r` |
| AC joint | `cross_body_l/r`, `ac_stress_l/r` |
| Biceps / SLAP | `speeds_l/r`, `yergason_l/r`, `obrien_l/r` |
| Instability | `apprehension_l/r`, `relocation_l/r`, `sulcus_l/r` |
| Scapular | `scap_assist_l/r`, `wall_pushup_l/r` |

Notes: `st_sh_notes`

#### 1b. `objective/sections/shoulder_tables.py`

Three sub-tables within `ShoulderPassiveTables`:

1. **Overpressure** — 7 movements (Flex/Ext/Abd/IR/ER/H.Add/H.Abd) × End-feel RadioGroup (Firm/Springy/Empty/Hard) + Response RadioGroup. Fields: `sh_op_{mov}_ef`, `sh_op_{mov}_resp`
2. **GH Accessory Movements** — Inferior/Posterior/Anterior glide × Maitland grade RadioGroup (I/II/III/IV/V) + Response. Fields: `sh_acc_{dir}_l/r_grade`, `sh_acc_{dir}_l/r_resp`
3. **AC/SC Joint** — AC stress, AC palpation, SC stress — bilateral RadioGroup rows. Fields: `sh_ac_stress_l/r`, `sh_ac_palp_l/r`, `sh_sc_stress_l/r`

`ShoulderMuscleTables` — bilateral GridInput, free text (accepts kg / 0–5 / "normal" / any string):

| Field | Test |
|---|---|
| `sh_str_flex_l/r` | Flexion strength |
| `sh_str_abd_l/r` | Abduction strength |
| `sh_str_ir_l/r` | IR strength |
| `sh_str_er_l/r` | ER strength |
| `sh_str_scap_l/r` | Scaption / full can strength |

#### 1c. `objective/kb/shoulder.yaml`

~22 entries covering every special test listed above. Content sourced from:
- `~/Projects/kb/md/Physiotherapy Clinical Special Tests _ Complete Re_2026.md`
- `~/Projects/kb/md/Shoulder Pain Differentiation_20260506_120417.md`
- `~/Projects/kb/md/Scapular Pain Differentiation_20260506_120417.md`

Each entry: label, purpose, position, procedure, sn_sp, cluster, note. Same format as `cervical.yaml`.

#### 1d. `region_section.py` registration

```python
from .shoulder_tables import ShoulderPassiveTables, ShoulderMuscleTables
REGION_EXTRAS = {
    ...existing...,
    ("shoulder", "passive"): ShoulderPassiveTables,
    ("shoulder", "muscle"):  ShoulderMuscleTables,
}
```

#### 1e. `storage.py` — add shoulder rendering blocks

Both `_render_objective_md()` and `_render_objective_raw()` updated in same commit. Blocks needed:
- Active movement (sh_ prefix, full L/R table)
- Passive / OP (sh_op_, sh_acc_, sh_ac_, sh_sc_)
- Muscle length + activation + strength
- Special tests (6 groups + notes)

#### 1f. Mandatory sync (same commit as 1e)

- `docs/field-key-reference.md` — all `sh_` field IDs
- `search.py` — `_FIELD_LABELS`, `_OBJ_KB_FIELDS`, `_SUBSECTIONS`

**Scapular assessment integration within shoulder:**
- Scapular posture observation → General section (01) — add `sh_scap_pos` observation field
- Scapular dynamic assessment → Functional section (07) — add `sh_scap_dyn` observation
- Scapular special tests → already in 1a (`scap_assist_l/r`, `wall_pushup_l/r`)

---

### Phase 2 — KB expansion to subjective sections

**Status:** Design only — not ready to build until Phase 1 is complete and tested.

#### The architecture problem

The KB panel (`KBPanel`) is physically at `AssessmentView` level (accessible from all sections via Ctrl+K). But it is only updated via `on_descendant_focus` in `objective_view.py`. The subjective sections have no equivalent wiring.

#### Design decision: region-aware subjective KB

`active_regions` is persisted in `_objective.json`. The subjective view can read this file (read-only) to know which regions are active, without coupling to the objective view widget.

**Proposed wiring:**
1. `AssessmentView` gets an `on_descendant_focus` handler that fires when any subjective field is focused
2. It reads `active_regions` from the in-memory session data (already loaded) to determine region context
3. It calls `kb_panel.update(region, field_id)` using the first active region (or a "general" fallback)
4. A new `sections/kb/` directory holds subjective KB YAML files, separate from `objective/kb/`
5. `kb_loader.py` is extended to load both directories, keyed separately

**Performance note:** `on_descendant_focus` in `AssessmentView` fires on every field focus in the subjective half. The KB lookup is O(1) dict lookup + ~10ms string format. This is safe. However — the `DescendantFocus` event bubbles through the DOM tree. We know from the focus latency fix that our DOM is deep. A single fast handler is fine; multiple handlers or any DOM manipulation in the handler is not. Rule: the subjective KB handler must be read-only (lookup + update Static text only, no DOM changes).

#### Subjective KB content for shoulder

Sourced from `~/Projects/kb/Differential diagnosis for common MSK presentations.pdf` — structured DDx tables covering 16 body regions with subjective features, objective patterns, and imaging decision rules. Shoulder content includes:

**History-taking prompts (field-level tooltips):**
- Onset field → "Sudden overload/trauma vs gradual? Traumatic = strain/tear/dislocation, gradual = tendinopathy/OA/frozen"
- Night pain field → "Unable to sleep on affected side = RC pathology, frozen shoulder, or significant structural injury"
- Behaviour field → "Pain below 90° = more severe involvement. Pain above 90° only = milder impingement pattern"
- Activities field → "Overhead athlete (throwing/swimming/racquet)? Increases SLAP, GIRD, AIOS probability"
- History field → "'Pop' + instability episode = screen for dislocation/SLAP. Catching/grinding = labral or scapular"

These map to EXISTING subjective field IDs (no new fields added yet — see Phase 3 below).

**Region-conditional display rule:** Subjective KB tooltips for shoulder only appear when `active_regions` contains "shoulder". If no region is set, tooltips fall back to general clinical prompts.

---

### Phase 3 — Region-conditional subjective fields (deferred)

**Status:** Do not build until Phase 2 is complete and the pattern is validated.

#### Vision

When a region is identified (shoulder toggled in the objective region topbar), additional subjective fields become visible within Section 02 (Subjective Examination). Example for shoulder: discrete fields for instability episodes, dominant hand, sport/occupation overhead demand, sleep position.

#### Why deferred

The region topbar currently lives inside `ObjectiveAssessmentView`. To make subjective fields region-conditional, either:
- **Option A:** The region topbar is duplicated or moved to a higher DOM level (AssessmentView or App), so it's visible from both halves
- **Option B:** Subjective section reads `active_regions` from the persisted JSON and shows/hides fields at load time (simpler, but not live — requires save + reload to see change)

Option B is buildable without major architectural change. Option A is cleaner long-term. Neither should be built until Phase 2 proves the subjective KB pattern works cleanly.

#### Classification tab (Section 04) expansion

The Classification tab (04 Pain Classification) will expand to become a differential diagnosis support tree, with region-specific content appearing when a region is active. This is a significant feature that needs its own planning phase. The Differential Diagnosis PDF is the primary content source. Not scoped here — flagged for a dedicated planning session.

---

### Phase 4 — Pluggable storage renderer (long-term, 5+ regions)

**Status:** Do not build until there are 4+ regions and the manual storage.py approach becomes visibly unmanageable.

#### Problem

`storage.py` currently has manual rendering blocks for each region in both `_render_objective_md()` and `_render_objective_raw()`. With 2 regions (lumbar + cervical) this is manageable. With 10 regions it will be ~1000 lines of repetitive code.

#### Proposed approach

A template-driven renderer that reads the same YAML files used for the form:
- YAML defines field IDs and labels
- A generic bilateral-table renderer iterates YAML groups and builds report tables
- Custom Python tables (OP, PAIVM, accessory) emit their own report fragments via a `render_md()` / `render_raw()` interface

This requires the Python table classes to implement a report interface — a moderate refactor. Not worth the risk until there are enough regions to justify it.

---

## 5. Risks and Constraints

| Risk | Severity | Notes |
|---|---|---|
| Neurological section already always-on | ✅ No risk | UL + LL + UMN always visible. Shoulder patients get full neuro automatically. No changes needed. |
| storage.py mirror rule | Medium | Both renderers must be updated in same commit. Checklist item on every region build. |
| Field count (widget count) | Low | Each new region adds ~80–120 widgets when active. With `update_node_styles()` now bypassed on focus return, this is not a freeze risk. Monitor if count exceeds 4000. |
| Subjective `on_descendant_focus` handler | Low | Must be read-only (lookup + Static.update only). No DOM manipulation, no layout triggers. |
| KB YAML file loading | None | Small files, loaded once at startup. O(1) lookup. No runtime cost. |
| region_section.py REGION_EXTRAS | None | Simple dict registration. No cascading effects. |
| search.py / field-key-reference.md drift | Medium | Must be updated in same commit as any field additions. Already a documented rule in CLAUDE.md. |

---

## 6. Open Questions (must be answered before Phase 2 build)

1. **Subjective KB directory:** Should subjective KB YAMLs live in `pab_assessment/sections/kb/` (mirroring `objective/kb/`) or in a unified `pab_assessment/kb/` with a `subjective/` subfolder? Decision needed before kb_loader.py is modified.

2. **KB fallback region:** When multiple regions are active (e.g. shoulder + cervical), the KB panel currently takes one region at a time. Should it show the KB entry for the most recently toggled region, or merge entries from all active regions?

3. **Scapular fields in General (01) and Functional (07):** Adding `sh_scap_pos` to General and `sh_scap_dyn` to Functional means those sections need region-conditional field visibility even before Phase 3. Is this worth the complexity, or should scapular observation live entirely within the shoulder variable tabs?

---

## 7. Build Order (Phase 1 sequencing)

When approved to build, execute in this order — do not skip steps:

```
Step 1:  Write shoulder.yaml (YAML only, no code changes)
Step 2:  Write shoulder_tables.py (passive + muscle Python widgets)
Step 3:  Register in region_section.py REGION_EXTRAS
Step 4:  Test in pabd — verify shoulder tab appears, fields render, autosave works
Step 5:  Write objective/kb/shoulder.yaml (KB tooltips for all special tests)
Step 6:  Update storage.py (both renderers, same commit)
         → Simultaneously update field-key-reference.md and search.py
Step 7:  Test full cycle in pabd — load session, fill shoulder fields, Ctrl+R report
Step 8:  User confirms in pabd
Step 9:  Push to main on explicit instruction only
```

Steps 1–4 are independent of storage.py and KB — they can be verified before the render and search work is done. Never push a step without the user confirming it in pabd.

---

## 8. Future Regions — Reference List

The Differential Diagnosis PDF covers these regions, all buildable using the same plugin pattern:

Cervical ✅ | Lumbar ✅ | Shoulder (this phase) | Thoracic | Elbow (lateral/medial/posterior) | Wrist/Hand | Hip (anterior/lateral) | Knee (acute/anterior/lateral/medial/posterior) | Ankle (medial/lateral/anterior) | Foot | SIJ/Pelvis | Groin

Each would follow the same 9-step build order above. Content sourced from the corresponding `~/Projects/kb/md/` file for that region.
