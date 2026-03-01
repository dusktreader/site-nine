"""DashboardScreen — epic progress cards + quick stats overview."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label, Static


class DashboardScreen(Screen):
    """Shows epic progress and quick stats. Stub for Phase 1."""

    DEFAULT_CSS = """
    DashboardScreen {
        align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold]Dashboard[/bold]\n\nEpic progress and system overview.\n[dim]Full implementation in Phase 3.[/dim]"
        )
