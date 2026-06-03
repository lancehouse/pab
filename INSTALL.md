# PAB — Installation Guide

Specialist physiotherapy body-chart and assessment tool.
Two cooperating apps: **bodychart** (GTK4/C, stylus drawing) and **assessment** (Python TUI, structured assessment + reports).

Tested on **Fedora 43 / GNOME**. Should work on any recent Fedora or GNOME-based distro with minor adjustments.

---

## Contents

- [System requirements](#system-requirements)
- [Quick install (clinic use)](#quick-install-clinic-use)
- [Developer setup (stable + dev branches)](#developer-setup)
- [USB drive install notes](#usb-drive-install-notes)
- [Hardware notes](#hardware-notes)

---

## System requirements

| Component | Minimum |
|---|---|
| OS | Fedora 40+ (GNOME) |
| Architecture | x86_64 |
| RAM | 2 GB |
| Disk | 500 MB (app + venv) + space for session data |
| Display | 1280×800 or better |
| Input | Keyboard + mouse; pressure-sensitive stylus strongly recommended for body chart |

---

## Quick install (clinic use)

This installs a single stable copy for daily clinical use. No dev tooling required beyond the build step.

### 1. Install system packages

```bash
sudo dnf install -y \
    git \
    gcc meson ninja-build pkg-config \
    gtk4-devel \
    cairo-devel \
    librsvg2-devel \
    json-c-devel \
    python3 python3-devel python3-pip python3-venv \
    pandoc
```

**Terminal emulator** — the bodychart app launches the assessment TUI in a terminal. It tries these in order:

```bash
# Preferred (GPU-accelerated, best touch/stylus behaviour):
sudo dnf install -y kitty

# ptyxis is the GNOME default on Fedora 41+; no extra install needed
# gnome-terminal also works as a fallback; no extra install needed
```

### 2. Clone the repository

```bash
mkdir -p ~/Projects
git clone git@github.com:lancehouse/pab.git ~/Projects/pab
# or HTTPS if you don't have an SSH key set up:
git clone https://github.com/lancehouse/pab.git ~/Projects/pab
```

### 3. Build the bodychart GTK app

```bash
cd ~/Projects/pab/bodychart

# First time: configure the build directory
meson setup build

# Build
ninja -C build
```

The binary is at `~/Projects/pab/bodychart/build/bodychart`.

### 4. Set up the assessment Python TUI

```bash
cd ~/Projects/pab/assessment

# Create a virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install the package and its dependencies
pip install -e .

# Deactivate — the launcher scripts activate it automatically
deactivate
```

The `assessment` binary is now at `~/Projects/pab/assessment/.venv/bin/assessment`.

### 5. Create session data directory

```bash
mkdir -p ~/PAB
mkdir -p ~/.local/share/pab
```

### 6. Install launchers

```bash
mkdir -p ~/.local/bin

# Main clinic launcher (bodychart)
ln -sf ~/Projects/pab/bodychart/build/bodychart ~/.local/bin/pab

# Assessment TUI (used by bodychart to open the TUI, or run standalone)
ln -sf ~/Projects/pab/assessment/.venv/bin/assessment ~/.local/bin/assessment
```

Make sure `~/.local/bin` is on your PATH. Add this to `~/.bashrc` or `~/.bash_profile` if needed:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then reload:

```bash
source ~/.bashrc
```

### 7. Test

```bash
# Launch body chart (opens assessment TUI automatically in a terminal)
pab

# Or launch the TUI on its own
assessment
```

### 8. Body chart PDF export (optional)

The `placepdf` tool places a body chart PNG export onto a prepared clinical PDF template using PyMuPDF.

**Install PyMuPDF:**

```bash
pip install pymupdf
```

**Install your private template:**

The template PDF is private and is not distributed with the repository. Place it at:

```
~/.local/share/pab/template.pdf
```

**Install the launcher:**

```bash
ln -sf ~/Projects/pab/tools/placepdf ~/.local/bin/placepdf
```

**Usage:**

```bash
# Uses template at ~/.local/share/pab/template.pdf by default
placepdf /path/to/combined.png

# Or specify a different template
placepdf /path/to/combined.png --template /path/to/other_template.pdf
```

Output is saved as a `.pdf` beside the input PNG.

---

## Developer setup

This sets up both a **stable** copy (always safe for clinic use) and a **dev** copy (for working on new features). They share one git history via a worktree.

Complete steps 1–5 above, then continue:

### 6. Create the stable worktree

```bash
cd ~/Projects/pab
git worktree add pab-stable main
```

### 7. Build the stable bodychart binary

```bash
cd ~/Projects/pab/pab-stable/bodychart
meson setup build-stable
ninja -C build-stable
```

### 8. Set up the stable assessment venv

```bash
cd ~/Projects/pab/pab-stable/assessment
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
deactivate
```

### 9. Install all launchers

```bash
mkdir -p ~/.local/bin

# Stable bodychart — safe for clinic (symlink into pab-stable)
ln -sf ~/Projects/pab/pab-stable/bodychart/build-stable/bodychart ~/.local/bin/pab

# Dev bodychart — current branch, may be broken
ln -sf ~/Projects/pab/bodychart/build/bodychart ~/.local/bin/pabd

# Stable launcher script (bodychart + assessment both from stable)
ln -sf ~/Projects/pab/pabs ~/.local/bin/pabs

# Dev launcher script
ln -sf ~/Projects/pab/pabd ~/.local/bin/pabd

# Assessment TUI (stable)
ln -sf ~/Projects/pab/pab-stable/assessment/.venv/bin/assessment ~/.local/bin/assessment
```

### 10. Branching workflow

```
pab / pabs    → always runs main (stable)
pabd          → runs current dev branch (may be broken)
```

When a feature is ready to promote:

```bash
cd ~/Projects/pab/pab-stable       # this worktree tracks main
git merge <your-branch>            # fast-forward merge
ninja -C bodychart/build-stable    # rebuild stable binary
git push
```

See `docs/dev-setup.md` for the full workflow.

---

## Updating

Pull the latest from GitHub and rebuild:

```bash
cd ~/Projects/pab
git pull

# Rebuild bodychart
ninja -C bodychart/build

# Update Python package (only needed if pyproject.toml or package structure changed)
cd assessment && source .venv/bin/activate && pip install -e . && deactivate
```

If you have the stable worktree:

```bash
cd ~/Projects/pab/pab-stable
git pull
ninja -C bodychart/build-stable
```

---

## USB drive install notes

A full Fedora Workstation install to a USB drive (not live — proper persistent install) works well for testing on different hardware.

**Installation:**
1. Install Fedora Workstation to the USB drive using Anaconda (the standard installer). Choose the USB as the installation target. Use a USB 3.x drive of at least 32 GB; 64 GB+ recommended.
2. Boot the target machine from the USB drive (F12 / F2 / Del at POST for boot menu).
3. Follow the Quick install steps above inside the USB-booted Fedora session.

**Performance notes:**
- Expect slower startup than an internal NVMe — Fedora on USB is fine once loaded.
- The `~/PAB/` session data directory will live on the USB drive. Back it up regularly (`cp -r ~/PAB /some/backup`).
- The SSH key for GitHub access won't be present on the USB install — either copy your key (`~/.ssh/`) or use HTTPS cloning.

**SSH key setup (if copying from your main machine):**

```bash
# On your main machine, copy key to USB-booted session:
ssh-copy-id -i ~/.ssh/id_ed25519.pub <usb-machine-ip>
# or just scp the ~/.ssh folder across
```

---

## Hardware notes

### Tablet / touchscreen (Lenovo Yoga / similar)

The bodychart app is designed for pressure-sensitive stylus input in tablet mode. It works with mouse/touch but the drawing quality is best with an active digitiser stylus.

- **Stylus pressure**: supported via GTK4's GDK stylus axis (`GDK_AXIS_PRESSURE`). Works out of the box on most Wacom and MPP-compatible styli on Linux.
- **Palm rejection**: enabled by default. The app ignores touch input within 500 ms of a stylus event.
- **Barrel button**: cycles through symptom types (configurable in `~/.config/pab/settings.conf`).
- **Tablet mode**: the GNOME on-screen keyboard will appear in tablet mode; dismiss it when using the assessment TUI.

### Settings file

On first run, bodychart reads (or creates) `~/.config/pab/settings.conf`. You can tune pen behaviour there:

```ini
pen_gamma = 0.3          # pressure curve (0.3 = sensitive, 1.5 = linear)
pen_wide_mode = false    # wide stroke band
pen_palm_reject = true   # palm rejection
pen_dot_radius = 1.0     # P&N dot size
```

### Session data location

All session data is stored in `~/PAB/<session-name>/`:

```
~/PAB/<session-name>/
  <name>_session.json     # body chart strokes, overlays (owned by bodychart)
  <name>_assessment.json  # assessment sections (owned by assessment TUI)
  <name>_objective.json   # objective chart (owned by assessment TUI)
  <name>_report.md        # generated clinical report (Markdown)
  <name>_report.docx      # same report in Word format (requires pandoc)
```

The active session pointer is at `~/.local/share/pab/session_current.json`. Both apps read this to know which session is open.

---

## Dependency summary

### System packages (dnf)

| Package | Purpose |
|---|---|
| `gcc` | C compiler for bodychart |
| `meson` + `ninja-build` | Build system |
| `pkg-config` | Library discovery |
| `gtk4-devel` | GTK4 GUI toolkit |
| `cairo-devel` | 2D drawing |
| `librsvg2-devel` | SVG body outline rendering |
| `json-c-devel` | JSON persistence |
| `python3` + `python3-devel` + `python3-venv` | Assessment TUI runtime |
| `pandoc` | Report export to .docx (optional but recommended) |
| `kitty` | Preferred terminal for TUI launch (optional) |
| `git` | Version control |

### Python packages (installed via pip into venv)

| Package | Purpose |
|---|---|
| `textual>=0.50.0` | TUI framework |
| `pydantic>=2.0.0` | Data validation |
| `jinja2>=3.0.0` | Report templating |
| `pyyaml>=6.0.0` | YAML form definitions |
| `pymupdf` | Body chart PDF export (`placepdf` tool, optional) |
