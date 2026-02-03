"""Reset project data with safety confirmations"""

from __future__ import annotations

import shutil
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from typerdrive import handle_errors

from site_nine.core.database import Database
from site_nine.core.paths import get_opencode_dir

console = Console()


@handle_errors("Failed to reset project")
def reset_command(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip first confirmation (still requires typing confirmation)"),
) -> None:
    """Reset project data - DANGEROUS!

    This command will DELETE:
    - All agent sessions (database records and session files)
    - All tasks (database records and task files)
    - All task dependencies
    - All daemon name usage counts (reset to 0)

    This command will PRESERVE:
    - Daemon names list (but usage counts reset to 0)
    - Task templates
    - Configuration files
    - Documentation files

    Requires DOUBLE confirmation to prevent accidental data loss.
    """
    try:
        opencode_dir = get_opencode_dir()
    except FileNotFoundError:
        console.print("[red]Error: .opencode directory not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    db_path = opencode_dir / "data" / "project.db"

    if not db_path.exists():
        console.print("[red]Error: project.db not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    console.print()
    console.print(
        Panel(
            "[bold red]⚠️  WARNING: DESTRUCTIVE OPERATION ⚠️[/bold red]\n\n"
            "This will permanently DELETE:\n"
            "  • All agent sessions (database + files)\n"
            "  • All tasks (database + files)\n"
            "  • All task dependencies\n"
            "  • Daemon name usage counts\n\n"
            "This CANNOT be undone without a backup!",
            border_style="red",
            title="[bold red]DANGER ZONE[/bold red]",
        )
    )
    console.print()

    # Get counts before deletion
    db = Database(db_path)

    agent_count = db.execute_query("SELECT COUNT(*) as count FROM agents")[0]["count"]
    task_count = db.execute_query("SELECT COUNT(*) as count FROM tasks")[0]["count"]
    dep_count = db.execute_query("SELECT COUNT(*) as count FROM task_dependencies")[0]["count"]

    console.print(f"[yellow]Data to be deleted:[/yellow]")
    console.print(f"  • {agent_count} agent sessions")
    console.print(f"  • {task_count} tasks")
    console.print(f"  • {dep_count} task dependencies")
    console.print()

    if agent_count == 0 and task_count == 0:
        console.print("[green]✓ No data to delete. Database is already clean.[/green]")
        return

    # First confirmation
    if not yes:
        console.print("[bold]First confirmation:[/bold]")
        if not Confirm.ask("Are you absolutely sure you want to reset the project?", default=False):
            console.print("[green]Cancelled. No changes made.[/green]")
            raise typer.Exit(0)
        console.print()

    # Second confirmation - require typing
    console.print("[bold red]Second confirmation (REQUIRED):[/bold red]")
    console.print("To confirm, type exactly: [bold]DELETE ALL DATA[/bold]")
    console.print()

    confirmation = typer.prompt("Confirmation")

    if confirmation != "DELETE ALL DATA":
        console.print("[green]Cancelled. Confirmation text did not match.[/green]")
        raise typer.Exit(0)

    console.print()
    console.print("[bold red]Proceeding with reset...[/bold red]")
    console.print()

    # Delete session files
    console.print("[bold]1. Deleting session files...[/bold]")
    sessions_dir = opencode_dir / "work" / "sessions"
    deleted_session_files = 0

    if sessions_dir.exists():
        for session_file in sessions_dir.glob("*.md"):
            # Skip README and TEMPLATE files
            if session_file.name in ("README.md", "TEMPLATE.md"):
                continue
            try:
                session_file.unlink()
                deleted_session_files += 1
            except Exception as e:
                console.print(f"  [yellow]⚠[/yellow] Failed to delete {session_file.name}: {e}")

    console.print(f"  [green]✓[/green] Deleted {deleted_session_files} session files")

    # Delete handoff files
    handoffs_dir = opencode_dir / "work" / "sessions" / "handoffs"
    deleted_handoff_files = 0

    if handoffs_dir.exists():
        for handoff_file in handoffs_dir.glob("*.md"):
            try:
                handoff_file.unlink()
                deleted_handoff_files += 1
            except Exception as e:
                console.print(f"  [yellow]⚠[/yellow] Failed to delete {handoff_file.name}: {e}")

    if deleted_handoff_files > 0:
        console.print(f"  [green]✓[/green] Deleted {deleted_handoff_files} handoff files")

    console.print()

    # Delete task files
    console.print("[bold]2. Deleting task files...[/bold]")
    tasks_dir = opencode_dir / "work" / "tasks"
    deleted_task_files = 0

    if tasks_dir.exists():
        for task_file in tasks_dir.glob("*.md"):
            # Skip README if it exists
            if task_file.name == "README.md":
                continue
            try:
                task_file.unlink()
                deleted_task_files += 1
            except Exception as e:
                console.print(f"  [yellow]⚠[/yellow] Failed to delete {task_file.name}: {e}")

    console.print(f"  [green]✓[/green] Deleted {deleted_task_files} task files")
    console.print()

    # Delete database records
    console.print("[bold]3. Clearing database records...[/bold]")

    # Delete task dependencies first (foreign key constraint)
    db.execute_update("DELETE FROM task_dependencies")
    console.print(f"  [green]✓[/green] Deleted {dep_count} task dependencies")

    # Delete tasks
    db.execute_update("DELETE FROM tasks")
    console.print(f"  [green]✓[/green] Deleted {task_count} tasks")

    # Delete agents
    db.execute_update("DELETE FROM agents")
    console.print(f"  [green]✓[/green] Deleted {agent_count} agent sessions")

    # Reset daemon name usage counts
    db.execute_update("UPDATE daemon_names SET usage_count = 0, last_used_at = NULL")
    console.print("  [green]✓[/green] Reset daemon name usage counts")

    console.print()

    # Vacuum database to reclaim space
    console.print("[bold]4. Optimizing database...[/bold]")
    try:
        db.execute_update("VACUUM")
        console.print("  [green]✓[/green] Database optimized")
    except Exception as e:
        console.print(f"  [yellow]⚠[/yellow] Failed to vacuum database: {e}")

    console.print()
    console.print("═" * 70)
    console.print()

    console.print(
        Panel(
            "[bold green]✅ Project reset complete![/bold green]\n\n"
            "Deleted:\n"
            f"  • {deleted_session_files} session files\n"
            f"  • {deleted_handoff_files} handoff files\n"
            f"  • {deleted_task_files} task files\n"
            f"  • {agent_count} agent records\n"
            f"  • {task_count} task records\n"
            f"  • {dep_count} dependencies\n\n"
            "Your project is now in a fresh state.",
            border_style="green",
            title="[bold green]Reset Complete[/bold green]",
        )
    )
    console.print()
