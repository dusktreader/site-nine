"""KeybindingFooter widget — shows global navigation keybindings."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label


# Screen navigation bindings displayed in the footer
SCREEN_BINDINGS = [
    ("[1]Dashboard", "1"),
    ("[2]Missions", "2"),
    ("[3]Messages", "3"),
    ("[4]Tasks", "4"),
    ("[5]ADRs", "5"),
    ("[6]Hist", "6"),
]


class KeybindingFooter(Widget):
    """
    Application footer bar showing navigation and global keybindings.

    Left side: screen navigation shortcuts
    Right side: global action hints (q=quit, ?=help, r=refresh)
    """

    DEFAULT_CSS = """
    KeybindingFooter {
        dock: bottom;
        height: 1;
        background: $primary-darken-1;
        color: $text-muted;
        layout: horizontal;
    }

    KeybindingFooter #nav {
        width: 1fr;
        content-align: left middle;
        padding: 0 1;
    }

    KeybindingFooter #actions {
        width: auto;
        content-align: right middle;
        padding: 0 1;
    }
    """

    active_screen: reactive[str] = reactive("dashboard")

    def compose(self) -> ComposeResult:
        yield Label("", id="nav")
        yield Label("[dim]r[/dim]=refresh  [dim]?[/dim]=help  [dim]q[/dim]=quit", id="actions")

    def on_mount(self) -> None:
        self._update_nav()

    def watch_active_screen(self, screen: str) -> None:
        self._update_nav()

    def _update_nav(self) -> None:
        try:
            nav_label = self.query_one("#nav", Label)
            parts = []
            for label, _ in SCREEN_BINDINGS:
                # Highlight the active screen name
                screen_key = label.split("]")[1].lower().rstrip("s") if "]" in label else label.lower()
                active = self.active_screen.lower()
                if active.startswith(screen_key) or screen_key.startswith(active[:4]):
                    parts.append(f"[bold]{label}[/bold]")
                else:
                    parts.append(f"[dim]{label}[/dim]")
            nav_label.update("  ".join(parts))
        except Exception:
            pass  # Widget not yet mounted
