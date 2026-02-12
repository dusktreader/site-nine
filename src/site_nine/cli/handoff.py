from __future__ import annotations

import json
from typing import Annotated, List

import pendulum
import typer
from rich.table import Table
from snick import conjoin
from typerdrive import handle_errors, terminal_message

from site_nine.cli.json_utils import format_json_response, output_json
from site_nine.cli.utils import abort, abort_unless, require_db_path
from site_nine.core.database import Database
from site_nine.core.roles import Role
from site_nine.handoffs import HandoffManager

app = typer.Typer(help="Manage work handoffs between missions")


@app.command()
@handle_errors("Failed to create handoff")
def create(
    task_id: Annotated[str, typer.Option("--task", "-t", help="Task ID being handed off")],
    from_mission: Annotated[int, typer.Option("--from-mission", "-f", help="Mission ID creating the handoff")],
    to_role: Annotated[str, typer.Option("--to-role", "-r", help="Role that should receive this handoff")],
    summary: Annotated[str, typer.Option("--summary", "-s", help="Brief summary of what's being handed off")],
    files: Annotated[
        List[str] | None, typer.Option("--file", help="Relevant file path (can specify multiple times)")
    ] = None,
    acceptance_criteria: Annotated[str | None, typer.Option("--criteria", "-c", help="What defines completion")] = None,
    notes: Annotated[str | None, typer.Option("--notes", "-n", help="Additional context or instructions")] = None,
) -> None:
    """Create a work handoff to another role (typically used by: agents)"""
    db_path = require_db_path()

    try:
        Role.from_string(to_role)
    except ValueError:
        valid_roles_str = ", ".join(Role.all_values())
        abort(f"Invalid role '{to_role}'. Valid roles: {valid_roles_str}")
    to_role = to_role.title()

    with Database(db_path) as db:
        manager = HandoffManager(db)
        handoff_id = manager.create_handoff(
            task_id=task_id,
            from_mission_id=from_mission,
            to_role=to_role,
            summary=summary,
            files=files if files else None,
            acceptance_criteria=acceptance_criteria,
            notes=notes,
        )

    body_parts = [
        f"Created handoff #{handoff_id}",
        f"  Task: {task_id}",
        f"  To role: {to_role}",
        f"  Summary: {summary}",
    ]
    if files:
        body_parts.append(f"  Files: {len(files)} file(s)")

    terminal_message(conjoin(*body_parts), subject="Handoff Created", subject_color="green")


@app.command()
@handle_errors("Failed to list handoffs")
def list(
    role: Annotated[str | None, typer.Option("--role", "-r", help="Filter by target role")] = None,
    from_mission: Annotated[int | None, typer.Option("--from-mission", help="Filter by source mission")] = None,
    include_deleted: Annotated[bool, typer.Option("--include-deleted", help="Include deleted handoffs")] = False,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """List handoffs (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = HandoffManager(db)
        handoffs = manager.list_handoffs(
            to_role=role,
            from_mission_id=from_mission,
            include_deleted=include_deleted,
        )

    if not handoffs:
        if json_output:
            output_json(format_json_response([]))
            return

        filter_msg = ""
        if role or from_mission:
            filter_parts = []
            if role:
                filter_parts.append(f"role={role}")
            if from_mission:
                filter_parts.append(f"from_mission={from_mission}")
            filter_msg = f" ({', '.join(filter_parts)})"
        terminal_message(
            f"No handoffs found{filter_msg}.",
            subject="Empty",
            subject_color="yellow",
        )
        return

    if json_output:
        data = []
        for handoff in handoffs:
            handoff_dict = {
                "id": handoff.id,
                "task_id": handoff.task_id,
                "to_role": handoff.to_role,
                "from_mission_id": handoff.from_mission_id,
                "summary": handoff.summary,
                "acceptance_criteria": handoff.acceptance_criteria,
                "files": json.loads(handoff.files) if handoff.files else None,
                "notes": handoff.notes,
                "created_at": handoff.created_at,
                "deleted_at": handoff.deleted_at,
            }
            data.append(handoff_dict)

        output_json(format_json_response(data))
        return

    table = Table(title="Handoffs")
    table.add_column("ID", style="cyan", justify="right", width=4)
    table.add_column("Task", style="magenta", width=12)
    table.add_column("To Role", style="blue", width=15)
    table.add_column("Summary", style="white", width=40)
    table.add_column("Created", style="dim", width=10)
    if include_deleted:
        table.add_column("Status", style="yellow", width=10)

    for handoff in handoffs:
        try:
            created_at_str = str(handoff.created_at)
            created_dt = pendulum.parse(created_at_str)
            created_str = created_dt.diff_for_humans()  # type: ignore[union-attr]
        except Exception:
            created_str = str(handoff.created_at)[:16]

        row_data = [
            str(handoff.id),
            handoff.task_id,
            handoff.to_role,
            handoff.summary[:60] + "..." if len(handoff.summary) > 60 else handoff.summary,
            created_str,
        ]

        if include_deleted:
            status = "[red]deleted[/red]" if handoff.deleted_at else "[green]active[/green]"
            row_data.append(status)

        table.add_row(*row_data)

    terminal_message(table, indent=False)


@app.command()
@handle_errors("Failed to show handoff")
def show(
    handoff_id: Annotated[int, typer.Argument(help="Handoff ID")],
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Show handoff details (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = HandoffManager(db)
        handoff = manager.get_handoff(handoff_id)

    abort_unless(handoff, f"Handoff #{handoff_id} not found.")

    if json_output:
        handoff_dict = {
            "id": handoff.id,
            "task_id": handoff.task_id,
            "to_role": handoff.to_role,
            "from_mission_id": handoff.from_mission_id,
            "summary": handoff.summary,
            "acceptance_criteria": handoff.acceptance_criteria,
            "files": json.loads(handoff.files) if handoff.files else None,
            "notes": handoff.notes,
            "created_at": handoff.created_at,
            "deleted_at": handoff.deleted_at,
        }

        output_json(format_json_response(handoff_dict))
        return

    if handoff.deleted_at:
        status_display = "Deleted"
    else:
        status_display = "Pending"

    body_parts = [
        f"Status:       {status_display}",
        f"Task:         {handoff.task_id}",
        f"To Role:      {handoff.to_role}",
        f"From Mission: {handoff.from_mission_id}",
        "",
        "Summary:",
        handoff.summary,
    ]

    if handoff.acceptance_criteria:
        body_parts.extend(["", "Acceptance Criteria:", handoff.acceptance_criteria])

    if handoff.files:
        body_parts.extend(["", "Relevant Files:"])
        files = json.loads(handoff.files)
        for file in files:
            body_parts.append(f"  - {file}")

    if handoff.notes:
        body_parts.extend(["", "Notes:", handoff.notes])

    body_parts.extend(["", f"Created:  {handoff.created_at}"])

    if handoff.deleted_at:
        body_parts.append(f"Deleted:  {handoff.deleted_at}")

    terminal_message(conjoin(*body_parts), subject=f"Handoff #{handoff.id}")


@app.command()
@handle_errors("Failed to delete handoff")
def delete(
    handoff_id: Annotated[int, typer.Argument(help="Handoff ID")],
) -> None:
    """
    Delete a handoff (soft delete).

    Note: Handoffs are automatically deleted when claimed via task claim.
    This command is for manual cleanup only.

    (typically used by: both)
    """
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = HandoffManager(db)
        handoff = manager.get_handoff(handoff_id)
        abort_unless(handoff, f"Handoff #{handoff_id} not found.")

        if handoff.deleted_at:
            terminal_message(
                f"Handoff #{handoff_id} is already deleted.",
                subject="Warning",
                subject_color="yellow",
            )
            return

        manager.delete_handoff(handoff_id)

    terminal_message(
        conjoin(
            f"Deleted handoff #{handoff_id}",
            f"  Task: {handoff.task_id}",
        ),
        subject="Deleted",
        subject_color="green",
    )
