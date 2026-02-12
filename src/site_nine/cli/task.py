from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table
from snick import conjoin
from typerdrive import handle_errors, terminal_message

from site_nine.adrs import ADRManager
from site_nine.blocks import BlockManager
from site_nine.cli.json_utils import format_json_response, output_json
from site_nine.cli.utils import CLIError, require_db_path, require_opencode_dir, open_in_editor
from site_nine.core.database import Database
from site_nine.core.roles import Role
from site_nine.core.types import Priority
from site_nine.dependencies import DependencyManager
from site_nine.epics import EpicManager
from site_nine.exceptions import SiteNineError
from site_nine.tasks import TaskManager

app = typer.Typer(help="Manage tasks")


@app.command()
@handle_errors("Failed to list tasks", handle_exc_class=SiteNineError)
def list(
    role: Annotated[str | None, typer.Option("--role", "-r", help="Filter by role")] = None,
    status: Annotated[str | None, typer.Option("--status", "-s", help="Filter by status")] = None,
    mission: Annotated[int | None, typer.Option("--mission", "-m", help="Filter by mission ID")] = None,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """List tasks"""
    db_path = require_db_path()

    if role:
        role = role.title()
    if status:
        status = status.upper()

    with Database(db_path) as db:
        manager = TaskManager(db)
        tasks = manager.list_tasks(status=status, role=role, mission_id=mission)

    if not tasks:
        if json_output:
            output_json(format_json_response([], count=0))
        else:
            terminal_message("No tasks found.", subject="Warning", subject_color="yellow")
        return

    if json_output:
        tasks_data = [
            {
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
                "role": task.role,
                "category": task.category,
                "current_mission_id": task.current_mission_id,
                "created_at": task.created_at,
                "claimed_at": task.claimed_at,
                "closed_at": task.closed_at,
                "epic_id": task.epic_id,
            }
            for task in tasks
        ]
        output_json(format_json_response(tasks_data))
    else:
        table = Table(title="Tasks")
        table.add_column("ID", style="cyan", justify="left")
        table.add_column("Title", style="magenta")
        table.add_column("Status", style="yellow")
        table.add_column("Priority", style="red")
        table.add_column("Role", style="green")
        table.add_column("Mission", style="blue")

        for task in tasks:
            table.add_row(
                task.id,
                task.title,
                task.status,
                task.priority,
                task.role,
                str(task.current_mission_id) if task.current_mission_id else "",
            )

        terminal_message(table, indent=False)


@app.command()
@handle_errors("Failed to show task", handle_exc_class=SiteNineError)
def show(
    task_id: Annotated[str, typer.Argument(help="Task ID")],
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Show task details"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = TaskManager(db)
        task = CLIError.enforce_defined(manager.get_task(task_id), f"Task '{task_id}' not found.")

    if json_output:
        task_data = {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
            "role": task.role,
            "category": task.category,
            "description": task.description,
            "notes": task.notes,
            "current_mission_id": task.current_mission_id,
            "claimed_at": task.claimed_at,
            "closed_at": task.closed_at,
            "created_at": task.created_at,
            "file_path": task.file_path,
            "epic_id": task.epic_id,
        }
        output_json(format_json_response(task_data))
    else:
        lines = [
            f"Title: {task.title}",
            f"Status: {task.status}",
            f"Priority: {task.priority}",
            f"Role: {task.role}",
        ]
        if task.category:
            lines.append(f"Category: {task.category}")
        if task.current_mission_id:
            lines.append(f"Mission: {task.current_mission_id}")
        if task.claimed_at:
            lines.append(f"Claimed: {task.claimed_at}")
        if task.closed_at:
            lines.append(f"Closed: {task.closed_at}")
        if task.description:
            lines.append(f"Description: {task.description}")
        if task.notes:
            lines.append(f"Notes: {task.notes}")
        lines.append(f"File: {task.file_path}")
        terminal_message(conjoin(*lines), subject=f"Task {task.id}")


@app.command()
@handle_errors("Failed to claim task", handle_exc_class=SiteNineError)
def claim(
    task_id: Annotated[str, typer.Argument(help="Task ID")],
    mission: Annotated[int, typer.Option("--mission", "-m", help="Mission ID claiming the task")],
    role: Annotated[str, typer.Option("--role", "-r", help="Role of the mission claiming the task")],
) -> None:
    """Claim a task (typically used by: agents)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = TaskManager(db)
        task = CLIError.enforce_defined(manager.get_task(task_id), f"Task '{task_id}' not found.")

        if task.role != role:
            raise CLIError(
                conjoin(
                    f"Task role '{task.role}' does not match claiming role '{role}'.",
                    f"Task requires role: {task.role}",
                ),
            )

        block_manager = BlockManager(db)
        dep_manager = DependencyManager(db)

        unresolved_blocks = block_manager.get_unresolved_blocks(task_id)
        if unresolved_blocks:
            block_lines = [f"Task {task_id} is blocked by {len(unresolved_blocks)} external blocker(s):"]
            for block in unresolved_blocks:
                block_lines.append(f"  - {block.block_type}: {block.description}")
            block_lines.append("")
            block_lines.append("Use 's9 block resolve <block-id>' to unblock this task.")
            raise CLIError(conjoin(*block_lines))

        incomplete_deps = dep_manager.check_task_blocked_by_dependencies(task_id)
        if incomplete_deps:
            dep_lines = [f"Task {task_id} is blocked by {len(incomplete_deps)} incomplete dependency(ies):"]
            for dep_id in incomplete_deps:
                dep_lines.append(f"  - {dep_id}")
            dep_lines.append("")
            dep_lines.append("These tasks must be completed first.")
            raise CLIError(conjoin(*dep_lines))

        manager.claim_task(task_id, mission, role)

    terminal_message(
        f"Task {task_id} claimed for mission {mission}",
        subject="Done",
        subject_color="green",
    )


@app.command()
@handle_errors("Failed to update task", handle_exc_class=SiteNineError)
def update(
    task_id: Annotated[str, typer.Argument(help="Task ID")],
    status: Annotated[str, typer.Option("--status", "-s", help="New status")],
    notes: Annotated[str | None, typer.Option("--notes", "-n", help="Progress notes")] = None,
) -> None:
    """Update task status (typically used by: agents)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = TaskManager(db)
        CLIError.enforce_defined(manager.get_task(task_id), f"Task '{task_id}' not found.")

        status_upper = status.upper()
        manager.update_status(task_id, status_upper, notes)

    terminal_message(
        f"Task {task_id} updated to {status_upper}",
        subject="Done",
        subject_color="green",
    )


@app.command()
@handle_errors("Failed to close task", handle_exc_class=SiteNineError)
def close(
    task_id: Annotated[str, typer.Argument(help="Task ID")],
    status: Annotated[str, typer.Option("--status", "-s", help="Completion status")] = "COMPLETE",
    notes: Annotated[str | None, typer.Option("--notes", "-n", help="Closing notes")] = None,
) -> None:
    """Close a task (typically used by: agents)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = TaskManager(db)
        CLIError.enforce_defined(manager.get_task(task_id), f"Task '{task_id}' not found.")

        status_upper = status.upper()
        CLIError.require_condition(
            status_upper in ("COMPLETE", "ABORTED"),
            f"Invalid close status '{status}'. Use COMPLETE or ABORTED.",
        )

        manager.update_status(task_id, status_upper, notes)

    terminal_message(
        f"Task {task_id} closed with status: {status_upper}",
        subject="Done",
        subject_color="green",
    )


@app.command()
@handle_errors("Failed to create task", handle_exc_class=SiteNineError)
def create(
    title: Annotated[
        str,
        typer.Option(
            "--title",
            "-t",
            help="Brief task description (e.g., 'Add rate limiting to API endpoints')",
        ),
    ],
    role: Annotated[
        str,
        typer.Option(
            "--role",
            "-r",
            help="Agent role responsible for this task",
        ),
    ],
    priority: Annotated[
        str,
        typer.Option(
            "--priority",
            "-p",
            help="Task priority (affects when it should be worked on)",
        ),
    ] = "MEDIUM",
    category: Annotated[
        str | None,
        typer.Option(
            "--category",
            "-c",
            help="Task category (what type of work is this?)",
        ),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option(
            "--description",
            "-d",
            help="Detailed description of what needs to be done and why",
        ),
    ] = None,
    epic: Annotated[
        str | None,
        typer.Option(
            "--epic",
            "-e",
            help="Epic ID to link this task to (e.g., EPC-H-0001)",
        ),
    ] = None,
) -> None:
    """Create a new task (task ID auto-generated based on role and priority)"""
    db_path = require_db_path()

    with CLIError.handle_errors("Invalid role or priority", handle_exc_class=ValueError):
        role_enum = Role.from_string(role)
        priority_enum = Priority.from_string(priority)

    with Database(db_path) as db:
        manager = TaskManager(db)
        task_id = manager.generate_task_id(role_enum.title_case, priority_enum.value)

        try:
            manager.create_task(
                task_id=task_id,
                title=title,
                role=role_enum.title_case,
                priority=priority_enum.value,
                category=category,
                description=description,
            )
            terminal_message(
                f"Created task {task_id}: {title}",
                subject="Done",
                subject_color="green",
            )

            if epic:
                epic_manager = EpicManager(db)
                try:
                    epic_manager.link_task(task_id, epic)
                    terminal_message(
                        f"Linked to epic: {epic}",
                        subject="Info",
                        subject_color="cyan",
                    )
                except ValueError as e:
                    terminal_message(
                        str(e),
                        subject="Warning",
                        subject_color="yellow",
                    )

        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                raise CLIError(f"Task '{task_id}' already exists.")
            raise


@app.command()
@handle_errors("Failed to list mission tasks", handle_exc_class=SiteNineError)
def mine(
    mission: Annotated[int, typer.Option("--mission", "-m", help="Mission ID")],
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Show tasks claimed by a mission"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = TaskManager(db)
        tasks = manager.list_tasks(mission_id=mission)

    if not tasks:
        if json_output:
            output_json(format_json_response([]))
            return
        terminal_message(
            f"No tasks found for mission {mission}",
            subject="Warning",
            subject_color="yellow",
        )
        return

    if json_output:
        data = []
        for task in tasks:
            task_dict = {
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
                "role": task.role,
                "category": task.category,
                "current_mission_id": task.current_mission_id,
                "claimed_at": task.claimed_at,
                "closed_at": task.closed_at,
            }
            data.append(task_dict)

        output_json(format_json_response(data))
        return

    table = Table(title=f"Tasks for Mission {mission}")
    table.add_column("ID", style="cyan", justify="left")
    table.add_column("Title", style="magenta")
    table.add_column("Status", style="yellow")
    table.add_column("Priority", style="red")
    table.add_column("Role", style="green")

    for task in tasks:
        title = task.title
        if len(title) > 40:
            title = title[:37] + "..."

        table.add_row(
            task.id,
            title,
            task.status,
            task.priority,
            task.role,
        )

    terminal_message(table, indent=False)
    terminal_message(f"Total: {len(tasks)} task(s)", subject="Info", subject_color="cyan")


@app.command()
@handle_errors("Failed to generate task report", handle_exc_class=SiteNineError)
def report(
    active_only: Annotated[
        bool, typer.Option("--active-only", help="Show only active tasks (excludes COMPLETE, ABORTED)")
    ] = False,
    role: Annotated[str | None, typer.Option("--role", "-r", help="Filter by role")] = None,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Generate task summary report"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = TaskManager(db)
        tasks = manager.generate_report(active_only=active_only, role=role)

    if not tasks:
        if json_output:
            output_json(format_json_response([]))
            return
        terminal_message("No tasks found matching criteria.", subject="Warning", subject_color="yellow")
        return

    if json_output:
        data = [
            {
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
                "role": task.role,
                "category": task.category,
                "current_mission_id": task.current_mission_id,
                "claimed_at": task.claimed_at,
                "closed_at": task.closed_at,
                "actual_hours": task.actual_hours,
                "created_at": task.created_at,
            }
            for task in tasks
        ]
        output_json(format_json_response(data))
        return

    table = Table(title="Task Report")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Status", style="yellow")
    table.add_column("Priority", style="magenta")
    table.add_column("Role", style="green")
    table.add_column("Mission", style="blue")

    for task in tasks:
        title = task.title
        if len(title) > 40:
            title = title[:37] + "..."

        mission_str = str(task.current_mission_id) if task.current_mission_id else "-"

        table.add_row(
            task.id,
            title,
            task.status,
            task.priority,
            task.role,
            mission_str,
        )

    terminal_message(table, indent=False)
    terminal_message(f"Total: {len(tasks)} task(s)", subject="Info", subject_color="cyan")


@app.command()
@handle_errors("Failed to search tasks", handle_exc_class=SiteNineError)
def search(
    keyword: Annotated[str, typer.Argument(help="Keyword to search for")],
    active_only: Annotated[bool, typer.Option("--active-only", help="Show only active tasks")] = False,
    role: Annotated[str | None, typer.Option("--role", "-r", help="Filter by role")] = None,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Search tasks by keyword"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = TaskManager(db)
        tasks = manager.search_tasks(keyword=keyword, active_only=active_only, role=role)

    if not tasks:
        if json_output:
            output_json(format_json_response([]))
            return
        terminal_message(f"No tasks found matching '{keyword}'.", subject="Warning", subject_color="yellow")
        return

    if json_output:
        data = [
            {
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "priority": task.priority,
                "role": task.role,
                "current_mission_id": task.current_mission_id,
                "created_at": task.created_at,
            }
            for task in tasks
        ]
        output_json(format_json_response(data))
        return

    table = Table(title=f"Search Results: '{keyword}'")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Status", style="yellow")
    table.add_column("Priority", style="magenta")
    table.add_column("Role", style="green")

    for task in tasks:
        title = task.title
        if len(title) > 50:
            title = title[:47] + "..."

        table.add_row(
            task.id,
            title,
            task.status,
            task.priority,
            task.role,
        )

    terminal_message(table, indent=False)
    terminal_message(f"Total: {len(tasks)} task(s)", subject="Info", subject_color="cyan")


@app.command()
@handle_errors("Failed to suggest next tasks", handle_exc_class=SiteNineError)
def next(
    role: Annotated[str | None, typer.Option("--role", "-r", help="Filter by role")] = None,
    count: Annotated[int, typer.Option("--count", "-c", help="Number of suggestions")] = 3,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Suggest next tasks to work on"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = TaskManager(db)
        todo_tasks = manager.suggest_next_tasks(role=role, count=count)

    if not todo_tasks:
        if json_output:
            output_json(format_json_response({"todo_tasks": []}))
            return
        if role:
            terminal_message(
                f"No TODO tasks for role '{role}'.",
                subject="Warning",
                subject_color="yellow",
            )
        else:
            terminal_message("No TODO tasks found.", subject="Warning", subject_color="yellow")
        return

    if json_output:
        data = {
            "todo_tasks": [
                {
                    "id": task.id,
                    "title": task.title,
                    "priority": task.priority,
                    "role": task.role,
                    "created_at": task.created_at,
                }
                for task in todo_tasks
            ],
        }
        output_json(format_json_response(data))
        return

    lines = ["Suggested Tasks to Start:"]
    for i, task in enumerate(todo_tasks, 1):
        lines.append(f"{i}. {task.id} - {task.title}")
        lines.append(f"   Priority: {task.priority} | Role: {task.role}")
    terminal_message(conjoin(*lines), subject="Next", subject_color="green")

    terminal_message(
        conjoin(
            "To claim a task: s9 task claim <TASK_ID> --mission <id> --role <role>",
            "To see details: s9 task show <TASK_ID>",
        ),
        subject="Tip",
        subject_color="cyan",
    )


@app.command(name="add-dependency")
@handle_errors("Failed to add task dependency", handle_exc_class=SiteNineError)
def add_dependency(
    task_id: Annotated[str, typer.Argument(help="Task ID")],
    depends_on: Annotated[str, typer.Argument(help="Task ID this depends on")],
) -> None:
    """Add a task dependency"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = TaskManager(db)
        for tid in [task_id, depends_on]:
            CLIError.require_condition(manager.get_task(tid) is not None, f"Task {tid} does not exist.")

        dep_manager = DependencyManager(db)
        dep_manager.add_dependency(task_id, depends_on)

    terminal_message(
        f"Added dependency: {task_id} depends on {depends_on}",
        subject="Done",
        subject_color="green",
    )


@app.command()
@handle_errors("Failed to sync task files", handle_exc_class=SiteNineError)
def sync(
    task_id: Annotated[
        str | None, typer.Option("--task", "-t", help="Sync specific task (syncs all if not provided)")
    ] = None,
) -> None:
    """Synchronize task markdown files with database"""
    db_path = require_db_path()
    opencode_dir = require_opencode_dir()

    with Database(db_path) as db:
        manager = TaskManager(db)
        if task_id:
            task = CLIError.enforce_defined(manager.get_task(task_id), f"Task {task_id} not found.")

            manager.sync_task_file(task, opencode_dir)
            terminal_message(
                f"Synced task {task_id}",
                subject="Done",
                subject_color="green",
            )
        else:
            tasks = manager.list_tasks()
            for task in tasks:
                manager.sync_task_file(task, opencode_dir)

            terminal_message(
                f"Synced {len(tasks)} task(s)",
                subject="Done",
                subject_color="green",
            )


@app.command()
@handle_errors("Failed to link task to epic", handle_exc_class=SiteNineError)
def link(
    task_id: Annotated[str, typer.Argument(help="Task ID to link")],
    epic_id: Annotated[str, typer.Argument(help="Epic ID to link to (e.g., EPC-H-0001)")],
) -> None:
    """Link a task to an epic"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = TaskManager(db)
        CLIError.enforce_defined(manager.get_task(task_id), f"Task {task_id} not found.")

        epic_manager = EpicManager(db)
        with CLIError.handle_errors("Failed to link task to epic", handle_exc_class=ValueError):
            epic_manager.link_task(task_id, epic_id)

    terminal_message(
        f"Linked task {task_id} to epic {epic_id}",
        subject="Done",
        subject_color="green",
    )


@app.command()
@handle_errors("Failed to unlink task from epic", handle_exc_class=SiteNineError)
def unlink(
    task_id: Annotated[str, typer.Argument(help="Task ID to unlink from its epic")],
) -> None:
    """Remove a task from its epic"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = TaskManager(db)
        task = CLIError.enforce_defined(manager.get_task(task_id), f"Task {task_id} not found.")

        if not task.epic_id:
            terminal_message(
                f"Task {task_id} is not linked to any epic.",
                subject="Warning",
                subject_color="yellow",
            )
            return

        epic_manager = EpicManager(db)
        epic_id = task.epic_id
        epic_manager.unlink_task(task_id)

    terminal_message(
        f"Unlinked task {task_id} from epic {epic_id}",
        subject="Done",
        subject_color="green",
    )


@app.command(name="link-adr")
@handle_errors("Failed to link ADR to task", handle_exc_class=SiteNineError)
def link_adr(
    task_id: Annotated[str, typer.Argument(help="Task ID")],
    adr_id: Annotated[str, typer.Argument(help="ADR ID (e.g., ADR-001)")],
) -> None:
    """Link an ADR to a task"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = TaskManager(db)
        CLIError.enforce_defined(manager.get_task(task_id), f"Task {task_id} not found.")

        with CLIError.handle_errors("Failed to link ADR to task", handle_exc_class=ValueError):
            adr_manager = ADRManager(db)
            adr_manager.link_to_task(adr_id, task_id)

    terminal_message(
        f"Linked ADR {adr_id} to task {task_id}",
        subject="Done",
        subject_color="green",
    )


@app.command(name="unlink-adr")
@handle_errors("Failed to unlink ADR from task", handle_exc_class=SiteNineError)
def unlink_adr(
    task_id: Annotated[str, typer.Argument(help="Task ID")],
    adr_id: Annotated[str, typer.Argument(help="ADR ID (e.g., ADR-001)")],
) -> None:
    """Unlink an ADR from a task"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = TaskManager(db)
        CLIError.enforce_defined(manager.get_task(task_id), f"Task {task_id} not found.")

        with CLIError.handle_errors("Failed to unlink ADR from task", handle_exc_class=ValueError):
            adr_manager = ADRManager(db)
            adr_manager.unlink_from_task(adr_id, task_id)

    terminal_message(
        f"Unlinked ADR {adr_id} from task {task_id}",
        subject="Done",
        subject_color="green",
    )


@app.command(name="modify")
@handle_errors("Failed to modify task", handle_exc_class=SiteNineError)
def modify(
    task_id: Annotated[str, typer.Argument(help="Task ID")],
    title: Annotated[str | None, typer.Option("--title", "-t", help="New title")] = None,
    description: Annotated[str | None, typer.Option("--description", "-d", help="New description")] = None,
    priority: Annotated[Priority | None, typer.Option("--priority", "-p", help="New priority")] = None,
    category: Annotated[str | None, typer.Option("--category", "-c", help="New category")] = None,
) -> None:
    """Modify task metadata (title, description, priority, category)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = TaskManager(db)
        CLIError.enforce_defined(manager.get_task(task_id), f"Task {task_id} not found.")

        updates = {}
        if title is not None:
            updates["title"] = title
        if description is not None:
            updates["description"] = description
        if priority is not None:
            updates["priority"] = priority.value
        if category is not None:
            updates["category"] = category

        CLIError.require_condition(
            bool(updates), "No changes specified. Use --title, --description, --priority, or --category."
        )

        manager.update_task(task_id, **updates)

        opencode_dir = require_opencode_dir()
        updated_task = manager.get_task(task_id)
        if updated_task:
            manager.sync_task_file(updated_task, opencode_dir)

    terminal_message(
        f"Updated task {task_id}",
        subject="Done",
        subject_color="green",
    )


@app.command(name="edit")
@handle_errors("Failed to edit task", handle_exc_class=SiteNineError)
def edit(
    task_id: Annotated[str, typer.Argument(help="Task ID")],
) -> None:
    """Open task file in $EDITOR for manual editing"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = TaskManager(db)
        task = CLIError.enforce_defined(manager.get_task(task_id), f"Task {task_id} not found.")

    opencode_dir = require_opencode_dir()
    task_file = Path(task.file_path)
    if not task_file.is_absolute():
        task_file = opencode_dir / task_file

    open_in_editor(f"Task {task_id}", task_file)
    terminal_message(
        f"Run 's9 task sync {task_id}' to update database.",
        subject="Tip",
        subject_color="cyan",
    )
