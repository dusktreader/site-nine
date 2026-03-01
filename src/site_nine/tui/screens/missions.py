"""MissionsScreen — active/idle/ended mission list with mission file preview."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static


class MissionsScreen(Screen):
    """Shows active and historical missions. Stub for Phase 1."""

    DEFAULT_CSS = """
    MissionsScreen {
        align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(
            "[bold]Missions[/bold]\n\nActive and historical mission list.\n[dim]Full implementation in Phase 3.[/dim]"
        )
