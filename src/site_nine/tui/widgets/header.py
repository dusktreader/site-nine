"""AppHeader widget — displays app logo, current screen title, clock, and help hint."""

from __future__ import annotations

import pendulum
from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label


class AppHeader(Widget):
    """
    Application header bar.

    Shows:
    - Left:   [s9] brand + current screen title
    - Right:  current time + [?] help hint

    The screen_title reactive attribute is updated by SiteNineApp when
    the active screen changes.
    """

    DEFAULT_CSS = """
    AppHeader {
        dock: top;
        height: 1;
        background: $primary;
        color: $text;
        layout: horizontal;
    }

    AppHeader #left {
        width: 1fr;
        content-align: left middle;
        padding: 0 1;
    }

    AppHeader #right {
        width: auto;
        content-align: right middle;
        padding: 0 1;
    }
    """

    screen_title: reactive[str] = reactive("Dashboard")

    def compose(self) -> ComposeResult:
        yield Label("", id="left")
        yield Label("", id="right")

    def on_mount(self) -> None:
        self._update_labels()
        # Refresh clock every second
        self.set_interval(1, self._update_clock)

    def watch_screen_title(self, title: str) -> None:
        self._update_labels()

    def _update_labels(self) -> None:
        now = pendulum.now()
        time_str = now.format("ddd HH:mm")
        try:
            left = self.query_one("#left", Label)
            right = self.query_one("#right", Label)
            left.update(f"[bold][s9][/bold]  {self.screen_title}")
            right.update(f"{time_str}  [dim][?][/dim]")
        except Exception:
            pass  # Widget not yet mounted

    def _update_clock(self) -> None:
        self._update_labels()
