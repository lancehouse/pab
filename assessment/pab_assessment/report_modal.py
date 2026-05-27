"""Ctrl+R report viewer — renders clean.md as formatted markdown in a modal overlay."""

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import MarkdownViewer
from textual.widgets._markdown import MarkdownTableOfContents


class ReportModal(ModalScreen):
    """Full-screen read-only markdown report viewer. Escape to close, t to toggle TOC."""

    BINDINGS = [
        Binding("escape", "dismiss_modal", "Close",    show=True),
        Binding("t",      "toggle_toc",    "TOC",      show=True),
    ]

    DEFAULT_CSS = """
    ReportModal {
        background: $background 85%;
        align: center middle;
    }
    #report_frame {
        width: 96%;
        height: 96%;
        background: $surface;
        border: solid $primary;
    }
    ReportModal MarkdownViewer {
        height: 1fr;
        border: none;
        scrollbar-gutter: stable;
        padding: 0;
    }
    ReportModal MarkdownViewer:focus {
        border: none;
    }
    /* TOC panel: fixed at ~1/3 width so content gets 2/3 */
    ReportModal MarkdownTableOfContents {
        width: 32;
        border-right: solid $primary 30%;
    }
    ReportModal MarkdownTableOfContents > Tree {
        width: 1fr;
        padding: 0 1;
    }
    """

    def __init__(self, markdown_text: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._markdown_text = markdown_text

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

    def action_toggle_toc(self) -> None:
        viewer = self.query_one("#report_viewer", MarkdownViewer)
        viewer.show_table_of_contents = not viewer.show_table_of_contents
