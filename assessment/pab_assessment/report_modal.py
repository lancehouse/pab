"""Ctrl+R report viewer — renders clean.md as formatted markdown in a modal overlay."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import MarkdownViewer


class ReportModal(ModalScreen):
    """Full-screen read-only markdown report viewer. Escape to close."""

    BINDINGS = [Binding("escape", "dismiss_modal", "Close", show=True)]

    DEFAULT_CSS = """
    ReportModal {
        background: $background 85%;
        align: center middle;
    }
    #report_frame {
        width: 94%;
        height: 94%;
        background: $surface;
        border: solid $primary;
    }
    #report_title_bar {
        height: 1;
        background: $primary;
        color: $background;
        padding: 0 2;
        content-align: left middle;
    }
    ReportModal MarkdownViewer {
        height: 1fr;
        padding: 0 1;
        border: none;
        scrollbar-gutter: stable;
    }
    ReportModal MarkdownViewer:focus {
        border: none;
    }
    """

    def __init__(self, markdown_text: str, title: str = "Clean Report", **kwargs) -> None:
        super().__init__(**kwargs)
        self._markdown_text = markdown_text
        self._title = title

    def compose(self) -> ComposeResult:
        with Container(id="report_frame"):
            yield MarkdownViewer(
                self._markdown_text,
                show_table_of_contents=True,
                id="report_viewer",
            )

    def on_mount(self) -> None:
        self.query_one("#report_viewer", MarkdownViewer).focus()

    def action_dismiss_modal(self) -> None:
        self.dismiss()
