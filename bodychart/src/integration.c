#include "integration.h"
#include "persistence.h"
#include <gtk/gtk.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <json-c/json.h>

/* ── Terminal preference list ────────────────────────────────────────────── *
 * Tried in order; first found is used.                                       */
typedef struct {
    const char *bin;
    /* Format string for the full launch command.                              *
     * %s = session JSON path                                                  */
    const char *cmd_fmt;
} TerminalDef;

/* Commands use bash -l (login shell) so the spawned process inherits the
 * user's full environment — PATH, WAYLAND_DISPLAY, XDG_SESSION_TYPE, etc.
 * Without this touch/mouse reporting may break in environments missing
 * variables set by the user's shell. */
static const TerminalDef TERMINALS[] = {
    { "ptyxis",        "bash -l -c 'ptyxis -- assessment --session %s'"        },
    { "gnome-terminal","bash -l -c 'gnome-terminal -- assessment --session %s'" },
    { "xterm",         "bash -l -c 'xterm -e assessment --session %s'"          },
    { NULL, NULL },
};

/* ── Helpers ─────────────────────────────────────────────────────────────── */

static const TerminalDef *find_terminal(void)
{
    const char *override = g_getenv("PHYSIO_TERMINAL");
    if (override) {
        for (int i = 0; TERMINALS[i].bin != NULL; i++) {
            if (strcmp(TERMINALS[i].bin, override) == 0
                && g_find_program_in_path(TERMINALS[i].bin))
                return &TERMINALS[i];
        }
        fprintf(stderr, "integration_spawn_tui: PHYSIO_TERMINAL=%s not found\n", override);
    }
    for (int i = 0; TERMINALS[i].bin != NULL; i++) {
        if (g_find_program_in_path(TERMINALS[i].bin))
            return &TERMINALS[i];
    }
    return NULL;
}

/* ── Focus monitor callback ───────────────────────────────────────────────── */

static void on_dir_changed(GFileMonitor *monitor, GFile *file, GFile *other,
                            GFileMonitorEvent ev, gpointer user_data)
{
    (void)monitor; (void)other;
    AppState *app = (AppState *)user_data;

    if (ev != G_FILE_MONITOR_EVENT_CREATED && ev != G_FILE_MONITOR_EVENT_CHANGED)
        return;

    char *basename = g_file_get_basename(file);
    if (strcmp(basename, ".focus_gtk") == 0) {
        /* Consume the signal file */
        g_file_delete(file, NULL, NULL);
        /* Raise our own window — safe on Wayland because we raise ourselves */
        if (app->window)
            gtk_window_present(GTK_WINDOW(app->window));
    }
    g_free(basename);
}

/* ── Public API ──────────────────────────────────────────────────────────── */

void integration_spawn_tui(AppState *app)
{
    if (!app->session_file[0]) return;

    const TerminalDef *term = find_terminal();
    if (!term) {
        fprintf(stderr, "integration_spawn_tui: no suitable terminal emulator found\n");
        return;
    }

    char cmd[1024];
    snprintf(cmd, sizeof(cmd), term->cmd_fmt, app->session_file);

    GError *err = NULL;
    if (!g_spawn_command_line_async(cmd, &err)) {
        fprintf(stderr, "integration_spawn_tui: failed to spawn '%s': %s\n",
                cmd, err ? err->message : "unknown");
        if (err) g_error_free(err);
    } else {
        fprintf(stderr, "integration_spawn_tui: launched with: %s\n", cmd);
    }
}

void integration_focus_monitor_start(AppState *app)
{
    if (!app->session_dir[0]) return;
    if (app->focus_monitor)   return;   /* already running */

    GFile *dir = g_file_new_for_path(app->session_dir);
    GError *err = NULL;
    app->focus_monitor = g_file_monitor_directory(
        dir, G_FILE_MONITOR_NONE, NULL, &err);
    g_object_unref(dir);

    if (!app->focus_monitor) {
        fprintf(stderr, "integration_focus_monitor_start: %s\n",
                err ? err->message : "unknown error");
        if (err) g_error_free(err);
        return;
    }
    g_signal_connect(app->focus_monitor, "changed",
                     G_CALLBACK(on_dir_changed), app);
}

void integration_focus_monitor_stop(AppState *app)
{
    if (!app->focus_monitor) return;
    g_file_monitor_cancel(app->focus_monitor);
    g_object_unref(app->focus_monitor);
    app->focus_monitor = NULL;
}

void integration_focus_tui(AppState *app)
{
    /* No-op: ptyxis does not support remote window focus.
     * Use the system window switcher (e.g. Alt+Tab) to return to the TUI. */
    (void)app;
}
