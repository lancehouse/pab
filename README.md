# PhysioChart — Clinical Assessment Tool for Physiotherapists

This is a personal clinical tool I built for my own practice — a pair of apps that work together to handle the full patient assessment workflow on a Lenovo Yoga tablet (Fedora, stylus/touchscreen).

The problem I was trying to solve: paper body charts + scattered notes + generic EMR software that wasn't designed for how physio assessment actually works. So I built something that fits the actual clinical flow.

---

## What it does

**Two apps, one session:**

The **body chart app** (GTK4/C) is a pressure-sensitive stylus canvas where I draw symptom areas, mark pain distribution, add dermatome/peripheral nerve overlays, and annotate regions. It's designed for touchscreen-first use in a tablet mode.

The **assessment TUI** (Python/Textual, runs in the terminal) handles the structured clinical narrative — subjective history, medical screening, pain classification, outcome measures, diagnosis, barriers to treatment, and a full objective examination section. It generates a clinical report automatically on every save.

Both apps read/write the same session directory (plain JSON files) so they stay in sync while you use them.

---

## Clinical features built so far

**Assessment sections (01–07 + Objective):**
- 01 Consent and consent documentation
- 02 Subjective history (presenting complaint, mechanism, behaviour, 24hr, history, special questions)
- 03 Medical screening (comorbidities, CVD risk, red flags — malignancy/fracture/infection/cauda equina/cord, differentials, medications)
- 04 Pain classification (inflammatory vs nociceptive vs neuropathic vs nociplastic)
- 05 Outcome measures
- 06 Diagnosis / clinical reasoning
- 07 Barriers to treatment and recovery (physical, psychological, sleep/social, medical)
- **Objective exam** — 8 sections including active/passive movement, neurological, sensory, functional, muscle testing, and special tests; region-based architecture (lumbar active by default, other regions toggle-on)

**Report generation:**
- Auto-saves every field change (2-second debounce)
- Generates `_report.md` (full verbose clinical record) and `_clean.md`/`_clean.txt` (condensed, clustered booleans)
- Clean report clusters YES/NO findings into PRESENT/ABSENT lines, red flags into NIL REPORTED or raised-flags format — much more readable for quick clinical review
- Barriers section shows active sub-findings inline

**Navigability:**
- Ctrl+F fuzzy search — jump to any section, subsection, widget, or field by typing
- F1–F8 section hotkeys, Alt+letter subsection jumps
- Sidebar navigation with completion indicators

**YAML-driven forms (pilot):**
- Sleep quality section defined in YAML — clinician can edit questions/structure without touching Python
- Sleep efficiency calculator built in
- Other sections to follow this pattern eventually

---

## Why it's built this way

- **Plain JSON, always.** Every session is a directory of human-readable files. No database, no binary formats. Files can be opened, searched, backed up, and recovered trivially.
- **No save button.** Auto-save on every field change. Atomic writes prevent corruption.
- **Two apps, separate ownership.** GTK owns `_session.json` (strokes, canvas state). TUI owns `_assessment.json` and `_objective.json`. They never write to each other's files.
- **Tablet-first layout.** All buttons ≤ ¼ screen width. Built for a 13" tablet in landscape or portrait.
- **Offline only.** No cloud sync, no network calls, no telemetry. Clinical data stays local.

---

## Project structure

```
bodychart/          GTK4/C body chart app
assessment/         Python 3.12 / Textual TUI
docs/               Architecture, dev notes, migration plans
```

Session data lives in `~/PAB/<session-name>/`:
```
<name>_session.json       GTK-owned: strokes, overlays, canvas state
<name>_assessment.json    TUI-owned: sections 01–07
<name>_objective.json     TUI-owned: objective examination
<name>_report.md          Auto-generated full clinical report
<name>_clean.md           Auto-generated condensed report
<name>_raw.txt / _clean.txt   Plain text versions
```

---

## Running it

**Body chart (GTK):**
```bash
cd bodychart
ninja -C build
./build/bodychart
```

**Assessment TUI:**
```bash
cd assessment
source .venv/bin/activate
physio-assessment
```

Or with a specific session:
```bash
physio-assessment --session /path/to/session/dir
```

Quick dev-launch scripts: `pabd.sh` (dev branch) and `pabs.sh` (stable).

---

## Tech

- **GTK4/C** — body chart, stylus input, Cairo rendering, session file ownership
- **Python 3.12 / Textual** — terminal UI, assessment forms, report generation
- **Fedora 43, GNOME, kitty terminal** — primary development environment
- **meson + ninja** — GTK build system
- **JSON** — only data format; no SQLite, no binary

---

## Status

Active development, personal use. Not a product, not licensed for clinical use by others. Built for a specific clinical workflow on specific hardware.

Current focus: YAML-driven form architecture so assessment content can be edited without touching Python. Objective examination regions (lumbar complete; cervical/shoulder/thoracic/hip/knee coming).
