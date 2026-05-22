# Development Setup & Two-Version Workflow

## Repo layout

```
~/Projects/pab/                    ← git repo root (dev branch)
  bodychart/                       ← GTK4/C app (dev)
  assessment/                      ← Python TUI (dev)
  pab-stable/                      ← stable worktree, always tracks main
    bodychart/                     ← GTK4/C app (stable)
    assessment/                    ← Python TUI (stable)
  docs/
  pabs                             ← stable launcher script
  pabd                             ← dev launcher script
```

`pab-stable/` is a **git worktree** — same repo, different directory, permanently checked out
to `main`. No duplication of history.

## Launchers

| Script | Alias | Branch | Use |
|---|---|---|---|
| `pabd` | `~/.local/bin/pabd` | current dev branch | Feature work — may be broken |
| `pabs` | `~/.local/bin/pabs` | `main` | Daily clinical use — always stable |
| `pab`  | `~/.local/bin/pab`  | `main` (stable binary) | Quick clinic launch |

## Day-to-day workflow

**Run clinic:** `pab` or `pabs`

**Do dev work:** `pabd`

**Emergency fallback** (dev branch broken, need clinic now): `pab` or `pabs` — the stable
worktree is completely unaffected by whatever is broken on the dev branch.

## Promoting dev work to stable

When a feature is tested and ready:

```bash
cd ~/Projects/pab
git checkout main
git merge <branch-name>     # e.g. git merge yaml-form-editor
git push
# pab-stable/ immediately reflects the new main — no extra steps
```

## Keeping stable up to date

The stable worktree tracks `main` automatically after a merge. If you ever need to explicitly
pull it (e.g. after pushing from another machine):

```bash
cd ~/Projects/pab/pab-stable
git pull
```

## Branching convention

- `main` — stable, clinical-use only, never commit experimental work directly
- feature branches (e.g. `yaml-form-editor`) — all dev work; merge to main when proven
- create a branch: `git checkout -b my-feature`
- switch back to main instantly: `git checkout main`
- delete old branch after merge: `git branch -d my-feature`

## Build GTK after C changes

```bash
ninja -C ~/Projects/pab/bodychart/build
```

Stable GTK:
```bash
ninja -C ~/Projects/pab/pab-stable/bodychart/build-stable
```

## Session data

New sessions are created in `~/PAB/<session-name>/`.
Active session pointer: `~/.local/share/pab/session_current.json`.

## If a branch is completely broken

```bash
git checkout main    # you're immediately back on stable code
```

The broken branch is untouched and can be fixed later or abandoned.
