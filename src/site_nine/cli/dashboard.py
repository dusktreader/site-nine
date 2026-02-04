"""Dashboard command to show project overview"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from site_nine.missions import MissionManager
from site_nine.core.database import Database
from site_nine.core.paths import get_opencode_dir
from site_nine.tasks import TaskManager

console = Console()


def dashboard_command(role: str | None = typer.Option(None, "--role", "-r", help="Filter tasks by role")) -> None:
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

            # Print header
            project_name = opencode_dir.parent.name
            console.print(Panel(f"[bold cyan]site-nine Dashboard[/bold cyan] - {project_name}", style="white on blue"))

            # Print quick stats
            console.print("\n[cyan]Quick Stats:[/cyan]")
            console.print(f"  Active agents: [bold]{len(active_missions)}[/bold]")
            console.print(f"  Total tasks: [bold]{sum(task_counts.values())}[/bold]")
            console.print(f"  In progress: [bold yellow]{task_counts['UNDERWAY']}[/bold yellow]")
            console.print(f"  Completed: [bold green]{task_counts['COMPLETE']}[/bold green]")
            if blocked_by_review_count > 0:
                console.print(f"  [red]Blocked by reviews: {blocked_by_review_count}[/red]")

            # Active missions table
            console.print("\n")
            mission_table = Table(title="Active Agent Sessions", show_header=True, title_style="bold green")
            mission_table.add_column("Name", style="magenta")
            mission_table.add_column("Role", style="green")
            mission_table.add_column("Start Time", style="blue")
            mission_table.add_column("Task", style="white")

            if active_missions:
                for mission in active_missions:
                    objective_display = (
                        mission.objective[:50] + "..."
                        if mission.objective and len(mission.objective) > 50
                        else (mission.objective or "")
                    )
                    mission_table.add_row(
                        mission.persona_name,
                        mission.role,
                        mission.start_time,
                        objective_display,
                    )
            else:
                mission_table.add_row("[dim]No active sessions[/dim]", "", "", "")

            console.print(mission_table)

            # Task summary table
            console.print("\n")
            task_table = Table(title="Task Summary", show_header=True, title_style="bold yellow")
            task_table.add_column("Status", style="yellow")
            task_table.add_column("Count", justify="right", style="cyan")

            for status in ["TODO", "UNDERWAY", "BLOCKED", "REVIEW", "COMPLETE", "PAUSED", "ABORTED"]:
                count = task_counts[status]
                if count > 0:
                    task_table.add_row(status, str(count))

            if sum(task_counts.values()) == 0:
                task_table.add_row("[dim]No tasks[/dim]", "0")

            console.print(task_table)

            # Recent tasks table
            console.print("\n")
            recent_tasks = Table(title="Recent Tasks", show_header=True, title_style="bold blue")
            recent_tasks.add_column("ID", style="cyan")
            recent_tasks.add_column("Title", style="magenta", max_width=40)
            recent_tasks.add_column("Status", style="yellow")
            recent_tasks.add_column("Priority", style="red")
            recent_tasks.add_column("Mission", style="blue")

            for task in all_tasks[:10]:  # Show top 10 most recent
                recent_tasks.add_row(
                    task.id,
                    task.title,
                    task.status,
                    task.priority,
                    str(task.current_mission_id) if task.current_mission_id else "",
                )

            if not all_tasks:
                recent_tasks.add_row("[dim]No tasks[/dim]", "", "", "", "")

            console.print(recent_tasks)

    except Exception as e:
        console.print(f"[red]Error showing dashboard: {e}[/red]")
        raise typer.Exit(1)
