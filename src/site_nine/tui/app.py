"""SiteNineApp — Root Textual application for the Site-Nine TUI.

Provides:
  - Global keybindings: 1-7 switch screens, q quit, ? help
  - Sidebar navigation shared across all content screens
  - Database connection shared to all screens at mount time
  - Graceful degradation when DB is unavailable (error screen shown instead)
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import Footer, Header, Static

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path

# Screen name constants used for switch_screen
SCREEN_DASHBOARD = "dashboard"
SCREEN_MISSIONS = "missions"
SCREEN_TASKS = "tasks"
SCREEN_MESSAGES = "messages"
SCREEN_ADRS = "adrs"
SCREEN_HISTORIES = "histories"
SCREEN_EPICS = "epics"
SCREEN_ERROR = "error"

# Ordered list of (number, name, label) tuples used in the sidebar and key bindings
SCREEN_ORDER: list[tuple[str, str, str]] = [
    ("1", SCREEN_DASHBOARD, "Dashboard"),
    ("2", SCREEN_MISSIONS, "Missions"),
    ("3", SCREEN_TASKS, "Tasks"),
    ("4", SCREEN_MESSAGES, "Messages"),
    ("5", SCREEN_ADRS, "ADRs"),
    ("6", SCREEN_HISTORIES, "Histories"),
    ("7", SCREEN_EPICS, "Epics"),
]


class SiteNineApp(App):
    """Root application — registers screens and handles global keybindings."""

    CSS_PATH = "styles/app.tcss"

    TITLE = "Site-Nine"
    SUB_TITLE = "AI Agent Orchestration HQ"

    BINDINGS: list[BindingType] = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("question_mark", "help", "Help", show=True),
        Binding("1", "switch_screen('dashboard')", "Dashboard", show=False, priority=True),
        Binding("2", "switch_screen('missions')", "Missions", show=False, priority=True),
        Binding("3", "switch_screen('tasks')", "Tasks", show=False, priority=True),
        Binding("4", "switch_screen('messages')", "Messages", show=False, priority=True),
        Binding("5", "switch_screen('adrs')", "ADRs", show=False, priority=True),
        Binding("6", "switch_screen('histories')", "Histories", show=False, priority=True),
        Binding("7", "switch_screen('epics')", "Epics", show=False, priority=True),
    ]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        """Open DB connection and register all screens."""
        db: Database | None = None
        try:
            db_path = get_db_path()
            db = Database(db_path)
        except FileNotFoundError:
            db = None

        if db is None:
            self._register_error_screen()
            self.push_screen(SCREEN_ERROR)
        else:
            self._register_screens(db)
            self.push_screen(SCREEN_DASHBOARD)

    def _register_error_screen(self) -> None:
        """Show a simple error screen when DB is unavailable."""
        from site_nine.tui.screens.error import ErrorScreen

        self.install_screen(
            ErrorScreen("Database unavailable. Run 's9 init' to initialise the project."),
            name=SCREEN_ERROR,
        )

    def _register_screens(self, db: Database) -> None:
        """Lazy-import and install all content screens."""
        # Import here to avoid circular imports and keep startup fast
        from site_nine.tui.screens.dashboard import DashboardScreen
        from site_nine.tui.screens.missions import MissionsScreen
        from site_nine.tui.screens.tasks import TasksScreen
        from site_nine.tui.screens.messages import MessagesScreen
        from site_nine.tui.screens.adrs import ADRsScreen
        from site_nine.tui.screens.histories import HistoriesScreen
        from site_nine.tui.screens.epics import EpicsScreen

        self.install_screen(DashboardScreen(db), name=SCREEN_DASHBOARD)
        self.install_screen(MissionsScreen(db), name=SCREEN_MISSIONS)
        self.install_screen(TasksScreen(db), name=SCREEN_TASKS)
        self.install_screen(MessagesScreen(db), name=SCREEN_MESSAGES)
        self.install_screen(ADRsScreen(db), name=SCREEN_ADRS)
        self.install_screen(HistoriesScreen(db), name=SCREEN_HISTORIES)
        self.install_screen(EpicsScreen(db), name=SCREEN_EPICS)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_help(self) -> None:
        """Show a help overlay."""
        from site_nine.tui.screens.help import HelpScreen

        self.push_screen(HelpScreen())
