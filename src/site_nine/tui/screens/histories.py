"""HistoriesScreen — All possessions as a historical record for the Site-Nine TUI.

This screen differs from MissionsScreen in intent and sort order:
  - Shows ALL possessions (active AND exorcised), emphasising historical context
  - Default sort: most-recent-exorcised first; active possessions are pinned to top
  - Focuses on the work-log perspective: what was done, when, by whom
  - Preview pane: possession metadata + first section of possession log
  - Full-page view: full possession log rendered and scrollable

Layout:
  - List pane: ID, Daemon, Role, Status, Dates
  - Preview pane: metadata + first portion of possession log markdown
  - Full-page view: full possession log content scrollable
  - Filter bar: by status, role, or daemon using / key
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
from site_nine.possessions.manager import PossessionManager
from site_nine.possessions.models import Possession
from site_nine.possessions.types import PossessionStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STATUS_COLOURS: dict[str, str] = {
    "ACTIVE": "green",
    "SUSPENDED": "magenta",
    "EXORCISED": "dim",
    "ROLE_PENDING": "cyan",
    "DAEMON_PENDING": "cyan",
}

_STATUS_SYMBOLS: dict[str, str] = {
    "ACTIVE": "●",
    "SUSPENDED": "⏸",
    "EXORCISED": "○",
    "ROLE_PENDING": "?",
    "DAEMON_PENDING": "?",
}


def _truncate(text: str | None, width: int) -> str:
    """Truncate string to *width* characters, appending '…' if needed."""
    if text is None:
        return ""
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"


def _status_value(possession: Possession) -> str:
    """Return the plain status string from a Possession."""
    return possession.status.value if isinstance(possession.status, PossessionStatus) else str(possession.status)


def _date_range(possession: Possession) -> str:
    """Return a compact date-range string for the possession."""
    start = possession.start_time[:10] if possession.start_time else "?"
    if possession.end_time:
        return f"{start} → done"
    return f"{start} → …"


def _sort_key(possession: Possession) -> tuple[int, str]:
    """
    Sort key placing EXORCISED possessions most-recent-first, active at top.

    Active possessions sort before exorcised ones. Within each group, most recent first.
    """
    status = _status_value(possession)
    # Group 0 = active/suspended (still running), group 1 = exorcised
    group = 1 if status == "EXORCISED" else 0
    # Within group sort descending by created_at (negate via string trick)
    ts = possession.created_at.format("YYYY-MM-DDTHH:mm:ss")
    return (group, ts)


# ---------------------------------------------------------------------------
# Full-page view (pushed screen)
# ---------------------------------------------------------------------------


class HistoryFullPage(Screen):
    """Full scrollable view of a possession's log content (historical perspective)."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("j", "scroll_down", "Scroll down", show=False),
        Binding("k", "scroll_up", "Scroll up", show=False),
        Binding("d", "scroll_page_down", "Page down", show=False),
        Binding("u", "scroll_page_up", "Page up", show=False),
        Binding("g", "scroll_home", "Top", show=False),
        Binding("G", "scroll_end", "Bottom", show=False),
    ]

    def __init__(self, possession: Possession, db: Database) -> None:
        super().__init__()
        self._possession = possession
        self._db = db

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        status = _status_value(self._possession)
        status_col = _STATUS_COLOURS.get(status, "white")
        sym = _STATUS_SYMBOLS.get(status, "●")
        title = (
            f"[ESC]  Possession #{self._possession.id}  "
            f"({self._possession.daemon_name} — {self._possession.role})  "
            f"[{status_col}]{sym} {status}[/{status_col}]"
        )
        yield Static(title, id="fullpage-title", classes="fullpage-title", markup=True)
        with ScrollableContainer(id="fullpage-scroll"):
            yield Static(self._build_content(), id="fullpage-body", markup=True)
        yield Footer()

    def _build_content(self) -> str:
        possession = self._possession
        status = _status_value(possession)
        status_col = _STATUS_COLOURS.get(status, "white")
        lines: list[str] = []

        # Metadata block
        lines.append(f"[bold]Possession:[/bold] #{possession.id}")
        lines.append(f"[bold]Daemon:[/bold]     {possession.daemon_name}")
        lines.append(f"[bold]Role:[/bold]       {possession.role}")
        lines.append(f"[bold]Status:[/bold]     [{status_col}]{status}[/{status_col}]")
        lines.append(f"[bold]Started:[/bold]    {possession.start_time}")
        if possession.end_time:
            lines.append(f"[bold]Ended:[/bold]      {possession.end_time}")
        if possession.epic_id:
            lines.append(f"[bold]Epic:[/bold]       {possession.epic_id}")
        if possession.desk_mode_active:
            lines.append("[bold]Desk Mode:[/bold] [green]active[/green]")
        lines.append(
            f"[dim]Created: {possession.created_at.format('YYYY-MM-DD HH:mm')}  "
            f"Updated: {possession.updated_at.format('YYYY-MM-DD HH:mm')}[/dim]"
        )
        lines.append("")

        # Possession log content
        possession_log = Path(possession.possession_log)
        if possession_log.exists():
            try:
                content = possession_log.read_text()
                lines.append("[bold]Possession Log:[/bold]")
                lines.append("")
                for line in content.splitlines():
                    lines.append(line.replace("[", "\\["))
            except OSError as exc:
                lines.append(f"[red]Error reading possession log: {exc}[/red]")
        else:
            lines.append(f"[dim]Possession log not found: {possession.possession_log}[/dim]")

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
    Histories screen — all possessions as a historical record (active + exorcised).

    Differs from MissionsScreen:
      - Shows ALL possessions, not just active ones
      - Default sort: active possessions first, then exorcised most-recent-first
      - Focus is on the historical/audit view of work done

    List view columns: ID, Daemon, Role, Status, Dates
    Preview pane: possession metadata + first section of possession log
    Full-page view: full possession log rendered and scrollable

    Filter: by status/role/daemon using / key

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
        self._manager = PossessionManager(db)
        self._possessions: list[Possession] = []
        self._filtered: list[Possession] = []
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
                    placeholder="Filter by status, role, or daemon (e.g. EXORCISED, Engineer)…",
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
        """Load all possessions (active + exorcised), sorted for historical view."""
        try:
            # List all possessions — active and exorcised
            all_possessions = self._manager.list_possessions()
            # Sort: active/suspended first (by created_at desc), then exorcised (by created_at desc)
            self._possessions = sorted(all_possessions, key=_sort_key)
        except Exception as exc:  # noqa: BLE001
            self._possessions = []
            self._set_preview(f"[red]Error loading histories: {exc}[/red]")

    def _apply_filter(self) -> None:
        """Apply the current filter text to the full possession list."""
        text = self._filter_text.strip().upper()
        if not text:
            self._filtered = list(self._possessions)
        else:
            self._filtered = [
                p
                for p in self._possessions
                if text in _status_value(p).upper() or text in p.role.upper() or text in p.daemon_name.upper()
            ]

    def _populate_table(self) -> None:
        """Rebuild the DataTable from the filtered list."""
        self._apply_filter()
        table = self.query_one("#histories-table", DataTable)
        table.clear(columns=True)
        table.add_columns("ID", "Daemon", "Role", "Status", "Dates")

        for possession in self._filtered:
            status = _status_value(possession)
            status_col = _STATUS_COLOURS.get(status, "white")
            sym = _STATUS_SYMBOLS.get(status, "●")
            date_range = _date_range(possession)

            table.add_row(
                str(possession.id),
                possession.daemon_name,
                possession.role,
                f"[{status_col}]{sym} {status}[/{status_col}]",
                date_range,
                key=str(possession.id),
            )

        if not self._filtered:
            self._set_preview("[dim]No possessions match the current filter.[/dim]")
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
        """Update preview pane with the selected possession's details."""
        table = self.query_one("#histories-table", DataTable)
        if table.row_count == 0:
            return
        try:
            possession_id_str = str(table.get_row_at(table.cursor_row)[0])
        except Exception:  # noqa: BLE001
            return
        self._show_preview_for(possession_id_str)

    def _show_preview_for(self, possession_id_str: str) -> None:
        """Render a preview for the selected possession."""
        try:
            possession_id = int(possession_id_str)
        except ValueError:
            return
        possession = next((p for p in self._filtered if p.id == possession_id), None)
        if possession is None:
            self._set_preview(f"[dim]Possession #{possession_id_str} not found.[/dim]")
            return

        status = _status_value(possession)
        status_col = _STATUS_COLOURS.get(status, "white")
        sym = _STATUS_SYMBOLS.get(status, "●")

        lines: list[str] = [
            f"[bold]Possession #{possession.id}[/bold]  [{status_col}]{sym} {status}[/{status_col}]",
            f"[bold]{possession.daemon_name}[/bold]  ({possession.role})",
            "",
            f"[bold]Started:[/bold]   {possession.start_time}",
        ]

        if possession.end_time:
            lines.append(f"[bold]Ended:[/bold]     {possession.end_time}")

        if possession.epic_id:
            lines.append(f"[bold]Epic:[/bold]      {possession.epic_id}")

        if possession.desk_mode_active:
            lines.append("[green]● desk mode active[/green]")

        lines.append(f"[dim]Updated: {possession.updated_at.format('YYYY-MM-DD HH:mm')}[/dim]")
        lines.append("")

        # Preview first section of the possession log
        possession_log = Path(possession.possession_log)
        if possession_log.exists():
            try:
                file_lines = possession_log.read_text().splitlines()
                preview_lines = file_lines[:20]
                lines.append("[bold]Possession Log (preview):[/bold]")
                for fl in preview_lines:
                    lines.append(fl.replace("[", "\\["))
                if len(file_lines) > 20:
                    lines.append(f"[dim]…{len(file_lines) - 20} more lines[/dim]")
            except OSError:
                lines.append("[dim]Could not read possession log.[/dim]")
        else:
            lines.append("[dim]Possession log not found.[/dim]")

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
            possession_id_str = str(table.get_row_at(table.cursor_row)[0])
            possession_id = int(possession_id_str)
        except Exception:  # noqa: BLE001
            return

        possession = next((p for p in self._filtered if p.id == possession_id), None)
        if possession is None:
            return

        self.app.push_screen(HistoryFullPage(possession, self._db))
