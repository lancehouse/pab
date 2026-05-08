"""Textual TUI main entry point."""

import sys
import asyncio
from pathlib import Path
from textual.app import ComposeResult, App
from textual.widgets import Header, Footer
from textual.containers import Container
from .tui import PhysioAssessmentTUI, SessionListScreen
from .storage import load_assessment, load_session_current


class PhysioAssessment(App):
    """Main Textual application for PhysioChart assessment system."""

    TITLE = "PhysioChart Assessment System"
    SUB_TITLE = "Specialist Physiotherapy Assessment & Report Generator"

    BINDINGS = [
        ("ctrl+q", "quit",              "Quit"),
        ("ctrl+l", "show_session_list", "Sessions"),
    ]

    CSS = """
    Screen { background: $surface; }
    """

    def __init__(self, session_path: str = "", **kwargs):
        super().__init__(**kwargs)
        self.current_session_path = session_path
        self.assessment_screen = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container()
        yield Footer()

    def on_mount(self) -> None:
        if self.current_session_path:
            asyncio.create_task(self.show_assessment_form())
            return

        current_data = load_session_current()
        if current_data and current_data.get("session_file"):
            self.current_session_path = current_data["session_file"]
            asyncio.create_task(self.show_assessment_form())
        else:
            self.show_session_list()

    def show_session_list(self) -> None:
        main = self.query_one(Container)
        main.remove_children()
        session_list = SessionListScreen(on_session_selected=self.on_session_selected)
        main.mount(session_list)

    async def on_session_selected(self, session_path: str) -> None:
        self.current_session_path = session_path
        await self.show_assessment_form()

    async def show_assessment_form(self) -> None:
        main = self.query_one(Container)
        main.remove_children()
        assessment = PhysioAssessmentTUI(session_path=self.current_session_path)
        self.assessment_screen = assessment
        main.mount(assessment)

    def on_session_list_screen_new_session_requested(self) -> None:
        self.show_session_list()

    def action_show_session_list(self) -> None:
        self.show_session_list()


def main():
    """Entry point — accepts optional --session <path> argument."""
    session_path = ""
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--session" and i + 1 < len(args):
            session_path = args[i + 1]
            break

    app = PhysioAssessment(session_path=session_path)
    app.run()


if __name__ == "__main__":
    main()
