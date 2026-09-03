"""Rich rendering helpers for dashboard views.

These functions produce Rich renderables (Tables, Trees, strings) from
dashboard model objects. They contain no data-fetching logic.
"""

from collections.abc import Callable

import pendulum
from rich.table import Table
from rich.tree import Tree

from site_nine.dashboard.models import (
    DashboardData,
    DashboardStats,
    EpicDashboardData,
    FullDashboardData,
    PossessionEntry,
    RoleDashboardData,
)
from site_nine.epics.models import Epic
from site_nine.possessions.types import PossessionStatus
from site_nine.tasks.models import Task


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

STATUS_COLORS: dict[str, str] = {
    "TODO": "yellow",
    "UNDERWAY": "cyan",
    "COMPLETE": "green",
    "ABORTED": "red",
}

PRIORITY_COLORS: dict[str, str] = {
    "CRITICAL": "red bold",
    "HIGH": "red",
    "MEDIUM": "yellow",
    "LOW": "blue",
}

PRIORITY_ORDER: dict[str, int] = {
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
}

TASK_STATUS_COLORS: dict[str, str] = {
    "TODO": "yellow",
    "UNDERWAY": "cyan bold",
    "COMPLETE": "green",
    "ABORTED": "dim red",
}


def generate_progress_bar(percent: int, width: int = 40) -> str:
    """Generate a text-based progress bar."""
    filled = int(width * percent / 100)
    empty = width - filled
    bar_color = "green" if percent == 100 else "cyan" if percent > 50 else "yellow" if percent > 0 else "dim"
    return f"[{bar_color}]{'█' * filled}{'░' * empty}[/{bar_color}] {percent}%"


# ---------------------------------------------------------------------------
# Epic-specific rendering
# ---------------------------------------------------------------------------


def render_epic_header(epic: Epic) -> list[str]:
    """Return Rich-markup lines describing an epic's header info."""
    status_color = STATUS_COLORS.get(epic.status or "", "white")
    lines = [
        f"[bold]Epic {epic.id}:[/bold] {epic.title}",
        f"[bold]Status:[/bold] [{status_color}]{epic.status}[/{status_color}]",
        f"[bold]Priority:[/bold] {epic.priority}",
    ]

    if epic.subtask_count and epic.subtask_count > 0:
        lines.append(
            f"[bold]Progress:[/bold] {epic.completed_count}/{epic.subtask_count} tasks ({epic.progress_percent}%)"
        )
        lines.append(generate_progress_bar(epic.progress_percent))

    return lines


def render_epic_subtasks_table(subtasks: list[Task]) -> Table:
    """Build the 'Epic Subtasks' table."""
    table = Table(title="Epic Subtasks", show_header=True, title_style="bold magenta")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white", max_width=50)
    table.add_column("Status", style="yellow")
    table.add_column("Role", style="green")
    table.add_column("Priority", style="red")
    table.add_column("Possession", style="blue")

    for task in subtasks:
        table.add_row(
            task.id,
            task.title,
            str(task.status),
            task.role,
            task.priority,
            str(task.current_possession_id) if task.current_possession_id else "",
        )

    return table


def render_available_tasks_tree(
    active_epics: list[Epic],
    available_tasks: list[Task],
    get_subtasks: Callable[[str], list[Task]],
) -> Tree:
    """Render a Rich Tree of available (TODO) tasks grouped under their epics.

    Epics that have at least one TODO subtask appear as branches.  Their node
    label shows ID, task count, priority and title.  Each leaf shows the task
    ID, role, status and title.  Individual tasks not linked to any epic appear
    as root-level leaves.

    Args:
        active_epics: Active epics (TODO / UNDERWAY status).
        available_tasks: Orphan TODO tasks (no epic_id).
        get_subtasks: Callable that returns all subtasks for an epic ID.

    Returns:
        A Rich Tree ready to print.
    """
    root = Tree("[bold cyan]Available Tasks[/bold cyan]")

    sorted_epics = sorted(
        active_epics,
        key=lambda e: (PRIORITY_ORDER.get(e.priority, 99), e.id),
    )

    for epic in sorted_epics:
        subtasks = [t for t in get_subtasks(epic.id) if t.status.value == "TODO"]
        if not subtasks:
            continue

        subtasks.sort(key=lambda t: (PRIORITY_ORDER.get(t.priority, 99), t.id))

        priority_color = PRIORITY_COLORS.get(epic.priority, "white")
        status_color = STATUS_COLORS.get(epic.status or "", "white")
        child_count = len(subtasks)
        epic_label = (
            f"[cyan]{epic.id}[/cyan]  "
            f"[dim]{child_count} task{'s' if child_count != 1 else ''}[/dim]  "
            f"[{status_color}]{epic.status}[/{status_color}]  "
            f"[{priority_color}]{epic.priority}[/{priority_color}]  "
            f"[white]{epic.title}[/white]"
        )
        branch = root.add(epic_label)

        max_shown = 10
        for task in subtasks[:max_shown]:
            task_status_color = TASK_STATUS_COLORS.get(task.status.value, "white")
            role_str = f"[green]{task.role}[/green]" if task.role else "[dim]—[/dim]"
            leaf_label = (
                f"[cyan]{task.id}[/cyan]  "
                f"{role_str}  "
                f"[{task_status_color}]{task.status}[/{task_status_color}]  "
                f"[white]{task.title}[/white]"
            )
            branch.add(leaf_label)
        if len(subtasks) > max_shown:
            branch.add(f"[dim italic]... and {len(subtasks) - max_shown} more tasks[/dim italic]")

    # Orphan TODO tasks — root-level leaves
    sorted_orphans = sorted(
        available_tasks,
        key=lambda t: (PRIORITY_ORDER.get(t.priority, 99), t.id),
    )
    for task in sorted_orphans:
        task_status_color = TASK_STATUS_COLORS.get(task.status.value, "white")
        role_str = f"[green]{task.role}[/green]" if task.role else "[dim]—[/dim]"
        leaf_label = (
            f"[cyan]{task.id}[/cyan]  "
            f"{role_str}  "
            f"[{task_status_color}]{task.status}[/{task_status_color}]  "
            f"[white]{task.title}[/white]"
        )
        root.add(leaf_label)

    return root


def render_underway_tasks_tree(
    active_epics: list[Epic],
    orphan_underway: list[Task],
    get_subtasks: Callable[[str], list[Task]],
    possession_entries: list["PossessionEntry"],
) -> Tree:
    """Render a Rich Tree of underway tasks grouped under their epics.

    Epics appear only when they have at least one UNDERWAY subtask.  Each leaf
    shows the task ID, assigned daemon (if any), role, status and title.
    Orphan UNDERWAY tasks (no epic) appear as root-level leaves.

    Args:
        active_epics: Active epics (TODO / UNDERWAY status).
        orphan_underway: Orphan UNDERWAY tasks (no epic_id).
        get_subtasks: Callable that returns all subtasks for an epic ID.
        possession_entries: Active possessions used to resolve daemon names.

    Returns:
        A Rich Tree ready to print.
    """
    daemon_by_possession: dict[int, str] = {
        pe.possession.id: pe.possession.daemon_name for pe in possession_entries if pe.possession.id is not None
    }

    root = Tree("[bold yellow]Underway Tasks[/bold yellow]")

    sorted_epics = sorted(
        active_epics,
        key=lambda e: (PRIORITY_ORDER.get(e.priority, 99), e.id),
    )

    for epic in sorted_epics:
        subtasks = get_subtasks(epic.id)
        underway = [t for t in subtasks if t.status.value == "UNDERWAY"]
        if not underway:
            continue

        underway.sort(key=lambda t: (PRIORITY_ORDER.get(t.priority, 99), t.id))

        priority_color = PRIORITY_COLORS.get(epic.priority, "white")
        status_color = STATUS_COLORS.get(epic.status or "", "white")
        child_count = len(underway)
        epic_label = (
            f"[cyan]{epic.id}[/cyan]  "
            f"[dim]{child_count} task{'s' if child_count != 1 else ''}[/dim]  "
            f"[{status_color}]{epic.status}[/{status_color}]  "
            f"[{priority_color}]{epic.priority}[/{priority_color}]  "
            f"[white]{epic.title}[/white]"
        )
        branch = root.add(epic_label)

        for task in underway:
            daemon_name = daemon_by_possession.get(task.current_possession_id) if task.current_possession_id else None
            daemon_str = f"[magenta]{daemon_name}[/magenta]" if daemon_name else "[dim]unassigned[/dim]"
            role_str = f"[green]{task.role}[/green]" if task.role else "[dim]—[/dim]"
            leaf_label = (
                f"[cyan]{task.id}[/cyan]  "
                f"{daemon_str}  "
                f"{role_str}  "
                f"[yellow bold]{task.status}[/yellow bold]  "
                f"[white]{task.title}[/white]"
            )
            branch.add(leaf_label)

    # Orphan UNDERWAY tasks — root-level leaves
    sorted_orphans = sorted(
        orphan_underway,
        key=lambda t: (PRIORITY_ORDER.get(t.priority, 99), t.id),
    )
    for task in sorted_orphans:
        daemon_name = daemon_by_possession.get(task.current_possession_id) if task.current_possession_id else None
        daemon_str = f"[magenta]{daemon_name}[/magenta]" if daemon_name else "[dim]unassigned[/dim]"
        role_str = f"[green]{task.role}[/green]" if task.role else "[dim]—[/dim]"
        leaf_label = (
            f"[cyan]{task.id}[/cyan]  "
            f"{daemon_str}  "
            f"{role_str}  "
            f"[yellow bold]{task.status}[/yellow bold]  "
            f"[white]{task.title}[/white]"
        )
        root.add(leaf_label)

    return root


def render_epic_tables(
    active_epics: list[Epic],
    get_subtasks: Callable[[str], list[Task]],
) -> list[Table | str]:
    """
    Render each active epic as a separate table with subtasks.

    Args:
        active_epics: List of active epics (already filtered to TODO/UNDERWAY).
        get_subtasks: Callable that takes an epic_id and returns list[Task].

    Returns:
        A list of Rich Tables (one per epic), or an empty list if there are no active epics.
    """
    if not active_epics:
        return []

    # Sort by priority
    sorted_epics = sorted(
        active_epics,
        key=lambda e: (PRIORITY_ORDER.get(e.priority, 99), e.id),
    )

    tables: list[Table | str] = []

    for epic_obj in sorted_epics[:5]:
        status_color = STATUS_COLORS.get(epic_obj.status or "", "white")
        priority_color = PRIORITY_COLORS.get(epic_obj.priority, "white")

        if epic_obj.subtask_count and epic_obj.subtask_count > 0:
            progress_text = f"{epic_obj.completed_count}/{epic_obj.subtask_count}"
        else:
            progress_text = "0/0"

        epic_title = (
            f"[cyan]{epic_obj.id}[/cyan] "
            f"[white]{epic_obj.title}[/white]  "
            f"[{status_color}]{epic_obj.status}[/{status_color}] "
            f"[{priority_color}]{epic_obj.priority}[/{priority_color}] "
            f"[dim]\\[{progress_text}][/dim]"
        )

        subtasks = [t for t in get_subtasks(epic_obj.id) if t.status.value in ("TODO", "UNDERWAY")]

        if not subtasks:
            continue

        status_priority = {
            "UNDERWAY": 0,
            "TODO": 1,
        }
        subtasks.sort(
            key=lambda t: (
                status_priority.get(t.status.value, 99),
                PRIORITY_ORDER.get(t.priority, 99),
                t.id,
            ),
        )

        table = Table(
            title=epic_title,
            show_header=True,
            title_style="bold",
            title_justify="left",
        )
        table.add_column("ID", style="cyan", width=12, no_wrap=True)
        table.add_column("Role", style="green", width=14, no_wrap=True)
        table.add_column("Status", width=10, no_wrap=True)
        table.add_column("Title", style="white", ratio=1)
        table.add_column("Possession", style="blue", width=8, no_wrap=True)

        for task in subtasks[:10]:
            task_status_color = TASK_STATUS_COLORS.get(task.status.value, "white")

            table.add_row(
                task.id,
                task.role or "",
                f"[{task_status_color}]{task.status}[/{task_status_color}]",
                task.title[:60],
                f"@{task.current_possession_id}" if task.current_possession_id else "",
            )

        if len(subtasks) > 10:
            table.add_row("", "", "", f"[dim italic]... and {len(subtasks) - 10} more tasks[/dim italic]", "")

        tables.append(table)

    return tables


# ---------------------------------------------------------------------------
# Full dashboard rendering
# ---------------------------------------------------------------------------


def render_available_tasks_table(tasks: list[Task], *, max_rows: int = 10) -> Table:
    """Build the 'Available Individual Tasks' table."""
    table = Table(
        title="Available Individual Tasks",
        show_header=True,
        title_style="bold magenta",
        title_justify="left",
    )
    table.add_column("ID", style="cyan", width=12)
    table.add_column("Priority", style="red", width=10)
    table.add_column("Role", style="green", width=14)
    table.add_column("Status", style="yellow", width=10)
    table.add_column("Title", style="white")

    sorted_tasks = sorted(
        tasks,
        key=lambda t: (PRIORITY_ORDER.get(t.priority, 99), t.role or "", t.id),
    )

    for task in sorted_tasks[:max_rows]:
        table.add_row(
            task.id,
            task.priority,
            task.role or "",
            str(task.status),
            task.title,
        )

    return table


POSSESSION_STATUS_COLORS: dict[str, str] = {
    "ACTIVE": "green",
    "SUSPENDED": "yellow",
    "EXORCISED": "dim",
    "ROLE_PENDING": "cyan",
    "DAEMON_PENDING": "cyan",
}


def _human_friendly_age(start_time: str | None) -> str:
    """Convert possession start_time ISO timestamp into a human-friendly age string."""
    if not start_time:
        return "unknown"
    try:
        start_dt = pendulum.parse(start_time)
        now = pendulum.now("UTC")
        diff = now - start_dt  # type: ignore[operator]
        total_seconds = int(diff.total_seconds())  # type: ignore[union-attr]

        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60

        if days > 0:
            return f"{days}d ago"
        elif hours > 0:
            return f"{hours}h ago"
        elif minutes > 0:
            return f"{minutes}m ago"
        else:
            return "just now"
    except Exception:
        return start_time or "unknown"


def render_open_missions_table(possession_entries: list[PossessionEntry]) -> Table:
    """Build the 'Active Possessions' table."""
    table = Table(
        title="Active Possessions",
        show_header=True,
        title_style="bold green",
        title_justify="left",
    )
    table.add_column("Daemon", style="magenta")
    table.add_column("Role", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Age", style="blue")

    if possession_entries:
        for pe in possession_entries:
            p = pe.possession
            status_color = POSSESSION_STATUS_COLORS.get(p.status.value, "white")
            status_display = f"[{status_color}]{p.status.value}[/{status_color}]"
            age_display = _human_friendly_age(p.start_time)
            table.add_row(
                p.daemon_name,
                p.role,
                status_display,
                age_display,
            )
    else:
        table.add_row("[dim]No active possessions[/dim]", "", "", "")

    return table


def render_stats_table(stats: DashboardStats) -> Table:
    """Build the 'Quick Stats' table."""
    table = Table(
        title="Quick Stats",
        show_header=True,
        title_style="bold cyan",
        title_justify="left",
    )
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right", style="bold")

    table.add_row("Active possessions", str(stats.active_possessions))
    table.add_row("Active daemons", f"[magenta]{stats.active_daemons}[/magenta]")
    table.add_row("Total tasks", str(stats.total_tasks))
    table.add_row("In progress", f"[yellow]{stats.in_progress}[/yellow]")
    table.add_row("Completed", f"[green]{stats.completed}[/green]")
    if stats.blocked_by_reviews > 0:
        table.add_row("Blocked by reviews", f"[red]{stats.blocked_by_reviews}[/red]")

    return table


def render_messaging_stats_table(stats: DashboardStats) -> list[str | Table]:
    """Build the 'Agent Communication (last 24h)' table and hint line."""
    table = Table(
        title="Agent Communication (last 24h)",
        show_header=True,
        title_style="bold magenta",
        title_justify="left",
    )
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right", style="bold")

    table.add_row("Active conversations", str(stats.active_conversations))
    table.add_row("Open discussions", str(stats.open_discussions))
    table.add_row("Messages sent", str(stats.messages_sent_24h))
    table.add_row("Unread messages (all agents)", str(stats.unread_messages))

    items: list[str | Table] = [table]
    items.append("[dim]💡 View details: s9 comms inbox[/dim]")
    return items


# ---------------------------------------------------------------------------
# Role dashboard rendering
# ---------------------------------------------------------------------------


def render_role_tasks_table(role: str, tasks: list[Task], *, max_rows: int = 10) -> Table:
    """Build the role-filtered available tasks table."""
    table = Table(
        title=f"Available Tasks - {role} Role",
        show_header=True,
        title_style="bold blue",
    )
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="magenta", max_width=40)
    table.add_column("Status", style="yellow")
    table.add_column("Priority", style="red")
    table.add_column("Possession", style="blue")
    table.add_column("Epic", style="magenta")

    for task in tasks[:max_rows]:
        table.add_row(
            task.id,
            task.title,
            str(task.status),
            task.priority,
            str(task.current_possession_id) if task.current_possession_id else "",
            task.epic_id or "",
        )

    return table


# ---------------------------------------------------------------------------
# JSON serialisation helpers
# ---------------------------------------------------------------------------


def full_dashboard_to_json(data: FullDashboardData) -> dict:
    """Convert FullDashboardData to a JSON-serialisable dict."""
    return {
        "active_epics": [
            {
                "id": e.id,
                "title": e.title,
                "status": e.status,
                "priority": e.priority,
                "progress_percent": e.progress_percent,
                "completed_count": e.completed_count,
                "subtask_count": e.subtask_count,
            }
            for e in data.active_epics
        ],
        "available_tasks": [
            {
                "id": t.id,
                "title": t.title,
                "status": str(t.status),
                "priority": t.priority,
                "role": t.role,
            }
            for t in data.available_tasks
        ],
        "active_possessions": [
            {
                "id": pe.possession.id,
                "daemon_name": pe.possession.daemon_name,
                "role": pe.possession.role,
                "status": pe.possession.status.value,
                "start_time": pe.possession.start_time,
            }
            for pe in data.possession_entries
        ],
        "stats": {
            "active_possessions": data.stats.active_possessions,
            "active_daemons": data.stats.active_daemons,
            "total_tasks": data.stats.total_tasks,
            "in_progress": data.stats.in_progress,
            "completed": data.stats.completed,
            "blocked_by_reviews": data.stats.blocked_by_reviews,
            "active_conversations": data.stats.active_conversations,
            "open_discussions": data.stats.open_discussions,
            "messages_sent_24h": data.stats.messages_sent_24h,
            "unread_messages": data.stats.unread_messages,
        },
    }


def role_dashboard_to_json(data: RoleDashboardData) -> dict:
    """Convert RoleDashboardData to a JSON-serialisable dict."""
    return {
        "role": data.role,
        "available_tasks": [
            {
                "id": t.id,
                "title": t.title,
                "status": str(t.status),
                "priority": t.priority,
                "current_possession_id": t.current_possession_id,
            }
            for t in data.available_tasks
        ],
    }


def epic_dashboard_to_json(data: EpicDashboardData) -> dict:
    """Convert EpicDashboardData to a JSON-serialisable dict."""
    return {
        "epic": {
            "id": data.epic.id,
            "title": data.epic.title,
            "status": data.epic.status,
            "priority": data.epic.priority,
            "progress_percent": data.epic.progress_percent,
            "completed_count": data.epic.completed_count,
            "subtask_count": data.epic.subtask_count,
        },
        "subtasks": [
            {
                "id": t.id,
                "title": t.title,
                "status": str(t.status),
                "priority": t.priority,
                "role": t.role,
                "current_possession_id": t.current_possession_id,
            }
            for t in data.subtasks
        ],
    }


# ---------------------------------------------------------------------------
# Dispatch helpers — single entry points for the CLI layer
# ---------------------------------------------------------------------------


def dashboard_to_json(data: DashboardData) -> dict:
    """Convert any dashboard data variant to a JSON-serialisable dict."""
    if isinstance(data, EpicDashboardData):
        return epic_dashboard_to_json(data)
    elif isinstance(data, RoleDashboardData):
        return role_dashboard_to_json(data)
    else:
        return full_dashboard_to_json(data)


def render_dashboard(
    data: DashboardData,
    get_subtasks: Callable[[str], list[Task]],
) -> list[str | Table | Tree]:
    """
    Render any dashboard data variant into a list of Rich renderables.

    Args:
        data: The dashboard data to render.
        get_subtasks: Callable used by the epic tree to fetch subtasks per epic.

    Returns:
        Ordered list of Rich-markup strings, Tables, and Trees.
    """
    if isinstance(data, EpicDashboardData):
        return _render_epic_dashboard(data)
    elif isinstance(data, RoleDashboardData):
        return _render_role_dashboard(data)
    else:
        return _render_full_dashboard(data, get_subtasks)


def _render_epic_dashboard(data: EpicDashboardData) -> list[str | Table | Tree]:
    items: list[str | Table | Tree] = list(render_epic_header(data.epic))
    if data.subtasks:
        items.append(render_epic_subtasks_table(data.subtasks))
    else:
        items.append("[yellow]No tasks linked to this epic[/yellow]")
    return items


def _render_role_dashboard(data: RoleDashboardData) -> list[str | Table | Tree]:
    if data.available_tasks:
        return [render_role_tasks_table(data.role, data.available_tasks)]
    return [f"[yellow]No available tasks for {data.role} role[/yellow]"]


def _render_full_dashboard(
    data: FullDashboardData,
    get_subtasks: Callable[[str], list[Task]],
) -> list[str | Table | Tree]:
    items: list[str | Table | Tree] = []

    # Split orphan tasks by status
    orphan_todo = [t for t in data.available_tasks if t.status.value == "TODO"]
    orphan_underway = [t for t in data.available_tasks if t.status.value == "UNDERWAY"]

    # Cache subtask lookups shared across both trees
    _subtask_cache: dict[str, list[Task]] = {}

    def _cached_subtasks(epic_id: str) -> list[Task]:
        if epic_id not in _subtask_cache:
            _subtask_cache[epic_id] = get_subtasks(epic_id)
        return _subtask_cache[epic_id]

    # Available Tasks tree — epics with TODO subtasks + orphan TODO tasks
    items.append(
        render_available_tasks_tree(
            data.active_epics,
            orphan_todo,
            _cached_subtasks,
        )
    )

    # Underway Tasks tree — epics with UNDERWAY subtasks + orphan UNDERWAY tasks
    items.append(
        render_underway_tasks_tree(
            data.active_epics,
            orphan_underway=orphan_underway,
            get_subtasks=_cached_subtasks,
            possession_entries=data.possession_entries,
        )
    )

    items.append(render_open_missions_table(data.possession_entries))
    items.append(render_stats_table(data.stats))
    items.extend(render_messaging_stats_table(data.stats))

    return items
