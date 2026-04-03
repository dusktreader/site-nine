"""Possession management commands (list, show, summary, update, suspend, resume)"""

from __future__ import annotations

import subprocess
from typing import Annotated

import typer
from rich.table import Table
from snick import conjoin
from typerdrive import handle_errors, terminal_message

from site_nine.cli.json_utils import format_json_error, format_json_response, output_json
from site_nine.cli.utils import CLIError, require_db_path
from site_nine.core.database import Database
from site_nine.core.roles import Role
from site_nine.core.settings import SiteNineSettings
from site_nine.exceptions import SiteNineError
from site_nine.possessions import PossessionManager
from site_nine.possessions.models import Possession
from site_nine.possessions.types import PossessionStatus

app = typer.Typer(help="Manage possessions")


@app.command("list")
@handle_errors("Failed to list possessions", handle_exc_class=SiteNineError)
def list_possessions(
    active_only: Annotated[bool, typer.Option("--active-only", help="Show only active possessions")] = False,
    role: Annotated[str | None, typer.Option("--role", "-r", help="Filter by role")] = None,
    epic: Annotated[str | None, typer.Option("--epic", "-e", help="Filter by epic ID")] = None,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """List possessions — typically used by: humans"""
    db_path = require_db_path()

    if role:
        role = role.title()

    with Database(db_path) as db:
        manager = PossessionManager(db)
        possessions = manager.list_possessions(active_only=active_only, role=role, epic_id=epic)

        possession_task_map: dict[int, str | None] = {}
        active_ids = [p.id for p in possessions if p.end_time is None and p.id is not None]
        if active_ids:
            placeholders = ", ".join(f":m{i}" for i in range(len(active_ids)))
            params = {f"m{i}": mid for i, mid in enumerate(active_ids)}
            task_rows = db.execute_query(
                f"SELECT id, current_possession_id FROM tasks WHERE current_possession_id IN ({placeholders}) AND status = 'UNDERWAY'",
                params,
            )
            for row in task_rows:
                possession_task_map[row["current_possession_id"]] = row["id"]

    def _get_availability(possession: Possession) -> str:
        if possession.status == PossessionStatus.EXORCISED:
            return "Ended"
        if possession.desk_mode_active:
            if possession.epic_id:
                return f"Desk ({possession.epic_id})"
            return "Desk (All)"
        mid = possession.id or 0
        current_task_id = possession_task_map.get(mid)
        if possession.epic_id:
            return f"Working ({possession.epic_id})"
        if current_task_id:
            return f"Working ({current_task_id})"
        return "Working"

    if not possessions:
        if json_output:
            output_json(format_json_response([], count=0))
        else:
            terminal_message("No possessions found.", subject="Warning", subject_color="yellow")
        return

    if json_output:
        possessions_data = [
            {
                "id": p.id,
                "persona_name": p.daemon_name,
                "role": p.role,
                "codename": "",
                "status": p.status.value,
                "epic_id": p.epic_id,
                "desk_mode_active": p.desk_mode_active,
                "current_task_id": possession_task_map.get(p.id or 0),
                "availability": _get_availability(p),
                "start_time": p.start_time,
                "end_time": p.end_time,
                "start_date": "",
                "objective": "",
                "mission_file": p.possession_log,
            }
            for p in possessions
        ]
        output_json(format_json_response(possessions_data))
    else:
        table = Table(title="Agent Sessions")
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("Daemon", style="magenta")
        table.add_column("Role", style="green")
        table.add_column("Codename", style="yellow")
        table.add_column("Availability", style="bright_green")
        table.add_column("Start Time", style="blue")
        table.add_column("End Time", style="blue")

        for p in possessions:
            table.add_row(
                str(p.id),
                p.daemon_name,
                p.role,
                "",
                _get_availability(p),
                p.start_time or "",
                p.end_time or "",
            )

        terminal_message(table, indent=False)


@app.command()
@handle_errors("Failed to show possession", handle_exc_class=SiteNineError)
def show(
    possession_id: Annotated[int, typer.Argument(help="Possession ID")],
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Show possession details — typically used by: both"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = PossessionManager(db)
        possession = manager.get_possession(possession_id)

    if not possession:
        if json_output:
            output_json(
                format_json_error(
                    error_message=f"Possession #{possession_id} not found",
                    error_code="MISSION_NOT_FOUND",
                    details={"mission_id": possession_id},
                )
            )
            raise typer.Exit(code=1)
        raise CLIError(f"Possession #{possession_id} not found.")

    status = str(possession.status)

    scope_info = None
    if possession.epic_id:
        scope_info = f"Epic-scoped ({possession.epic_id})"
    else:
        task_rows = db.execute_query(
            "SELECT id FROM tasks WHERE current_possession_id = :possession_id LIMIT 1",
            {"possession_id": possession.id},
        )
        if task_rows:
            scope_info = f"Task-scoped ({task_rows[0]['id']})"
        else:
            scope_info = "General"

    if json_output:
        possession_data = {
            "id": possession.id,
            "persona_name": possession.daemon_name,
            "codename": "",
            "role": possession.role,
            "status": status,
            "start_date": "",
            "start_time": possession.start_time,
            "end_time": possession.end_time,
            "mission_file": possession.possession_log,
            "objective": "",
            "epic_id": possession.epic_id,
            "scope": scope_info,
        }
        output_json(format_json_response(possession_data))
    else:
        lines = [
            f"Daemon: {possession.daemon_name}",
            f"Role: {possession.role}",
            f"Status: {status}",
            f"Scope: {scope_info}",
            f"Start Time: {possession.start_time}",
        ]
        if possession.end_time:
            lines.append(f"End Time: {possession.end_time}")
        lines.append(f"Possession Log: {possession.possession_log}")
        terminal_message(conjoin(*lines), subject=f"Possession #{possession.id}")


@app.command()
@handle_errors("Failed to generate possession summary", handle_exc_class=SiteNineError)
def summary(
    possession_id: Annotated[int, typer.Argument(help="Possession ID")],
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Generate possession summary from git history and database — typically used by: humans

    Auto-generates a summary showing:
    - Files changed since possession start
    - Commits made (filtered by daemon)
    - Tasks claimed and their status
    """
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = PossessionManager(db)

        try:
            possession_summary = manager.generate_summary(possession_id)
        except Exception:
            if json_output:
                output_json(
                    format_json_error(
                        error_message=f"Possession #{possession_id} not found",
                        error_code="MISSION_NOT_FOUND",
                        details={"mission_id": possession_id},
                    )
                )
                raise typer.Exit(code=1)
            raise CLIError(f"Possession #{possession_id} not found.")

    possession = possession_summary.possession

    if not json_output:
        for warning in possession_summary.warnings:
            terminal_message(warning, subject="Warning", subject_color="yellow")

    if json_output:
        summary_data = {
            "mission_id": possession.id,
            "persona_name": possession.daemon_name,
            "role": possession.role,
            "codename": "",
            "start_time": possession.start_time,
            "end_time": possession.end_time,
            "objective": "",
            "files_changed": [{"status": f.status, "file": f.file} for f in possession_summary.files_changed],
            "commits": possession_summary.commits,
            "tasks": [{"id": t.id, "title": t.title, "status": t.status} for t in possession_summary.tasks],
        }
        output_json(format_json_response(summary_data))
    else:
        lines = [
            f"Possession #{possession.id} ({possession.daemon_name} - {possession.role})",
            "",
            f"Start: {possession.start_time}",
        ]
        if possession.end_time:
            lines.append(f"End: {possession.end_time}")

        lines.append("")
        lines.append("Files Changed:")
        if possession_summary.files_changed:
            for file in possession_summary.files_changed:
                lines.append(f"  - [{file.status}] {file.file}")
        else:
            lines.append("  (No files changed or git unavailable)")

        lines.append("")
        lines.append("Commits:")
        if possession_summary.commits:
            for commit in possession_summary.commits:
                lines.append(f"  - {commit}")
        else:
            lines.append("  (No commits found)")

        lines.append("")
        lines.append("Tasks Claimed:")
        if possession_summary.tasks:
            for task in possession_summary.tasks:
                status_icon = {
                    "COMPLETE": "\u2713",
                    "UNDERWAY": "\u2192",
                    "TODO": "\u25cb",
                    "ABORTED": "\u2717",
                }.get(task.status, "?")
                lines.append(f"  {status_icon} [{task.status}] {task.id} - {task.title}")
        else:
            lines.append("  (No tasks claimed)")

        terminal_message(conjoin(*lines), subject="Summary")


@app.command()
@handle_errors("Failed to update possession", handle_exc_class=SiteNineError)
def update(
    possession_id: Annotated[int, typer.Argument(help="Possession ID to update")],
    objective: Annotated[str | None, typer.Option("--task", "-t", help="Update task summary")] = None,
    role: Annotated[str | None, typer.Option("--role", "-r", help="Update role")] = None,
) -> None:
    """Update possession metadata — typically used by: agents"""
    db_path = require_db_path()

    if not objective and not role:
        terminal_message(
            "No updates specified. Use --task or --role.",
            subject="Warning",
            subject_color="yellow",
        )
        raise typer.Exit(0)

    if role:
        valid_roles_str = ", ".join(Role.all_values())
        with CLIError.handle_errors(
            f"Invalid role: {role}. Valid values: {valid_roles_str}", handle_exc_class=ValueError
        ):
            Role.from_string(role)
        role = role.title()

    with Database(db_path) as db:
        manager = PossessionManager(db)
        possession = CLIError.enforce_defined(
            manager.get_possession(possession_id), f"Possession #{possession_id} not found."
        )

        CLIError.require_condition(
            possession.end_time is None,
            "Cannot update completed possession. Only active possessions can be updated.",
        )

        manager.update_possession(possession_id, role=role)

    lines = [f"Updated possession #{possession_id}"]
    if objective:
        lines.append(f"  Task: {objective}")
    if role:
        lines.append(f"  Role: {role}")
    terminal_message(conjoin(*lines), subject="Done", subject_color="green")


@app.command()
@handle_errors("Failed to suspend possession", handle_exc_class=SiteNineError)
def suspend(
    possession_id: Annotated[int, typer.Argument(help="Possession ID")],
    reason: Annotated[str | None, typer.Option("--reason", "-r", help="Reason for suspension")] = None,
) -> None:
    """Suspend a possession

    Transitions possession to SUSPENDED status. Typically used when a session closes
    unexpectedly or when manually pausing work. Suspended possessions can be resumed
    later with 's9 possession resume'.
    """
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = PossessionManager(db)
        possession = CLIError.enforce_defined(
            manager.get_possession(possession_id), f"Possession #{possession_id} not found."
        )

        if possession.status == PossessionStatus.EXORCISED:
            terminal_message(
                f"Possession #{possession_id} has already ended and cannot be suspended.",
                subject="Error",
                subject_color="red",
            )
            raise typer.Exit(code=1)

        if possession.status == PossessionStatus.SUSPENDED:
            terminal_message(
                f"Possession #{possession_id} is already suspended.",
                subject="Warning",
                subject_color="yellow",
            )
            raise typer.Exit(code=0)

        manager.suspend_possession(possession_id, reason=reason)

    reason_text = f"\nReason: {reason}" if reason else ""
    terminal_message(
        f"Suspended possession #{possession_id}{reason_text}",
        subject="Done",
        subject_color="green",
    )


@app.command()
@handle_errors("Failed to resume possession", handle_exc_class=SiteNineError)
def resume(
    possession_identifier: Annotated[str, typer.Argument(help="Possession ID")],
    model: Annotated[str | None, typer.Option("--model", "-m", help="Model to use (provider/model format)")] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-d", help="Show command that would be run without executing")
    ] = False,
) -> None:
    """Resume a suspended possession

    Transitions possession from SUSPENDED to ACTIVE status and launches OpenCode
    with a context message summarizing the resumed possession state.

    You can specify either a possession ID (e.g., 126) or legacy codename.
    """
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = PossessionManager(db)

        possession = None
        try:
            possession_id = int(possession_identifier)
            possession = manager.get_possession(possession_id)
        except ValueError:
            pass

        possession = CLIError.enforce_defined(
            possession,
            f"Possession '{possession_identifier}' not found. Use 's9 possession list' to see available possessions.",
        )

        if possession.status != PossessionStatus.SUSPENDED:
            terminal_message(
                f"Possession #{possession.id} is not suspended (current status: {possession.status}).\n"
                f"Only suspended possessions can be resumed.",
                subject="Error",
                subject_color="red",
            )
            raise typer.Exit(code=1)

        task_rows = db.execute_query(
            "SELECT id, title, status FROM tasks WHERE current_possession_id = :possession_id",
            {"possession_id": possession.id},
        )

        if not dry_run:
            manager.resume_possession(possession.id or 0)

    if model is None:
        settings = SiteNineSettings()
        model = settings.default_model or "github-copilot/claude-sonnet-4.5"

    context_lines = [
        f"Resuming possession #{possession.id}",
        f"Daemon: {possession.daemon_name}",
        f"Role: {possession.role}",
    ]
    if possession.epic_id:
        context_lines.append(f"Epic: {possession.epic_id}")

    if task_rows:
        context_lines.append("")
        context_lines.append("Your tasks:")
        for task in task_rows:
            status_icon = {"COMPLETE": "✓", "UNDERWAY": "→", "TODO": "○"}.get(task["status"], "?")
            context_lines.append(f"  {status_icon} {task['id']}: {task['title']}")

    context_lines.append("")
    context_lines.append("Continue working on your mission.")

    context_message = "\n".join(context_lines)

    if dry_run:
        terminal_message(
            f'Dry run - would execute: opencode --model {model} --prompt "{context_message}"',
            subject="Dry Run",
            subject_color="yellow",
        )
        return

    terminal_message(
        f"Resuming possession #{possession.id}\nLaunching OpenCode...",
        subject="Resume",
    )

    try:
        subprocess.run(["opencode", "--model", model, "--prompt", context_message], check=True)
    except subprocess.CalledProcessError as e:
        raise CLIError(f"Error launching OpenCode: {e}")
    except FileNotFoundError:
        raise CLIError("'opencode' command not found. Is OpenCode installed?")
