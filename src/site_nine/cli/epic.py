from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table
from rich.text import Text
from snick import conjoin
from typerdrive import handle_errors, terminal_message

from site_nine.adrs import ADRManager
from site_nine.cli.json_utils import format_json_response, output_json
from site_nine.cli.utils import CLIError, require_db_path
from site_nine.core.database import Database
from site_nine.core.paths import get_opencode_dir
from site_nine.core.types import Priority
from site_nine.epics import Epic, EpicManager, EpicStatus
from site_nine.exceptions import SiteNineError

app = typer.Typer(help="Manage epics")


@app.command()
@handle_errors("Failed to create epic", handle_exc_class=SiteNineError)
def create(
    title: Annotated[str, typer.Option("--title", "-t", help="Epic title")],
    priority: Annotated[str, typer.Option("--priority", "-p", help="Priority (CRITICAL, HIGH, MEDIUM, LOW)")],
    description: Annotated[str | None, typer.Option("--description", "-d", help="Epic description")] = None,
) -> None:
    """Create a new epic (typically used by: humans)"""
    db_path = require_db_path()

    with CLIError.handle_errors("Invalid priority", handle_exc_class=ValueError):
        priority_enum = Priority.from_string(priority)

    with Database(db_path) as db:
        manager = EpicManager(db)
        epic = manager.create_epic(title=title, priority=priority_enum.value, description=description)

        try:
            opencode_dir = get_opencode_dir()
            manager.sync_epic_file(epic, opencode_dir)
        except Exception as e:
            terminal_message(
                f"Failed to create markdown file: {e}",
                subject="Warning",
                subject_color="yellow",
            )

    terminal_message(
        conjoin(
            f"Created epic {epic.id}",
            f"Title: {title}",
            f"Priority: {priority_enum.value}",
            f"Status: {epic.status}",
            f"File: {epic.file_path}",
        ),
        subject="Success",
        subject_color="green",
    )


@app.command()
@handle_errors("Failed to list epics", handle_exc_class=SiteNineError)
def list(
    status: Annotated[
        str | None, typer.Option("--status", "-s", help="Filter by status (TODO, UNDERWAY, COMPLETE, ABORTED)")
    ] = None,
    priority: Annotated[str | None, typer.Option("--priority", "-p", help="Filter by priority")] = None,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """List epics (typically used by: both)"""
    db_path = require_db_path()

    status_value = status.upper() if status else None
    priority_value = priority.upper() if priority else None

    CLIError.require_condition(
        not status_value or status_value in [s.value for s in EpicStatus],
        f"Invalid status '{status}'. Valid values: {', '.join(s.value for s in EpicStatus)}",
    )

    CLIError.require_condition(
        not priority_value or priority_value in [p.value for p in Priority],
        f"Invalid priority '{priority}'. Valid values: {', '.join(p.value for p in Priority)}",
    )

    with Database(db_path) as db:
        manager = EpicManager(db)
        epics = manager.list_epics(status=status_value, priority=priority_value)

    if not epics:
        if json_output:
            output_json(format_json_response([], count=0))
        else:
            filter_msg = ""
            if status or priority:
                filters = []
                if status:
                    filters.append(f"status={status_value}")
                if priority:
                    filters.append(f"priority={priority_value}")
                filter_msg = f" matching {', '.join(filters)}"
            terminal_message(f"No epics found{filter_msg}", subject="Empty", subject_color="yellow")
        return

    if json_output:
        epics_data = [
            {
                "id": epic.id,
                "title": epic.title,
                "status": epic.status,
                "priority": epic.priority,
                "description": epic.description,
                "progress_percent": epic.progress_percent,
                "completed_count": epic.completed_count,
                "subtask_count": epic.subtask_count,
                "created_at": epic.created_at,
                "status_details": epic.status_details,
                "locked": epic.locked,
                "locked_at": str(epic.locked_at) if epic.locked_at else None,
                "file_path": epic.file_path,
            }
            for epic in epics
        ]
        output_json(format_json_response(epics_data))
    else:
        table = Table(title="Epics")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Title", style="white", no_wrap=True)
        table.add_column("Status", style="yellow")
        table.add_column("Priority", style="magenta")
        table.add_column("Progress", style="green")
        table.add_column("Lk", style="yellow", no_wrap=True)
        table.add_column("Created", style="dim")

        for epic in epics:
            status_color = {
                "TODO": "yellow",
                "UNDERWAY": "cyan",
                "COMPLETE": "green",
                "ABORTED": "red",
            }.get(epic.status or "TODO", "white")

            status_text = Text(epic.status or "UNKNOWN", style=status_color)

            if epic.subtask_count and epic.subtask_count > 0:
                progress = f"{epic.completed_count}/{epic.subtask_count} ({epic.progress_percent}%)"
            else:
                progress = "No tasks"

            created_date = epic.created_at.format("YYYY-MM-DD")
            locked_text = Text("*", style="yellow bold") if epic.locked else Text("-", style="dim")

            table.add_row(
                epic.id,
                epic.title,
                status_text,
                epic.priority,
                progress,
                locked_text,
                created_date,
            )

        terminal_message(table, indent=False)


@app.command()
@handle_errors("Failed to show epic", handle_exc_class=SiteNineError)
def show(
    epic_id: Annotated[str, typer.Argument(help="Epic ID")],
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Show epic details (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = EpicManager(db)
        epic = CLIError.enforce_defined(manager.get_epic(epic_id), f"Epic {epic_id} not found")

        subtasks = manager.get_subtasks(epic_id)

    if json_output:
        epic_data = {
            "id": epic.id,
            "title": epic.title,
            "status": epic.status,
            "priority": epic.priority,
            "description": epic.description,
            "progress_percent": epic.progress_percent,
            "completed_count": epic.completed_count,
            "subtask_count": epic.subtask_count,
            "created_at": epic.created_at,
            "updated_at": epic.updated_at,
            "status_details": epic.status_details,
            "locked": epic.locked,
            "locked_at": str(epic.locked_at) if epic.locked_at else None,
            "file_path": epic.file_path,
            "subtasks": [
                {
                    "id": task.id,
                    "title": task.title,
                    "status": task.status,
                    "role": task.role,
                    "priority": task.priority,
                }
                for task in subtasks
            ],
        }
        output_json(format_json_response(epic_data))
        return

    status_color = {
        "TODO": "yellow",
        "UNDERWAY": "cyan",
        "COMPLETE": "green",
        "ABORTED": "red",
    }.get(epic.status or "TODO", "white")

    if epic.subtask_count and epic.subtask_count > 0:
        progress = f"{epic.completed_count}/{epic.subtask_count} tasks ({epic.progress_percent}%)"
    else:
        progress = "No tasks"

    body_parts = [
        f"Title:        {epic.title}",
        f"Status:       [{status_color}]{epic.status or 'UNKNOWN'}[/{status_color}]",
        f"Priority:     {epic.priority}",
        f"Progress:     {progress}",
        f"Locked:       {'[yellow]YES[/yellow]' if epic.locked else 'No'}",
        "",
        f"Created:      {epic.created_at}",
        f"Updated:      {epic.updated_at}",
    ]

    if epic.locked and epic.locked_at:
        body_parts.append(f"Locked At:    {epic.locked_at}")

    if epic.status_details:
        body_parts.append(f"Status Notes: {epic.status_details}")

    if epic.description:
        body_parts.extend(["", "Description:", epic.description])

    terminal_message(conjoin(*body_parts), subject=f"Epic {epic.id}")

    if subtasks:
        task_table = Table(title="Subtasks", show_header=True, box=None, padding=(0, 1))
        task_table.add_column("Task ID", style="cyan")
        task_table.add_column("Title", style="white")
        task_table.add_column("Status", style="yellow")
        task_table.add_column("Role", style="magenta")

        for task in subtasks:
            task_status_color = {
                "TODO": "yellow",
                "UNDERWAY": "cyan",
                "COMPLETE": "green",
                "ABORTED": "red",
            }.get(task.status, "white")

            task_table.add_row(
                task.id,
                task.title,
                Text(task.status, style=task_status_color),
                task.role,
            )

        terminal_message(task_table, indent=False)

    terminal_message(f"File: {epic.file_path}", subject="Path", subject_color="dim")


@app.command()
@handle_errors("Failed to update epic", handle_exc_class=SiteNineError)
def update(
    epic_id: Annotated[str, typer.Argument(help="Epic ID")],
    title: Annotated[str | None, typer.Option("--title", "-t", help="New title")] = None,
    description: Annotated[str | None, typer.Option("--description", "-d", help="New description")] = None,
    priority: Annotated[str | None, typer.Option("--priority", "-p", help="New priority")] = None,
) -> None:
    """Update epic fields (typically used by: humans)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = EpicManager(db)
        CLIError.enforce_defined(manager.get_epic(epic_id), f"Epic {epic_id} not found")

        updates: dict[str, str] = {}
        if title:
            updates["title"] = title
        if description is not None:  # Allow empty string to clear description
            updates["description"] = description
        if priority:
            with CLIError.handle_errors("Invalid priority", handle_exc_class=ValueError):
                priority_enum = Priority.from_string(priority)
                updates["priority"] = priority_enum.value

        if not updates:
            terminal_message("No updates provided", subject="Warning", subject_color="yellow")
            return

        updated_epic = manager.update_epic(epic_id, **updates)

        try:
            opencode_dir = get_opencode_dir()
            manager.sync_epic_file(updated_epic, opencode_dir)
        except Exception as e:
            terminal_message(
                f"Failed to update markdown file: {e}",
                subject="Warning",
                subject_color="yellow",
            )

    body_parts = [f"Updated epic {epic_id}"]
    for field, value in updates.items():
        body_parts.append(f"{field.title()}: {value}")

    terminal_message(conjoin(*body_parts), subject="Success", subject_color="green")


@app.command(name="abort")
@handle_errors("Failed to abort epic", handle_exc_class=SiteNineError)
def abort_epic(
    epic_id: Annotated[str, typer.Argument(help="Epic ID")],
    reason: Annotated[str, typer.Option("--reason", "-r", help="Reason for aborting")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation prompt")] = False,
) -> None:
    """Abort an epic and all its subtasks (typically used by: humans)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = EpicManager(db)
        epic = CLIError.enforce_defined(manager.get_epic(epic_id), f"Epic {epic_id} not found")

        if epic.status == "ABORTED":
            terminal_message(
                f"Epic {epic_id} is already aborted",
                subject="Warning",
                subject_color="yellow",
            )
            return

        subtasks = manager.get_subtasks(epic_id)

        if not yes:
            terminal_message(
                conjoin(
                    f"This will abort epic {epic_id} and all its subtasks",
                    "",
                    f"Epic: {epic.title}",
                    f"Subtasks: {len(subtasks)} task(s) will be aborted",
                ),
                subject="Warning",
                subject_color="yellow",
            )

            if subtasks:
                task_lines = ["Tasks to be aborted:"]
                for task in subtasks[:5]:
                    task_lines.append(f"  - {task.id}: {task.title}")
                if len(subtasks) > 5:
                    task_lines.append(f"  ... and {len(subtasks) - 5} more")
                terminal_message(conjoin(*task_lines))

            terminal_message(f"Reason: {reason}")

            confirm = typer.confirm("Are you sure you want to abort this epic?")
            if not confirm:
                terminal_message("Abort cancelled", subject="Cancelled", subject_color="yellow")
                raise typer.Exit(0)

        manager.abort_epic(epic_id, reason)

        try:
            opencode_dir = get_opencode_dir()
            aborted_epic = manager.get_epic(epic_id)
            if aborted_epic:
                manager.sync_epic_file(aborted_epic, opencode_dir)
        except Exception as e:
            terminal_message(
                f"Failed to update markdown file: {e}",
                subject="Warning",
                subject_color="yellow",
            )

    terminal_message(
        conjoin(
            f"Aborted epic {epic_id}",
            f"Reason: {reason}",
            f"Subtasks aborted: {len(subtasks)}",
        ),
        subject="Aborted",
        subject_color="red",
    )


@app.command()
@handle_errors("Failed to sync epic files", handle_exc_class=SiteNineError)
def sync(
    epic_id: Annotated[
        str | None, typer.Option("--epic", "-e", help="Sync specific epic (syncs all if not provided)")
    ] = None,
) -> None:
    """Synchronize epic markdown files with database (typically used by: both)"""
    db_path = require_db_path()
    try:
        opencode_dir = get_opencode_dir()
    except FileNotFoundError:
        raise CLIError(".opencode directory not found. Run 's9 init' first.")

    with Database(db_path) as db:
        manager = EpicManager(db)
        if epic_id:
            epic = CLIError.enforce_defined(manager.get_epic(epic_id), f"Epic {epic_id} not found")

            manager.sync_epic_file(epic, opencode_dir)
            terminal_message(f"Synced epic {epic_id}", subject="Success", subject_color="green")
        else:
            epics = manager.list_epics()
            for epic in epics:
                manager.sync_epic_file(epic, opencode_dir)

            terminal_message(f"Synced {len(epics)} epic(s)", subject="Success", subject_color="green")


@app.command(name="link-adr")
@handle_errors("Failed to link ADR to epic", handle_exc_class=SiteNineError)
def link_adr(
    epic_id: Annotated[str, typer.Argument(help="Epic ID")],
    adr_id: Annotated[str, typer.Argument(help="ADR ID (e.g., ADR-001)")],
) -> None:
    """Link an ADR to an epic (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = EpicManager(db)
        CLIError.enforce_defined(manager.get_epic(epic_id), f"Epic {epic_id} not found")

        adr_manager = ADRManager(db)
        adr_manager.link_to_epic(adr_id, epic_id)

    terminal_message(f"Linked ADR {adr_id} to epic {epic_id}", subject="Success", subject_color="green")


@app.command(name="unlink-adr")
@handle_errors("Failed to unlink ADR from epic", handle_exc_class=SiteNineError)
def unlink_adr(
    epic_id: Annotated[str, typer.Argument(help="Epic ID")],
    adr_id: Annotated[str, typer.Argument(help="ADR ID (e.g., ADR-001)")],
) -> None:
    """Unlink an ADR from an epic (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = EpicManager(db)
        CLIError.enforce_defined(manager.get_epic(epic_id), f"Epic {epic_id} not found")

        adr_manager = ADRManager(db)
        adr_manager.unlink_from_epic(adr_id, epic_id)

    terminal_message(f"Unlinked ADR {adr_id} from epic {epic_id}", subject="Success", subject_color="green")


@app.command(name="lock")
@handle_errors("Failed to lock epic", handle_exc_class=SiteNineError)
def lock_epic(
    epic_id: Annotated[str, typer.Argument(help="Epic ID")],
) -> None:
    """Lock an epic to prevent agents from claiming its tasks (Director-only)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = EpicManager(db)
        locked_epic = manager.lock_epic(epic_id)

    terminal_message(
        conjoin(
            f"Epic {epic_id} is now locked",
            f"Title: {locked_epic.title}",
            "Agents cannot claim tasks belonging to this epic until it is unlocked.",
        ),
        subject="Locked",
        subject_color="yellow",
    )


@app.command(name="unlock")
@handle_errors("Failed to unlock epic", handle_exc_class=SiteNineError)
def unlock_epic(
    epic_id: Annotated[str, typer.Argument(help="Epic ID")],
) -> None:
    """Unlock an epic to allow agents to claim its tasks again (Director-only)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = EpicManager(db)
        unlocked_epic = manager.unlock_epic(epic_id)

    terminal_message(
        conjoin(
            f"Epic {epic_id} is now unlocked",
            f"Title: {unlocked_epic.title}",
            "Agents can now claim tasks belonging to this epic.",
        ),
        subject="Unlocked",
        subject_color="green",
    )
