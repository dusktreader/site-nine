"""Base ContentScreen — 3-pane layout used by all content screens.

Layout:
  ┌──────────────────────────────────────────────────────────────┐
  │ Header                                                        │
  ├──────────────┬───────────────────────────────────────────────┤
  │  Sidebar     │  List pane (DataTable)                         │
  │  1 Dashboard │  ┌──────────────────────────────────────────┐ │
  │  2 Missions  │  │ col1 │ col2 │ ...                        │ │
  │  3 Tasks     │  └──────────────────────────────────────────┘ │
  │  4 Messages  ├───────────────────────────────────────────────┤
  │  5 ADRs      │  Preview pane (selected item)                  │
  │  6 Histories │  [first ~20 lines, markup rendered]            │
  │  7 Epics     │                                                │
  └──────────────┴───────────────────────────────────────────────┘
  │ Footer                                                        │
  └──────────────────────────────────────────────────────────────┘

Subclasses override:
  - SCREEN_NAME: str  — used to highlight the correct sidebar entry
  - compose_list_pane() → ComposeResult  — yields the DataTable + controls
  - on_mount_hook()  — load data, populate table
"""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from site_nine.core.database import Database
from site_nine.tui.app import SCREEN_ORDER

# ---------------------------------------------------------------------------
# Shared colour/symbol mappings used across multiple screens
# ---------------------------------------------------------------------------

STATUS_COLOURS: dict[str, str] = {
    "TODO": "white",
    "UNDERWAY": "yellow",
    "COMPLETE": "green",
    "ABORTED": "dim",
    "BLOCKED": "red",
    "PAUSED": "cyan",
    "REVIEW": "magenta",
    # Mission statuses
    "ACTIVE": "green",
    "IDLE": "dim",
    "ENDED": "dim",
    "SUSPENDED": "dim",
}

PRIORITY_COLOURS: dict[str, str] = {
    "CRITICAL": "red",
    "HIGH": "yellow",
    "MEDIUM": "white",
    "LOW": "dim",
}

STATUS_SYMBOLS: dict[str, str] = {
    "TODO": "○",
    "UNDERWAY": "●",
    "COMPLETE": "✓",
    "ABORTED": "✗",
    "BLOCKED": "⊘",
    "PAUSED": "⏸",
    "REVIEW": "⊙",
    "ACTIVE": "●",
    "IDLE": "◌",
    "ENDED": "✓",
}


def truncate(text: str, width: int) -> str:
    """Truncate *text* to *width* characters, appending '…' if needed."""
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"


# ---------------------------------------------------------------------------
# Base screen
# ---------------------------------------------------------------------------


class ContentScreen(Screen):
    """
    Abstract 3-pane content screen.

    Subclasses must:
      1. Set SCREEN_NAME to their sidebar label string (e.g. "dashboard")
      2. Override on_mount() (or call super().on_mount() then load data)
      3. Use the provided DataTable (id="list-table") and preview Static
         (id="preview-text") widgets.
    """

    SCREEN_NAME: ClassVar[str] = ""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("up", "cursor_up", "Up", show=False),
        Binding("g", "cursor_top", "Top", show=False),
        Binding("G", "cursor_bottom", "Bottom", show=False),
        Binding("enter", "open_fullpage", "Open", show=True),
        Binding("escape", "app.pop_screen", "Back", show=False),
        # Global screen-switch bindings (mirrors app-level for screens)
        Binding("1", "app.switch_screen('dashboard')", "Dashboard", show=False),
        Binding("2", "app.switch_screen('missions')", "Missions", show=False),
        Binding("3", "app.switch_screen('tasks')", "Tasks", show=False),
        Binding("4", "app.switch_screen('messages')", "Messages", show=False),
        Binding("5", "app.switch_screen('adrs')", "ADRs", show=False),
        Binding("6", "app.switch_screen('histories')", "Histories", show=False),
        Binding("7", "app.switch_screen('epics')", "Epics", show=False),
    ]

    def __init__(self, db: Database | None) -> None:
        super().__init__()
        self._db = db

    # ------------------------------------------------------------------
    # Compose — builds the 3-pane layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="content-body"):
            with Vertical(id="sidebar", classes="sidebar"):
                for _num, name, label in SCREEN_ORDER:
                    css_class = "sidebar-active" if name == self.SCREEN_NAME else "sidebar-item"
                    num = _num
                    yield Static(f"{num} {label}", classes=css_class)
            with Vertical(id="main-area"):
                yield from self.compose_content()
        yield Footer()

    def compose_content(self) -> ComposeResult:
        """
        Override in subclasses to yield widgets for the main (non-sidebar) area.

        Default layout: DataTable on top, scrollable preview pane below.
        """
        yield DataTable(id="list-table", show_cursor=True, zebra_stripes=True)
        with ScrollableContainer(id="preview-pane", classes="preview-pane"):
            yield Static("", id="preview-text", markup=True)

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def set_preview(self, markup: str) -> None:
        """Update the preview pane content."""
        try:
            self.query_one("#preview-text", Static).update(markup)
        except Exception:  # noqa: BLE001
            pass

    def get_table(self) -> DataTable:
        return self.query_one("#list-table", DataTable)

    # ------------------------------------------------------------------
    # Default actions — subclasses can override
    # ------------------------------------------------------------------

    def action_cursor_down(self) -> None:
        try:
            self.get_table().action_cursor_down()
        except Exception:  # noqa: BLE001
            pass

    def action_cursor_up(self) -> None:
        try:
            self.get_table().action_cursor_up()
        except Exception:  # noqa: BLE001
            pass

    def action_cursor_top(self) -> None:
        try:
            table = self.get_table()
            if table.row_count:
                table.move_cursor(row=0)
        except Exception:  # noqa: BLE001
            pass

    def action_cursor_bottom(self) -> None:
        try:
            table = self.get_table()
            if table.row_count:
                table.move_cursor(row=table.row_count - 1)
        except Exception:  # noqa: BLE001
            pass

    def action_open_fullpage(self) -> None:
        """Override in subclasses to push a full-page view."""
        pass
