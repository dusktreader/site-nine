"""EpicsScreen — Epic viewer for the Site-Nine TUI.

Layout:
  - List pane: table of epics (id, title, status, priority, progress bar)
  - Preview pane: epic description + task list with status indicators
  - Full-page view: full epic file content + complete task breakdown
  - Color-coded by status
  - Keybindings: j/k or up/down, Enter for full page, Escape to close
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from site_nine.core.database import Database
from site_nine.epics.manager import EpicManager
from site_nine.epics.models import Epic
from site_nine.tasks.models import Task

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STATUS_COLOURS: dict[str, str] = {
    "TODO": "white",
    "UNDERWAY": "yellow",
    "COMPLETE": "green",
    "ABORTED": "dim",
}

_PRIORITY_COLOURS: dict[str, str] = {
    "CRITICAL": "red",
    "HIGH": "yellow",
    "MEDIUM": "white",
    "LOW": "dim",
}

_STATUS_SYMBOLS: dict[str, str] = {
    "TODO": "○",
    "UNDERWAY": "●",
    "COMPLETE": "✓",
    "ABORTED": "✗",
}

_TASK_STATUS_SYMBOLS: dict[str, str] = {
    "TODO": "□",
    "UNDERWAY": "◉",
    "COMPLETE": "✓",
    "ABORTED": "✗",
}


def _truncate(text: str, width: int) -> str:
    """Truncate string to *width* characters, appending '…' if needed."""
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"


def _progress_bar(percent: int, width: int = 20) -> str:
    """Render a simple ASCII progress bar."""
    filled = int(width * percent / 100)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    return f"[{bar}] {percent:3d}%"


# ---------------------------------------------------------------------------
# Full-page view (pushed screen)
# ---------------------------------------------------------------------------


class EpicFullPage(Screen):
    """Full scrollable view of an epic including its task breakdown."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("j", "scroll_down", "Scroll down", show=False),
        Binding("k", "scroll_up", "Scroll up", show=False),
        Binding("d", "scroll_page_down", "Page down", show=False),
        Binding("u", "scroll_page_up", "Page up", show=False),
        Binding("g", "scroll_home", "Top", show=False),
        Binding("G", "scroll_end", "Bottom", show=False),
    ]

    def __init__(self, epic: Epic, subtasks: list[Task], db: Database) -> None:
        super().__init__()
        self._epic = epic
        self._subtasks = subtasks
        self._db = db

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        status_col = _STATUS_COLOURS.get(self._epic.status or "TODO", "white")
        title = (
            f"[ESC]  {self._epic.id}: {self._epic.title}  "
            f"[{status_col}]{self._epic.status or 'TODO'}[/{status_col}]  "
            f"{self._epic.priority}"
        )
        yield Static(title, id="fullpage-title", classes="fullpage-title", markup=True)
        with ScrollableContainer(id="fullpage-scroll"):
            yield Static(self._build_content(), id="fullpage-body", markup=True)
        yield Footer()

    def _build_content(self) -> str:
        epic = self._epic
        lines: list[str] = []

        # Progress
        if epic.subtask_count:
            completed = epic.completed_count or 0
            bar = _progress_bar(epic.progress_percent)
            lines.append(f"[bold]Progress:[/bold] {completed}/{epic.subtask_count} tasks complete")
            lines.append(bar)
            lines.append("")

        # Description
        if epic.description:
            lines.append("[bold]Description:[/bold]")
            lines.append(epic.description)
            lines.append("")

        if epic.status_details:
            lines.append(f"[bold]Status Notes:[/bold] {epic.status_details}")
            lines.append("")

        # Timestamps
        lines.append(
            f"[dim]Created: {epic.created_at.format('YYYY-MM-DD HH:mm')}  "
            f"Updated: {epic.updated_at.format('YYYY-MM-DD HH:mm')}[/dim]"
        )
        lines.append("")

        # Task breakdown
        if self._subtasks:
            lines.append("[bold]Subtasks:[/bold]")
            lines.append("")
            for task in self._subtasks:
                sym = _TASK_STATUS_SYMBOLS.get(task.status, "□")
                priority_col = _PRIORITY_COLOURS.get(task.priority, "white")
                status_col = _STATUS_COLOURS.get(task.status, "white")
                lines.append(
                    f"  [{status_col}]{sym}[/{status_col}] "
                    f"[bold]{task.id}[/bold]  "
                    f"[{priority_col}]{task.priority}[/{priority_col}]  "
                    f"[{status_col}]{task.status}[/{status_col}]  "
                    f"{task.role}"
                )
                lines.append(f"     {_truncate(task.title, 80)}")
                lines.append("")
        else:
            lines.append("[dim]No subtasks linked to this epic.[/dim]")

        # Try to read the epic file for additional notes/goals sections
        epic_file = Path(epic.file_path)
        if epic_file.exists():
            try:
                content = epic_file.read_text()
                # Extract sections below the auto-generated header
                section_lines = content.split("\n")
                in_section = False
                section_text: list[str] = []
                for line in section_lines:
                    if line.startswith("## ") and line not in ("## Progress", "## Subtasks", "## Related Architecture"):
                        in_section = True
                    if in_section:
                        section_text.append(line)
                if section_text:
                    lines.append("")
                    lines.append("[bold]Epic Notes:[/bold]")
                    lines.append("")
                    # Render without markup to avoid injection
                    for line in section_text:
                        lines.append(line.replace("[", "\\["))
            except OSError:
                pass

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
# Epics screen
# ---------------------------------------------------------------------------


class EpicsScreen(Screen):
    """
    Epics screen — epic list with progress and task breakdown.

    List view columns: ID, Title, Status, Priority, Progress
    Preview pane: epic description + task list with status indicators
    Full-page view: all epic fields + complete task breakdown + file sections

    Keybindings:
        j / down    Move selection down
        k / up      Move selection up
        Enter       Open full-page view
        Escape      Pop this screen
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("up", "cursor_up", "Up", show=False),
        Binding("enter", "open_fullpage", "Open"),
        Binding("escape", "app.pop_screen", "Back"),
        Binding("7", "app.switch_screen('epics')", "Epics", show=False),
    ]

    def __init__(self, db: Database) -> None:
        super().__init__()
        self._db = db
        self._manager = EpicManager(db)
        self._epics: list[Epic] = []

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="epics-body"):
            with Vertical(id="sidebar", classes="sidebar"):
                yield Static("7 Epics", classes="sidebar-active")
            with Vertical(id="content-area"):
                yield DataTable(id="epics-table", show_cursor=True, zebra_stripes=True)
                with ScrollableContainer(id="preview-pane", classes="preview-pane"):
                    yield Static("", id="preview-text", markup=True)
        yield Footer()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        self._load_data()
        self._populate_table()

    def _load_data(self) -> None:
        """Load epics from the database."""
        try:
            self._epics = self._manager.list_epics()
        except Exception as exc:  # noqa: BLE001
            self._epics = []
            self._set_preview(f"[red]Error loading epics: {exc}[/red]")

    def _populate_table(self) -> None:
        """Populate the DataTable with epic data."""
        table = self.query_one("#epics-table", DataTable)
        table.clear(columns=True)
        table.add_columns("ID", "Title", "Status", "Priority", "Progress")

        for epic in self._epics:
            status = epic.status or "TODO"
            status_col = _STATUS_COLOURS.get(status, "white")
            priority_col = _PRIORITY_COLOURS.get(epic.priority, "white")
            sym = _STATUS_SYMBOLS.get(status, "○")

            if epic.subtask_count:
                progress = f"{epic.completed_count or 0}/{epic.subtask_count} ({epic.progress_percent}%)"
            else:
                progress = "[dim]no tasks[/dim]"

            table.add_row(
                epic.id,
                _truncate(epic.title, 45),
                f"[{status_col}]{sym} {status}[/{status_col}]",
                f"[{priority_col}]{epic.priority}[/{priority_col}]",
                progress,
                key=epic.id,
            )

        if not self._epics:
            self._set_preview("[dim]No epics found.[/dim]")
        else:
            table.move_cursor(row=0)
            self._refresh_preview()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:  # noqa: ARG002
        self._refresh_preview()

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def _refresh_preview(self) -> None:
        """Update preview pane with details of the selected epic."""
        table = self.query_one("#epics-table", DataTable)
        if table.row_count == 0:
            return
        try:
            epic_id = str(table.get_row_at(table.cursor_row)[0])
        except Exception:  # noqa: BLE001
            return
        self._show_preview_for(epic_id)

    def _show_preview_for(self, epic_id: str) -> None:
        """Render a preview of the selected epic."""
        epic = next((e for e in self._epics if e.id == epic_id), None)
        if epic is None:
            self._set_preview(f"[dim]{epic_id} not found.[/dim]")
            return

        status = epic.status or "TODO"
        status_col = _STATUS_COLOURS.get(status, "white")
        priority_col = _PRIORITY_COLOURS.get(epic.priority, "white")

        lines: list[str] = [
            f"[bold]{epic.id}[/bold]  "
            f"[{status_col}]{status}[/{status_col}]  "
            f"[{priority_col}]{epic.priority}[/{priority_col}]",
            f"[bold]{epic.title}[/bold]",
            "",
        ]

        # Progress bar
        if epic.subtask_count:
            completed = epic.completed_count or 0
            bar = _progress_bar(epic.progress_percent, width=30)
            lines.append(f"{bar}  {completed}/{epic.subtask_count} tasks")
            lines.append("")

        # Description snippet
        if epic.description:
            desc_lines = epic.description.splitlines()[:4]
            lines.extend(desc_lines)
            if len(epic.description.splitlines()) > 4:
                lines.append("[dim]...[/dim]")
            lines.append("")

        # Recent subtasks
        try:
            subtasks = self._manager.get_subtasks(epic_id)
            if subtasks:
                lines.append("[bold]Tasks:[/bold]")
                for task in subtasks[:8]:
                    sym = _TASK_STATUS_SYMBOLS.get(task.status, "□")
                    status_col_t = _STATUS_COLOURS.get(task.status, "white")
                    lines.append(
                        f"  [{status_col_t}]{sym}[/{status_col_t}] "
                        f"{task.id}  [{status_col_t}]{task.status}[/{status_col_t}]  "
                        f"{_truncate(task.title, 40)}"
                    )
                if len(subtasks) > 8:
                    lines.append(f"  [dim]...and {len(subtasks) - 8} more[/dim]")
        except Exception as exc:  # noqa: BLE001
            lines.append(f"[red]Error loading subtasks: {exc}[/red]")

        self._set_preview("\n".join(lines))

    def _set_preview(self, markup: str) -> None:
        self.query_one("#preview-text", Static).update(markup)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_cursor_down(self) -> None:
        self.query_one("#epics-table", DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#epics-table", DataTable).action_cursor_up()

    def action_open_fullpage(self) -> None:
        """Push the full-page epic view."""
        table = self.query_one("#epics-table", DataTable)
        if table.row_count == 0:
            return
        try:
            epic_id = str(table.get_row_at(table.cursor_row)[0])
        except Exception:  # noqa: BLE001
            return

        epic = next((e for e in self._epics if e.id == epic_id), None)
        if epic is None:
            return

        try:
            subtasks = self._manager.get_subtasks(epic_id)
        except Exception:  # noqa: BLE001
            subtasks = []

        self.app.push_screen(EpicFullPage(epic, subtasks, self._db))
