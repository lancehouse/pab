#pragma once
#include "canvas.h"   /* AppState */

/* Spawn the assessment TUI in a terminal emulator after a session is opened.
 * Terminal preference: kitty → ptyxis → gnome-terminal → xterm.
 * If kitty is used, a remote-control socket is set up so Ctrl+A can refocus it.
 * Writes tui_socket to session_current.json after spawning. */
void integration_spawn_tui(AppState *app);

/* Start watching session_dir for a .focus_gtk signal file written by the TUI.
 * When the file appears, GTK deletes it and presents its own window. */
void integration_focus_monitor_start(AppState *app);

/* Stop the .focus_gtk directory monitor. */
void integration_focus_monitor_stop(AppState *app);

/* Focus the TUI terminal window.
 * Uses the kitty socket stored in session_current.json if available. */
void integration_focus_tui(AppState *app);
