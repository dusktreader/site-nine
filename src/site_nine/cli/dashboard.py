"""Dashboard command to show project overview"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from site_nine.missions import MissionManager
from site_nine.core.database import Database
from site_nine.core.paths import get_opencode_dir
from site_nine.tasks import TaskManager
from site_nine.epics import EpicManager

console = Console()


def dashboard_command(
    role: str | None = typer.Option(None, "--role", "-r", help="Filter tasks by role"),
    epic: str | None = typer.Option(None, "--epic", "-e", help="Filter tasks by epic ID"),
) -> None:
    """Show project dashboard with overview of missions and tasks"""
    try:
        # Get database
        try:
            opencode_dir = get_opencode_dir()
        except FileNotFoundError:
            console.print("[red]Error: .opencode directory not found. Run 's9 init' first.[/red]")
            raise typer.Exit(1)

        db_path = opencode_dir / "data" / "project.db"
        if not db_path.exists():
            console.print("[red]Error: project.db not found. Run 's9 init' first.[/red]")
            raise typer.Exit(1)

        db = Database(db_path)
        mission_manager = MissionManager(db)
        task_manager = TaskManager(db)
        epic_manager = EpicManager(db)

        # Handle epic filter
        if epic:
            # Show epic-specific dashboard
            epic_obj = epic_manager.get_epic(epic)
            if not epic_obj:
                console.print(f"[red]Error: Epic {epic} not found[/red]")
                raise typer.Exit(1)

            # Get subtasks
            subtasks = epic_manager.get_subtasks(epic)

            # Display epic header
            console.print()
            status_color = {
                "TODO": "yellow",
                "UNDERWAY": "cyan",
                "COMPLETE": "green",
                "ABORTED": "red",
            }.get(epic_obj.status, "white")

            console.print(f"[bold]Epic {epic}:[/bold] {epic_obj.title}")
            console.print(f"[bold]Status:[/bold] [{status_color}]{epic_obj.status}[/{status_color}]")
            console.print(f"[bold]Priority:[/bold] {epic_obj.priority}")

            if epic_obj.subtask_count and epic_obj.subtask_count > 0:
                progress_bar = _generate_progress_bar(epic_obj.progress_percent)
                console.print(
                    f"[bold]Progress:[/bold] {epic_obj.completed_count}/{epic_obj.subtask_count} tasks ({epic_obj.progress_percent}%)"
                )
                console.print(progress_bar)

            # Display subtasks table
            console.print()
            if subtasks:
                tasks_table = Table(title="Epic Subtasks", show_header=True, title_style="bold magenta")
                tasks_table.add_column("ID", style="cyan")
                tasks_table.add_column("Title", style="white", max_width=50)
                tasks_table.add_column("Status", style="yellow")
                tasks_table.add_column("Role", style="green")
                tasks_table.add_column("Priority", style="red")
                tasks_table.add_column("Mission", style="blue")

                for task in subtasks:
                    tasks_table.add_row(
                        task.id,
                        task.title,
                        task.status,
                        task.role,
                        task.priority,
                        str(task.current_mission_id) if task.current_mission_id else "",
                    )

                console.print(tasks_table)
            else:
                console.print("[yellow]No tasks linked to this epic[/yellow]")

            return

        # Get data
        all_tasks = task_manager.list_tasks(role=role)

        # If role filter is active, show only available tasks for that role
        if role:
            # Filter to only TODO and UNDERWAY tasks (available tasks)
            available_tasks = [t for t in all_tasks if t.status in ("TODO", "UNDERWAY")]

            # Show only tasks table for the filtered role
            tasks_title = f"Available Tasks - {role} Role"
            tasks_table = Table(title=tasks_title, show_header=True, title_style="bold blue")
            tasks_table.add_column("ID", style="cyan")
            tasks_table.add_column("Title", style="magenta", max_width=40)
            tasks_table.add_column("Status", style="yellow")
            tasks_table.add_column("Priority", style="red")
            tasks_table.add_column("Mission", style="blue")

            if available_tasks:
                for task in available_tasks[:10]:  # Show top 10 most recent
                    tasks_table.add_row(
                        task.id,
                        task.title,
                        task.status,
                        task.priority,
                        str(task.current_mission_id) if task.current_mission_id else "",
                    )
                console.print(tasks_table)
            else:
                # No available tasks for this role
                console.print(f"\n[yellow]No available tasks for {role} role[/yellow]")

        else:
            # Show full dashboard when no role filter is active
            active_missions = mission_manager.list_missions(active_only=True)

            # Count tasks by status
            task_counts = {
                "TODO": 0,
                "UNDERWAY": 0,
                "BLOCKED": 0,
                "PAUSED": 0,
                "REVIEW": 0,
                "COMPLETE": 0,
                "ABORTED": 0,
            }
            for task in all_tasks:
                task_counts[task.status] = task_counts.get(task.status, 0) + 1

            # Count tasks blocked by reviews
            blocked_by_review_count = sum(1 for task in all_tasks if task.blocks_on_review_id is not None)

            # Find idle missions (active missions with no UNDERWAY tasks)
            missions_with_underway = {
                task.current_mission_id for task in all_tasks if task.status == "UNDERWAY" and task.current_mission_id
            }
            idle_missions = [m for m in active_missions if m.id not in missions_with_underway]

            # 1. Available Tasks table (show TODO and UNDERWAY tasks FIRST)
            console.print("\n")
            available_tasks = [t for t in all_tasks if t.status in ("TODO", "UNDERWAY")]
            tasks_table = Table(
                title="Available Tasks", show_header=True, title_style="bold magenta", title_justify="left"
            )
            tasks_table.add_column("ID", style="cyan", width=12)
            tasks_table.add_column("Priority", style="red", width=10)
            tasks_table.add_column("Role", style="green", width=14)
            tasks_table.add_column("Status", style="yellow", width=10)
            tasks_table.add_column("Title", style="white")

            if available_tasks:
                # Sort by priority (CRITICAL > HIGH > MEDIUM > LOW), then by role
                priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
                available_tasks.sort(key=lambda t: (priority_order.get(t.priority, 99), t.role or "", t.id))

                # Show up to 10 most relevant tasks
                for task in available_tasks[:10]:
                    tasks_table.add_row(
                        task.id,
                        task.priority,
                        task.role or "",
                        task.status,
                        task.title,
                    )
                console.print(tasks_table)
            else:
                console.print("[green]No available tasks - all work complete![/green]")

            # 2. Open missions table (all active missions)
            console.print("\n")
            open_table = Table(title="Open Missions", show_header=True, title_style="bold green", title_justify="left")
            open_table.add_column("Name", style="magenta")
            open_table.add_column("Role", style="green")
            open_table.add_column("Status", style="yellow")
            open_table.add_column("Start Time", style="blue")
            open_table.add_column("Objective", style="white")

            if active_missions:
                for mission in active_missions:
                    objective_display = (
                        mission.objective[:50] + "..."
                        if mission.objective and len(mission.objective) > 50
                        else (mission.objective or "")
                    )
                    # Determine if mission is idle or active based on UNDERWAY tasks
                    status = "IDLE" if mission.id in [m.id for m in idle_missions] else "WORKING"
                    open_table.add_row(
                        mission.persona_name,
                        mission.role,
                        status,
                        mission.start_time,
                        objective_display,
                    )
            else:
                open_table.add_row("[dim]No open missions[/dim]", "", "", "", "")

            console.print(open_table)

            # 3. Quick Stats table
            console.print("\n")
            persona_count = len(set(m.persona_name for m in active_missions))
            stats_table = Table(title="Quick Stats", show_header=True, title_style="bold cyan", title_justify="left")
            stats_table.add_column("Metric", style="cyan")
            stats_table.add_column("Count", justify="right", style="bold")

            stats_table.add_row("Active missions", str(len(active_missions)))
            stats_table.add_row("Idle missions", f"[yellow]{len(idle_missions)}[/yellow]")
            stats_table.add_row("Active personas", f"[magenta]{persona_count}[/magenta]")
            stats_table.add_row("Total tasks", str(sum(task_counts.values())))
            stats_table.add_row("In progress", f"[yellow]{task_counts['UNDERWAY']}[/yellow]")
            stats_table.add_row("Completed", f"[green]{task_counts['COMPLETE']}[/green]")
            if blocked_by_review_count > 0:
                stats_table.add_row("Blocked by reviews", f"[red]{blocked_by_review_count}[/red]")

            console.print(stats_table)

            # 4. Active Epics table
            console.print("\n")
            active_epics = epic_manager.list_epics(status="TODO") + epic_manager.list_epics(status="UNDERWAY")

            if active_epics:
                epics_table = Table(
                    title="Active Epics", show_header=True, title_style="bold yellow", title_justify="left"
                )
                epics_table.add_column("ID", style="cyan", width=12)
                epics_table.add_column("Title", style="white", max_width=40)
                epics_table.add_column("Status", style="yellow", width=10)
                epics_table.add_column("Priority", style="red", width=10)
                epics_table.add_column("Progress", style="green")

                # Sort by priority (CRITICAL > HIGH > MEDIUM > LOW)
                priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
                active_epics.sort(key=lambda e: (priority_order.get(e.priority, 99), e.id))

                for epic_obj in active_epics[:5]:  # Show top 5 active epics
                    if epic_obj.subtask_count and epic_obj.subtask_count > 0:
                        progress = f"{epic_obj.completed_count}/{epic_obj.subtask_count} ({epic_obj.progress_percent}%)"
                    else:
                        progress = "No tasks"

                    epics_table.add_row(
                        epic_obj.id,
                        epic_obj.title,
                        epic_obj.status,
                        epic_obj.priority,
                        progress,
                    )

                console.print(epics_table)
                console.print("[dim]💡 View epic details: [bold]s9 epic show <EPIC_ID>[/bold][/dim]")
                console.print("[dim]💡 View epic tasks: [bold]s9 dashboard --epic <EPIC_ID>[/bold][/dim]")

    except Exception as e:
        console.print(f"[red]Error showing dashboard: {e}[/red]")
        raise typer.Exit(1)


def _generate_progress_bar(percent: int, width: int = 40) -> str:
    """Generate a text-based progress bar"""
    filled = int(width * percent / 100)
    empty = width - filled
    bar_color = "green" if percent == 100 else "cyan" if percent > 50 else "yellow" if percent > 0 else "dim"
    return f"[{bar_color}]{'█' * filled}{'░' * empty}[/{bar_color}] {percent}%"
