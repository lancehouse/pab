# PAB — Project Context (paste into new Claude chat)

## What this project is

A physiotherapy assessment tool consisting of two integrated apps:

1. **bodychart** (GTK4/C) — a stylus body chart app for marking symptoms on a human outline. Runs on a Lenovo Yoga touchscreen. Saves strokes, notes, arrows, and objective markers to JSON.

2. **assessment** (Python/Textual) — a TUI assessment form with 7 sections covering the full physiotherapy assessment workflow. Auto-saves to the same session JSON.

The two apps run side by side: GTK spawns the TUI in ptyxis (terminal). Ctrl+B (TUI) switches to the GTK body chart. Ctrl+A (GTK) switches back to the TUI (kitty only). They communicate via file-based IPC (session_current.json + signal files) — Wayland-safe.

## Repository layout

```
pab/
  bodychart/               ← GTK4/C app
    src/
      canvas.c/.h          ← AppState struct, drawing pipeline
      integration.c/.h     ← terminal spawn, focus IPC
      persistence.c        ← JSON save/load, writes gtk_pid
      window.c             ← sidebar UI, Ctrl+A handler
      obj_chart.c          ← objective zone/point rendering
    meson.build
  assessment/              ← Python/Textual TUI
    pab_assessment/
      main.py              ← entry point, --session arg
      tui.py               ← PhysioAssessmentTUI, Ctrl+B/E/S bindings, session list
      assessment_view.py   ← mounts all 7 sections, save/load routing
      storage.py           ← all JSON functions, export, focus signals
      watcher.py           ← file watcher thread (session switch, chart update, focus)
      sections/
        base.py            ← BaseSection (do not modify)
        consent.py         ← 01 Consent; contains YesNoField
        subjective.py      ← 02 Subjective
        medical.py         ← 03 Medical; contains LikelihoodField
        pain_classification.py  ← 04 Pain Classification
        outcome_measures.py     ← 05 Outcome Measures; contains CycleField
        diagnosis.py       ← 06 Diagnosis
        barriers.py        ← 07 Barriers & Treatment (most complex)
      docs/
        customising-the-assessment-form.md  ← how to add/modify fields
        project-context-paste.md            ← this file
```

## Current state — ALL 7 SECTIONS COMPLETE

All assessment sections are built, wired to storage, and cross-referencing each other via badges. GTK ↔ TUI integration is complete (Phase 2.8).

## What's pending / next candidates

- Body chart data → assessment auto-population (body chart JSON → symptom summary in TUI)
- PDF export: body chart PNG + assessment markdown → single PDF
- GNOME focus stealing fix: install "Steal My Focus" GNOME Shell extension
- Ctrl+A focus for non-kitty terminals (ptyxis has no remote control API)

## Key design decisions

- **File-based IPC**: `.focus_gtk` / `.focus_tui` signal files (not sockets, not D-Bus) — Wayland safe
- **session_current.json** (schema v3): `gtk_pid`, `tui_pid`, `tui_socket` (kitty socket path)
- **Terminal detection**: ptyxis first, then kitty, gnome-terminal, xterm. Override: `PHYSIO_TERMINAL=kitty`
- **Atomic JSON writes**: temp file + rename everywhere
- **Fixed nav bar pattern**: BaseSection → NavBar (height: auto) + ScrollableContainer (1fr)
- **Auto-save**: 2s debounce triggered by `FieldChanged` message; no explicit Save required (Ctrl+S also available)
- **Cross-ref badges**: `Static` widgets updated on navigation to show relevant data from other sections

## Build / launch

```bash
# Build GTK:
ninja -C ~/Projects/pab/bodychart/build

# Launch GTK (auto-spawns TUI):
cd ~/Projects/pab/bodychart && ./build/bodychart

# Launch TUI standalone:
assessment

# Install symlink for PATH access:
ln -s ~/Projects/pab/assessment/.venv/bin/assessment ~/.local/bin/assessment
```

## Important rules / gotchas

- Widget IDs must be globally unique across all mounted sections
- Use `YesNoField` from consent.py, `CycleField` from outcome_measures.py, `LikelihoodField` from medical.py — don't redefine them
- Always import-test a section after editing: `.venv/bin/python3 -c "from pab_assessment.sections.X import Y; print('OK')"`
- Use Sonnet 4.6 or Opus — Haiku 4.5 struggles with complex Textual UI
- `scroll_to_widget(target, top=True)` is the correct Textual 8.x API for jump-to-section
