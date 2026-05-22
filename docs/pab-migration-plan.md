# PAB Migration Plan — Strict Step-by-Step Checklist

**STATUS: ✅ COMPLETE — 2026-05-22**

**Goal:** Rename the project from the confusing triple-use of `physio-bodychart` to a clean
three-level hierarchy: root project `pab`, GTK sub-app `bodychart`, TUI sub-app `assessment`.

**Do this on a day with no clinic commitment. Allow 3–4 hours uninterrupted.**

---

## Naming decisions (final, locked)

| Concept | Old name | New name |
|---|---|---|
| Root project / repo | `physio-bodychart` | `pab` |
| Root folder | `~/Projects/physio-bodychart/` | `~/Projects/pab/` |
| GTK sub-folder | `physio-bodychart/` | `bodychart/` |
| GTK binary | `physio-bodychart` | `bodychart` |
| GTK desktop app-ID | `com.physio.bodychart` | `com.pab.bodychart` |
| TUI sub-folder | `physio-assessment/` | `assessment/` |
| Python package dir | `physio_assessment/` | `pab_assessment/` |
| Python package name | `physio-assessment` | `pab-assessment` |
| TUI entry script | `physio-assessment` | `assessment` |
| Stable worktree | `physio-assessment-stable/` | `pab-stable/` |
| Stable GTK path | `physio-assessment-stable/physio-bodychart/` | `pab-stable/bodychart/` |
| Stable TUI path | `physio-assessment-stable/physio-assessment/` | `pab-stable/assessment/` |
| Shared state dir | `~/.local/share/physio-bodychart/` | `~/.local/share/pab/` |
| Session data dir | `~/Physio-Bodychart/` | `~/PAB/` |
| TUI spawn env var | `PHYSIO_TUI_BIN` (did not exist) | `PAB_TUI_BIN` |
| GitHub repo | `lancehouse/physio-bodychart` | `lancehouse/pab` |

**Worktree note:** Git worktrees are whole-repo checkouts. One `pab-stable/` worktree contains
BOTH `bodychart/` and `assessment/` inside it. You cannot have separate worktrees per sub-folder
in a mono-repo. The effective stable paths are:
- `~/Projects/pab/pab-stable/bodychart/` — stable GTK source
- `~/Projects/pab/pab-stable/assessment/` — stable TUI source

**Coexistence model:**
- Old app (`~/Projects/physio-bodychart/`, `~/.local/bin/pab`) keeps running for clinic throughout.
- New app lives in `~/Projects/pab/` and uses `~/PAB/` + `~/.local/share/pab/` — completely separate paths.
- Old `pab` symlink is NOT touched until Phase 11 (cutover).
- Test new app only with throwaway sessions until Phase 10 sign-off.

---

## Source files that must change

### GTK — `bodychart/` (4 files)

| File | What changes |
|---|---|
| `meson.build` line 1 | `project('physio-bodychart', ...)` → `project('bodychart', ...)` |
| `meson.build` line 33 | `executable('physio-bodychart', ...)` → `executable('bodychart', ...)` |
| `meson.build` line 38 | `install_data('data/com.physio.bodychart.desktop', ...)` → `install_data('data/com.pab.bodychart.desktop', ...)` |
| `data/com.physio.bodychart.desktop` | Rename file to `com.pab.bodychart.desktop`; `Exec=physio-bodychart` → `Exec=bodychart`; `Icon=physio-bodychart` → `Icon=com.pab.bodychart` |
| `src/integration.c` line 28 | `physio-assessment` → `assessment` in ptyxis cmd_fmt |
| `src/integration.c` line 33 | `physio-assessment` → `assessment` in kitty cmd_fmt |
| `src/integration.c` line 38 | `physio-assessment` → `assessment` in gnome-terminal cmd_fmt |
| `src/integration.c` line 43 | `physio-assessment` → `assessment` in xterm cmd_fmt |
| `src/integration.c` line 76 | `physio-bodychart/session_current.json` → `pab/session_current.json` |
| `src/integration.c` line 116 | `physio-bodychart/session_current.json` → `pab/session_current.json` |
| `src/persistence.c` line 1078 | `~/.local/share/physio-bodychart` → `~/.local/share/pab` |
| `src/persistence.c` line 1089 | `~/.local/share/physio-bodychart/session_current.json` → `~/.local/share/pab/session_current.json` |

### Python TUI — `assessment/` (5 files)

| File | What changes |
|---|---|
| `pyproject.toml` | `name = "physio-assessment"` → `name = "pab-assessment"` |
| `pyproject.toml` | Entry script: `physio-assessment = "physio_assessment.main:main"` → `assessment = "pab_assessment.main:main"` |
| `pyproject.toml` | Packages list: all 4 entries `physio_assessment.*` → `pab_assessment.*` |
| `pab_assessment/storage.py` | 6× `~/.local/share/physio-bodychart/` → `~/.local/share/pab/` |
| `pab_assessment/watcher.py` | 1× `SESSION_CURRENT = Path.home() / ".local/share/physio-bodychart/session_current.json"` → `~/.local/share/pab/session_current.json` |
| `check_mapping.py` | `from physio_assessment.mapping` → `from pab_assessment.mapping` |

### Docs — (5 files, no functional impact)

- `CLAUDE.md` (root)
- `docs/dev-setup.md`
- `SESSION_JSON_SCHEMA.md`
- `docs/customising-the-assessment-form.md` (import examples in docs)
- `docs/project-context-paste.md` (import examples in docs)
- `README.md`

---

## Phase-by-phase checklist

---

### PHASE 0 — Safety anchor
**Est. time: 5 min. Clinic risk: none.**

- [ ] `cd ~/Projects/physio-bodychart`
- [ ] `git tag v1.0-pre-rename`
- [ ] `git push origin v1.0-pre-rename`
- [ ] Launch `pab` (clinic binary) once to confirm it still works. Close it.
- [ ] Note: `~/.local/bin/pab` currently points to `~/Projects/physio-bodychart/physio-bodychart/build/physio-bodychart`. Do not touch this until Phase 11.

---

### PHASE 1 — Create new repo structure
**Est. time: 15 min. Clinic risk: none.**

```bash
# Clone full history into new root
git clone ~/Projects/physio-bodychart ~/Projects/pab
cd ~/Projects/pab

# The clone's remote currently points at the local source — update after Phase 2
# Clean up stale worktree refs from the clone
git worktree prune

# Create fresh stable worktree tracking main
git worktree add pab-stable main
```

Verify:
- [ ] `ls ~/Projects/pab/` shows: `physio-bodychart/`, `physio-assessment/`, `physio-assessment-stable/`, `pab-stable/`, `docs/`, etc.
- [ ] `ls ~/Projects/pab/pab-stable/` shows: `physio-bodychart/`, `physio-assessment/`, `docs/`, etc.
- [ ] `git -C ~/Projects/pab log --oneline -3` matches old repo history
- [ ] `git -C ~/Projects/pab worktree list` shows both root and `pab-stable`

---

### PHASE 2 — Wire up new GitHub remote
**Est. time: 10 min. Clinic risk: none.**

- [ ] On github.com: create new repo named `pab` under your account (do NOT initialise with README)
- [ ] `cd ~/Projects/pab`
- [ ] `git remote set-url origin git@github.com:lancehouse/pab.git`
- [ ] `git push -u origin main`
- [ ] `git push --tags` (pushes `v1.0-pre-rename` tag)
- [ ] Verify on github.com that `lancehouse/pab` now has all commits and the tag
- [ ] (Optional) On github.com: rename old repo `physio-bodychart` → `physio-bodychart-archive` in Settings → Repository name
- [ ] (Optional) `git -C ~/Projects/physio-bodychart remote set-url origin git@github.com:lancehouse/physio-bodychart-archive.git`

---

### PHASE 3 — Rename sub-folders in new repo
**Est. time: 10 min. Clinic risk: none.**

```bash
cd ~/Projects/pab

# Rename via git mv so history is tracked
git mv physio-bodychart bodychart
git mv physio-assessment assessment

# The stable worktree is a separate checkout — rename its sub-folders manually
# (worktrees share the git index; git mv in one worktree affects all)
# Do NOT git mv inside pab-stable — just plain mv the dirs after the index move
# Actually: git mv above already updates the index for all worktrees.
# The pab-stable/ working tree still has old folder names on disk — update it:
cd pab-stable
mv physio-bodychart bodychart
mv physio-assessment assessment
cd ..

git commit -m "Rename sub-folders: physio-bodychart→bodychart, physio-assessment→assessment"
git push
```

Verify:
- [ ] `ls ~/Projects/pab/` shows `bodychart/`, `assessment/`, `pab-stable/`
- [ ] `ls ~/Projects/pab/pab-stable/` shows `bodychart/`, `assessment/`
- [ ] `git status` is clean

---

### PHASE 4 — Rename Python module directory
**Est. time: 5 min. Clinic risk: none.**

```bash
cd ~/Projects/pab/assessment
git mv physio_assessment pab_assessment

cd ~/Projects/pab/pab-stable/assessment
mv physio_assessment pab_assessment    # plain mv — index already updated above

cd ~/Projects/pab
git commit -m "Rename Python package dir: physio_assessment→pab_assessment"
git push
```

Verify:
- [ ] `ls ~/Projects/pab/assessment/pab_assessment/` shows `main.py`, `storage.py`, `sections/`, etc.
- [ ] `ls ~/Projects/pab/pab-stable/assessment/pab_assessment/` same

---

### PHASE 5 — GTK source code changes
**Est. time: 25 min. Clinic risk: none (old binary untouched).**

All edits inside `~/Projects/pab/bodychart/`.

#### 5a — meson.build
- [ ] Line 1: `project('physio-bodychart', 'c',` → `project('bodychart', 'c',`
- [ ] Line 33: `executable('physio-bodychart',` → `executable('bodychart',`
- [ ] Line 38: `install_data('data/com.physio.bodychart.desktop',` → `install_data('data/com.pab.bodychart.desktop',`

#### 5b — desktop file
- [ ] Rename: `data/com.physio.bodychart.desktop` → `data/com.pab.bodychart.desktop`
- [ ] Inside the renamed file: `Exec=physio-bodychart` → `Exec=bodychart`
- [ ] Inside the renamed file: `Icon=physio-bodychart` → `Icon=com.pab.bodychart`
- [ ] (Delete the old desktop file if git mv wasn't used: `git rm data/com.physio.bodychart.desktop`)

#### 5c — src/integration.c
The four `cmd_fmt` strings in the `TERMINALS[]` array:
- [ ] Line 28: `'ptyxis -- physio-assessment --session %s'` → `'ptyxis -- assessment --session %s'`
- [ ] Line 33: `'kitty --listen-on %s physio-assessment --session %s'` → `'kitty --listen-on %s assessment --session %s'`
- [ ] Line 38: `'gnome-terminal -- physio-assessment --session %s'` → `'gnome-terminal -- assessment --session %s'`
- [ ] Line 43: `'xterm -e physio-assessment --session %s'` → `'xterm -e assessment --session %s'`

The shared-state path (appears in two functions: `write_tui_socket` and `read_session_current_field`):
- [ ] Line 76: `physio-bodychart/session_current.json` → `pab/session_current.json`
- [ ] Line 116: `physio-bodychart/session_current.json` → `pab/session_current.json`

Also add `PAB_TUI_BIN` env var override (new feature — allows launchers to specify exact binary path):
In `find_terminal()` or just before each spawn, add at the top of the spawn function:
```c
const char *tui_bin = g_getenv("PAB_TUI_BIN");
if (!tui_bin) tui_bin = "assessment";
```
Then use `tui_bin` instead of the literal `assessment` in every `cmd_fmt`. This requires making
`cmd_fmt` dynamic rather than static — discuss with Claude before implementing.
**Alternative (simpler, sufficient):** Just hardcode `assessment` in the strings; skip `PAB_TUI_BIN` for now.
- [ ] Decision made: _______________________________________

#### 5d — src/persistence.c
- [ ] Line 1078: `physio-bodychart` → `pab` in the `snprintf` that creates the share dir
- [ ] Line 1089: `physio-bodychart/session_current.json` → `pab/session_current.json`

Commit:
```bash
cd ~/Projects/pab
git add bodychart/
git commit -m "bodychart: rename binary, app ID, TUI spawn cmd, and shared-state path to pab"
git push
```

---

### PHASE 6 — Python TUI source code changes
**Est. time: 20 min. Clinic risk: none.**

All edits inside `~/Projects/pab/assessment/`.

#### 6a — pyproject.toml
- [ ] `name = "physio-assessment"` → `name = "pab-assessment"`
- [ ] Entry script line: `physio-assessment = "physio_assessment.main:main"` → `assessment = "pab_assessment.main:main"`
- [ ] Packages list — all four entries:
  - `"physio_assessment"` → `"pab_assessment"`
  - `"physio_assessment.sections"` → `"pab_assessment.sections"`
  - `"physio_assessment.objective"` → `"pab_assessment.objective"`
  - `"physio_assessment.objective.sections"` → `"pab_assessment.objective.sections"`

#### 6b — pab_assessment/storage.py
Six path strings, all the same change:
- [ ] `~/.local/share/physio-bodychart/session_current.json` → `~/.local/share/pab/session_current.json`
  (Lines ~81, ~152, ~165, ~255, ~268, ~279 — grep for `physio-bodychart` to find all)

#### 6c — pab_assessment/watcher.py
- [ ] Line 15: `SESSION_CURRENT = Path.home() / ".local/share/physio-bodychart/session_current.json"` → `Path.home() / ".local/share/pab/session_current.json"`

#### 6d — check_mapping.py (repo root of assessment/)
- [ ] Line 2: `from physio_assessment.mapping import build_prefill` → `from pab_assessment.mapping import build_prefill`

Commit:
```bash
cd ~/Projects/pab
git add assessment/
git commit -m "assessment: rename package to pab_assessment, update shared-state path to pab"
git push
```

---

### PHASE 7 — Docs update
**Est. time: 20 min. Clinic risk: none.**

Update all path/name references in:
- [ ] `CLAUDE.md` (root) — architecture diagram, paths, build commands
- [ ] `docs/dev-setup.md` — all paths, launcher table, workflow section
- [ ] `SESSION_JSON_SCHEMA.md` — `~/.local/share/physio-bodychart/` references
- [ ] `docs/customising-the-assessment-form.md` — import examples
- [ ] `docs/project-context-paste.md` — import examples (if file exists)
- [ ] `README.md` — any path references

Also update the `physio-bodychart/CLAUDE.md` (the GTK sub-app's own CLAUDE.md):
- [ ] `~/Projects/pab/bodychart/CLAUDE.md` — update build path comment

Commit:
```bash
cd ~/Projects/pab
git add .
git commit -m "docs: update all paths and names for pab rename"
git push
```

---

### PHASE 8 — Build new binaries
**Est. time: 30 min. Clinic risk: none (old binary untouched).**

#### 8a — GTK dev binary

```bash
cd ~/Projects/pab/bodychart
meson setup build        # first time — creates new builddir
ninja -C build
ls build/bodychart       # verify binary exists
```

- [ ] `build/bodychart` binary created successfully

#### 8b — GTK stable binary

```bash
cd ~/Projects/pab/pab-stable/bodychart
meson setup build-stable
ninja -C build-stable
ls build-stable/bodychart
```

- [ ] `build-stable/bodychart` binary created successfully

#### 8c — Python TUI dev venv

```bash
cd ~/Projects/pab/assessment
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
assessment --help        # must print usage, not error
deactivate
```

- [ ] `assessment --help` prints TUI usage

#### 8d — Python TUI stable venv

```bash
cd ~/Projects/pab/pab-stable/assessment
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
assessment --help
deactivate
```

- [ ] `assessment --help` prints TUI usage

---

### PHASE 9 — Write launcher scripts and test symlinks
**Est. time: 15 min. Clinic risk: none.**

#### 9a — Write launchers

Create `~/Projects/pab/pabd` (dev):
```bash
#!/bin/bash
# PAB dev launcher — bodychart (GTK) dev build + assessment (TUI) dev branch
exec ~/Projects/pab/bodychart/build/bodychart "$@"
```

Create `~/Projects/pab/pabs` (stable):
```bash
#!/bin/bash
# PAB stable launcher — bodychart stable build + assessment (TUI) main branch
exec ~/Projects/pab/pab-stable/bodychart/build-stable/bodychart "$@"
```

Note: The GTK binary spawns the TUI. In the new code `assessment` is found via PATH
(if `~/.local/bin/assessment` exists) or via `PAB_TUI_BIN` env var.
Add `PAB_TUI_BIN` to launchers to point at the correct venv's `assessment` binary:

```bash
# pabd:
export PAB_TUI_BIN=~/Projects/pab/assessment/.venv/bin/assessment

# pabs:
export PAB_TUI_BIN=~/Projects/pab/pab-stable/assessment/.venv/bin/assessment
```

```bash
chmod +x ~/Projects/pab/pabd ~/Projects/pab/pabs
```

- [ ] Both launcher scripts written and executable

#### 9b — Create test symlinks (do NOT overwrite existing pab/pabs/pabd yet)

```bash
ln -sf ~/Projects/pab/pabd ~/.local/bin/pabd-new
ln -sf ~/Projects/pab/pabs ~/.local/bin/pabs-new
```

- [ ] `pabd-new --help` or `pabd-new` launches new GTK app
- [ ] `pabs-new` launches stable version of new GTK app

---

### PHASE 10 — End-to-end testing (throwaway sessions only)
**Est. time: 60 min. Do on a non-clinic day. Clinic risk: none if you do not touch ~/Physio-Bodychart/.**

Launch new dev app:
```bash
pabd-new
```

Test checklist:
- [ ] GTK app opens with correct title / no crash
- [ ] Create a new test session — verify it is created in `~/PAB/<name>/` (NOT `~/Physio-Bodychart/`)
- [ ] `~/.local/share/pab/session_current.json` is created/updated on session open
- [ ] GTK launches TUI (Ctrl+A or toolbar button) — TUI opens and loads the test session
- [ ] TUI sections save data — verify `~/PAB/<name>/_assessment.json` is updated
- [ ] Switch sessions — verify watcher detects the change
- [ ] Close GTK — verify `~/PAB/<name>/_session.json` is written correctly
- [ ] Re-open session from GTK file picker — data reloads correctly
- [ ] Verify `~/Physio-Bodychart/` is completely untouched (ls timestamps)
- [ ] Verify `~/.local/share/physio-bodychart/session_current.json` is untouched
- [ ] Launch old `pab` (clinic binary) and verify it still opens an old session normally

Test stable launcher:
- [ ] `pabs-new` opens without crash
- [ ] Session creation in stable version writes to `~/PAB/` correctly

**Sign-off:** Only proceed to Phase 11 when all boxes above are ticked.

---

### PHASE 11 — Cutover (clinic is fully on new app)
**Est. time: 10 min. Do on a non-clinic day. This is the point of no return for the symlinks.**

```bash
# Update main launchers to new binaries
ln -sf ~/Projects/pab/pab-stable/bodychart/build-stable/bodychart ~/.local/bin/pab
ln -sf ~/Projects/pab/pabs ~/.local/bin/pabs
ln -sf ~/Projects/pab/pabd ~/.local/bin/pabd

# Remove test aliases
rm ~/.local/bin/pabd-new ~/.local/bin/pabs-new
```

- [ ] `pab` now runs new stable bodychart binary
- [ ] `pabs` now runs new stable launcher
- [ ] `pabd` now runs new dev launcher
- [ ] Launch `pab` once to confirm clinic workflow works

---

### PHASE 12 — Session data migration (optional, on your schedule)
**Do only when you are ready for old sessions to appear in the new app.**

```bash
# Sessions are plain JSON — copy is safe
# Old sessions in ~/Physio-Bodychart/ remain readable by old app indefinitely
cp -r ~/Physio-Bodychart/* ~/PAB/
```

- [ ] Copied sessions appear in new GTK session picker
- [ ] Open one old session in new app — assessment data loads correctly
- [ ] Old app (`~/Projects/physio-bodychart/` run directly) still opens the same sessions

---

### PHASE 13 — Archive old repo (at least 1 month after cutover)

- [ ] `mv ~/Projects/physio-bodychart ~/Projects/physio-bodychart-archive`
- [ ] Verify no scripts in `~/.local/bin/` still reference the old path: `grep -r physio-bodychart ~/.local/bin/`
- [ ] Old GitHub repo `physio-bodychart` stays as archive — do not delete

---

## Rollback plan

At any phase before Phase 11 cutover:
- Clinic: `~/.local/bin/pab` still points at old binary — just use `pab`
- Code: `~/Projects/physio-bodychart/` completely untouched — nothing to recover

After Phase 11 cutover, rollback if needed:
```bash
ln -sf ~/Projects/physio-bodychart/physio-bodychart/build/physio-bodychart ~/.local/bin/pab
```
One command. Old binary is back.

Emergency (new app totally broken, need clinic now):
```bash
cd ~/Projects/physio-bodychart/physio-assessment
source .venv/bin/activate
physio-assessment --session /path/to/session.json
```

---

## What does NOT change

- All JSON file formats — `_session.json`, `_assessment.json`, `_objective.json`, `_report.md`
- Session schema version number
- Git history — 100% preserved via clone
- All C source logic, Python section logic, widget code
- Session data directory layout (`<session-name>/` folder structure inside `~/PAB/`)
- Internal Python relative imports (all `from .X import Y` — no changes needed)
- The `~/Physio-Bodychart/` directory and its contents (old app uses it indefinitely)
