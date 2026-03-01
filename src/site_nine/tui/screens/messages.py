"""MessagesScreen — conversation list with thread view."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static


class MessagesScreen(Screen):
    """Shows agent conversations and message threads. Stub for Phase 1."""

    DEFAULT_CSS = """
    MessagesScreen {
        align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold]Messages[/bold]\n\nConversation inbox and thread viewer.\n[dim]Full implementation in Phase 3.[/dim]"
        )
