"""Agent session management commands"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table
from typerdrive import handle_errors

from s9.agents.sessions import AgentSessionManager
from s9.core.database import Database
from s9.core.paths import get_opencode_dir

app = typer.Typer(help="Manage agent sessions")
console = Console()


def _get_manager() -> AgentSessionManager:
    """Get agent session manager"""
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
    return AgentSessionManager(db)


@app.command()
@handle_errors("Failed to start agent session")
def start(
    name: str = typer.Argument(..., help="Daemon name"),
    role: str = typer.Option(..., "--role", "-r", help="Agent role"),
    task: str = typer.Option("", "--task", "-t", help="Task summary"),
) -> None:
    """Start a new agent session"""
    manager = _get_manager()

    # Validate and convert role to title case
    valid_roles = [
        "administrator",
        "architect",
        "builder",
        "tester",
        "documentarian",
        "designer",
        "inspector",
        "operator",
    ]
    if role.lower() not in valid_roles:
        console.print(f"[red]Invalid role: {role}. Valid values: {', '.join(valid_roles)}[/red]")
        raise typer.Exit(1)
    role = role.title()

    session_id = manager.start_session(name=name, role=role, task_summary=task)

    console.print(f"[green]✓[/green] Started agent session #{session_id}")
    console.print(f"  Name: {name}")
    console.print(f"  Role: {role}")
    if task:
        console.print(f"  Task: {task}")
    logger.info(f"Started agent session {session_id}: {name} ({role})")


@app.command()
@handle_errors("Failed to list agent sessions")
def list(
    active_only: bool = typer.Option(False, "--active-only", help="Show only active sessions"),
    role: str = typer.Option(None, "--role", "-r", help="Filter by role"),
) -> None:
    """List agent sessions"""
    manager = _get_manager()

    # Normalize role to title case for case-insensitive filtering
    if role:
        role = role.title()

    sessions = manager.list_sessions(active_only=active_only, role=role)

    if not sessions:
        console.print("[yellow]No sessions found.[/yellow]")
        return

    table = Table(title="Agent Sessions")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Name", style="magenta")
    table.add_column("Role", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Start Time", style="blue")
    table.add_column("End Time", style="blue")

    for session in sessions:
        table.add_row(
            str(session.id),
            session.name,
            session.role,
            session.status,
            session.start_time or "",
            session.end_time or "",
        )

    console.print(table)
    logger.debug(f"Listed {len(sessions)} agent sessions")


@app.command()
@handle_errors("Failed to show agent session")
def show(
    agent_id: int = typer.Argument(..., help="Agent session ID"),
) -> None:
    """Show agent session details"""
    manager = _get_manager()
    session = manager.get_session(agent_id)

    if not session:
        console.print(f"[red]Error: Agent session #{agent_id} not found.[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Agent Session #{session.id}[/bold]")
    console.print(f"  Name: {session.name}")
    console.print(f"  Base Name: {session.base_name}")
    if session.suffix:
        console.print(f"  Suffix: {session.suffix}")
    console.print(f"  Role: {session.role}")
    console.print(f"  Status: {session.status}")
    console.print(f"  Session Date: {session.session_date}")
    console.print(f"  Start Time: {session.start_time}")
    if session.end_time:
        console.print(f"  End Time: {session.end_time}")
    console.print(f"  Session File: {session.session_file}")
    if session.task_summary:
        console.print(f"  Task: {session.task_summary}")
    logger.debug(f"Displayed details for agent session {agent_id}")


@app.command()
@handle_errors("Failed to end agent session")
def end(
    agent_id: int = typer.Argument(..., help="Agent session ID"),
    status: str = typer.Option("completed", "--status", help="End status"),
) -> None:
    """End an agent session"""
    manager = _get_manager()

    # Verify session exists
    session = manager.get_session(agent_id)
    if not session:
        console.print(f"[red]Error: Agent session #{agent_id} not found.[/red]")
        raise typer.Exit(1)

    manager.end_session(agent_id, status)
    console.print(f"[green]✓[/green] Ended agent session #{agent_id} with status: {status}")
    logger.info(f"Ended agent session {agent_id} with status: {status}")


@app.command()
@handle_errors("Failed to pause agent session")
def pause(
    agent_id: int = typer.Argument(..., help="Agent session ID to pause"),
    reason: str | None = typer.Option(None, "--reason", help="Reason for pausing"),
) -> None:
    """Pause an active agent session"""
    manager = _get_manager()

    # Verify session exists and is active
    session = manager.get_session(agent_id)
    if not session:
        console.print(f"[red]Error: Agent session #{agent_id} not found.[/red]")
        raise typer.Exit(1)

    if session.status != "in-progress":
        console.print(
            f"[red]Error: Cannot pause session with status '{session.status}'. "
            f"Only 'in-progress' sessions can be paused.[/red]"
        )
        raise typer.Exit(1)

    manager.pause_session(agent_id)
    console.print(f"[green]⏸️  Paused agent session #{agent_id} ({session.name})[/green]")

    if reason:
        console.print(f"[dim]Reason: {reason}[/dim]")

    console.print(f"[dim]Resume with: s9 agent resume {agent_id}[/dim]")
    logger.info(f"Paused agent session {agent_id}")


@app.command()
@handle_errors("Failed to resume agent session")
def resume(
    agent_id: int = typer.Argument(..., help="Agent session ID to resume"),
) -> None:
    """Resume a paused agent session"""
    manager = _get_manager()

    # Verify session exists and is paused
    session = manager.get_session(agent_id)
    if not session:
        console.print(f"[red]Error: Agent session #{agent_id} not found.[/red]")
        raise typer.Exit(1)

    if session.status != "paused":
        console.print(
            f"[red]Error: Cannot resume session with status '{session.status}'. "
            f"Only 'paused' sessions can be resumed.[/red]"
        )
        raise typer.Exit(1)

    manager.resume_session(agent_id)
    console.print(f"[green]▶️  Resumed agent session #{agent_id} ({session.name})[/green]")
    console.print("[dim]Status is now: in-progress[/dim]")
    logger.info(f"Resumed agent session {agent_id}")


@app.command()
@handle_errors("Failed to update agent session")
def update(
    agent_id: int = typer.Argument(..., help="Agent session ID to update"),
    task_summary: str | None = typer.Option(None, "--task", "-t", help="Update task summary"),
    role: str | None = typer.Option(None, "--role", "-r", help="Update role"),
) -> None:
    """Update agent session metadata"""
    manager = _get_manager()

    if not task_summary and not role:
        console.print("[yellow]No updates specified. Use --task or --role[/yellow]")
        raise typer.Exit(0)

    # Verify session exists
    session = manager.get_session(agent_id)
    if not session:
        console.print(f"[red]Error: Agent session #{agent_id} not found.[/red]")
        raise typer.Exit(1)

    if session.status not in ["in-progress", "paused"]:
        console.print(
            f"[red]Error: Cannot update session with status '{session.status}'. "
            f"Only active or paused sessions can be updated.[/red]"
        )
        raise typer.Exit(1)

    # Validate role if provided
    if role:
        valid_roles = [
            "administrator",
            "architect",
            "builder",
            "tester",
            "documentarian",
            "designer",
            "inspector",
            "operator",
        ]
        if role.lower() not in valid_roles:
            console.print(f"[red]Invalid role: {role}. Valid values: {', '.join(valid_roles)}[/red]")
            raise typer.Exit(1)
        role = role.title()

    manager.update_session(agent_id, task_summary=task_summary, role=role)

    console.print(f"[green]✓[/green] Updated agent session #{agent_id}")
    if task_summary:
        console.print(f"  Task: {task_summary}")
    if role:
        console.print(f"  Role: {role}")
    logger.info(f"Updated agent session {agent_id}")


def _find_current_opencode_session(project_root: Path) -> str | None:
    """
    Find the current OpenCode session by looking for the most recent
    agent session file in session diffs.

    This is more reliable than using modification time alone, as it identifies
    which OpenCode session actually created/modified the agent's session file.

    Args:
        project_root: Absolute path to the project root directory

    Returns:
        Session ID (e.g., "ses_xxx") or None if not found
    """
    home = Path.home()
    session_diff_dir = home / ".local" / "share" / "opencode" / "storage" / "session_diff"

    if not session_diff_dir.exists():
        return None

    # Find the most recent agent session file for this project
    # Try both old (.opencode/sessions) and new (.opencode/work/sessions) locations
    sessions_dirs = [
        project_root / ".opencode" / "work" / "sessions",
        project_root / ".opencode" / "sessions",
    ]

    session_files = []
    for sessions_dir in sessions_dirs:
        if sessions_dir.exists():
            session_files.extend(sessions_dir.glob("*.md"))

    if not session_files:
        return None

    latest_session_file = max(session_files, key=lambda p: p.stat().st_mtime)
    relative_path = str(latest_session_file.relative_to(project_root))

    # Search session_diff files for this path
    # Check most recent diffs first for better performance
    diff_files = sorted(
        session_diff_dir.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    # Look in recent diffs (last 50 should be more than enough)
    for diff_file in diff_files[:50]:
        try:
            with open(diff_file) as f:
                diff_data = json.load(f)

            # Check if this diff mentions our session file
            # diff_data is a list of file change objects
            if not isinstance(diff_data, dict):
                # It's a list of file changes
                for file_change in diff_data:
                    if relative_path in file_change.get("file", ""):
                        # Found it! Return the session ID
                        return diff_file.stem

        except (json.JSONDecodeError, KeyError, FileNotFoundError):
            # Skip corrupted or deleted files
            continue

    return None


@app.command("roles")
def roles() -> None:
    """Display available agent roles with descriptions

    Shows a formatted list of all available agent roles and their responsibilities.
    This is used during session initialization to present consistent role options.
    """
    console.print("\n[bold cyan]Which role should I assume for this session?[/bold cyan]\n")

    roles_list = [
        ("Administrator", "coordinate and delegate to other agents"),
        ("Architect", "design systems and make technical decisions"),
        ("Builder", "implement features and write code"),
        ("Tester", "write tests and validate functionality"),
        ("Documentarian", "create documentation and guides"),
        ("Designer", "design user interfaces and experiences"),
        ("Historian", "document project history and decisions"),
        ("Inspector", "review code and audit security"),
        ("Operator", "deploy systems and manage infrastructure"),
    ]

    for role, description in roles_list:
        console.print(f"  • [bold green]{role}[/bold green]: {description}")

    console.print()


def _find_opencode_storage() -> tuple[Path, Path]:
    """Find and validate OpenCode storage directories

    Returns:
        Tuple of (session_diff_storage, session_storage) paths

    Raises:
        typer.Exit: If OpenCode storage directory is not found
    """
    opencode_storage = Path.home() / ".local" / "share" / "opencode" / "storage"
    if not opencode_storage.exists():
        console.print("[red]Error: OpenCode storage directory not found.[/red]")
        console.print("[dim]Expected: ~/.local/share/opencode/storage[/dim]")
        raise typer.Exit(1)

    session_diff_storage = opencode_storage / "session_diff"
    session_storage = opencode_storage / "session"
    return session_diff_storage, session_storage


def _detect_session_via_diff_recency(
    project_root: Path,
    session_diff_storage: Path,
    session_storage: Path,
) -> str | None:
    """Detect current OpenCode session by finding most recently modified diff file

    This is the most reliable method because the active session continuously
    writes to its diff file as you work. We verify the session is for the
    current project before returning it.

    Args:
        project_root: Project root directory
        session_diff_storage: Path to OpenCode session_diff directory
        session_storage: Path to OpenCode session storage directory

    Returns:
        Session ID (e.g., "ses_xxx") or None if no matching session found
    """
    import time

    # Find all diff files sorted by modification time
    diff_files = sorted(session_diff_storage.glob("ses_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not diff_files:
        return None

    # Check the most recently modified diffs (top 5 to handle multi-project scenarios)
    for diff_file in diff_files[:5]:
        session_id = diff_file.stem

        # Find the corresponding session file to verify project
        session_file = None
        for project_dir in session_storage.iterdir():
            if not project_dir.is_dir():
                continue
            candidate = project_dir / f"{session_id}.json"
            if candidate.exists():
                session_file = candidate
                break

        if not session_file:
            continue

        # Check if this session is for the current project
        try:
            with open(session_file) as f:
                session_data = json.load(f)
            session_dir = session_data.get("directory", "")
            if session_dir and Path(session_dir).resolve() == project_root.resolve():
                # Found it! This is our session
                mtime = diff_file.stat().st_mtime
                age_seconds = time.time() - mtime
                logger.debug("session_detected_via_diff_recency", session_id=session_id, age_seconds=int(age_seconds))
                return session_id
        except (json.JSONDecodeError, FileNotFoundError, PermissionError):
            continue

    # No matching session found
    return None


def _find_project_sessions(
    project_root: Path,
    session_storage: Path,
) -> list[tuple[Path, float]]:
    """Find all OpenCode sessions for the current project

    Args:
        project_root: Project root directory
        session_storage: Path to OpenCode session storage directory

    Returns:
        List of (session_file_path, modification_time) tuples
    """
    project_sessions = []
    for project_dir in session_storage.iterdir():
        if not project_dir.is_dir() or project_dir.name == "global":
            continue

        for session_file in project_dir.glob("ses_*.json"):
            try:
                with open(session_file) as f:
                    session_data = json.load(f)

                session_dir = session_data.get("directory", "")
                if session_dir and Path(session_dir).resolve() == project_root.resolve():
                    mtime = session_file.stat().st_mtime
                    project_sessions.append((session_file, mtime))
            except (json.JSONDecodeError, FileNotFoundError, PermissionError):
                continue

    return project_sessions


def _detect_session_via_recency(
    project_root: Path,
    project_sessions: list[tuple[Path, float]],
) -> str | None:
    """Detect current OpenCode session based on recent activity

    Uses modification time to identify the most likely current session.
    Handles multiple active sessions by prompting the user.

    Args:
        project_root: Project root directory
        project_sessions: List of (session_file_path, modification_time) tuples

    Returns:
        Session ID (e.g., "ses_xxx") or None

    Raises:
        typer.Exit: If multiple sessions are active and user needs to choose
    """
    import time

    if not project_sessions:
        console.print(f"[red]Error: No OpenCode sessions found for project {project_root.name}[/red]")
        raise typer.Exit(1)

    # Find sessions modified in last 3 seconds (very recent activity)
    very_recent_sessions = [(f, mt) for f, mt in project_sessions if time.time() - mt < 3]

    if len(very_recent_sessions) == 1:
        # Only one session active in the last 3 seconds - must be us!
        session_id = very_recent_sessions[0][0].stem
        logger.debug("session_auto_detected_single_active", session_id=session_id)
        return session_id

    elif len(very_recent_sessions) > 1:
        # Multiple sessions active - need user to specify
        console.print("[yellow]Multiple active OpenCode sessions detected for this project.[/yellow]")
        console.print("[yellow]Please specify which session to rename:[/yellow]\n")

        for session_file, mtime in sorted(very_recent_sessions, key=lambda x: x[1], reverse=True):
            try:
                with open(session_file) as f:
                    session_data = json.load(f)
                title = session_data.get("title", "Untitled")
                slug = session_data.get("slug", "")
                age = int(time.time() - mtime)
                console.print(f"  [green]{session_file.stem}[/green] ({slug}) - {age}s ago")
                console.print(f"    {title}\n")
            except:
                pass

        console.print("[yellow]Run with: s9 agent rename-tui <name> <role> --session-id <id>[/yellow]")
        console.print("[yellow]Or use: s9 agent list-opencode-sessions (to see all sessions)[/yellow]")
        raise typer.Exit(1)

    else:
        # No very recent activity - use most recent
        import time

        most_recent = max(project_sessions, key=lambda x: x[1])
        session_id = most_recent[0].stem
        mtime = most_recent[1]
        age = int(time.time() - mtime)
        console.print(f"[yellow]No session modified in last 3 seconds. Using most recent ({age}s ago).[/yellow]")
        console.print(f"[yellow]Session: {session_id}[/yellow]")
        console.print(f"[yellow]If this is wrong, pass --session-id explicitly[/yellow]\n")
        logger.debug("session_auto_detected_fallback", session_id=session_id, age_seconds=age)
        return session_id


def _locate_session_file(
    session_id: str,
    session_storage: Path,
) -> Path:
    """Locate the session JSON file for a given session ID

    Args:
        session_id: OpenCode session ID (e.g., "ses_xxx")
        session_storage: Path to OpenCode session storage directory

    Returns:
        Path to the session JSON file

    Raises:
        typer.Exit: If session file is not found
    """
    for project_dir in session_storage.iterdir():
        if not project_dir.is_dir():
            continue
        candidate = project_dir / f"{session_id}.json"
        # Use try/except to handle race condition if file is deleted
        try:
            if candidate.exists():
                return candidate
        except (FileNotFoundError, PermissionError):
            # File was deleted or became inaccessible between check and access
            continue

    console.print(f"[red]Session file not found for {session_id}[/red]")
    raise typer.Exit(1)


def _update_session_title(
    session_file: Path,
    new_title: str,
    project_root: Path,
) -> None:
    """Update the title of an OpenCode session using atomic write

    Uses a temporary file and atomic rename to ensure the session file
    is never in a partially-written state.

    Args:
        session_file: Path to the session JSON file
        new_title: New title to set
        project_root: Project root directory (for validation warning)

    Raises:
        typer.Exit: If session file cannot be updated
    """
    try:
        # Read current session data
        with open(session_file) as f:
            session_data = json.load(f)

        # Verify this session is for the current project (warn if not)
        session_dir = session_data.get("directory", "")
        if session_dir and not Path(session_dir).samefile(project_root):
            console.print("[yellow]Warning: Active session is for different project:[/yellow]")
            console.print(f"[dim]  Session: {session_dir}[/dim]")
            console.print(f"[dim]  Current: {project_root}[/dim]")
            console.print("[yellow]Renaming anyway (session may have been from renamed directory)[/yellow]")

        # Update the title
        old_title = session_data.get("title", "Untitled")
        session_data["title"] = new_title

        # Atomic write: write to temp file, then rename
        # This ensures the file is never in a partially-written state
        temp_fd, temp_path = tempfile.mkstemp(dir=session_file.parent, prefix=".tmp_", suffix=".json", text=True)
        try:
            with open(temp_fd, "w") as f:
                json.dump(session_data, f, indent=2)

            # Atomic rename - this is atomic on POSIX systems
            # If OpenCode is reading the file, it will either see old or new data
            # but never partial data
            Path(temp_path).replace(session_file)

            console.print(f"[green]✓[/green] Renamed OpenCode session to [bold]{new_title}[/bold]")
            console.print(f"[dim]Previous title: {old_title}[/dim]")
            logger.info(
                "opencode_session_renamed",
                session_id=session_file.stem,
                old_title=old_title,
                new_title=new_title,
            )
        except Exception:
            # Clean up temp file if rename failed
            try:
                Path(temp_path).unlink()
            except Exception:
                pass
            raise

    except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
        console.print(f"[red]Failed to update session file: {e}[/red]")
        console.print("[yellow]The session file may have been modified by OpenCode.[/yellow]")
        raise typer.Exit(1)


@app.command("list-opencode-sessions")
def list_opencode_sessions() -> None:
    """List OpenCode TUI sessions for the current project

    Shows session IDs and titles to help identify which session to rename.
    Use the session ID with: s9 agent rename-tui <name> <role> --session-id <id>
    """
    import hashlib

    try:
        opencode_dir = get_opencode_dir()
        project_root = opencode_dir.parent
    except FileNotFoundError:
        console.print("[red]Error: .opencode directory not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    opencode_storage = Path.home() / ".local" / "share" / "opencode" / "storage" / "session"
    if not opencode_storage.exists():
        console.print("[red]Error: OpenCode storage directory not found.[/red]")
        raise typer.Exit(1)

    # Find all session directories and check which ones match this project
    console.print(f"\n[cyan]OpenCode sessions for {project_root.name}:[/cyan]\n")

    found_any = False
    for project_dir in opencode_storage.iterdir():
        if not project_dir.is_dir() or project_dir.name == "global":
            continue

        for session_file in project_dir.glob("ses_*.json"):
            try:
                with open(session_file) as f:
                    session_data = json.load(f)

                session_dir = session_data.get("directory", "")
                if session_dir and Path(session_dir).resolve() == project_root.resolve():
                    found_any = True
                    session_id = session_data.get("id", session_file.stem)
                    title = session_data.get("title", "Untitled")
                    slug = session_data.get("slug", "")

                    # Check age
                    import time

                    mtime = session_file.stat().st_mtime
                    age_seconds = time.time() - mtime
                    if age_seconds < 60:
                        age = f"{int(age_seconds)}s ago"
                    elif age_seconds < 3600:
                        age = f"{int(age_seconds / 60)}m ago"
                    else:
                        age = f"{int(age_seconds / 3600)}h ago"

                    console.print(f"  [green]{session_id}[/green] ({slug}) - modified {age}")
                    console.print(f"    {title}")
                    console.print()

            except (json.JSONDecodeError, FileNotFoundError, PermissionError):
                continue

    if not found_any:
        console.print("[yellow]No OpenCode sessions found for this project.[/yellow]")
    else:
        console.print("[dim]To rename a session, use:[/dim]")
        console.print("[dim]  s9 agent rename-tui <name> <role> --session-id <session-id>[/dim]\n")


@app.command("rename-tui")
@handle_errors("Failed to rename OpenCode TUI session")
def rename_tui(
    name: str = typer.Argument(..., help="Agent daemon name"),
    role: str = typer.Argument(..., help="Agent role"),
    session_id: str | None = typer.Option(None, "--session-id", "-s", help="OpenCode session ID (e.g., ses_xxx)"),
) -> None:
    """Rename the current OpenCode TUI session to match agent identity

    If --session-id is provided, renames that specific session. Otherwise, attempts
    to auto-detect the current session by finding the most recently active session
    diff file for this project.
    """
    # Find the project root (contains .opencode directory)
    try:
        opencode_dir = get_opencode_dir()
        project_root = opencode_dir.parent
    except FileNotFoundError:
        console.print("[red]Error: .opencode directory not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    # Find OpenCode storage directories
    session_diff_storage, session_storage = _find_opencode_storage()

    # Determine session ID: use provided or auto-detect
    current_session_id = None
    if session_id:
        current_session_id = session_id
        logger.debug("session_id_provided", session_id=session_id)
    else:
        # Use diff file recency - the most reliable detection method
        # The active session continuously writes to its diff file
        current_session_id = _detect_session_via_diff_recency(project_root, session_diff_storage, session_storage)

        # If that somehow fails, fall back to session file recency
        if not current_session_id:
            logger.debug("diff_recency_failed_fallback_to_session_recency")
            project_sessions = _find_project_sessions(project_root, session_storage)
            current_session_id = _detect_session_via_recency(project_root, project_sessions)

    # At this point, current_session_id should be set (or we would have exited)
    if not current_session_id:
        console.print("[red]Error: Failed to determine session ID[/red]")
        raise typer.Exit(1)

    # Locate the session file
    session_file = _locate_session_file(current_session_id, session_storage)

    # Update the session title
    new_title = f"{name.capitalize()} - {role}"
    _update_session_title(session_file, new_title, project_root)
