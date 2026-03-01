"""SiteNineApp — root Textual application for the site-nine TUI.

Launches when `s9` is invoked with no arguments (and stdout is a TTY).
All existing CLI subcommands continue to work via TTY detection + --no-tui flag.

Architecture: ARC-H-0239 (Mission #167, rogue-typhoon)
Implementation: ENG-H-0240 (Mission #170, shadow-blaze)
"""

from __future__ import annotations

from pathlib import Path
from importlib.resources import files as _pkg_files

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Label

from site_nine.tui.data.loader import DataLoader
from site_nine.tui.screens.adrs import ADRsScreen
from site_nine.tui.screens.dashboard import DashboardScreen
from site_nine.tui.screens.histories import HistoriesScreen
from site_nine.tui.screens.messages import MessagesScreen
from site_nine.tui.screens.missions import MissionsScreen
from site_nine.tui.screens.tasks import TasksScreen
from site_nine.tui.widgets.footer import KeybindingFooter
from site_nine.tui.widgets.header import AppHeader

# Screen registry: name → (class, title, key)
_SCREENS: list[tuple[str, type[Screen], str, str]] = [
    ("dashboard", DashboardScreen, "Dashboard", "1"),
    ("missions", MissionsScreen, "Missions", "2"),
    ("messages", MessagesScreen, "Messages", "3"),
    ("tasks", TasksScreen, "Tasks", "4"),
    ("adrs", ADRsScreen, "ADRs", "5"),
    ("histories", HistoriesScreen, "Histories", "6"),
]

# Resolve stylesheet path from package resources
_CSS_PATH = Path(str(_pkg_files("site_nine").joinpath("tui/styles/app.tcss")))


class SiteNineApp(App):
    """
    Root Textual application for the site-nine TUI.

    CSS_PATH points to the bundled styles/app.tcss stylesheet.

    Global keybindings:
        1–6     Switch to numbered screen
        d       Dashboard
        m       Missions
        g       Messages (comms/telegrams)
        t       Tasks
        a       ADRs
        h       Histories
        ?       Help (Phase 4)
        r       Refresh current screen
        q       Quit
    """

    CSS_PATH = _CSS_PATH

    SCREENS = {name: cls for name, cls, _title, _key in _SCREENS}

    BINDINGS = [
        Binding("1", "switch_screen('dashboard')", "Dashboard", show=False),
        Binding("2", "switch_screen('missions')", "Missions", show=False),
        Binding("3", "switch_screen('messages')", "Messages", show=False),
        Binding("4", "switch_screen('tasks')", "Tasks", show=False),
        Binding("5", "switch_screen('adrs')", "ADRs", show=False),
        Binding("6", "switch_screen('histories')", "Histories", show=False),
        Binding("d", "switch_screen('dashboard')", "Dashboard", show=False),
        Binding("m", "switch_screen('missions')", "Missions", show=False),
        Binding("g", "switch_screen('messages')", "Messages", show=False),
        Binding("t", "switch_screen('tasks')", "Tasks", show=False),
        Binding("a", "switch_screen('adrs')", "ADRs", show=False),
        Binding("h", "switch_screen('histories')", "Histories", show=False),
        Binding("q", "quit", "Quit", show=False),
        Binding("r", "refresh_screen", "Refresh", show=False),
        Binding("?", "show_help", "Help", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._data_loader: DataLoader | None = None
        self._active_screen_name: str = "dashboard"

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        """Initialise DataLoader on mount, then push the dashboard screen."""
        self._init_data_loader()
        # Install all screens
        for name, cls, _title, _key in _SCREENS:
            self.install_screen(cls(), name=name)
        self.push_screen("dashboard")

    def _init_data_loader(self) -> None:
        """
        Try to connect to the project database and create a DataLoader.
        If the .opencode dir or DB is missing, set loader to None — screens
        will handle the missing-loader case gracefully.
        """
        try:
            from site_nine.core.database import Database
            from site_nine.core.paths import get_db_path

            db_path = get_db_path()
            self._db = Database(db_path)
            self._data_loader = DataLoader(self._db)
        except FileNotFoundError:
            self._data_loader = None

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        """Mount the persistent header and footer; the main content area is
        filled by the active screen."""
        yield AppHeader()
        yield KeybindingFooter()

    # ------------------------------------------------------------------
    # Screen switching
    # ------------------------------------------------------------------

    def action_switch_screen(self, screen_name: str) -> None:
        """Switch to the named screen and update the header title."""
        # Find the human-readable title for this screen
        title = screen_name.title()
        for name, _cls, t, _key in _SCREENS:
            if name == screen_name:
                title = t
                break

        self._active_screen_name = screen_name
        self._update_header_title(title)
        self._update_footer_active(screen_name)
        self.switch_screen(screen_name)

    def _update_header_title(self, title: str) -> None:
        try:
            header = self.query_one(AppHeader)
            header.screen_title = title
        except Exception:
            pass

    def _update_footer_active(self, screen_name: str) -> None:
        try:
            footer = self.query_one(KeybindingFooter)
            footer.active_screen = screen_name
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Other global actions
    # ------------------------------------------------------------------

    def action_refresh_screen(self) -> None:
        """Trigger a data refresh on the current screen."""
        if hasattr(self.screen, "refresh_data"):
            self.call_later(self.screen.refresh_data)  # type: ignore[attr-defined]

    def action_show_help(self) -> None:
        """Show help overlay. Implemented in Phase 4 (ENG-M-0244)."""
        self.notify("Help overlay — coming in Phase 4!", severity="information")

    # ------------------------------------------------------------------
    # DataLoader access
    # ------------------------------------------------------------------

    @property
    def data_loader(self) -> DataLoader | None:
        """Return the shared DataLoader, or None if DB is unavailable."""
        return self._data_loader
