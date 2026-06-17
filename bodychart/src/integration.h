#pragma once
#include <gtk/gtk.h>
#include "canvas.h"   /* AppState */

/* Create the TUI window and spawn the assessment process inside it.
 * Called once after a session is opened. */
void integration_create_tui_window(AppState *app, GtkApplication *gapp);

/* Present the TUI window (Ctrl+A). No-op if window not yet created. */
void integration_focus_tui(AppState *app);

/* Destroy the TUI window (called when bodychart's main window closes). */
void integration_destroy_tui(AppState *app);
