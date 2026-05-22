#include "integration.h"
#include "persistence.h"
#include <gtk/gtk.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <json-c/json.h>

/* ── Terminal preference list ────────────────────────────────────────────── *
 * Tried in order; first found is used.  kitty gets a remote-control socket  *
 * so Ctrl+A (GTK → TUI focus) works.  Other terminals spawn without socket. */
typedef struct {
    const char *bin;
    /* Format string for the full launch command.                              *
     * %1$s = socket path (kitty only, ignored otherwise)                     *
     * %2$s = session JSON path                                                */
    const char *cmd_fmt;
    gboolean    has_socket;
} TerminalDef;

/* Commands use bash -l (login shell) so the spawned process inherits the
 * user's full environment — PATH, WAYLAND_DISPLAY, XDG_SESSION_TYPE, etc.
 * Without this, touch/mouse reporting breaks because kitty launched from a
 * bare GTK spawn environment is missing variables set by the user's shell. */
static const TerminalDef TERMINALS[] = {
    {
        "ptyxis",
        "bash -l -c 'ptyxis -- physio-assessment --session %s'",
        FALSE,
    },
    {
        "kitty",
        "bash -l -c 'kitty --listen-on %s physio-assessment --session %s'",
        TRUE,
    },
    {
        "gnome-terminal",
        "bash -l -c 'gnome-terminal -- physio-assessment --session %s'",
        FALSE,
    },
    {
        "xterm",
        "bash -l -c 'xterm -e physio-assessment --session %s'",
        FALSE,
    },
    { NULL, NULL, FALSE },
};

/* ── Helpers ─────────────────────────────────────────────────────────────── */

static const TerminalDef *find_terminal(void)
{
    /* Allow override via PHYSIO_TERMINAL env var, e.g. export PHYSIO_TERMINAL=kitty */
    const char *override = g_getenv("PHYSIO_TERMINAL");
    if (override) {
        for (int i = 0; TERMINALS[i].bin != NULL; i++) {
            if (strcmp(TERMINALS[i].bin, override) == 0
                && g_find_program_in_path(TERMINALS[i].bin))
                return &TERMINALS[i];
        }
        fprintf(stderr, "integration_spawn_tui: PHYSIO_TERMINAL=%s not found or not supported\n", override);
    }
    for (int i = 0; TERMINALS[i].bin != NULL; i++) {
        if (g_find_program_in_path(TERMINALS[i].bin))
            return &TERMINALS[i];
    }
    return NULL;
}

/* Write tui_socket into session_current.json (best-effort). */
static void write_tui_socket(const char *socket_path)
{
    const char *home = g_get_home_dir();
    char path[512];
    snprintf(path, sizeof(path),
             "%s/.local/share/physio-bodychart/session_current.json", home);

    json_object *root = NULL;
    {
        FILE *f = fopen(path, "r");
        if (f) {
            fseek(f, 0, SEEK_END);
            long len = ftell(f);
            rewind(f);
            char *buf = g_malloc(len + 1);
            fread(buf, 1, len, f);
            buf[len] = '\0';
            fclose(f);
            root = json_tokener_parse(buf);
            g_free(buf);
        }
    }
    if (!root) root = json_object_new_object();

    json_object_object_add(root, "tui_socket",
                           json_object_new_string(socket_path));

    /* Atomic write */
    char tmp[520];
    snprintf(tmp, sizeof(tmp), "%s.tmp", path);
    FILE *out = fopen(tmp, "w");
    if (out) {
        fputs(json_object_to_json_string_ext(root, JSON_C_TO_STRING_PRETTY), out);
        fclose(out);
        rename(tmp, path);
    }
    json_object_put(root);
}

/* Read a string field from session_current.json. Caller must g_free result. */
static char *read_session_current_field(const char *field)
{
    const char *home = g_get_home_dir();
    char path[512];
    snprintf(path, sizeof(path),
             "%s/.local/share/physio-bodychart/session_current.json", home);
    FILE *f = fopen(path, "r");
    if (!f) return NULL;
    fseek(f, 0, SEEK_END);
    long len = ftell(f);
    rewind(f);
    char *buf = g_malloc(len + 1);
    fread(buf, 1, len, f);
    buf[len] = '\0';
    fclose(f);

    json_object *root = json_tokener_parse(buf);
    g_free(buf);
    if (!root) return NULL;

    json_object *val = NULL;
    char *result = NULL;
    if (json_object_object_get_ex(root, field, &val))
        result = g_strdup(json_object_get_string(val));
    json_object_put(root);
    return result;
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
    if (term->has_socket) {
        /* Generate a unique socket path using our PID */
        char socket_path[256];
        snprintf(socket_path, sizeof(socket_path),
                 "unix:/tmp/physio-tui-%d.sock", (int)getpid());

        snprintf(cmd, sizeof(cmd), term->cmd_fmt, socket_path, app->session_file);
        write_tui_socket(socket_path);
    } else {
        /* Terminal doesn't support sockets — skip socket, format without it */
        snprintf(cmd, sizeof(cmd), term->cmd_fmt, app->session_file);
    }

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
    (void)app;
    /* Read the kitty socket path written by integration_spawn_tui */
    char *socket = read_session_current_field("tui_socket");
    if (socket && socket[0]) {
        char cmd[512];
        snprintf(cmd, sizeof(cmd), "kitty @ --to %s focus-window", socket);
        GError *err = NULL;
        if (!g_spawn_command_line_async(cmd, &err)) {
            fprintf(stderr, "integration_focus_tui: %s\n",
                    err ? err->message : "failed");
            if (err) g_error_free(err);
        }
    } else {
        fprintf(stderr, "integration_focus_tui: no tui_socket in session_current.json\n");
    }
    g_free(socket);
}
