"""Epic management commands"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.text import Text
from typerdrive import handle_errors

from site_nine.core.database import Database
from site_nine.core.paths import get_opencode_dir, validate_path_within_project
from site_nine.epics import Epic, EpicManager

app = typer.Typer(help="Manage epics")
console = Console()


class Priority(str, Enum):
    """Epic priority levels"""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

    @classmethod
    def from_string(cls, value: str) -> "Priority":
        """Convert string to Priority enum (case-insensitive)"""
        value_upper = value.upper()
        for member in cls:
            if member.value.upper() == value_upper:
                return member
        raise ValueError(f"Invalid priority: {value}. Valid values: {', '.join(m.value for m in cls)}")


class Status(str, Enum):
    """Epic status values"""

    TODO = "TODO"
    UNDERWAY = "UNDERWAY"
    COMPLETE = "COMPLETE"
    ABORTED = "ABORTED"


def _get_manager() -> EpicManager:
    """Get epic manager"""
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
    return EpicManager(db)


@app.command()
@handle_errors("Failed to create epic")
def create(
    title: str = typer.Option(..., "--title", "-t", help="Epic title"),
    priority: str = typer.Option(..., "--priority", "-p", help="Priority (CRITICAL, HIGH, MEDIUM, LOW)"),
    description: str | None = typer.Option(None, "--description", "-d", help="Epic description"),
) -> None:
    """Create a new epic"""
    manager = _get_manager()

    # Validate priority
    try:
        priority_enum = Priority.from_string(priority)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    # Create epic
    epic = manager.create_epic(title=title, priority=priority_enum.value, description=description)

    # Generate markdown file
    try:
        opencode_dir = get_opencode_dir()
        _sync_epic_file(epic, manager, opencode_dir)
    except Exception as e:
        console.print(f"[yellow]Warning: Failed to create markdown file: {e}[/yellow]")

    console.print(f"[green]✓[/green] Created epic {epic.id}")
    console.print(f"  Title: {title}")
    console.print(f"  Priority: {priority_enum.value}")
    console.print(f"  Status: {epic.status}")
    console.print(f"  File: {epic.file_path}")

    logger.info(f"Created epic {epic.id}: {title}")


@app.command()
@handle_errors("Failed to list epics")
def list(
    status: str | None = typer.Option(
        None, "--status", "-s", help="Filter by status (TODO, UNDERWAY, COMPLETE, ABORTED)"
    ),
    priority: str | None = typer.Option(None, "--priority", "-p", help="Filter by priority"),
) -> None:
    """List epics"""
    manager = _get_manager()

    # Normalize filters
    status_value = status.upper() if status else None
    priority_value = priority.upper() if priority else None

    # Validate status
    if status_value and status_value not in [s.value for s in Status]:
        console.print(
            f"[red]Error: Invalid status '{status}'. Valid values: {', '.join(s.value for s in Status)}[/red]"
        )
        raise typer.Exit(1)

    # Validate priority
    if priority_value and priority_value not in [p.value for p in Priority]:
        console.print(
            f"[red]Error: Invalid priority '{priority}'. Valid values: {', '.join(p.value for p in Priority)}[/red]"
        )
        raise typer.Exit(1)

    epics = manager.list_epics(status=status_value, priority=priority_value)

    if not epics:
        filter_msg = ""
        if status or priority:
            filters = []
            if status:
                filters.append(f"status={status_value}")
            if priority:
                filters.append(f"priority={priority_value}")
            filter_msg = f" matching {', '.join(filters)}"
        console.print(f"No epics found{filter_msg}")
        return

    # Create table
    table = Table(title="Epics")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Title", style="white")
    table.add_column("Status", style="yellow")
    table.add_column("Priority", style="magenta")
    table.add_column("Progress", style="green")
    table.add_column("Created", style="dim")

    for epic in epics:
        # Format status with color
        status_color = {
            "TODO": "yellow",
            "UNDERWAY": "cyan",
            "COMPLETE": "green",
            "ABORTED": "red",
        }.get(epic.status, "white")

        status_text = Text(epic.status, style=status_color)

        # Format progress
        if epic.subtask_count and epic.subtask_count > 0:
            progress = f"{epic.completed_count}/{epic.subtask_count} ({epic.progress_percent}%)"
        else:
            progress = "No tasks"

        # Format created date
        created_date = epic.created_at.split("T")[0] if "T" in epic.created_at else epic.created_at[:10]

        table.add_row(
            epic.id,
            epic.title,
            status_text,
            epic.priority,
            progress,
            created_date,
        )

    console.print(table)
    logger.debug(f"Listed {len(epics)} epics")


@app.command()
@handle_errors("Failed to show epic")
def show(epic_id: str = typer.Argument(..., help="Epic ID")) -> None:
    """Show epic details"""
    manager = _get_manager()

    epic = manager.get_epic(epic_id)
    if not epic:
        console.print(f"[red]Error: Epic {epic_id} not found[/red]")
        raise typer.Exit(1)

    # Print epic details
    console.print(f"\n[bold cyan]Epic {epic.id}[/bold cyan]")
    console.print()
    console.print(f"[bold]Title:[/bold]       {epic.title}")

    # Status with color
    status_color = {
        "TODO": "yellow",
        "UNDERWAY": "cyan",
        "COMPLETE": "green",
        "ABORTED": "red",
    }.get(epic.status, "white")
    console.print(f"[bold]Status:[/bold]      [{status_color}]{epic.status}[/{status_color}]")

    console.print(f"[bold]Priority:[/bold]    {epic.priority}")

    # Progress
    if epic.subtask_count and epic.subtask_count > 0:
        progress = f"{epic.completed_count}/{epic.subtask_count} tasks ({epic.progress_percent}%)"
    else:
        progress = "No tasks"
    console.print(f"[bold]Progress:[/bold]    {progress}")

    console.print()
    console.print(f"[bold]Created:[/bold]     {epic.created_at}")
    console.print(f"[bold]Updated:[/bold]     {epic.updated_at}")

    if epic.completed_at:
        console.print(f"[bold]Completed:[/bold]   {epic.completed_at}")

    if epic.aborted_at:
        console.print(f"[bold]Aborted:[/bold]     {epic.aborted_at}")
        if epic.aborted_reason:
            console.print(f"[bold]Reason:[/bold]      {epic.aborted_reason}")

    if epic.description:
        console.print()
        console.print("[bold]Description:[/bold]")
        console.print(epic.description)

    # Show subtasks
    subtasks = manager.get_subtasks(epic_id)
    if subtasks:
        console.print()
        console.print("[bold]Subtasks:[/bold]")

        task_table = Table(show_header=True, box=None, padding=(0, 1))
        task_table.add_column("Task ID", style="cyan")
        task_table.add_column("Title", style="white")
        task_table.add_column("Status", style="yellow")
        task_table.add_column("Role", style="magenta")

        for task in subtasks:
            task_status_color = {
                "TODO": "yellow",
                "UNDERWAY": "cyan",
                "BLOCKED": "red",
                "PAUSED": "dim",
                "REVIEW": "magenta",
                "COMPLETE": "green",
                "ABORTED": "red",
            }.get(task.status, "white")

            task_table.add_row(
                task.id,
                task.title,
                Text(task.status, style=task_status_color),
                task.role,
            )

        console.print(task_table)

    console.print()
    console.print(f"[dim]File: {epic.file_path}[/dim]")

    logger.debug(f"Displayed details for epic {epic_id}")


@app.command()
@handle_errors("Failed to update epic")
def update(
    epic_id: str = typer.Argument(..., help="Epic ID"),
    title: str | None = typer.Option(None, "--title", "-t", help="New title"),
    description: str | None = typer.Option(None, "--description", "-d", help="New description"),
    priority: str | None = typer.Option(None, "--priority", "-p", help="New priority"),
) -> None:
    """Update epic fields"""
    manager = _get_manager()

    # Verify epic exists
    epic = manager.get_epic(epic_id)
    if not epic:
        console.print(f"[red]Error: Epic {epic_id} not found[/red]")
        raise typer.Exit(1)

    # Build updates
    updates = {}
    if title:
        updates["title"] = title
    if description is not None:  # Allow empty string to clear description
        updates["description"] = description
    if priority:
        try:
            priority_enum = Priority.from_string(priority)
            updates["priority"] = priority_enum.value
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

    if not updates:
        console.print("[yellow]No updates provided[/yellow]")
        return

    # Update epic
    updated_epic = manager.update_epic(epic_id, **updates)

    # Sync markdown file
    try:
        opencode_dir = get_opencode_dir()
        _sync_epic_file(updated_epic, manager, opencode_dir)
    except Exception as e:
        console.print(f"[yellow]Warning: Failed to update markdown file: {e}[/yellow]")

    console.print(f"[green]✓[/green] Updated epic {epic_id}")
    for field, value in updates.items():
        console.print(f"  {field.title()}: {value}")

    logger.info(f"Updated epic {epic_id}: {updates}")


@app.command()
@handle_errors("Failed to abort epic")
def abort(
    epic_id: str = typer.Argument(..., help="Epic ID"),
    reason: str = typer.Option(..., "--reason", "-r", help="Reason for aborting"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Abort an epic and all its subtasks"""
    manager = _get_manager()

    # Verify epic exists
    epic = manager.get_epic(epic_id)
    if not epic:
        console.print(f"[red]Error: Epic {epic_id} not found[/red]")
        raise typer.Exit(1)

    # Check if already aborted
    if epic.status == "ABORTED":
        console.print(f"[yellow]Epic {epic_id} is already aborted[/yellow]")
        return

    # Get subtasks
    subtasks = manager.get_subtasks(epic_id)

    # Confirmation prompt
    if not yes:
        console.print(f"\n[bold yellow]⚠ Warning: This will abort epic {epic_id} and all its subtasks[/bold yellow]")
        console.print(f"\n[bold]Epic:[/bold] {epic.title}")
        console.print(f"[bold]Subtasks:[/bold] {len(subtasks)} task(s) will be aborted")

        if subtasks:
            console.print("\nTasks to be aborted:")
            for task in subtasks[:5]:  # Show first 5
                console.print(f"  • {task.id}: {task.title}")
            if len(subtasks) > 5:
                console.print(f"  ... and {len(subtasks) - 5} more")

        console.print(f"\n[bold]Reason:[/bold] {reason}")
        console.print()

        confirm = typer.confirm("Are you sure you want to abort this epic?")
        if not confirm:
            console.print("[yellow]Abort cancelled[/yellow]")
            raise typer.Exit(0)

    # Abort epic
    manager.abort_epic(epic_id, reason)

    # Sync markdown file to reflect aborted status
    try:
        opencode_dir = get_opencode_dir()
        aborted_epic = manager.get_epic(epic_id)
        if aborted_epic:
            _sync_epic_file(aborted_epic, manager, opencode_dir)
    except Exception as e:
        console.print(f"[yellow]Warning: Failed to update markdown file: {e}[/yellow]")

    console.print(f"[green]✓[/green] Aborted epic {epic_id}")
    console.print(f"  Reason: {reason}")
    console.print(f"  Subtasks aborted: {len(subtasks)}")

    logger.info(f"Aborted epic {epic_id}: {reason}")


@app.command()
@handle_errors("Failed to sync epic files")
def sync(
    epic_id: str | None = typer.Option(None, "--epic", "-e", help="Sync specific epic (syncs all if not provided)"),
) -> None:
    """Synchronize epic markdown files with database"""
    manager = _get_manager()
    try:
        opencode_dir = get_opencode_dir()
    except FileNotFoundError:
        console.print("[red]Error: .opencode directory not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    if epic_id:
        # Sync specific epic
        epic = manager.get_epic(epic_id)
        if not epic:
            console.print(f"[red]Error: Epic {epic_id} not found[/red]")
            raise typer.Exit(1)

        _sync_epic_file(epic, manager, opencode_dir)
        console.print(f"[green]✓[/green] Synced epic {epic_id}")
        logger.info(f"Synced epic file {epic_id}")
    else:
        # Sync all epics
        epics = manager.list_epics()
        for epic in epics:
            _sync_epic_file(epic, manager, opencode_dir)

        console.print(f"[green]✓[/green] Synced {len(epics)} epic(s)")
        logger.info(f"Synced {len(epics)} epic files")


def _sync_epic_file(epic: Epic, manager: EpicManager, opencode_dir: Path) -> None:
    """Helper to sync a single epic file"""

    # Handle file_path which may include .opencode prefix
    if epic.file_path.startswith(".opencode/"):
        file_path = Path(epic.file_path)
    else:
        file_path = opencode_dir / epic.file_path

    # Validate path to prevent directory traversal
    file_path = validate_path_within_project(file_path)

    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing body if file exists
    body = ""
    if file_path.exists():
        content = file_path.read_text()
        lines = content.split("\n")
        body_start_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("## "):
                body_start_idx = i
                break
        if body_start_idx > 0:
            body = "\n".join(lines[body_start_idx:])

    # Build header with epic metadata
    status_emoji = {
        "TODO": "📋",
        "UNDERWAY": "🚧",
        "COMPLETE": "✅",
        "ABORTED": "❌",
    }.get(epic.status, "📋")

    header_parts = [
        f"# Epic {epic.id}: {epic.title}",
        "",
        f"**Status:** {status_emoji} {epic.status}",
        f"**Priority:** {epic.priority}",
        f"**Created:** {epic.created_at}",
        f"**Updated:** {epic.updated_at}",
    ]

    if epic.completed_at:
        header_parts.append(f"**Completed:** {epic.completed_at}")

    if epic.aborted_at:
        header_parts.append(f"**Aborted:** {epic.aborted_at}")
        if epic.aborted_reason:
            header_parts.append(f"**Abort Reason:** {epic.aborted_reason}")

    # Add progress information
    if epic.subtask_count and epic.subtask_count > 0:
        progress_bar = _generate_progress_bar(epic.progress_percent)
        header_parts.extend(
            [
                "",
                "## Progress",
                "",
                f"**Tasks:** {epic.completed_count}/{epic.subtask_count} complete ({epic.progress_percent}%)",
                f"{progress_bar}",
            ]
        )

    # Add subtasks table
    subtasks = manager.get_subtasks(epic.id)
    if subtasks:
        header_parts.extend(["", "## Subtasks", ""])

        # Create markdown table
        table_lines = [
            "| Task ID | Title | Status | Role | Priority |",
            "|---------|-------|--------|------|----------|",
        ]

        for task in subtasks:
            status_symbol = {
                "TODO": "⬜",
                "UNDERWAY": "🔵",
                "BLOCKED": "🔴",
                "PAUSED": "⏸️",
                "REVIEW": "👀",
                "COMPLETE": "✅",
                "ABORTED": "❌",
            }.get(task.status, "⬜")

            table_lines.append(
                f"| {task.id} | {task.title} | {status_symbol} {task.status} | {task.role} | {task.priority} |"
            )

        header_parts.extend(table_lines)

    header = "\n".join(header_parts)

    # Create default body if none exists
    if not body:
        description_text = epic.description or "[Describe the high-level goals and scope of this epic]"
        body = f"""

## Description

{description_text}

## Goals

- [Key objective 1]
- [Key objective 2]
- [Key objective 3]

## Success Criteria

- [What needs to be achieved for this epic to be considered complete?]

## Notes

[Epic-level notes, decisions, blockers, and context]
"""

    # Write combined content
    file_path.write_text(header + "\n" + body)


def _generate_progress_bar(percent: int, width: int = 30) -> str:
    """Generate a text-based progress bar"""
    filled = int(width * percent / 100)
    empty = width - filled
    return f"[{'█' * filled}{'░' * empty}] {percent}%"
