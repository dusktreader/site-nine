from __future__ import annotations

import subprocess
from typing import Annotated

import typer
from rich.table import Table
from snick import conjoin
from typerdrive import handle_errors, terminal_message

from site_nine.cli.json_utils import format_json_error, format_json_response, output_json
from site_nine.cli.utils import CLIError, require_db_path, require_opencode_dir
from site_nine.core.database import Database
from site_nine.core.roles import Role
from site_nine.core.settings import SiteNineSettings
from site_nine.exceptions import SiteNineError
from site_nine.possessions import PossessionManager
from site_nine.possessions.models import Possession as Mission
from site_nine.possessions.types import PossessionStatus as MissionStatus
from site_nine.opencode import OpenCodeSessionManager

app = typer.Typer(help="Manage missions")


@app.command()
@handle_errors("Failed to start mission", handle_exc_class=SiteNineError)
def start(
    role: Annotated[str, typer.Option("--role", "-r", help="Agent role")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="Persona name (auto-selects if omitted)")] = None,
    task: Annotated[str, typer.Option("--task", "-t", help="Task summary")] = "",
    epic: Annotated[str | None, typer.Option("--epic", "-e", help="Epic ID for epic-scoped mission")] = None,
) -> None:
    """Start a new mission (typically used by: agents)

    Missions can be scoped in three ways:
    - Task-scoped: --task flag (existing behavior)
    - Epic-scoped: --epic flag (work through multiple tasks in an epic)
    - General: no flags (flexible coordination work)

    If --name is omitted, automatically selects the least-used persona for the role.

    Note: --task and --epic are mutually exclusive.
    """
    db_path = require_db_path()

    # Validate mutual exclusivity of --task and --epic
    CLIError.require_condition(
        not (task and epic),
        "Cannot specify both --task and --epic. Choose one scoping mode:\n"
        "  - Task-scoped: --task (work on specific task)\n"
        "  - Epic-scoped: --epic (work through multiple tasks in epic)\n"
        "  - General: neither flag (flexible coordination work)",
    )

    valid_roles_str = ", ".join(Role.all_values())
    with CLIError.handle_errors(f"Invalid role: {role}. Valid values: {valid_roles_str}", handle_exc_class=ValueError):
        Role.from_string(role)
    role = role.title()

    with Database(db_path) as db:
        manager = PossessionManager(db)

        # Validate epic exists if provided
        if epic:
            epic_result = db.execute_query("SELECT id FROM epics WHERE id = :epic_id", {"epic_id": epic})
            CLIError.require_condition(
                bool(epic_result), f"Epic {epic} not found. Use 's9 epic list' to see available epics."
            )

        mission_id = manager.start_possession(role=role, daemon_name=name, epic_id=epic)

        # Get the persona name if it was auto-assigned
        if name is None:
            mission = manager.get_possession(mission_id)
            name = mission.daemon_name if mission else "unknown"

    lines = [
        f"Started mission #{mission_id}",
        f"  Persona: {name}",
        f"  Role: {role}",
    ]
    if epic:
        lines.append(f"  Epic: {epic}")
    if task:
        lines.append(f"  Objective: {task}")
    terminal_message(conjoin(*lines), subject="Done", subject_color="green")


@app.command()
@handle_errors("Failed to list missions", handle_exc_class=SiteNineError)
def list(
    active_only: Annotated[bool, typer.Option("--active-only", help="Show only active missions")] = False,
    role: Annotated[str | None, typer.Option("--role", "-r", help="Filter by role")] = None,
    epic: Annotated[str | None, typer.Option("--epic", "-e", help="Filter by epic ID")] = None,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """List missions (typically used by: humans)"""
    db_path = require_db_path()

    if role:
        role = role.title()

    with Database(db_path) as db:
        manager = PossessionManager(db)
        missions = manager.list_possessions(active_only=active_only, role=role, epic_id=epic)

        # Build mapping of mission_id -> current_task_id for active missions
        mission_task_map: dict[int, str | None] = {}
        active_mission_ids = [m.id for m in missions if m.end_time is None and m.id is not None]
        if active_mission_ids:
            placeholders = ", ".join(f":m{i}" for i in range(len(active_mission_ids)))
            params = {f"m{i}": mid for i, mid in enumerate(active_mission_ids)}
            task_rows = db.execute_query(
                f"SELECT id, current_possession_id FROM tasks WHERE current_possession_id IN ({placeholders}) AND status = 'UNDERWAY'",
                params,
            )
            for row in task_rows:
                mission_task_map[row["current_possession_id"]] = row["id"]

    def _get_availability(mission: Mission) -> str:
        """Compute availability status per ADR-009."""
        if mission.status == MissionStatus.EXORCISED:
            return "Ended"
        if mission.desk_mode_active:
            if mission.epic_id:
                return f"Desk ({mission.epic_id})"
            return "Desk (All)"
        mid = mission.id or 0
        current_task_id = mission_task_map.get(mid)
        if mission.epic_id:
            return f"Working ({mission.epic_id})"
        if current_task_id:
            return f"Working ({current_task_id})"
        return "Working"

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
                "persona_name": mission.daemon_name,
                "role": mission.role,
                "codename": "",
                "status": mission.status.value,
                "epic_id": mission.epic_id,
                "desk_mode_active": mission.desk_mode_active,
                "current_task_id": mission_task_map.get(mission.id or 0),
                "availability": _get_availability(mission),
                "start_time": mission.start_time,
                "end_time": mission.end_time,
                "start_date": "",
                "objective": "",
                "mission_file": mission.possession_log,
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
        table.add_column("Availability", style="bright_green")
        table.add_column("Start Time", style="blue")
        table.add_column("End Time", style="blue")

        for mission in missions:
            table.add_row(
                str(mission.id),
                mission.daemon_name,
                mission.role,
                "",
                _get_availability(mission),
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
        manager = PossessionManager(db)
        mission = manager.get_possession(mission_id)

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

    status = str(mission.status)

    # Determine mission scope (ADR-009)
    scope_info = None
    if mission.epic_id:
        scope_info = f"Epic-scoped ({mission.epic_id})"
    else:
        # Check if this mission has a claimed task (task-scoped)
        task_rows = db.execute_query(
            "SELECT id FROM tasks WHERE current_possession_id = :mission_id LIMIT 1",
            {"mission_id": mission.id},
        )
        if task_rows:
            scope_info = f"Task-scoped ({task_rows[0]['id']})"
        else:
            scope_info = "General"

    if json_output:
        mission_data = {
            "id": mission.id,
            "persona_name": mission.daemon_name,
            "codename": "",
            "role": mission.role,
            "status": status,
            "start_date": "",
            "start_time": mission.start_time,
            "end_time": mission.end_time,
            "mission_file": mission.possession_log,
            "objective": "",
            "epic_id": mission.epic_id,
            "scope": scope_info,
        }
        output_json(format_json_response(mission_data))
    else:
        lines = [
            f"Persona: {mission.daemon_name}",
            f"Role: {mission.role}",
            f"Status: {status}",
            f"Scope: {scope_info}",
            f"Start Time: {mission.start_time}",
        ]
        if mission.end_time:
            lines.append(f"End Time: {mission.end_time}")
        lines.append(f"Mission File: {mission.possession_log}")
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
        manager = PossessionManager(db)

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

    mission = mission_summary.possession

    if not json_output:
        for warning in mission_summary.warnings:
            terminal_message(warning, subject="Warning", subject_color="yellow")

    if json_output:
        summary_data = {
            "mission_id": mission.id,
            "persona_name": mission.daemon_name,
            "role": mission.role,
            "codename": "",
            "start_time": mission.start_time,
            "end_time": mission.end_time,
            "objective": "",
            "files_changed": [{"status": f.status, "file": f.file} for f in mission_summary.files_changed],
            "commits": mission_summary.commits,
            "tasks": [{"id": t.id, "title": t.title, "status": t.status} for t in mission_summary.tasks],
        }
        output_json(format_json_response(summary_data))
    else:
        lines = [
            f"Mission #{mission.id} ({mission.daemon_name} - {mission.role})",
            "",
            f"Start: {mission.start_time}",
        ]
        if mission.end_time:
            lines.append(f"End: {mission.end_time}")

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
        manager = PossessionManager(db)
        CLIError.enforce_defined(manager.get_possession(mission_id), f"Mission #{mission_id} not found.")

        manager.exorcise(mission_id)

    terminal_message(
        f"Ended mission #{mission_id}",
        subject="Done",
        subject_color="green",
    )


@app.command()
@handle_errors("Failed to suspend mission", handle_exc_class=SiteNineError)
def suspend(
    mission_id: Annotated[int, typer.Argument(help="Mission ID")],
    reason: Annotated[str | None, typer.Option("--reason", "-r", help="Reason for suspension")] = None,
) -> None:
    """Suspend a mission (ADR-013)

    Transitions mission to SUSPENDED status. Typically used when a session closes
    unexpectedly or when manually pausing work. Suspended missions can be resumed
    later with 's9 mission resume'.
    """
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = PossessionManager(db)
        mission = CLIError.enforce_defined(manager.get_possession(mission_id), f"Mission #{mission_id} not found.")

        # Check mission status
        if mission.status == MissionStatus.EXORCISED:
            terminal_message(
                f"Mission #{mission_id} has already ended and cannot be suspended.",
                subject="Error",
                subject_color="red",
            )
            raise typer.Exit(code=1)

        if mission.status == MissionStatus.SUSPENDED:
            terminal_message(
                f"Mission #{mission_id} is already suspended.",
                subject="Warning",
                subject_color="yellow",
            )
            raise typer.Exit(code=0)

        manager.suspend_possession(mission_id, reason=reason)

    reason_text = f"\nReason: {reason}" if reason else ""
    terminal_message(
        f"Suspended mission #{mission_id}{reason_text}",
        subject="Done",
        subject_color="green",
    )


@app.command()
@handle_errors("Failed to resume mission", handle_exc_class=SiteNineError)
def resume(
    mission_identifier: Annotated[str, typer.Argument(help="Mission ID or codename")],
    model: Annotated[str | None, typer.Option("--model", "-m", help="Model to use (provider/model format)")] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-d", help="Show command that would be run without executing")
    ] = False,
) -> None:
    """Resume a suspended mission (ADR-013)

    Transitions mission from SUSPENDED to ACTIVE status and launches OpenCode
    with a context message summarizing the resumed mission state. Use this to
    continue work on a mission that was previously suspended.

    You can specify either a mission ID (e.g., 126) or codename (e.g., bold-comet).
    """
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = PossessionManager(db)

        # Try to parse as integer ID first
        mission = None
        try:
            mission_id = int(mission_identifier)
            mission = manager.get_possession(mission_id)
        except ValueError:
            pass

        mission = CLIError.enforce_defined(
            mission, f"Mission '{mission_identifier}' not found. Use 's9 mission list' to see available missions."
        )

        # Check mission status
        if mission.status != MissionStatus.SUSPENDED:
            terminal_message(
                f"Mission #{mission.id} is not suspended (current status: {mission.status}).\n"
                f"Only suspended missions can be resumed.",
                subject="Error",
                subject_color="red",
            )
            raise typer.Exit(code=1)

        # Get task information for context
        task_rows = db.execute_query(
            "SELECT id, title, status FROM tasks WHERE current_possession_id = :mission_id",
            {"mission_id": mission.id},
        )

        # Resume the mission in the database (skip if dry run)
        if not dry_run:
            manager.resume_possession(mission.id or 0)

    # Get model from config if not specified
    if model is None:
        settings = SiteNineSettings()
        model = settings.default_model or "github-copilot/claude-sonnet-4.5"

    # Build context message for resumed mission
    context_lines = [
        f"Resuming mission #{mission.id}",
        f"Persona: {mission.daemon_name}",
        f"Role: {mission.role}",
    ]
    if mission.epic_id:
        context_lines.append(f"Epic: {mission.epic_id}")

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
        f"Resuming mission #{mission.id}\nLaunching OpenCode...",
        subject="Resume",
    )

    # Launch OpenCode with context message
    try:
        subprocess.run(["opencode", "--model", model, "--prompt", context_message], check=True)
    except subprocess.CalledProcessError as e:
        raise CLIError(f"Error launching OpenCode: {e}")
    except FileNotFoundError:
        raise CLIError("'opencode' command not found. Is OpenCode installed?")


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
        manager = PossessionManager(db)
        mission = CLIError.enforce_defined(manager.get_possession(mission_id), f"Mission #{mission_id} not found.")

        CLIError.require_condition(
            mission.end_time is None,
            "Cannot update completed mission. Only active missions can be updated.",
        )

        manager.update_possession(mission_id, role=role)

    lines = [f"Updated mission #{mission_id}"]
    if objective:
        lines.append(f"  Task: {objective}")
    if role:
        lines.append(f"  Role: {role}")
    terminal_message(conjoin(*lines), subject="Done", subject_color="green")


@app.command()
@handle_errors("Failed to send heartbeat", handle_exc_class=SiteNineError)
def heartbeat(
    mission_id: Annotated[int, typer.Argument(help="Mission ID")],
) -> None:
    """Update mission last_active_at timestamp (typically used by: agents)

    Agents should call this periodically to indicate they are still active.
    This also sets the mission status to ACTIVE if it was IDLE.
    """
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = PossessionManager(db)
        manager.heartbeat(mission_id)

    terminal_message(
        f"Heartbeat recorded for mission #{mission_id}",
        subject="Done",
        subject_color="green",
    )


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
    lines.append("  s9 mission rename-tui <name> <role>")
    terminal_message(conjoin(*lines), subject="Sessions", subject_color="cyan")


@app.command("rename-tui")
@handle_errors("Failed to rename OpenCode TUI session", handle_exc_class=SiteNineError)
def rename_tui(
    name: Annotated[str, typer.Argument(help="Persona name")],
    role: Annotated[str, typer.Argument(help="Agent role")],
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

    If --uuid-marker is provided, searches for that marker in session data (most reliable).
    Otherwise, attempts to auto-detect using DB recency and filesystem heuristics.
    If --suffix is provided, appends it to the session title (useful for indicating mission status).
    """
    opencode_dir = require_opencode_dir()
    project_root = opencode_dir.parent

    session_mgr = OpenCodeSessionManager(project_root)

    detection = session_mgr.detect_session(uuid_marker=uuid_marker)

    if detection.warning:
        terminal_message(detection.warning, subject="Warning", subject_color="yellow")

    session_id_value = CLIError.enforce_defined(detection.session_id, "Failed to determine session ID.")

    # Get current possession and task from database
    db_path = opencode_dir / "data" / "project.db"
    with Database(db_path) as db:
        # Get current possession ID and task
        mission_result = db.execute_query(
            "SELECT id FROM possessions WHERE daemon_name = :daemon_name AND status != 'EXORCISED' ORDER BY created_at DESC LIMIT 1",
            {"daemon_name": name.lower()},
        )

        current_task = None
        if mission_result:
            mission_id = mission_result[0]["id"]
            task_result = db.execute_query(
                "SELECT id, title FROM tasks WHERE current_possession_id = :mission_id AND status = 'UNDERWAY' LIMIT 1",
                {"mission_id": mission_id},
            )
            if task_result:
                current_task = task_result[0]

    # Build title
    new_title = f"{name.capitalize()} - {role}"

    if current_task:
        new_title = f"{new_title} | {current_task['id']}"

    if suffix:
        new_title = f"{new_title} {suffix}"

    result = session_mgr.update_session_title(session_id_value, new_title)

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
                "to verify which session was updated.",
            ),
            subject="Warning",
            subject_color="yellow",
        )
