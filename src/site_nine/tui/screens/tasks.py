"""TasksScreen — task list with filtering and task file preview."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static


class TasksScreen(Screen):
    """Shows filterable task list with preview. Stub for Phase 1."""

    DEFAULT_CSS = """
    TasksScreen {
        align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold]Tasks[/bold]\n\nFilterable task list with file preview.\n[dim]Full implementation in Phase 3.[/dim]"
        )
