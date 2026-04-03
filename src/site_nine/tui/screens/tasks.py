"""TasksScreen — Task queue viewer for the Site-Nine TUI.

Layout:
  - List pane: table of tasks (id, title, role, priority, status, mission if claimed)
  - Preview pane: full title, description snippet, notes, epic link, claimed_by mission
  - Full-page view: all task fields + description + notes scrollable
  - Color-coded rows by priority (CRITICAL=red, HIGH=yellow, MEDIUM=default, LOW=dim)
  - Filter bar: by status (TODO/UNDERWAY/COMPLETE), by role, by priority
  - Keybindings: j/k or up/down, Enter for full page, Escape to close, / to filter
"""

from __future__ import annotations

from typing import ClassVar

import pendulum
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, Static

from site_nine.core.database import Database
from site_nine.tasks.manager import TaskManager
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

_PRIORITY_SYMBOLS: dict[str, str] = {
    "CRITICAL": "!!",
    "HIGH": "! ",
    "MEDIUM": "  ",
    "LOW": "  ",
}

_FILTER_STATUSES = ["(all)", "TODO", "UNDERWAY", "COMPLETE", "ABORTED"]
_FILTER_PRIORITIES = ["(all)", "CRITICAL", "HIGH", "MEDIUM", "LOW"]


def _truncate(text: str, width: int) -> str:
    """Truncate string to *width* characters, appending '…' if needed."""
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"


def _age(dt: pendulum.DateTime) -> str:
    """Human-readable age string."""
    now = pendulum.now("UTC")
    diff = now.diff(dt)
    if diff.in_seconds() < 60:
        return "just now"
    if diff.in_minutes() < 60:
        return f"{diff.in_minutes()}m ago"
    if diff.in_hours() < 24:
        return f"{diff.in_hours()}h ago"
    return f"{diff.in_days()}d ago"


# ---------------------------------------------------------------------------
# Full-page view (pushed screen)
# ---------------------------------------------------------------------------


class TaskFullPage(Screen):
    """Full scrollable view of a single task."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("j", "scroll_down", "Scroll down", show=False),
        Binding("k", "scroll_up", "Scroll up", show=False),
        Binding("d", "scroll_page_down", "Page down", show=False),
        Binding("u", "scroll_page_up", "Page up", show=False),
        Binding("g", "scroll_home", "Top", show=False),
        Binding("G", "scroll_end", "Bottom", show=False),
    ]

    def __init__(self, task: Task, db: Database) -> None:
        super().__init__()
        self._site_task = task
        self._site_db = db

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        task = self._site_task
        status_col = _STATUS_COLOURS.get(task.status.value, "white")
        priority_col = _PRIORITY_COLOURS.get(task.priority, "white")
        title = (
            f"[ESC]  {task.id}  "
            f"[{priority_col}]{task.priority}[/{priority_col}]  "
            f"[{status_col}]{task.status.value}[/{status_col}]  "
            f"[bold]{_truncate(task.title, 60)}[/bold]"
        )
        yield Static(title, id="fullpage-title", classes="fullpage-title", markup=True)
        with ScrollableContainer(id="fullpage-scroll"):
            yield Static(self._build_content(), id="fullpage-body", markup=True)
        yield Footer()

    def _build_content(self) -> str:
        task = self._site_task
        lines: list[str] = []

        # Metadata block
        status_col = _STATUS_COLOURS.get(task.status.value, "white")
        priority_col = _PRIORITY_COLOURS.get(task.priority, "white")

        lines.append(f"[bold]Title:[/bold]    {task.title}")
        lines.append(f"[bold]Role:[/bold]     {task.role}")
        lines.append(f"[bold]Priority:[/bold] [{priority_col}]{task.priority}[/{priority_col}]")
        lines.append(f"[bold]Status:[/bold]   [{status_col}]{task.status.value}[/{status_col}]")
        if task.category:
            lines.append(f"[bold]Category:[/bold] {task.category}")
        if task.epic_id:
            lines.append(f"[bold]Epic:[/bold]     {task.epic_id}")
        if task.current_possession_id:
            claimed_str = ""
            if task.claimed_at:
                claimed_str = f"  (claimed {_age(task.claimed_at)})"
            lines.append(f"[bold]Possession:[/bold]  #{task.current_possession_id}{claimed_str}")
        lines.append(
            f"[dim]Created: {task.created_at.format('YYYY-MM-DD HH:mm')}  "
            f"Updated: {task.updated_at.format('YYYY-MM-DD HH:mm')}[/dim]"
        )
        if task.closed_at:
            lines.append(f"[dim]Closed: {task.closed_at.format('YYYY-MM-DD HH:mm')}[/dim]")
        lines.append("")

        # Description
        if task.description:
            lines.append("[bold]Description:[/bold]")
            lines.append("")
            for line in task.description.splitlines():
                lines.append(line.replace("[", "\\["))
            lines.append("")

        # Notes
        if task.notes:
            lines.append("[bold]Notes:[/bold]")
            lines.append("")
            for line in task.notes.splitlines():
                lines.append(line.replace("[", "\\["))
            lines.append("")

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
# Tasks screen
# ---------------------------------------------------------------------------


class TasksScreen(Screen):
    """
    Tasks screen — task queue with priority-colour-coded rows and filters.

    List view columns: ID, Title, Role, Priority, Status, Mission
    Preview pane: full title, description snippet, notes, epic, claimed mission
    Full-page view: all task fields + description + notes

    Keybindings:
        j / down    Move selection down
        k / up      Move selection up
        Enter       Open full-page view
        Escape      Pop this screen
        /           Focus filter input
        s           Cycle status filter
        p           Cycle priority filter
        r           Reset all filters
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("j", "cursor_down", "Down", show=False, priority=True),
        Binding("k", "cursor_up", "Up", show=False, priority=True),
        Binding("down", "cursor_down", "Down", show=False, priority=True),
        Binding("up", "cursor_up", "Up", show=False, priority=True),
        Binding("enter", "open_fullpage", "Open", priority=True),
        Binding("escape", "app.pop_screen", "Back", priority=True),
        Binding("/", "focus_filter", "Filter", show=True, priority=True),
        Binding("s", "cycle_status", "Status filter", show=False, priority=True),
        Binding("p", "cycle_priority", "Priority filter", show=False, priority=True),
        Binding("r", "reset_filters", "Reset", show=False, priority=True),
        Binding("3", "app.switch_screen('tasks')", "Tasks", show=False),
    ]

    # Active filter state
    filter_status: reactive[str] = reactive("(all)")
    filter_priority: reactive[str] = reactive("(all)")
    filter_role: reactive[str] = reactive("(all)")

    def __init__(self, db: Database) -> None:
        super().__init__()
        self._db = db
        self._manager = TaskManager(db)
        self._all_tasks: list[Task] = []
        self._filtered_tasks: list[Task] = []

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="tasks-body"):
            with Vertical(id="sidebar", classes="sidebar"):
                yield Static("3 Tasks", classes="sidebar-active")
            with Vertical(id="content-area"):
                yield Static(self._filter_label(), id="filter-label", classes="subview-label", markup=True)
                yield Input(
                    placeholder="Filter by role (Enter to apply, Esc to cancel)",
                    id="role-filter-input",
                    classes="filter-input",
                )
                yield DataTable(id="tasks-table", show_cursor=True, zebra_stripes=True)
                with ScrollableContainer(id="preview-pane", classes="preview-pane"):
                    yield Static("", id="preview-text", markup=True)
        yield Footer()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        # Hide the filter input by default
        self.query_one("#role-filter-input", Input).display = False
        self._load_data()
        self._populate_table()

    def _load_data(self) -> None:
        """Load all tasks from the database."""
        try:
            self._all_tasks = self._manager.list_tasks()
        except Exception as exc:  # noqa: BLE001
            self._all_tasks = []
            self._set_preview(f"[red]Error loading tasks: {exc}[/red]")

    def _apply_filters(self) -> list[Task]:
        """Return tasks filtered by current filter state."""
        result = self._all_tasks
        if self.filter_status != "(all)":
            result = [t for t in result if t.status.value == self.filter_status]
        if self.filter_priority != "(all)":
            result = [t for t in result if t.priority == self.filter_priority]
        if self.filter_role != "(all)":
            role_lower = self.filter_role.lower()
            result = [t for t in result if t.role.lower().startswith(role_lower)]
        return result

    def _populate_table(self) -> None:
        """Populate the DataTable with filtered task data."""
        # Guard: DOM may not be composed yet (reactive watchers fire early)
        tables = self.query("#tasks-table")
        if not tables:
            return
        self._filtered_tasks = self._apply_filters()
        table = self.query_one("#tasks-table", DataTable)
        table.clear(columns=True)
        table.add_columns("ID", "Title", "Role", "Priority", "Status", "Mission")

        for task in self._filtered_tasks:
            status_val = task.status.value
            status_col = _STATUS_COLOURS.get(status_val, "white")
            priority_col = _PRIORITY_COLOURS.get(task.priority, "white")
            sym = _STATUS_SYMBOLS.get(status_val, "○")
            mission_cell = f"#{task.current_possession_id}" if task.current_possession_id else "[dim]-[/dim]"

            table.add_row(
                task.id,
                _truncate(task.title, 42),
                task.role,
                f"[{priority_col}]{task.priority}[/{priority_col}]",
                f"[{status_col}]{sym} {status_val}[/{status_col}]",
                mission_cell,
                key=task.id,
            )

        # Update filter label
        self.query_one("#filter-label", Static).update(self._filter_label())

        if not self._filtered_tasks:
            self._set_preview("[dim]No tasks match the current filters.[/dim]")
        else:
            table.move_cursor(row=0)
            self._refresh_preview()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:  # noqa: ARG002
        self._refresh_preview()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Apply role filter when Enter is pressed in the filter input."""
        role_value = event.value.strip()
        self.filter_role = role_value if role_value else "(all)"
        input_widget = self.query_one("#role-filter-input", Input)
        input_widget.display = False
        self.query_one("#tasks-table", DataTable).focus()
        self._populate_table()

    def on_input_key(self, event) -> None:  # type: ignore[override]
        """Hide filter input on Escape."""
        if hasattr(event, "key") and event.key == "escape":
            input_widget = self.query_one("#role-filter-input", Input)
            if input_widget.display:
                input_widget.display = False
                self.query_one("#tasks-table", DataTable).focus()

    # ------------------------------------------------------------------
    # Reactive watchers
    # ------------------------------------------------------------------

    def watch_filter_status(self, _: str) -> None:
        if self.is_attached:
            self._populate_table()

    def watch_filter_priority(self, _: str) -> None:
        if self.is_attached:
            self._populate_table()

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def _refresh_preview(self) -> None:
        """Update preview pane for the currently selected task."""
        table = self.query_one("#tasks-table", DataTable)
        if table.row_count == 0:
            return
        try:
            task_id = str(table.get_row_at(table.cursor_row)[0])
        except Exception:  # noqa: BLE001
            return
        self._show_preview_for(task_id)

    def _show_preview_for(self, task_id: str) -> None:
        """Render a preview for the selected task."""
        task = next((t for t in self._filtered_tasks if t.id == task_id), None)
        if task is None:
            self._set_preview(f"[dim]{task_id} not found.[/dim]")
            return

        status_val = task.status.value
        status_col = _STATUS_COLOURS.get(status_val, "white")
        priority_col = _PRIORITY_COLOURS.get(task.priority, "white")

        lines: list[str] = [
            f"[bold]{task.id}[/bold]  "
            f"[{priority_col}]{task.priority}[/{priority_col}]  "
            f"[{status_col}]{status_val}[/{status_col}]  "
            f"{task.role}",
            f"[bold]{task.title}[/bold]",
            "",
        ]

        if task.epic_id:
            lines.append(f"[dim]Epic:[/dim] {task.epic_id}")

        if task.current_possession_id:
            claimed_str = ""
            if task.claimed_at:
                claimed_str = f"  ({_age(task.claimed_at)})"
            lines.append(f"[dim]Claimed by:[/dim] #{task.current_possession_id}{claimed_str}")

        if task.category:
            lines.append(f"[dim]Category:[/dim] {task.category}")

        lines.append(f"[dim]Updated {_age(task.updated_at)}[/dim]")
        lines.append("")

        if task.description:
            desc_lines = task.description.splitlines()[:6]
            for line in desc_lines:
                lines.append(line.replace("[", "\\["))
            if len(task.description.splitlines()) > 6:
                lines.append("[dim]...[/dim]")
            lines.append("")

        if task.notes:
            lines.append("[bold]Notes:[/bold]")
            note_lines = task.notes.splitlines()[:3]
            for line in note_lines:
                lines.append(f"  {line.replace('[', chr(92) + '[')}")
            if len(task.notes.splitlines()) > 3:
                lines.append("  [dim]...[/dim]")

        self._set_preview("\n".join(lines))

    def _set_preview(self, markup: str) -> None:
        self.query_one("#preview-text", Static).update(markup)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_cursor_down(self) -> None:
        self.query_one("#tasks-table", DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#tasks-table", DataTable).action_cursor_up()

    def action_open_fullpage(self) -> None:
        """Push full-page view for the selected task."""
        table = self.query_one("#tasks-table", DataTable)
        if table.row_count == 0:
            return
        try:
            task_id = str(table.get_row_at(table.cursor_row)[0])
        except Exception:  # noqa: BLE001
            return

        task = next((t for t in self._filtered_tasks if t.id == task_id), None)
        if task is None:
            return
        self.app.push_screen(TaskFullPage(task, self._db))

    def action_focus_filter(self) -> None:
        """Show and focus the role filter input."""
        input_widget = self.query_one("#role-filter-input", Input)
        input_widget.display = True
        input_widget.focus()

    def action_cycle_status(self) -> None:
        """Cycle through status filter options."""
        current_idx = _FILTER_STATUSES.index(self.filter_status)
        self.filter_status = _FILTER_STATUSES[(current_idx + 1) % len(_FILTER_STATUSES)]

    def action_cycle_priority(self) -> None:
        """Cycle through priority filter options."""
        current_idx = _FILTER_PRIORITIES.index(self.filter_priority)
        self.filter_priority = _FILTER_PRIORITIES[(current_idx + 1) % len(_FILTER_PRIORITIES)]

    def action_reset_filters(self) -> None:
        """Reset all filters."""
        self.filter_status = "(all)"
        self.filter_priority = "(all)"
        self.filter_role = "(all)"
        self.query_one("#role-filter-input", Input).value = ""
        self._populate_table()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _filter_label(self) -> str:
        parts = []
        if self.filter_status != "(all)":
            status_col = _STATUS_COLOURS.get(self.filter_status, "white")
            parts.append(f"status:[{status_col}]{self.filter_status}[/{status_col}]")
        else:
            parts.append("[dim]status:all[/dim]")

        if self.filter_priority != "(all)":
            priority_col = _PRIORITY_COLOURS.get(self.filter_priority, "white")
            parts.append(f"priority:[{priority_col}]{self.filter_priority}[/{priority_col}]")
        else:
            parts.append("[dim]priority:all[/dim]")

        if self.filter_role != "(all)":
            parts.append(f"role:{self.filter_role}")
        else:
            parts.append("[dim]role:all[/dim]")

        count = len(self._filtered_tasks)
        total = len(self._all_tasks)
        count_str = f"[dim]({count}/{total})[/dim]" if count != total else f"[dim]({total})[/dim]"

        return "  ".join(parts) + f"  {count_str}  [dim]s=status  p=priority  /=role  r=reset[/dim]"
