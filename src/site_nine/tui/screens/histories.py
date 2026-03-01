"""HistoriesScreen — ended missions list with summary preview."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static


class HistoriesScreen(Screen):
    """Shows historical (ended) missions. Stub for Phase 1."""

    DEFAULT_CSS = """
    HistoriesScreen {
        align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("[bold]Histories[/bold]\n\nEnded mission history.\n[dim]Full implementation in Phase 3.[/dim]")
