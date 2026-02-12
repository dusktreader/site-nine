from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table
from snick import conjoin
from typerdrive import handle_errors, terminal_message

from site_nine.cli.json_utils import format_json_error, format_json_response, output_json
from site_nine.cli.utils import CLIError, require_db_path, require_opencode_dir
from site_nine.core.database import Database
from site_nine.core.roles import Role
from site_nine.exceptions import SiteNineError
from site_nine.missions import MissionManager
from site_nine.opencode import OpenCodeSessionManager

app = typer.Typer(help="Manage missions")


@app.command()
@handle_errors("Failed to start mission", handle_exc_class=SiteNineError)
def start(
    name: Annotated[str, typer.Argument(help="Daemon name")],
    role: Annotated[str, typer.Option("--role", "-r", help="Agent role")],
    task: Annotated[str, typer.Option("--task", "-t", help="Task summary")] = "",
) -> None:
    """Start a new mission (typically used by: agents)"""
    db_path = require_db_path()

    valid_roles_str = ", ".join(Role.all_values())
    with CLIError.handle_errors(f"Invalid role: {role}. Valid values: {valid_roles_str}", handle_exc_class=ValueError):
        Role.from_string(role)
    role = role.title()

    with Database(db_path) as db:
        manager = MissionManager(db)
        mission_id = manager.start_mission(persona_name=name, role=role, objective=task)

    lines = [
        f"Started mission #{mission_id}",
        f"  Persona: {name}",
        f"  Role: {role}",
    ]
    if task:
        lines.append(f"  Objective: {task}")
    terminal_message(conjoin(*lines), subject="Done", subject_color="green")


@app.command()
@handle_errors("Failed to list missions", handle_exc_class=SiteNineError)
def list(
    active_only: Annotated[bool, typer.Option("--active-only", help="Show only active missions")] = False,
    role: Annotated[str | None, typer.Option("--role", "-r", help="Filter by role")] = None,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """List missions (typically used by: humans)"""
    db_path = require_db_path()

    if role:
        role = role.title()

    with Database(db_path) as db:
        manager = MissionManager(db)
        missions = manager.list_missions(active_only=active_only, role=role)

    if not missions:
        if json_output:
            output_json(format_json_response([], count=0))
        else:
            terminal_message("No missions found.", subject="Warning", subject_color="yellow")
        return

    if json_output:
        missions_data = [
            {
                "id": mission.id,
                "persona_name": mission.persona_name,
                "role": mission.role,
                "codename": mission.codename,
                "start_time": mission.start_time,
                "end_time": mission.end_time,
                "start_date": mission.start_date,
                "objective": mission.objective,
                "mission_file": mission.mission_file,
            }
            for mission in missions
        ]
        output_json(format_json_response(missions_data))
    else:
        table = Table(title="Agent Sessions")
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("Persona", style="magenta")
        table.add_column("Role", style="green")
        table.add_column("Codename", style="yellow")
        table.add_column("Start Time", style="blue")
        table.add_column("End Time", style="blue")

        for mission in missions:
            table.add_row(
                str(mission.id),
                mission.persona_name,
                mission.role,
                mission.codename,
                mission.start_time or "",
                mission.end_time or "",
            )

        terminal_message(table, indent=False)


@app.command()
@handle_errors("Failed to show mission", handle_exc_class=SiteNineError)
def show(
    mission_id: Annotated[int, typer.Argument(help="Mission ID")],
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Show mission details (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = MissionManager(db)
        mission = manager.get_mission(mission_id)

    if not mission:
        if json_output:
            output_json(
                format_json_error(
                    error_message=f"Mission #{mission_id} not found",
                    error_code="MISSION_NOT_FOUND",
                    details={"mission_id": mission_id},
                )
            )
            raise typer.Exit(code=1)
        raise CLIError(f"Mission #{mission_id} not found.")

    status = "Active" if mission.end_time is None else "Complete"

    if json_output:
        mission_data = {
            "id": mission.id,
            "persona_name": mission.persona_name,
            "codename": mission.codename,
            "role": mission.role,
            "status": status,
            "start_date": mission.start_date,
            "start_time": mission.start_time,
            "end_time": mission.end_time,
            "mission_file": mission.mission_file,
            "objective": mission.objective,
        }
        output_json(format_json_response(mission_data))
    else:
        lines = [
            f"Persona: {mission.persona_name}",
            f"Codename: {mission.codename}",
            f"Role: {mission.role}",
            f"Status: {status}",
            f"Start Date: {mission.start_date}",
            f"Start Time: {mission.start_time}",
        ]
        if mission.end_time:
            lines.append(f"End Time: {mission.end_time}")
        lines.append(f"Mission File: {mission.mission_file}")
        if mission.objective:
            lines.append(f"Objective: {mission.objective}")
        terminal_message(conjoin(*lines), subject=f"Mission #{mission.id}")


@app.command()
@handle_errors("Failed to generate mission summary", handle_exc_class=SiteNineError)
def summary(
    mission_id: Annotated[int, typer.Argument(help="Mission ID")],
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Generate mission summary from git history and database (typically used by: humans)

    Auto-generates a summary showing:
    - Files changed since mission start
    - Commits made (filtered by persona)
    - Tasks claimed and their status
    """
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = MissionManager(db)

        try:
            mission_summary = manager.generate_summary(mission_id)
        except Exception:
            if json_output:
                output_json(
                    format_json_error(
                        error_message=f"Mission #{mission_id} not found",
                        error_code="MISSION_NOT_FOUND",
                        details={"mission_id": mission_id},
                    )
                )
                raise typer.Exit(code=1)
            raise CLIError(f"Mission #{mission_id} not found.")

    mission = mission_summary.mission

    if not json_output:
        for warning in mission_summary.warnings:
            terminal_message(warning, subject="Warning", subject_color="yellow")

    if json_output:
        summary_data = {
            "mission_id": mission.id,
            "persona_name": mission.persona_name,
            "role": mission.role,
            "codename": mission.codename,
            "start_time": mission.start_time,
            "end_time": mission.end_time,
            "objective": mission.objective,
            "files_changed": [{"status": f.status, "file": f.file} for f in mission_summary.files_changed],
            "commits": mission_summary.commits,
            "tasks": [{"id": t.id, "title": t.title, "status": t.status} for t in mission_summary.tasks],
        }
        output_json(format_json_response(summary_data))
    else:
        lines = [
            f"Mission #{mission.id} ({mission.persona_name} - {mission.role})",
            "",
            f"Codename: {mission.codename}",
            f"Start: {mission.start_time}",
        ]
        if mission.end_time:
            lines.append(f"End: {mission.end_time}")
        if mission.objective:
            lines.append(f"Objective: {mission.objective}")

        lines.append("")
        lines.append("Files Changed:")
        if mission_summary.files_changed:
            for file in mission_summary.files_changed:
                lines.append(f"  - [{file.status}] {file.file}")
        else:
            lines.append("  (No files changed or git unavailable)")

        lines.append("")
        lines.append("Commits:")
        if mission_summary.commits:
            for commit in mission_summary.commits:
                lines.append(f"  - {commit}")
        else:
            lines.append("  (No commits found)")

        lines.append("")
        lines.append("Tasks Claimed:")
        if mission_summary.tasks:
            for task in mission_summary.tasks:
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
@handle_errors("Failed to end mission", handle_exc_class=SiteNineError)
def end(
    mission_id: Annotated[int, typer.Argument(help="Mission ID")],
) -> None:
    """End a mission (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = MissionManager(db)
        CLIError.enforce_defined(manager.get_mission(mission_id), f"Mission #{mission_id} not found.")

        manager.end_mission(mission_id)

    terminal_message(
        f"Ended mission #{mission_id}",
        subject="Done",
        subject_color="green",
    )


@app.command()
@handle_errors("Failed to update mission", handle_exc_class=SiteNineError)
def update(
    mission_id: Annotated[int, typer.Argument(help="Mission ID to update")],
    objective: Annotated[str | None, typer.Option("--task", "-t", help="Update task summary")] = None,
    role: Annotated[str | None, typer.Option("--role", "-r", help="Update role")] = None,
) -> None:
    """Update mission metadata (typically used by: agents)"""
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
        manager = MissionManager(db)
        mission = CLIError.enforce_defined(manager.get_mission(mission_id), f"Mission #{mission_id} not found.")

        CLIError.require_condition(
            mission.end_time is None,
            "Cannot update completed mission. Only active missions can be updated.",
        )

        manager.update_mission(mission_id, objective=objective, role=role)

    lines = [f"Updated mission #{mission_id}"]
    if objective:
        lines.append(f"  Task: {objective}")
    if role:
        lines.append(f"  Role: {role}")
    terminal_message(conjoin(*lines), subject="Done", subject_color="green")


@app.command("roles")
def roles(
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Display available agent roles with descriptions (typically used by: agents)

    Shows a formatted list of all available agent roles and their responsibilities.
    This is used during session initialization to present consistent role options.
    """
    roles_list = [{"name": role.title_case, "description": role.description} for role in Role]

    if json_output:
        output_json(format_json_response(roles_list))
    else:
        lines = ["Which role should I assume for this session?", ""]
        for role_info in roles_list:
            lines.append(f"  - {role_info['name']}: {role_info['description']}")
        terminal_message(conjoin(*lines), subject="Roles", subject_color="cyan")


@app.command("generate-session-uuid")
def generate_session_uuid() -> None:
    """Generate a unique session UUID marker for reliable session detection (typically used by: agents)

    This command outputs a UUID that OpenCode captures in the session data.
    This allows rename-tui to reliably identify the current OpenCode session
    even when multiple sessions are active.

    The UUID is only output to the console (not written to any files), which
    prevents race conditions when multiple sessions run session-start concurrently.

    Usage in session-start workflow:
    1. Agent calls: s9 mission generate-session-uuid
    2. OpenCode captures the UUID output in this session's data
    3. Agent captures the UUID from output
    4. Agent calls: s9 mission rename-tui <name> <role> --uuid-marker <uuid>
    5. rename-tui searches session data for the UUID to identify this session
    """
    opencode_dir = require_opencode_dir()
    project_root = opencode_dir.parent

    session_mgr = OpenCodeSessionManager(project_root)
    session_uuid = session_mgr.generate_session_uuid()

    # Using print() directly because this output is meant to be parsed by other commands
    print(f"Session UUID: {session_uuid}")
    print(f"Use this marker with: s9 mission rename-tui <name> <role> --uuid-marker {session_uuid}")
    print(session_uuid)


@app.command("list-opencode-sessions")
@handle_errors("Failed to list OpenCode sessions", handle_exc_class=SiteNineError)
def list_opencode_sessions() -> None:
    """List OpenCode TUI missions for the current project (typically used by: humans)

    Shows session IDs and titles to help identify which session to rename.
    Use the session ID with: s9 mission rename-tui <name> <role> --session-id <id>
    """
    opencode_dir = require_opencode_dir()
    project_root = opencode_dir.parent

    session_mgr = OpenCodeSessionManager(project_root)
    sessions = session_mgr.list_project_sessions()

    if not sessions:
        terminal_message(
            "No OpenCode missions found for this project.",
            subject="Warning",
            subject_color="yellow",
        )
        return

    lines = [f"OpenCode missions for {project_root.name}:", ""]
    for session in sessions:
        lines.append(f"  {session.session_id} ({session.slug}) - modified {session.age_display}")
        lines.append(f"    {session.title}")
        lines.append("")

    lines.append("To rename a session, use:")
    lines.append("  s9 mission rename-tui <name> <role> --session-id <session-id>")
    terminal_message(conjoin(*lines), subject="Sessions", subject_color="cyan")


@app.command("rename-tui")
@handle_errors("Failed to rename OpenCode TUI session", handle_exc_class=SiteNineError)
def rename_tui(
    name: Annotated[str, typer.Argument(help="Persona name")],
    role: Annotated[str, typer.Argument(help="Agent role")],
    mission_id: Annotated[
        str | None, typer.Option("--session-id", "-s", help="OpenCode session ID (e.g., ses_xxx)")
    ] = None,
    uuid_marker: Annotated[
        str | None,
        typer.Option("--uuid-marker", "-u", help="Session UUID marker from generate-session-uuid"),
    ] = None,
    suffix: Annotated[
        str | None,
        typer.Option("--suffix", help="Optional suffix to append to title (e.g., '[DISMISSED]')"),
    ] = None,
) -> None:
    """Rename the current OpenCode TUI session to match agent identity (typically used by: agents)

    If --session-id is provided, renames that specific mission.
    If --uuid-marker is provided, searches session diffs for that marker (most reliable).
    Otherwise, attempts to auto-detect using content correlation and timestamps.
    If --suffix is provided, appends it to the session title (useful for indicating mission status).
    """
    opencode_dir = require_opencode_dir()
    project_root = opencode_dir.parent

    session_mgr = OpenCodeSessionManager(project_root)

    _, session_storage, _ = session_mgr.find_storage()

    detection = session_mgr.detect_session(session_id=mission_id, uuid_marker=uuid_marker)

    if detection.warning:
        terminal_message(detection.warning, subject="Warning", subject_color="yellow")

    session_id_value = CLIError.enforce_defined(detection.session_id, "Failed to determine session ID.")

    session_file = session_mgr.locate_session_file(session_id_value, session_storage)

    # Get mission codename from database
    db_path = opencode_dir / "data" / "project.db"
    with Database(db_path) as db:
        manager = MissionManager(db)
        codename = manager.get_active_codename(name)

    if codename:
        new_title = f"Operation {codename}: {name.capitalize()} - {role}"
    else:
        new_title = f"{name.capitalize()} - {role}"

    if suffix:
        new_title = f"{new_title} {suffix}"

    result = session_mgr.update_session_title(session_file, new_title)

    if result.warning:
        terminal_message(result.warning, subject="Warning", subject_color="yellow")

    terminal_message(
        conjoin(
            f"Renamed OpenCode session to: {result.new_title}",
            f"Previous title: {result.old_title}",
        ),
        subject="Done",
        subject_color="green",
    )

    if detection.multiple_active:
        terminal_message(
            conjoin(
                "Multiple active sessions detected.",
                "If the wrong session was renamed, run:",
                "  s9 mission list-opencode-sessions",
                f"  s9 mission rename-tui {name} {role} --session-id <correct-session-id>",
            ),
            subject="Warning",
            subject_color="yellow",
        )
