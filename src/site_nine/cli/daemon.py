"""Daemon management commands (summon, exorcise, heartbeat, session utilities)"""

from __future__ import annotations

import subprocess
from typing import Annotated

import typer
from snick import conjoin
from typerdrive import handle_errors, terminal_message

from site_nine.cli.json_utils import format_json_response, output_json
from site_nine.cli.utils import CLIError, require_db_path, require_opencode_dir
from site_nine.core.database import Database
from site_nine.core.roles import Role
from site_nine.core.settings import SiteNineSettings
from site_nine.exceptions import SiteNineError
from site_nine.possessions import PossessionManager
from site_nine.opencode import OpenCodeSessionManager

app = typer.Typer(help="Manage daemons (summon, exorcise, heartbeat)")


@app.command()
@handle_errors("Failed to summon daemon", handle_exc_class=SiteNineError)
def summon(
    role: Annotated[str, typer.Option("--role", "-r", help="Agent role")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="Daemon name (auto-selects if omitted)")] = None,
    task: Annotated[str, typer.Option("--task", "-t", help="Task summary")] = "",
    epic: Annotated[str | None, typer.Option("--epic", "-e", help="Epic ID for epic-scoped possession")] = None,
) -> None:
    """Summon a new daemon (start a possession) — typically used by: agents

    Possessions can be scoped in three ways:
    - Task-scoped: --task flag (existing behavior)
    - Epic-scoped: --epic flag (work through multiple tasks in an epic)
    - General: no flags (flexible coordination work)

    If --name is omitted, automatically selects the least-used daemon for the role.

    Note: --task and --epic are mutually exclusive.
    """
    db_path = require_db_path()

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

        if epic:
            epic_result = db.execute_query("SELECT id FROM epics WHERE id = :epic_id", {"epic_id": epic})
            CLIError.require_condition(
                bool(epic_result), f"Epic {epic} not found. Use 's9 epic list' to see available epics."
            )

        possession_id = manager.start_possession(role=role, daemon_name=name, epic_id=epic)

        if name is None:
            possession = manager.get_possession(possession_id)
            name = possession.daemon_name if possession else "unknown"

    lines = [
        f"Summoned daemon #{possession_id}",
        f"  Daemon: {name}",
        f"  Role: {role}",
    ]
    if epic:
        lines.append(f"  Epic: {epic}")
    if task:
        lines.append(f"  Objective: {task}")
    terminal_message(conjoin(*lines), subject="Done", subject_color="green")


@app.command()
@handle_errors("Failed to exorcise daemon", handle_exc_class=SiteNineError)
def exorcise(
    possession_id: Annotated[int, typer.Argument(help="Possession ID")],
) -> None:
    """Exorcise a daemon (end a possession) — typically used by: both"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = PossessionManager(db)
        CLIError.enforce_defined(manager.get_possession(possession_id), f"Possession #{possession_id} not found.")

        manager.exorcise(possession_id)

    terminal_message(
        f"Exorcised daemon #{possession_id}",
        subject="Done",
        subject_color="green",
    )


@app.command()
@handle_errors("Failed to send heartbeat", handle_exc_class=SiteNineError)
def heartbeat(
    possession_id: Annotated[int, typer.Argument(help="Possession ID")],
) -> None:
    """Update possession last_active_at timestamp — typically used by: agents

    Agents should call this periodically to indicate they are still active.
    This also sets the possession status to ACTIVE if it was IDLE.
    """
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = PossessionManager(db)
        manager.heartbeat(possession_id)

    terminal_message(
        f"Heartbeat recorded for possession #{possession_id}",
        subject="Done",
        subject_color="green",
    )


@app.command("roles")
def roles(
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Display available agent roles with descriptions — typically used by: agents

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
    """Generate a unique session UUID marker for reliable session detection — typically used by: agents

    This command outputs a UUID that OpenCode captures in the session data.
    This allows rename-tui to reliably identify the current OpenCode session
    even when multiple sessions are active.

    Usage in session-start workflow:
    1. Agent calls: s9 daemon generate-session-uuid
    2. OpenCode captures the UUID output in this session's data
    3. Agent captures the UUID from output
    4. Agent calls: s9 daemon rename-tui <name> <role> --uuid-marker <uuid>
    5. rename-tui searches session data for the UUID to identify this session
    """
    opencode_dir = require_opencode_dir()
    project_root = opencode_dir.parent

    session_mgr = OpenCodeSessionManager(project_root)
    session_uuid = session_mgr.generate_session_uuid()

    print(f"Session UUID: {session_uuid}")
    print(f"Use this marker with: s9 daemon rename-tui <name> <role> --uuid-marker {session_uuid}")
    print(session_uuid)


@app.command("list-opencode-sessions")
@handle_errors("Failed to list OpenCode sessions", handle_exc_class=SiteNineError)
def list_opencode_sessions() -> None:
    """List OpenCode TUI sessions for the current project — typically used by: humans

    Shows session IDs and titles to help identify which session to rename.
    """
    opencode_dir = require_opencode_dir()
    project_root = opencode_dir.parent

    session_mgr = OpenCodeSessionManager(project_root)
    sessions = session_mgr.list_project_sessions()

    if not sessions:
        terminal_message(
            "No OpenCode sessions found for this project.",
            subject="Warning",
            subject_color="yellow",
        )
        return

    lines = [f"OpenCode sessions for {project_root.name}:", ""]
    for session in sessions:
        lines.append(f"  {session.session_id} ({session.slug}) - modified {session.age_display}")
        lines.append(f"    {session.title}")
        lines.append("")

    lines.append("To rename a session, use:")
    lines.append("  s9 daemon rename-tui <name> <role>")
    terminal_message(conjoin(*lines), subject="Sessions", subject_color="cyan")


@app.command("rename-tui")
@handle_errors("Failed to rename OpenCode TUI session", handle_exc_class=SiteNineError)
def rename_tui(
    name: Annotated[str, typer.Argument(help="Daemon name")],
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
    """Rename the current OpenCode TUI session to match daemon identity — typically used by: agents

    If --uuid-marker is provided, searches for that marker in session data (most reliable).
    Otherwise, attempts to auto-detect using DB recency and filesystem heuristics.
    If --suffix is provided, appends it to the session title (useful for indicating possession status).
    """
    opencode_dir = require_opencode_dir()
    project_root = opencode_dir.parent

    session_mgr = OpenCodeSessionManager(project_root)

    detection = session_mgr.detect_session(uuid_marker=uuid_marker)

    if detection.warning:
        terminal_message(detection.warning, subject="Warning", subject_color="yellow")

    session_id_value = CLIError.enforce_defined(detection.session_id, "Failed to determine session ID.")

    db_path = opencode_dir / "data" / "project.db"
    with Database(db_path) as db:
        possession_result = db.execute_query(
            "SELECT id FROM possessions WHERE daemon_name = :daemon_name AND status != 'EXORCISED' ORDER BY created_at DESC LIMIT 1",
            {"daemon_name": name.lower()},
        )

        current_task = None
        if possession_result:
            possession_id = possession_result[0]["id"]
            task_result = db.execute_query(
                "SELECT id, title FROM tasks WHERE current_possession_id = :possession_id AND status = 'UNDERWAY' LIMIT 1",
                {"possession_id": possession_id},
            )
            if task_result:
                current_task = task_result[0]

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
                "  s9 daemon list-opencode-sessions",
                "to verify which session was updated.",
            ),
            subject="Warning",
            subject_color="yellow",
        )
