#include "integration.h"
#include "persistence.h"
#include <gtk/gtk.h>
#include <vte/vte.h>

/* ── Internal callbacks ───────────────────────────────────────────────────── */

/* Deferred fullscreen — same rationale as window.c: 200 ms timeout to let
 * Mutter complete the windowed configure round-trip and establish
 * zwp_tablet_v2 input routing before we request fullscreen. */
static gboolean deferred_fullscreen(gpointer w)
{
    gtk_window_fullscreen(GTK_WINDOW(w));
    return G_SOURCE_REMOVE;
}

/* TUI process exited (Ctrl+D, `exit`, or crash) — treat as session end. */
static void on_tui_child_exited(VteTerminal *term, int status, gpointer user_data)
{
    (void)term; (void)status;
    AppState *app = user_data;
    if (app->window)
        gtk_window_destroy(GTK_WINDOW(app->window));
}

/* F11 captured at the TUI window level before VTE sees it. */
static gboolean on_tui_key_pressed(GtkEventControllerKey *ctrl,
                                    guint keyval, guint keycode,
                                    GdkModifierType mods, gpointer user_data)
{
    (void)ctrl; (void)keycode; (void)mods;
    GtkWindow *win = GTK_WINDOW(user_data);
    if (keyval == GDK_KEY_F11) {
        if (gtk_window_is_fullscreen(win))
            gtk_window_unfullscreen(win);
        else
            gtk_window_fullscreen(win);
        return TRUE;
    }
    return FALSE;
}

/* TUI window destroyed (window manager close button or integration_destroy_tui). */
static void on_tui_window_destroyed(GtkWidget *w, gpointer user_data)
{
    (void)w;
    AppState *app = user_data;
    app->tui_window   = NULL;
    app->tui_terminal = NULL;
    if (app->window)
        gtk_window_destroy(GTK_WINDOW(app->window));
}

/* ── Public API ───────────────────────────────────────────────────────────── */

void integration_create_tui_window(AppState *app, GtkApplication *gapp)
{
    if (!app->session_file[0]) return;

    GtkWidget *term = vte_terminal_new();
    app->tui_terminal = term;

    GtkWidget *win = gtk_application_window_new(gapp);
    gtk_window_set_title(GTK_WINDOW(win), "PAB Assessment");
    gtk_window_set_default_size(GTK_WINDOW(win), 900, 700);
    gtk_window_set_child(GTK_WINDOW(win), term);
    app->tui_window = win;

    /* Capture F11 at window level before VTE consumes it */
    GtkEventController *key_ctrl = gtk_event_controller_key_new();
    gtk_event_controller_set_propagation_phase(key_ctrl, GTK_PHASE_CAPTURE);
    gtk_widget_add_controller(win, key_ctrl);
    g_signal_connect(key_ctrl, "key-pressed",
                     G_CALLBACK(on_tui_key_pressed), win);

    g_signal_connect(term, "child-exited",
                     G_CALLBACK(on_tui_child_exited), app);
    g_signal_connect(win, "destroy",
                     G_CALLBACK(on_tui_window_destroyed), app);

    gtk_window_present(GTK_WINDOW(win));
    g_timeout_add(200, deferred_fullscreen, win);

    char *argv[] = { "assessments", "--session", app->session_file, NULL };
    vte_terminal_spawn_async(
        VTE_TERMINAL(term),
        VTE_PTY_DEFAULT,
        NULL,               /* working dir — inherit */
        argv,
        NULL,               /* env — inherit */
        G_SPAWN_SEARCH_PATH,
        NULL, NULL,         /* child setup */
        NULL,               /* pid out */
        -1,                 /* timeout */
        NULL,               /* cancellable */
        NULL, NULL);        /* callback */
}

void integration_focus_tui(AppState *app)
{
    if (app->tui_window)
        gtk_window_present(GTK_WINDOW(app->tui_window));
}

void integration_destroy_tui(AppState *app)
{
    if (app->tui_window)
        gtk_window_destroy(GTK_WINDOW(app->tui_window));
    /* on_tui_window_destroyed NULLs the pointers; no further action needed. */
}
