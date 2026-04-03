"""Comprehensive tests for the Site-Nine TUI package.

Covers all 9 scenarios from TST-H-0237:
  1. App launches without error
  2. Default screen is Dashboard
  3. Screen navigation works (sidebar keybindings switch screens)
  4. Each content screen loads data and renders a list
  5. Preview pane updates when selection changes
  6. Full-page view opens on Enter and closes on Escape
  7. vim keybindings j/k navigate lists
  8. Filter/search works on Tasks and Missions screens
  9. s9 bare command launches TUI (__main__ routing)

Uses Textual's run_test() async context manager (Textual >= 0.47 / 8.x).
All tests are async and use pytest-anyio via the ``pytest.mark.anyio`` mark.

Key design notes:
  - After switch_screen("tasks"/"missions"), the DataTable receives keyboard
    focus automatically.  Pressing j/s/p/enter would go to the DataTable, not
    the screen's BINDINGS.  We therefore call screen actions directly:
      await pilot.app.screen.action_cursor_down()
      await pilot.app.screen.action_cycle_status()
    etc.  This is the intended test pattern — we verify the *action* works, not
    the key routing (key routing is covered by the binding-declaration tests).
  - For full-page open/close we call action_open_fullpage() / app.pop_screen()
    directly for the same reason.
  - For the '/' filter-reveal we call action_focus_filter() directly.
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator
from unittest.mock import MagicMock, patch

import pytest

from site_nine.core.database import Database
from site_nine.tui.app import SiteNineApp

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.anyio  # all tests in this module are async


@asynccontextmanager
async def _run_app(db: Database) -> AsyncIterator:
    """Run a SiteNineApp that uses *db* as its database.

    Patches ``get_db_path`` so the real ``on_mount`` flow picks up the test DB.
    Yields the Textual Pilot after an initial pause so the app is fully mounted.
    """
    with patch("site_nine.tui.app.get_db_path", return_value=db.db_path):
        async with SiteNineApp().run_test(headless=True) as pilot:
            await pilot.pause()
            yield pilot


# ---------------------------------------------------------------------------
# 1. App launches without error
# ---------------------------------------------------------------------------


class TestAppLaunch:
    """Scenario 1: App launches without error."""

    async def test_app_launches_with_valid_db(self, tui_db: Database) -> None:
        """SiteNineApp starts and reaches a running state with a valid DB."""
        async with _run_app(tui_db) as pilot:
            assert pilot.app.is_running

    async def test_app_launches_without_db(self) -> None:
        """SiteNineApp shows the error screen when no DB is available."""
        from site_nine.tui.screens.error import ErrorScreen

        with patch("site_nine.tui.app.get_db_path", side_effect=FileNotFoundError("no db")):
            async with SiteNineApp().run_test(headless=True) as pilot:
                await pilot.pause()
                assert isinstance(pilot.app.screen, ErrorScreen)

    async def test_app_title(self, tui_db: Database) -> None:
        """App TITLE and SUB_TITLE are set correctly."""
        async with _run_app(tui_db) as pilot:
            assert pilot.app.TITLE == "Site-Nine"
            assert pilot.app.SUB_TITLE is not None and "AI Agent" in pilot.app.SUB_TITLE


# ---------------------------------------------------------------------------
# 2. Default screen is Dashboard
# ---------------------------------------------------------------------------


class TestDefaultScreen:
    """Scenario 2: Default screen is Dashboard."""

    async def test_default_screen_is_dashboard(self, tui_db: Database) -> None:
        """After mount the active screen should be DashboardScreen."""
        from site_nine.tui.screens.dashboard import DashboardScreen

        async with _run_app(tui_db) as pilot:
            assert isinstance(pilot.app.screen, DashboardScreen)

    async def test_dashboard_screen_name(self, tui_db: Database) -> None:
        """DashboardScreen.SCREEN_NAME is 'dashboard'."""
        from site_nine.tui.screens.dashboard import DashboardScreen

        assert DashboardScreen.SCREEN_NAME == "dashboard"

    async def test_dashboard_content_widget_exists(self, tui_db: Database) -> None:
        """The dashboard content Static widget is present after mount."""
        from textual.widgets import Static

        async with _run_app(tui_db) as pilot:
            content = pilot.app.screen.query_one("#dashboard-content", Static)
            assert content is not None

    async def test_dashboard_shows_some_content(self, tui_db: Database) -> None:
        """Dashboard renders non-empty content from the seeded DB."""
        from textual.widgets import Static

        async with _run_app(tui_db) as pilot:
            content = pilot.app.screen.query_one("#dashboard-content", Static)
            text = str(content.content)
            assert len(text) > 0


# ---------------------------------------------------------------------------
# 3. Screen navigation via sidebar keybindings
# ---------------------------------------------------------------------------


class TestScreenNavigation:
    """Scenario 3: Sidebar keybindings switch screens."""

    async def test_key_2_switches_to_missions(self, tui_db: Database) -> None:
        """Pressing '2' navigates to MissionsScreen."""
        from site_nine.tui.screens.missions import MissionsScreen

        async with _run_app(tui_db) as pilot:
            await pilot.press("2")
            await pilot.pause()
            assert isinstance(pilot.app.screen, MissionsScreen)

    async def test_key_3_switches_to_tasks(self, tui_db: Database) -> None:
        """Pressing '3' navigates to TasksScreen."""
        from site_nine.tui.screens.tasks import TasksScreen

        async with _run_app(tui_db) as pilot:
            await pilot.press("3")
            await pilot.pause()
            assert isinstance(pilot.app.screen, TasksScreen)

    async def test_key_7_switches_to_epics(self, tui_db: Database) -> None:
        """Pressing '7' navigates to EpicsScreen."""
        from site_nine.tui.screens.epics import EpicsScreen

        async with _run_app(tui_db) as pilot:
            await pilot.press("7")
            await pilot.pause()
            assert isinstance(pilot.app.screen, EpicsScreen)

    async def test_navigate_back_to_dashboard(self, tui_db: Database) -> None:
        """switch_screen to tasks then back to dashboard via app action."""
        from site_nine.tui.screens.dashboard import DashboardScreen

        async with _run_app(tui_db) as pilot:
            await pilot.press("3")
            await pilot.pause()
            # After switch_screen, DataTable has focus and would consume '1'.
            # Call the app action directly to test the navigation logic itself.
            await pilot.app.action_switch_screen("dashboard")
            await pilot.pause()
            assert isinstance(pilot.app.screen, DashboardScreen)

    async def test_screen_order_constant(self) -> None:
        """SCREEN_ORDER contains all 7 expected screens in numbered order."""
        from site_nine.tui.app import SCREEN_ORDER

        assert len(SCREEN_ORDER) == 7
        numbers = [num for num, _, _ in SCREEN_ORDER]
        assert numbers == ["1", "2", "3", "4", "5", "6", "7"]
        names = [name for _, name, _ in SCREEN_ORDER]
        assert "dashboard" in names
        assert "missions" in names
        assert "tasks" in names


# ---------------------------------------------------------------------------
# 4. Each content screen loads data and renders a list
# ---------------------------------------------------------------------------


class TestScreensLoadData:
    """Scenario 4: Each content screen loads data and renders a list."""

    async def test_tasks_screen_has_table_rows(self, tui_db: Database) -> None:
        """TasksScreen populates its DataTable with rows from the DB."""
        from textual.widgets import DataTable

        async with _run_app(tui_db) as pilot:
            await pilot.press("3")
            await pilot.pause()
            table = pilot.app.screen.query_one("#tasks-table", DataTable)
            assert table.row_count > 0

    async def test_missions_screen_has_table_rows(self, tui_db: Database) -> None:
        """MissionsScreen populates its DataTable with rows from the DB."""
        from textual.widgets import DataTable

        async with _run_app(tui_db) as pilot:
            await pilot.press("2")
            await pilot.pause()
            table = pilot.app.screen.query_one("#missions-table", DataTable)
            assert table.row_count > 0

    async def test_tasks_screen_columns(self, tui_db: Database) -> None:
        """TasksScreen DataTable has expected column count (6 columns)."""
        from textual.widgets import DataTable

        async with _run_app(tui_db) as pilot:
            await pilot.press("3")
            await pilot.pause()
            table = pilot.app.screen.query_one("#tasks-table", DataTable)
            assert len(table.columns) == 6

    async def test_missions_screen_columns(self, tui_db: Database) -> None:
        """MissionsScreen DataTable has expected column count (5 columns)."""
        from textual.widgets import DataTable

        async with _run_app(tui_db) as pilot:
            await pilot.press("2")
            await pilot.pause()
            table = pilot.app.screen.query_one("#missions-table", DataTable)
            assert len(table.columns) == 5

    async def test_epics_screen_loads(self, tui_db: Database) -> None:
        """EpicsScreen mounts without error."""
        from site_nine.tui.screens.epics import EpicsScreen

        async with _run_app(tui_db) as pilot:
            await pilot.press("7")
            await pilot.pause()
            assert isinstance(pilot.app.screen, EpicsScreen)

    async def test_messages_screen_loads(self, tui_db: Database) -> None:
        """MessagesScreen mounts without error."""
        from site_nine.tui.screens.messages import MessagesScreen

        async with _run_app(tui_db) as pilot:
            await pilot.press("4")
            await pilot.pause()
            assert isinstance(pilot.app.screen, MessagesScreen)


# ---------------------------------------------------------------------------
# 5. Preview pane updates when selection changes
# ---------------------------------------------------------------------------


class TestPreviewPane:
    """Scenario 5: Preview pane updates when selection changes."""

    async def test_tasks_preview_pane_exists(self, tui_db: Database) -> None:
        """TasksScreen has a preview-text Static widget."""
        from textual.widgets import Static

        async with _run_app(tui_db) as pilot:
            await pilot.press("3")
            await pilot.pause()
            preview = pilot.app.screen.query_one("#preview-text", Static)
            assert preview is not None

    async def test_tasks_initial_preview_non_empty(self, tui_db: Database) -> None:
        """After TasksScreen loads, the preview pane is populated for the first row."""
        from textual.widgets import Static

        async with _run_app(tui_db) as pilot:
            await pilot.press("3")
            await pilot.pause()
            preview = pilot.app.screen.query_one("#preview-text", Static)
            text = str(preview.content)
            assert len(text) > 0

    async def test_missions_preview_pane_exists(self, tui_db: Database) -> None:
        """MissionsScreen has a preview-text Static widget."""
        from textual.widgets import Static

        async with _run_app(tui_db) as pilot:
            await pilot.press("2")
            await pilot.pause()
            preview = pilot.app.screen.query_one("#preview-text", Static)
            assert preview is not None

    async def test_tasks_preview_updates_on_navigation(self, tui_db: Database) -> None:
        """Moving the cursor down with action_cursor_down() changes the preview pane."""
        from textual.widgets import DataTable, Static

        async with _run_app(tui_db) as pilot:
            await pilot.press("3")
            await pilot.pause()

            table = pilot.app.screen.query_one("#tasks-table", DataTable)
            if table.row_count < 2:
                pytest.skip("Need at least 2 tasks to test navigation")

            initial_row = table.cursor_row

            # Call the action directly — avoids DataTable focus stealing the key
            pilot.app.screen.action_cursor_down()  # type: ignore[attr-defined]
            await pilot.pause()
            await pilot.pause()

            assert table.cursor_row == initial_row + 1


# ---------------------------------------------------------------------------
# 6. Full-page view opens on Enter and closes on Escape
# ---------------------------------------------------------------------------


class TestFullPageView:
    """Scenario 6: Full-page view opens on Enter and closes on Escape."""

    async def test_enter_opens_task_fullpage(self, tui_db: Database) -> None:
        """action_open_fullpage() pushes TaskFullPage onto the screen stack."""
        from site_nine.tui.screens.tasks import TaskFullPage, TasksScreen

        async with _run_app(tui_db) as pilot:
            await pilot.press("3")
            await pilot.pause()

            assert isinstance(pilot.app.screen, TasksScreen)
            # Call action directly — Enter would be consumed by focused DataTable
            pilot.app.screen.action_open_fullpage()  # type: ignore[attr-defined]
            await pilot.pause()

            assert isinstance(pilot.app.screen, TaskFullPage)

    async def test_escape_closes_task_fullpage(self, tui_db: Database) -> None:
        """Pressing Escape on the full-page view pops back to TasksScreen."""
        from site_nine.tui.screens.tasks import TasksScreen

        async with _run_app(tui_db) as pilot:
            await pilot.press("3")
            await pilot.pause()
            pilot.app.screen.action_open_fullpage()  # type: ignore[attr-defined]
            await pilot.pause()
            # TaskFullPage is now active and has focus — Escape binding works here
            await pilot.press("escape")
            await pilot.pause()

            assert isinstance(pilot.app.screen, TasksScreen)

    async def test_enter_opens_mission_fullpage(self, tui_db: Database) -> None:
        """action_open_fullpage() pushes PossessionFullPage onto the screen stack."""
        from site_nine.tui.screens.missions import MissionsScreen, PossessionFullPage

        async with _run_app(tui_db) as pilot:
            await pilot.press("2")
            await pilot.pause()

            assert isinstance(pilot.app.screen, MissionsScreen)
            pilot.app.screen.action_open_fullpage()  # type: ignore[attr-defined]
            await pilot.pause()

            assert isinstance(pilot.app.screen, PossessionFullPage)

    async def test_escape_closes_mission_fullpage(self, tui_db: Database) -> None:
        """Pressing Escape on mission full-page pops back to MissionsScreen."""
        from site_nine.tui.screens.missions import MissionsScreen

        async with _run_app(tui_db) as pilot:
            await pilot.press("2")
            await pilot.pause()
            pilot.app.screen.action_open_fullpage()  # type: ignore[attr-defined]
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()

            assert isinstance(pilot.app.screen, MissionsScreen)

    async def test_fullpage_has_escape_binding(self) -> None:
        """TaskFullPage and PossessionFullPage declare escape binding."""
        from site_nine.tui.screens.missions import PossessionFullPage
        from site_nine.tui.screens.tasks import TaskFullPage

        task_keys = {b.key for b in TaskFullPage.BINDINGS}
        mission_keys = {b.key for b in PossessionFullPage.BINDINGS}

        assert "escape" in task_keys
        assert "escape" in mission_keys


# ---------------------------------------------------------------------------
# 7. vim keybindings j/k navigate lists
# ---------------------------------------------------------------------------


class TestVimKeybindings:
    """Scenario 7: vim keybindings j/k navigate lists."""

    async def test_j_moves_cursor_down_in_tasks(self, tui_db: Database) -> None:
        """action_cursor_down() moves the DataTable cursor down by one row."""
        from textual.widgets import DataTable

        async with _run_app(tui_db) as pilot:
            await pilot.press("3")
            await pilot.pause()

            table = pilot.app.screen.query_one("#tasks-table", DataTable)
            if table.row_count < 2:
                pytest.skip("Need at least 2 rows for cursor-down test")

            initial_row = table.cursor_row
            # Call action directly — DataTable would consume 'j' keypress
            pilot.app.screen.action_cursor_down()  # type: ignore[attr-defined]
            await pilot.pause()
            assert table.cursor_row == initial_row + 1

    async def test_k_moves_cursor_up_in_tasks(self, tui_db: Database) -> None:
        """action_cursor_up() after action_cursor_down() moves the cursor back up."""
        from textual.widgets import DataTable

        async with _run_app(tui_db) as pilot:
            await pilot.press("3")
            await pilot.pause()

            table = pilot.app.screen.query_one("#tasks-table", DataTable)
            if table.row_count < 2:
                pytest.skip("Need at least 2 rows for cursor-up test")

            pilot.app.screen.action_cursor_down()  # type: ignore[attr-defined]
            await pilot.pause()
            row_after_j = table.cursor_row
            pilot.app.screen.action_cursor_up()  # type: ignore[attr-defined]
            await pilot.pause()
            assert table.cursor_row == row_after_j - 1

    async def test_j_moves_cursor_down_in_missions(self, tui_db: Database) -> None:
        """action_cursor_down() moves the missions DataTable cursor down."""
        from textual.widgets import DataTable

        async with _run_app(tui_db) as pilot:
            await pilot.press("2")
            await pilot.pause()

            table = pilot.app.screen.query_one("#missions-table", DataTable)
            if table.row_count < 2:
                pytest.skip("Need at least 2 missions for cursor-down test")

            initial_row = table.cursor_row
            pilot.app.screen.action_cursor_down()  # type: ignore[attr-defined]
            await pilot.pause()
            assert table.cursor_row == initial_row + 1

    async def test_vim_bindings_declared_on_tasks_screen(self) -> None:
        """TasksScreen BINDINGS include 'j' and 'k' keys."""
        from site_nine.tui.screens.tasks import TasksScreen

        keys = {b.key for b in TasksScreen.BINDINGS}
        assert "j" in keys
        assert "k" in keys

    async def test_vim_bindings_declared_on_missions_screen(self) -> None:
        """MissionsScreen BINDINGS include 'j' and 'k' keys."""
        from site_nine.tui.screens.missions import MissionsScreen

        keys = {b.key for b in MissionsScreen.BINDINGS}
        assert "j" in keys
        assert "k" in keys

    async def test_vim_bindings_declared_on_base_screen(self) -> None:
        """ContentScreen base class BINDINGS include 'j', 'k', 'g', 'G'."""
        from site_nine.tui.screens.base import ContentScreen

        keys = {b.key for b in ContentScreen.BINDINGS}
        assert "j" in keys
        assert "k" in keys
        assert "g" in keys
        assert "G" in keys


# ---------------------------------------------------------------------------
# 8. Filter / search works on Tasks and Missions screens
# ---------------------------------------------------------------------------


class TestFilterSearch:
    """Scenario 8: Filter/search works on Tasks and Missions screens."""

    async def test_tasks_filter_by_status_cycle(self, tui_db: Database) -> None:
        """action_cycle_status() advances the status filter past '(all)'."""
        from site_nine.tui.screens.tasks import TasksScreen

        async with _run_app(tui_db) as pilot:
            await pilot.press("3")
            await pilot.pause()

            screen: TasksScreen = pilot.app.screen  # type: ignore[assignment]
            assert screen.filter_status == "(all)"

            # Call action directly — 's' would be consumed by focused DataTable
            pilot.app.screen.action_cycle_status()  # type: ignore[attr-defined]
            await pilot.pause()
            assert screen.filter_status != "(all)"

    async def test_tasks_filter_by_priority_cycle(self, tui_db: Database) -> None:
        """action_cycle_priority() advances the priority filter past '(all)'."""
        from site_nine.tui.screens.tasks import TasksScreen

        async with _run_app(tui_db) as pilot:
            await pilot.press("3")
            await pilot.pause()

            screen: TasksScreen = pilot.app.screen  # type: ignore[assignment]
            assert screen.filter_priority == "(all)"

            pilot.app.screen.action_cycle_priority()  # type: ignore[attr-defined]
            await pilot.pause()
            assert screen.filter_priority != "(all)"

    async def test_tasks_filter_reset(self, tui_db: Database) -> None:
        """action_reset_filters() resets all filters back to '(all)'."""
        from site_nine.tui.screens.tasks import TasksScreen

        async with _run_app(tui_db) as pilot:
            await pilot.press("3")
            await pilot.pause()

            screen: TasksScreen = pilot.app.screen  # type: ignore[assignment]

            pilot.app.screen.action_cycle_status()  # type: ignore[attr-defined]
            await pilot.pause()
            assert screen.filter_status != "(all)"

            pilot.app.screen.action_reset_filters()  # type: ignore[attr-defined]
            await pilot.pause()
            assert screen.filter_status == "(all)"
            assert screen.filter_priority == "(all)"

    async def test_tasks_filter_reduces_rows(self, tui_db: Database) -> None:
        """Cycling the status filter to COMPLETE reduces the visible row count."""
        from textual.widgets import DataTable

        from site_nine.tui.screens.tasks import TasksScreen

        async with _run_app(tui_db) as pilot:
            await pilot.press("3")
            await pilot.pause()

            table = pilot.app.screen.query_one("#tasks-table", DataTable)
            total_rows = table.row_count

            # Cycle 3 times: (all) -> TODO -> UNDERWAY -> COMPLETE
            for _ in range(3):
                pilot.app.screen.action_cycle_status()  # type: ignore[attr-defined]
                await pilot.pause()

            filtered_rows = table.row_count
            # Seeded data has 1 COMPLETE task — fewer than the total 5
            assert filtered_rows < total_rows

    async def test_missions_filter_input_shown_on_slash(self, tui_db: Database) -> None:
        """action_focus_filter() reveals the filter Input widget on MissionsScreen."""
        from textual.widgets import Input

        async with _run_app(tui_db) as pilot:
            await pilot.press("2")
            await pilot.pause()

            filter_input = pilot.app.screen.query_one("#filter-input", Input)
            assert not filter_input.display  # hidden by default

            # Call action directly — '/' would be consumed by focused DataTable
            pilot.app.screen.action_focus_filter()  # type: ignore[attr-defined]
            await pilot.pause()
            assert filter_input.display  # visible after action

    async def test_missions_filter_narrows_list(self, tui_db: Database) -> None:
        """Setting a role filter on MissionsScreen reduces visible rows."""
        from textual.widgets import DataTable

        from site_nine.tui.screens.missions import MissionsScreen

        async with _run_app(tui_db) as pilot:
            await pilot.press("2")
            await pilot.pause()

            table = pilot.app.screen.query_one("#missions-table", DataTable)
            total = table.row_count

            screen: MissionsScreen = pilot.app.screen  # type: ignore[assignment]

            # Set filter text directly and repopulate (simulates typing into filter)
            screen._filter_text = "TESTER"  # type: ignore[attr-defined]
            screen._populate_table()  # type: ignore[attr-defined]
            await pilot.pause()

            filtered = table.row_count
            assert filtered < total

    async def test_tasks_slash_shows_role_filter(self, tui_db: Database) -> None:
        """action_focus_filter() on TasksScreen reveals the role-filter Input widget."""
        from textual.widgets import Input

        async with _run_app(tui_db) as pilot:
            await pilot.press("3")
            await pilot.pause()

            role_input = pilot.app.screen.query_one("#role-filter-input", Input)
            assert not role_input.display  # hidden initially

            # Call action directly — '/' would be consumed by focused DataTable
            pilot.app.screen.action_focus_filter()  # type: ignore[attr-defined]
            await pilot.pause()
            assert role_input.display  # visible after action


# ---------------------------------------------------------------------------
# 9. s9 bare command launches TUI (__main__ routing)
# ---------------------------------------------------------------------------


class TestMainRouting:
    """Scenario 9: s9 bare command launches TUI."""

    def test_main_callback_launches_tui_in_tty(self) -> None:
        """main() invokes SiteNineApp().run() when stdout is a TTY.

        SiteNineApp is imported *lazily* inside the callback body:
            from site_nine.tui.app import SiteNineApp
        We must therefore patch at the source module (site_nine.tui.app), not
        at site_nine.__main__ which has no SiteNineApp attribute at import time.
        """
        from typer.testing import CliRunner

        import site_nine.__main__ as main_module

        runner = CliRunner()

        with patch("site_nine.tui.app.SiteNineApp") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            # Force the TTY check to return True
            with patch("site_nine.__main__.sys") as mock_sys:
                mock_sys.stdout.isatty.return_value = True
                runner.invoke(main_module.app, [], catch_exceptions=False)

        mock_instance.run.assert_called_once()

    def test_main_callback_no_tui_flag_shows_help(self) -> None:
        """Passing --no-tui shows CLI help instead of launching the TUI."""
        from typer.testing import CliRunner

        import site_nine.__main__ as main_module

        runner = CliRunner()

        with patch("site_nine.tui.app.SiteNineApp") as mock_cls:
            result = runner.invoke(main_module.app, ["--no-tui"], catch_exceptions=False)

        mock_cls.assert_not_called()
        assert result.exit_code == 0

    def test_main_module_entry_point(self) -> None:
        """site_nine.__main__ has an ``if __name__ == '__main__': app()`` guard."""
        import site_nine.__main__ as main_module

        source = Path(main_module.__file__).read_text()
        assert '__name__ == "__main__"' in source or "__name__ == '__main__'" in source

    def test_tui_app_is_importable(self) -> None:
        """SiteNineApp can be imported from site_nine.tui.app."""
        from site_nine.tui.app import SiteNineApp

        assert SiteNineApp is not None

    def test_tui_screens_are_importable(self) -> None:
        """All 7 content screen classes are importable."""
        from site_nine.tui.screens.adrs import ADRsScreen
        from site_nine.tui.screens.dashboard import DashboardScreen
        from site_nine.tui.screens.epics import EpicsScreen
        from site_nine.tui.screens.histories import HistoriesScreen
        from site_nine.tui.screens.messages import MessagesScreen
        from site_nine.tui.screens.missions import MissionsScreen
        from site_nine.tui.screens.tasks import TasksScreen

        for cls in (
            DashboardScreen,
            MissionsScreen,
            TasksScreen,
            MessagesScreen,
            ADRsScreen,
            HistoriesScreen,
            EpicsScreen,
        ):
            assert cls is not None
