"""Rich rendering helpers for dashboard views.

These functions produce Rich renderables (Tables, Trees, strings) from
dashboard model objects. They contain no data-fetching logic.
"""

from collections.abc import Callable

from rich.table import Table
from rich.tree import Tree

from site_nine.dashboard.models import (
    DashboardData,
    DashboardStats,
    EpicDashboardData,
    FullDashboardData,
    MissionStatus,
    RoleDashboardData,
)
from site_nine.epics.models import Epic
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
    table.add_column("Mission", style="blue")

    for task in subtasks:
        table.add_row(
            task.id,
            task.title,
            str(task.status),
            task.role,
            task.priority,
            str(task.current_mission_id) if task.current_mission_id else "",
        )

    return table


def render_epic_tree(active_epics: list[Epic], get_subtasks: Callable[[str], list[Task]]) -> Tree | None:
    """
    Render a tree view of active epics with their subtasks.

    Args:
        active_epics: List of active epics (already filtered to TODO/UNDERWAY).
        get_subtasks: Callable that takes an epic_id and returns list[Task].

    Returns:
        A Rich Tree, or None if there are no active epics.
    """
    if not active_epics:
        return None

    # Sort by priority
    sorted_epics = sorted(
        active_epics,
        key=lambda e: (PRIORITY_ORDER.get(e.priority, 99), e.id),
    )

    tree = Tree("[bold yellow]Active Epics with Subtasks[/bold yellow]")

    for epic_obj in sorted_epics[:5]:
        status_color = STATUS_COLORS.get(epic_obj.status or "", "white")
        priority_color = PRIORITY_COLORS.get(epic_obj.priority, "white")

        if epic_obj.subtask_count and epic_obj.subtask_count > 0:
            progress_text = f"[{epic_obj.completed_count}/{epic_obj.subtask_count}]"
        else:
            progress_text = "[0/0]"

        epic_label = (
            f"[cyan]{epic_obj.id}[/cyan] "
            f"[{priority_color}]{epic_obj.priority}[/{priority_color}] "
            f"[{status_color}]{epic_obj.status}[/{status_color}] "
            f"[white]{epic_obj.title}[/white] "
            f"[dim]{progress_text}[/dim]"
        )

        epic_branch = tree.add(epic_label)

        subtasks = get_subtasks(epic_obj.id)

        if not subtasks:
            epic_branch.add("[dim italic]No subtasks linked[/dim italic]")
        else:
            status_priority = {
                "UNDERWAY": 0,
                "TODO": 1,
                "COMPLETE": 2,
                "ABORTED": 3,
            }
            subtasks.sort(
                key=lambda t: (
                    status_priority.get(str(t.status), 99),
                    PRIORITY_ORDER.get(t.priority, 99),
                    t.id,
                ),
            )

            for task in subtasks[:10]:
                task_status_color = TASK_STATUS_COLORS.get(str(task.status), "white")
                task_priority_color = PRIORITY_COLORS.get(task.priority, "white")
                mission_text = f"[blue]@{task.current_mission_id}[/blue]" if task.current_mission_id else ""

                task_label = (
                    f"[cyan]{task.id}[/cyan] "
                    f"[{task_priority_color}]{task.priority}[/{task_priority_color}] "
                    f"[green]{task.role or ''}[/green] "
                    f"[{task_status_color}]{task.status}[/{task_status_color}] "
                    f"[white]{task.title[:60]}[/white] "
                    f"{mission_text}"
                )

                epic_branch.add(task_label)

            if len(subtasks) > 10:
                epic_branch.add(f"[dim italic]... and {len(subtasks) - 10} more tasks[/dim italic]")

    return tree


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


def render_open_missions_table(mission_statuses: list[MissionStatus]) -> Table:
    """Build the 'Open Missions' table."""
    table = Table(
        title="Open Missions",
        show_header=True,
        title_style="bold green",
        title_justify="left",
    )
    table.add_column("Name", style="magenta")
    table.add_column("Role", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Start Time", style="blue")
    table.add_column("Objective", style="white")

    if mission_statuses:
        for ms in mission_statuses:
            m = ms.mission
            objective_display = (
                m.objective[:50] + "..." if m.objective and len(m.objective) > 50 else (m.objective or "")
            )
            table.add_row(
                m.persona_name,
                m.role,
                ms.status,
                m.start_time,
                objective_display,
            )
    else:
        table.add_row("[dim]No open missions[/dim]", "", "", "", "")

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

    table.add_row("Active missions", str(stats.active_missions))
    table.add_row("Idle missions", f"[yellow]{stats.idle_missions}[/yellow]")
    table.add_row("Active personas", f"[magenta]{stats.active_personas}[/magenta]")
    table.add_row("Total tasks", str(stats.total_tasks))
    table.add_row("In progress", f"[yellow]{stats.in_progress}[/yellow]")
    table.add_row("Completed", f"[green]{stats.completed}[/green]")
    if stats.blocked_by_reviews > 0:
        table.add_row("Blocked by reviews", f"[red]{stats.blocked_by_reviews}[/red]")

    return table


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
    table.add_column("Mission", style="blue")
    table.add_column("Epic", style="magenta")

    for task in tasks[:max_rows]:
        table.add_row(
            task.id,
            task.title,
            str(task.status),
            task.priority,
            str(task.current_mission_id) if task.current_mission_id else "",
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
        "active_missions": [
            {
                "id": ms.mission.id,
                "persona_name": ms.mission.persona_name,
                "role": ms.mission.role,
                "status": ms.status,
                "start_time": ms.mission.start_time,
                "objective": ms.mission.objective,
            }
            for ms in data.mission_statuses
        ],
        "stats": {
            "active_missions": data.stats.active_missions,
            "idle_missions": data.stats.idle_missions,
            "active_personas": data.stats.active_personas,
            "total_tasks": data.stats.total_tasks,
            "in_progress": data.stats.in_progress,
            "completed": data.stats.completed,
            "blocked_by_reviews": data.stats.blocked_by_reviews,
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
                "current_mission_id": t.current_mission_id,
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
                "current_mission_id": t.current_mission_id,
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

    Each item in the returned list should be passed to ``terminal_message``
    by the CLI layer.

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

    epic_tree = render_epic_tree(data.active_epics, get_subtasks)
    if epic_tree is not None:
        items.append(epic_tree)

    if data.available_tasks:
        items.append(render_available_tasks_table(data.available_tasks))
    else:
        items.append("[green]No available tasks - all work complete![/green]")

    items.append(render_open_missions_table(data.mission_statuses))
    items.append(render_stats_table(data.stats))

    return items
