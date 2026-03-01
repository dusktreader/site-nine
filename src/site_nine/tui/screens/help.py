"""HelpScreen — keyboard shortcut overlay for the Site-Nine TUI."""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer
from textual.screen import ModalScreen
from textual.widgets import Footer, Static

_HELP_TEXT = """\
[bold underline]Site-Nine TUI — Keyboard Reference[/bold underline]

[bold]Global[/bold]
  [yellow]1-7[/yellow]       Switch screens
  [yellow]q[/yellow]         Quit application
  [yellow]?[/yellow]         Show this help

[bold]Navigation (list)[/bold]
  [yellow]j / ↓[/yellow]     Move selection down
  [yellow]k / ↑[/yellow]     Move selection up
  [yellow]g[/yellow]         Jump to top
  [yellow]G[/yellow]         Jump to bottom
  [yellow]Enter[/yellow]     Open full-page view
  [yellow]Escape[/yellow]    Go back / close

[bold]Full-page view[/bold]
  [yellow]j / ↓[/yellow]     Scroll down
  [yellow]k / ↑[/yellow]     Scroll up
  [yellow]d[/yellow]         Scroll half-page down
  [yellow]u[/yellow]         Scroll half-page up
  [yellow]g[/yellow]         Scroll to top
  [yellow]G[/yellow]         Scroll to bottom
  [yellow]Escape[/yellow]    Close full-page view

[bold]Screens[/bold]
  [yellow]1[/yellow]  Dashboard   — stats, active missions, task counts
  [yellow]2[/yellow]  Missions    — active missions with mission file preview
  [yellow]3[/yellow]  Tasks       — task queue with priority/status filters
  [yellow]4[/yellow]  Messages    — conversations and discussions
  [yellow]5[/yellow]  ADRs        — architecture decision records
  [yellow]6[/yellow]  Histories   — all missions as historical record
  [yellow]7[/yellow]  Epics       — epics with progress bars

[bold]Messages screen[/bold]
  [yellow]Tab[/yellow]       Toggle Conversations ↔ Discussions

[bold]Tasks screen[/bold]
  [yellow]r[/yellow]         Refresh data

[dim]Press Escape or ? to close this help.[/dim]
"""


class HelpScreen(ModalScreen):
    """Modal help overlay."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Close"),
        Binding("question_mark", "app.pop_screen", "Close"),
        Binding("q", "app.pop_screen", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with ScrollableContainer(id="help-scroll"):
            yield Static(_HELP_TEXT, id="help-text", markup=True)
        yield Footer()
