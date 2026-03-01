"""ErrorScreen — simple error display when TUI cannot initialise properly."""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static


class ErrorScreen(Screen):
    """Displays an error message and allows quitting."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "app.quit", "Quit", priority=True),
    ]

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static(
            f"[red bold]Error[/red bold]\n\n{self._message}\n\n[dim]Press q to quit.[/dim]",
            id="error-text",
            markup=True,
        )
        yield Footer()
