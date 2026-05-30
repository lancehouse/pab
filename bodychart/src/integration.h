#pragma once
#include "canvas.h"   /* AppState */

/* Spawn the assessment TUI in a terminal emulator after a session is opened.
 * Terminal preference: ptyxis → gnome-terminal → xterm.
 * Override with PHYSIO_TERMINAL env var. */
void integration_spawn_tui(AppState *app);

/* Start watching session_dir for a .focus_gtk signal file written by the TUI.
 * When the file appears, GTK deletes it and presents its own window. */
void integration_focus_monitor_start(AppState *app);

/* Stop the .focus_gtk directory monitor. */
void integration_focus_monitor_stop(AppState *app);

/* Focus the TUI terminal window. Currently a no-op — use system Alt+Tab. */
void integration_focus_tui(AppState *app);
