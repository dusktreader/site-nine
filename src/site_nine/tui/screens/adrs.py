"""ADRsScreen — Architecture Decision Record list with markdown content preview."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static


class ADRsScreen(Screen):
    """Shows Architecture Decision Records with markdown preview. Stub for Phase 1."""

    DEFAULT_CSS = """
    ADRsScreen {
        align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("[bold]ADRs[/bold]\n\nArchitecture Decision Records.\n[dim]Full implementation in Phase 3.[/dim]")
