"""HistoriesScreen — All missions as a historical record for the Site-Nine TUI.

This screen differs from MissionsScreen in intent and sort order:
  - Shows ALL missions (active AND ended), emphasising historical context
  - Default sort: most-recent-ended first; active missions are pinned to top
  - Focuses on the work-log perspective: what was done, when, by whom
  - Preview pane: mission metadata + first section of mission file
  - Full-page view: full mission file rendered and scrollable

Layout:
  - List pane: ID, Codename, Persona, Role, Status, Date range, Objective
  - Preview pane: metadata + first portion of mission file markdown
  - Full-page view: full mission file content scrollable
  - Filter bar: by status, role, or persona using / key
  - Keybindings: j/k or up/down, Enter for full page, Escape to close, / to filter
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pendulum
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, Static

from site_nine.core.database import Database
from site_nine.missions.manager import MissionManager
from site_nine.missions.models import Mission
from site_nine.missions.types import MissionStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STATUS_COLOURS: dict[str, str] = {
    "ACTIVE": "green",
    "IDLE": "yellow",
    "SUSPENDED": "magenta",
    "ENDED": "dim",
    "ROLE_PENDING": "cyan",
    "PERSONA_PENDING": "cyan",
}

_STATUS_SYMBOLS: dict[str, str] = {
    "ACTIVE": "●",
    "IDLE": "◌",
    "SUSPENDED": "⏸",
    "ENDED": "○",
    "ROLE_PENDING": "?",
    "PERSONA_PENDING": "?",
}


def _truncate(text: str, width: int) -> str:
    """Truncate string to *width* characters, appending '…' if needed."""
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"


def _status_value(mission: Mission) -> str:
    """Return the plain status string from a Mission."""
    return mission.status.value if isinstance(mission.status, MissionStatus) else str(mission.status)


def _date_range(mission: Mission) -> str:
    """Return a compact date-range string for the mission."""
    start = mission.start_date
    if mission.end_time:
        # Show just date if ended
        return f"{start} → done"
    return f"{start} → …"


def _sort_key(mission: Mission) -> tuple[int, str]:
    """
    Sort key placing ENDED missions most-recent-first, active/idle at top.

    Active missions sort before ended ones. Within each group, most recent first.
    """
    status = _status_value(mission)
    # Group 0 = active/idle/suspended (still running), group 1 = ended
    group = 1 if status == "ENDED" else 0
    # Within group sort descending by created_at (negate via string trick)
    ts = mission.created_at.format("YYYY-MM-DDTHH:mm:ss")
    return (group, ts)


# ---------------------------------------------------------------------------
# Full-page view (pushed screen)
# ---------------------------------------------------------------------------


class HistoryFullPage(Screen):
    """Full scrollable view of a mission's file content (historical perspective)."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("j", "scroll_down", "Scroll down", show=False),
        Binding("k", "scroll_up", "Scroll up", show=False),
        Binding("d", "scroll_page_down", "Page down", show=False),
        Binding("u", "scroll_page_up", "Page up", show=False),
        Binding("g", "scroll_home", "Top", show=False),
        Binding("G", "scroll_end", "Bottom", show=False),
    ]

    def __init__(self, mission: Mission, db: Database) -> None:
        super().__init__()
        self._mission = mission
        self._db = db

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        status = _status_value(self._mission)
        status_col = _STATUS_COLOURS.get(status, "white")
        sym = _STATUS_SYMBOLS.get(status, "●")
        title = (
            f"[ESC]  Mission #{self._mission.id}  "
            f"[bold]{self._mission.codename}[/bold]  "
            f"({self._mission.persona_name} — {self._mission.role})  "
            f"[{status_col}]{sym} {status}[/{status_col}]"
        )
        yield Static(title, id="fullpage-title", classes="fullpage-title", markup=True)
        with ScrollableContainer(id="fullpage-scroll"):
            yield Static(self._build_content(), id="fullpage-body", markup=True)
        yield Footer()

    def _build_content(self) -> str:
        mission = self._mission
        status = _status_value(mission)
        status_col = _STATUS_COLOURS.get(status, "white")
        lines: list[str] = []

        # Metadata block
        lines.append(f"[bold]Mission:[/bold]   #{mission.id}  {mission.codename}")
        lines.append(f"[bold]Persona:[/bold]   {mission.persona_name}")
        lines.append(f"[bold]Role:[/bold]      {mission.role}")
        lines.append(f"[bold]Status:[/bold]    [{status_col}]{status}[/{status_col}]")
        lines.append(f"[bold]Objective:[/bold] {mission.objective}")
        lines.append(f"[bold]Started:[/bold]   {mission.start_date} {mission.start_time}")
        if mission.end_time:
            lines.append(f"[bold]Ended:[/bold]     {mission.start_date} {mission.end_time}")
        if mission.epic_id:
            lines.append(f"[bold]Epic:[/bold]      {mission.epic_id}")
        if mission.desk_mode_active:
            lines.append("[bold]Desk Mode:[/bold] [green]active[/green]")
        lines.append(
            f"[dim]Created: {mission.created_at.format('YYYY-MM-DD HH:mm')}  "
            f"Updated: {mission.updated_at.format('YYYY-MM-DD HH:mm')}[/dim]"
        )
        lines.append("")

        # Mission file content
        mission_file = Path(mission.mission_file)
        if mission_file.exists():
            try:
                content = mission_file.read_text()
                lines.append("[bold]Mission File:[/bold]")
                lines.append("")
                for line in content.splitlines():
                    lines.append(line.replace("[", "\\["))
            except OSError as exc:
                lines.append(f"[red]Error reading mission file: {exc}[/red]")
        else:
            lines.append(f"[dim]Mission file not found: {mission.mission_file}[/dim]")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_scroll_down(self) -> None:
        self.query_one("#fullpage-scroll", ScrollableContainer).scroll_down()

    def action_scroll_up(self) -> None:
        self.query_one("#fullpage-scroll", ScrollableContainer).scroll_up()

    def action_scroll_page_down(self) -> None:
        scroll = self.query_one("#fullpage-scroll", ScrollableContainer)
        scroll.scroll_relative(y=scroll.size.height // 2)

    def action_scroll_page_up(self) -> None:
        scroll = self.query_one("#fullpage-scroll", ScrollableContainer)
        scroll.scroll_relative(y=-(scroll.size.height // 2))

    def action_scroll_home(self) -> None:
        self.query_one("#fullpage-scroll", ScrollableContainer).scroll_home()

    def action_scroll_end(self) -> None:
        self.query_one("#fullpage-scroll", ScrollableContainer).scroll_end()


# ---------------------------------------------------------------------------
# Histories screen
# ---------------------------------------------------------------------------


class HistoriesScreen(Screen):
    """
    Histories screen — all missions as a historical record (active + ended).

    Differs from MissionsScreen:
      - Shows ALL missions, not just active ones
      - Default sort: active missions first, then ended missions most-recent-first
      - Focus is on the historical/audit view of work done

    List view columns: ID, Codename, Persona, Role, Status, Date Range, Objective
    Preview pane: mission metadata + first section of mission file
    Full-page view: full mission file rendered and scrollable

    Filter: by status/role/persona using / key

    Keybindings:
        j / down    Move selection down
        k / up      Move selection up
        /           Focus filter input
        Enter       Open full-page view
        Escape      Pop this screen
        6           Switch to this screen (Histories is screen 6)
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("up", "cursor_up", "Up", show=False),
        Binding("enter", "open_fullpage", "Open"),
        Binding("escape", "app.pop_screen", "Back"),
        Binding("/", "focus_filter", "Filter", show=True),
        Binding("6", "app.switch_screen('histories')", "Histories", show=False),
    ]

    def __init__(self, db: Database) -> None:
        super().__init__()
        self._db = db
        self._manager = MissionManager(db)
        self._missions: list[Mission] = []
        self._filtered: list[Mission] = []
        self._filter_text: str = ""

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="histories-body"):
            with Vertical(id="sidebar", classes="sidebar"):
                yield Static("6 Histories", classes="sidebar-active")
            with Vertical(id="content-area"):
                yield Input(
                    placeholder="Filter by status, role, or persona (e.g. ENDED, Engineer)…",
                    id="filter-input",
                    classes="filter-bar",
                )
                yield DataTable(id="histories-table", show_cursor=True, zebra_stripes=True)
                with ScrollableContainer(id="preview-pane", classes="preview-pane"):
                    yield Static("", id="preview-text", markup=True)
        yield Footer()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        self.query_one("#filter-input", Input).display = False
        self._load_data()
        self._populate_table()

    def _load_data(self) -> None:
        """Load all missions (active + ended), sorted for historical view."""
        try:
            # List all missions — active and ended
            all_missions = self._manager.list_missions()
            # Sort: active/idle/suspended first (by created_at desc), then ended (by created_at desc)
            self._missions = sorted(all_missions, key=_sort_key)
        except Exception as exc:  # noqa: BLE001
            self._missions = []
            self._set_preview(f"[red]Error loading histories: {exc}[/red]")

    def _apply_filter(self) -> None:
        """Apply the current filter text to the full mission list."""
        text = self._filter_text.strip().upper()
        if not text:
            self._filtered = list(self._missions)
        else:
            self._filtered = [
                m
                for m in self._missions
                if text in _status_value(m).upper()
                or text in m.role.upper()
                or text in m.persona_name.upper()
                or text in m.codename.upper()
            ]

    def _populate_table(self) -> None:
        """Rebuild the DataTable from the filtered list."""
        self._apply_filter()
        table = self.query_one("#histories-table", DataTable)
        table.clear(columns=True)
        table.add_columns("ID", "Codename", "Persona", "Role", "Status", "Dates", "Objective")

        for mission in self._filtered:
            status = _status_value(mission)
            status_col = _STATUS_COLOURS.get(status, "white")
            sym = _STATUS_SYMBOLS.get(status, "●")
            date_range = _date_range(mission)

            table.add_row(
                str(mission.id),
                mission.codename,
                mission.persona_name,
                mission.role,
                f"[{status_col}]{sym} {status}[/{status_col}]",
                date_range,
                _truncate(mission.objective, 40),
                key=str(mission.id),
            )

        if not self._filtered:
            self._set_preview("[dim]No missions match the current filter.[/dim]")
        else:
            table.move_cursor(row=0)
            self._refresh_preview()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:  # noqa: ARG002
        self._refresh_preview()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filter-input":
            self._filter_text = event.value
            self._populate_table()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "filter-input":
            self.query_one("#filter-input", Input).display = False
            self.query_one("#histories-table", DataTable).focus()

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def _refresh_preview(self) -> None:
        """Update preview pane with the selected mission's details."""
        table = self.query_one("#histories-table", DataTable)
        if table.row_count == 0:
            return
        try:
            mission_id_str = str(table.get_row_at(table.cursor_row)[0])
        except Exception:  # noqa: BLE001
            return
        self._show_preview_for(mission_id_str)

    def _show_preview_for(self, mission_id_str: str) -> None:
        """Render a preview for the selected mission."""
        try:
            mission_id = int(mission_id_str)
        except ValueError:
            return
        mission = next((m for m in self._filtered if m.id == mission_id), None)
        if mission is None:
            self._set_preview(f"[dim]Mission #{mission_id_str} not found.[/dim]")
            return

        status = _status_value(mission)
        status_col = _STATUS_COLOURS.get(status, "white")
        sym = _STATUS_SYMBOLS.get(status, "●")

        lines: list[str] = [
            f"[bold]Mission #{mission.id}[/bold]  [{status_col}]{sym} {status}[/{status_col}]",
            f"[bold]{mission.codename}[/bold]  ({mission.persona_name} — {mission.role})",
            "",
            f"[bold]Objective:[/bold] {mission.objective}",
            f"[bold]Started:[/bold]   {mission.start_date} {mission.start_time}",
        ]

        if mission.end_time:
            lines.append(f"[bold]Ended:[/bold]     {mission.start_date} {mission.end_time}")

        if mission.epic_id:
            lines.append(f"[bold]Epic:[/bold]      {mission.epic_id}")

        if mission.desk_mode_active:
            lines.append("[green]● desk mode active[/green]")

        lines.append(f"[dim]Updated: {mission.updated_at.format('YYYY-MM-DD HH:mm')}[/dim]")
        lines.append("")

        # Preview first section of the mission file
        mission_file = Path(mission.mission_file)
        if mission_file.exists():
            try:
                file_lines = mission_file.read_text().splitlines()
                # Find end of first section (first blank line after ## heading)
                preview_lines = file_lines[:20]
                lines.append("[bold]Mission File (preview):[/bold]")
                for fl in preview_lines:
                    lines.append(fl.replace("[", "\\["))
                if len(file_lines) > 20:
                    lines.append(f"[dim]…{len(file_lines) - 20} more lines[/dim]")
            except OSError:
                lines.append("[dim]Could not read mission file.[/dim]")
        else:
            lines.append("[dim]Mission file not found.[/dim]")

        self._set_preview("\n".join(lines))

    def _set_preview(self, markup: str) -> None:
        self.query_one("#preview-text", Static).update(markup)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_cursor_down(self) -> None:
        self.query_one("#histories-table", DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#histories-table", DataTable).action_cursor_up()

    def action_focus_filter(self) -> None:
        """Show and focus the filter input."""
        fi = self.query_one("#filter-input", Input)
        fi.display = True
        fi.focus()

    def action_open_fullpage(self) -> None:
        """Push the full-page history view."""
        table = self.query_one("#histories-table", DataTable)
        if table.row_count == 0:
            return
        try:
            mission_id_str = str(table.get_row_at(table.cursor_row)[0])
            mission_id = int(mission_id_str)
        except Exception:  # noqa: BLE001
            return

        mission = next((m for m in self._filtered if m.id == mission_id), None)
        if mission is None:
            return

        self.app.push_screen(HistoryFullPage(mission, self._db))
