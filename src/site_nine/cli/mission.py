"""Mission management commands"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table
from typerdrive import handle_errors

from site_nine.missions import MissionManager
from site_nine.core.database import Database
from site_nine.core.paths import get_opencode_dir

app = typer.Typer(help="Manage missions")
console = Console()


def _get_manager() -> MissionManager:
    """Get mission manager"""
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
    return MissionManager(db)


@app.command()
@handle_errors("Failed to start mission")
def start(
    name: str = typer.Argument(..., help="Daemon name"),
    role: str = typer.Option(..., "--role", "-r", help="Agent role"),
    task: str = typer.Option("", "--task", "-t", help="Task summary"),
) -> None:
    """Start a new mission"""
    manager = _get_manager()

    # Validate and convert role to title case
    valid_roles = [
        "administrator",
        "architect",
        "engineer",
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

    mission_id = manager.start_mission(persona_name=name, role=role, objective=task)

    console.print(f"[green]✓[/green] Started mission #{mission_id}")
    console.print(f"  Persona: {name}")
    console.print(f"  Role: {role}")
    if task:
        console.print(f"  Objective: {task}")
    logger.info(f"Started mission {mission_id}: {name} ({role})")


@app.command()
@handle_errors("Failed to list missions")
def list(
    active_only: bool = typer.Option(False, "--active-only", help="Show only active missions"),
    role: str = typer.Option(None, "--role", "-r", help="Filter by role"),
) -> None:
    """List missions"""
    manager = _get_manager()

    # Normalize role to title case for case-insensitive filtering
    if role:
        role = role.title()

    missions = manager.list_missions(active_only=active_only, role=role)

    if not missions:
        console.print("[yellow]No missions found.[/yellow]")
        return

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

    console.print(table)
    logger.debug(f"Listed {len(missions)} missions")


@app.command()
@handle_errors("Failed to show mission")
def show(
    mission_id: int = typer.Argument(..., help="Mission ID"),
) -> None:
    """Show mission details"""
    manager = _get_manager()
    mission = manager.get_mission(mission_id)

    if not mission:
        console.print(f"[red]Error: Mission #{mission_id} not found.[/red]")
        raise typer.Exit(1)

    # Determine status from end_time
    status = "Active" if mission.end_time is None else "Complete"

    console.print(f"[bold]Mission #{mission.id}[/bold]")
    console.print(f"  Persona: {mission.persona_name}")
    console.print(f"  Codename: {mission.codename}")
    console.print(f"  Role: {mission.role}")
    console.print(f"  Status: {status}")
    console.print(f"  Start Date: {mission.start_date}")
    console.print(f"  Start Time: {mission.start_time}")
    if mission.end_time:
        console.print(f"  End Time: {mission.end_time}")
    console.print(f"  Mission File: {mission.mission_file}")
    if mission.objective:
        console.print(f"  Objective: {mission.objective}")
    logger.debug(f"Displayed details for mission {mission_id}")


@app.command()
@handle_errors("Failed to generate mission summary")
def summary(
    mission_id: int = typer.Argument(..., help="Mission ID"),
) -> None:
    """Generate mission summary from git history and database

    Auto-generates a summary showing:
    - Files changed since mission start
    - Commits made (filtered by persona)
    - Tasks claimed and their status
    """
    manager = _get_manager()
    mission = manager.get_mission(mission_id)

    if not mission:
        console.print(f"[red]Error: Mission #{mission_id} not found.[/red]")
        raise typer.Exit(1)

    console.print(
        f"\n[bold cyan]Mission Summary for #{mission.id} ({mission.persona_name} - {mission.role})[/bold cyan]\n"
    )

    # Mission details
    console.print(f"[bold]Mission Details:[/bold]")
    console.print(f"  Codename: {mission.codename}")
    console.print(f"  Start: {mission.start_time}")
    if mission.end_time:
        console.print(f"  End: {mission.end_time}")
    if mission.objective:
        console.print(f"  Objective: {mission.objective}")

    # Get files changed via git
    console.print(f"\n[bold]Files Changed:[/bold]")
    try:
        import subprocess

        # Get files changed since mission start using git diff
        result = subprocess.run(
            ["git", "diff", "--name-status", f"@{{'{mission.start_time}'}}", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                parts = line.split("\t", 1)
                if len(parts) == 2:
                    status, filepath = parts
                    status_map = {"M": "modified", "A": "added", "D": "deleted", "R": "renamed"}
                    status_display = status_map.get(status[0], status)
                    console.print(f"  • [{status_display}] {filepath}")
        else:
            # Fallback: use git log --name-status
            result = subprocess.run(
                ["git", "log", "--name-status", "--pretty=format:", f"--since={mission.start_time}"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0 and result.stdout.strip():
                files_seen = set()
                for line in result.stdout.strip().split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        status, filepath = parts
                        if filepath not in files_seen:
                            files_seen.add(filepath)
                            status_map = {"M": "modified", "A": "added", "D": "deleted", "R": "renamed"}
                            status_display = status_map.get(status[0], status)
                            console.print(f"  • [{status_display}] {filepath}")
            else:
                console.print("  [dim]No files changed (or git unavailable)[/dim]")

    except Exception as e:
        console.print(f"  [yellow]Could not retrieve git history: {e}[/yellow]")

    # Get commits made
    console.print(f"\n[bold]Commits:[/bold]")
    try:
        # Try to find commits with persona name in commit message
        result = subprocess.run(
            [
                "git",
                "log",
                "--oneline",
                f"--since={mission.start_time}",
                f"--grep={mission.persona_name}",
                "--grep=Mission:",
                "--perl-regexp",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                console.print(f"  • {line}")
        else:
            # Show all commits since mission start
            result = subprocess.run(
                ["git", "log", "--oneline", f"--since={mission.start_time}", "-10"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                console.print("  [dim](Showing recent commits, may include other work):[/dim]")
                for line in result.stdout.strip().split("\n"):
                    console.print(f"  • {line}")
            else:
                console.print("  [dim]No commits found[/dim]")

    except Exception as e:
        console.print(f"  [yellow]Could not retrieve commits: {e}[/yellow]")

    # Get tasks claimed
    console.print(f"\n[bold]Tasks Claimed:[/bold]")
    try:
        from site_nine.tasks import TaskManager

        task_manager = TaskManager(manager.db)

        # Get all tasks for this mission
        tasks = task_manager.list_tasks(mission_id=mission_id)

        if tasks:
            for task in tasks:
                status_icon = {
                    "COMPLETE": "✓",
                    "UNDERWAY": "→",
                    "PAUSED": "⏸",
                    "BLOCKED": "🚫",
                    "REVIEW": "👀",
                    "TODO": "○",
                    "ABORTED": "✗",
                }.get(task.status, "?")
                console.print(f"  {status_icon} [{task.status}] {task.id} - {task.title}")
        else:
            console.print("  [dim]No tasks claimed[/dim]")

    except Exception as e:
        console.print(f"  [yellow]Could not retrieve tasks: {e}[/yellow]")

    console.print()
    logger.info(f"Generated summary for mission {mission_id}")


@app.command()
@handle_errors("Failed to end mission")
def end(
    mission_id: int = typer.Argument(..., help="Mission ID"),
) -> None:
    """End a mission"""
    manager = _get_manager()

    # Verify mission exists
    mission = manager.get_mission(mission_id)
    if not mission:
        console.print(f"[red]Error: Mission #{mission_id} not found.[/red]")
        raise typer.Exit(1)

    manager.end_mission(mission_id)
    console.print(f"[green]✓[/green] Ended mission #{mission_id}")
    logger.info(f"Ended mission {mission_id}")


# NOTE: Pause/resume commands removed per ADR-006
# Missions no longer have status field - they are either active (end_time IS NULL) or complete
# @app.command()
# @handle_errors("Failed to pause mission")
# def pause(
#     mission_id: int = typer.Argument(..., help="Mission ID to pause"),
#     reason: str | None = typer.Option(None, "--reason", help="Reason for pausing"),
# ) -> None:
#     """Pause an active mission"""
#     ...


# NOTE: Pause/resume commands removed per ADR-006
# @app.command()
# @handle_errors("Failed to resume mission")
# def resume(
#     mission_id: int = typer.Argument(..., help="Mission ID to resume"),
# ) -> None:
#     """Resume a paused mission"""
#     ...


@app.command()
@handle_errors("Failed to update mission")
def update(
    mission_id: int = typer.Argument(..., help="Mission ID to update"),
    objective: str | None = typer.Option(None, "--task", "-t", help="Update task summary"),
    role: str | None = typer.Option(None, "--role", "-r", help="Update role"),
) -> None:
    """Update mission metadata"""
    manager = _get_manager()

    if not objective and not role:
        console.print("[yellow]No updates specified. Use --task or --role[/yellow]")
        raise typer.Exit(0)

    # Verify mission exists
    mission = manager.get_mission(mission_id)
    if not mission:
        console.print(f"[red]Error: Mission #{mission_id} not found.[/red]")
        raise typer.Exit(1)

    # Check if mission is active (no end_time)
    if mission.end_time is not None:
        console.print(f"[red]Error: Cannot update completed mission. Only active missions can be updated.[/red]")
        raise typer.Exit(1)

    # Validate role if provided
    if role:
        valid_roles = [
            "administrator",
            "architect",
            "engineer",
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

    manager.update_mission(mission_id, objective=objective, role=role)

    console.print(f"[green]✓[/green] Updated mission #{mission_id}")
    if objective:
        console.print(f"  Task: {objective}")
    if role:
        console.print(f"  Role: {role}")
    logger.info(f"Updated mission {mission_id}")


def _find_current_opencode_session(project_root: Path) -> str | None:
    """
    Find the current OpenCode session by looking for the most recent
    mission file in session diffs.

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

    # Find the most recent mission file for this project
    # Try both old (.opencode/sessions) and new (.opencode/work/sessions) locations
    missions_dirs = [
        project_root / ".opencode" / "work" / "missions",
        project_root / ".opencode" / "missions",
    ]

    session_files = []
    for missions_dir in missions_dirs:
        if missions_dir.exists():
            session_files.extend(missions_dir.glob("*.md"))

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
        ("Engineer", "implement features and write code"),
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


def _find_opencode_storage() -> tuple[Path, Path, Path]:
    """Find and validate OpenCode storage directories

    Returns:
        Tuple of (session_diff_storage, session_storage, part_storage) paths

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
    part_storage = opencode_storage / "part"
    return session_diff_storage, session_storage, part_storage


def _detect_session_via_uuid_marker(
    uuid_marker: str,
    project_root: Path,
    session_diff_storage: Path,
    session_storage: Path,
    part_storage: Path,
) -> str | None:
    """Detect current OpenCode session by searching for UUID marker in message parts

    This is the most reliable detection method. The UUID marker should be generated
    at session start using `generate-session-uuid` command, which outputs to console.
    OpenCode captures this output in the message part files, which we search here.

    Args:
        uuid_marker: UUID marker to search for (e.g., "session-marker-abc123")
        project_root: Project root directory
        session_diff_storage: Path to OpenCode session_diff directory (unused but kept for compatibility)
        session_storage: Path to OpenCode session storage directory
        part_storage: Path to OpenCode part directory

    Returns:
        Session ID (e.g., "ses_xxx") or None if no matching session found
    """
    import json
    import time

    # Search all recent message parts for the UUID marker
    current_time = time.time()
    recent_threshold = 600  # Check parts modified in last 10 minutes

    # Collect all part files sorted by modification time (most recent first)
    part_files = []
    for msg_dir in part_storage.iterdir():
        if not msg_dir.is_dir() or not msg_dir.name.startswith("msg_"):
            continue
        for part_file in msg_dir.glob("prt_*.json"):
            try:
                mtime = part_file.stat().st_mtime
                age_seconds = current_time - mtime
                if age_seconds <= recent_threshold:
                    part_files.append((part_file, mtime))
            except (FileNotFoundError, PermissionError):
                continue

    # Sort by modification time (most recent first)
    part_files.sort(key=lambda x: x[1], reverse=True)

    # Track which sessions we've already verified for project match
    verified_sessions = {}

    for part_file, mtime in part_files:
        try:
            with open(part_file) as f:
                part_data = json.load(f)

            # Check if this is a tool part (contains tool outputs)
            if part_data.get("type") != "tool":
                continue

            session_id = part_data.get("sessionID")
            if not session_id:
                continue

            # Check if we've already verified this session belongs to this project
            if session_id not in verified_sessions:
                # Verify this session is for the current project
                session_file = None
                for project_dir in session_storage.iterdir():
                    if not project_dir.is_dir():
                        continue
                    candidate = project_dir / f"{session_id}.json"
                    if candidate.exists():
                        session_file = candidate
                        break

                if not session_file:
                    verified_sessions[session_id] = False
                    continue

                try:
                    with open(session_file) as f:
                        session_data = json.load(f)
                    session_dir = session_data.get("directory", "")
                    matches = session_dir and Path(session_dir).resolve() == project_root.resolve()
                    verified_sessions[session_id] = matches
                    if not matches:
                        continue
                except (json.JSONDecodeError, FileNotFoundError, PermissionError):
                    verified_sessions[session_id] = False
                    continue
            elif not verified_sessions[session_id]:
                continue

            # Search the tool output for the UUID marker
            state = part_data.get("state", {})
            output = state.get("output", "")
            if isinstance(output, str) and uuid_marker in output:
                age_seconds = current_time - mtime
                logger.debug(
                    "session_detected_via_uuid_marker",
                    session_id=session_id,
                    uuid_marker=uuid_marker,
                    age_seconds=int(age_seconds),
                )
                return session_id

        except (json.JSONDecodeError, FileNotFoundError, PermissionError):
            continue

    logger.debug("uuid_marker_not_found", uuid_marker=uuid_marker)
    return None


def _detect_session_via_diff_content(
    project_root: Path,
    session_diff_storage: Path,
    session_storage: Path,
) -> str | None:
    """Detect current OpenCode session by correlating recent git changes with diff content

    This is more reliable than timestamp-based detection when multiple sessions are active.
    We check which session's diff file contains the files we've most recently edited.

    Args:
        project_root: Project root directory
        session_diff_storage: Path to OpenCode session_diff directory
        session_storage: Path to OpenCode session storage directory

    Returns:
        Session ID (e.g., "ses_xxx") or None if no matching session found
    """
    import json
    import subprocess
    import time

    # Get list of recently modified files from git (last 60 seconds of activity)
    try:
        # Get files modified in the last minute according to git
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=2,
        )
        recent_files = set(result.stdout.strip().split("\n")) if result.stdout.strip() else set()

        # Also get staged files
        result = subprocess.run(
            ["git", "diff", "--name-only", "--cached"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.stdout.strip():
            recent_files.update(result.stdout.strip().split("\n"))

        # If no git changes, we can't use content correlation
        if not recent_files:
            logger.debug("no_git_changes_for_content_correlation")
            return None

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        logger.debug("git_command_failed_in_content_correlation")
        return None

    # Find sessions for this project that have been recently modified
    current_time = time.time()
    recent_threshold = 60  # Check sessions modified in last minute

    diff_files = sorted(session_diff_storage.glob("ses_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    candidate_sessions = []

    for diff_file in diff_files:
        mtime = diff_file.stat().st_mtime
        age_seconds = current_time - mtime

        # Only check recently modified sessions
        if age_seconds > recent_threshold:
            break

        mission_id = diff_file.stem

        # Verify this session is for the current project
        session_file = None
        for project_dir in session_storage.iterdir():
            if not project_dir.is_dir():
                continue
            candidate = project_dir / f"{mission_id}.json"
            if candidate.exists():
                session_file = candidate
                break

        if not session_file:
            continue

        try:
            with open(session_file) as f:
                session_data = json.load(f)
            session_dir = session_data.get("directory", "")
            if not (session_dir and Path(session_dir).resolve() == project_root.resolve()):
                continue
        except (json.JSONDecodeError, FileNotFoundError, PermissionError):
            continue

        # Now check if this session's diff contains our recent files
        try:
            with open(diff_file) as f:
                diff_data = json.load(f)

            # Get the last few entries from the diff (most recent edits)
            if not (type(diff_data).__name__ == "list" and len(diff_data) > 0):
                continue

            # Check last 10 entries for overlap with our recent files
            recent_diff_files = {entry.get("file", "") for entry in diff_data[-10:]}
            overlap = recent_files & recent_diff_files

            if overlap:
                # Calculate a match score based on how many files overlap
                score = len(overlap)
                candidate_sessions.append((mission_id, score, age_seconds))
                logger.debug(
                    "session_content_match_found",
                    mission_id=mission_id,
                    matched_files=[*overlap][:3],  # Log first 3 matches
                    score=score,
                )

        except (json.JSONDecodeError, FileNotFoundError, PermissionError):
            continue

    # Return the session with the best match (highest score, then most recent)
    if candidate_sessions:
        # Sort by score (descending), then by age (ascending)
        best_match = sorted(candidate_sessions, key=lambda x: (-x[1], x[2]))[0]
        mission_id, score, age_seconds = best_match
        logger.debug(
            "session_detected_via_content_correlation", mission_id=mission_id, score=score, age_seconds=int(age_seconds)
        )
        return mission_id

    return None


def _detect_session_via_diff_recency(
    project_root: Path,
    session_diff_storage: Path,
    session_storage: Path,
) -> str | None:
    """Detect current OpenCode session by finding most recently modified diff file

    This is a fallback method when content correlation doesn't work. When multiple
    sessions are active, uses a 10-second recency window to reduce race conditions.

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

    current_time = time.time()
    recent_threshold = 10  # Only consider files modified in last 10 seconds

    # First pass: Find project sessions modified within the recent threshold
    recent_project_sessions = []
    for diff_file in diff_files:
        mtime = diff_file.stat().st_mtime
        age_seconds = current_time - mtime

        # Skip files older than threshold
        if age_seconds > recent_threshold:
            # Since files are sorted by mtime, we can stop here
            break

        mission_id = diff_file.stem

        # Find the corresponding session file to verify project
        session_file = None
        for project_dir in session_storage.iterdir():
            if not project_dir.is_dir():
                continue
            candidate = project_dir / f"{mission_id}.json"
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
                recent_project_sessions.append((mission_id, age_seconds))
        except (json.JSONDecodeError, FileNotFoundError, PermissionError):
            continue

    # If we found recent sessions for this project, return the most recent one
    if recent_project_sessions:
        mission_id, age_seconds = min(recent_project_sessions, key=lambda x: x[1])

        # Warn if multiple sessions are active (potential race condition)
        if len(recent_project_sessions) > 1:
            logger.warning(
                "multiple_active_sessions_detected",
                count=len(recent_project_sessions),
                selected=mission_id,
                note="If wrong session renamed, use --session-id flag",
            )

        logger.debug("session_detected_via_diff_recency", mission_id=mission_id, age_seconds=int(age_seconds))
        return mission_id

    # Fallback: No recent sessions found, use old behavior (first match in top 5)
    for diff_file in diff_files[:5]:
        mission_id = diff_file.stem

        # Find the corresponding session file to verify project
        session_file = None
        for project_dir in session_storage.iterdir():
            if not project_dir.is_dir():
                continue
            candidate = project_dir / f"{mission_id}.json"
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
                mtime = diff_file.stat().st_mtime
                age_seconds = current_time - mtime
                logger.debug(
                    "session_detected_via_diff_recency_fallback", mission_id=mission_id, age_seconds=int(age_seconds)
                )
                return mission_id
        except (json.JSONDecodeError, FileNotFoundError, PermissionError):
            continue

    # No matching session found
    return None


def _find_project_sessions(
    project_root: Path,
    session_storage: Path,
) -> list[tuple[Path, float]]:
    """Find all OpenCode missions for the current project

    Args:
        project_root: Project root directory
        session_storage: Path to OpenCode session storage directory

    Returns:
        List of (session_file_path, modification_time) tuples
    """
    project_missions = []
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
                    project_missions.append((session_file, mtime))
            except (json.JSONDecodeError, FileNotFoundError, PermissionError):
                continue

    return project_missions


def _detect_session_via_recency(
    project_root: Path,
    project_sessions: list[tuple[Path, float]],
) -> str | None:
    """Detect current OpenCode session based on recent activity

    Uses modification time to identify the most likely current mission.
    Handles multiple active missions by prompting the user.

    Args:
        project_root: Project root directory
        project_sessions: List of (session_file_path, modification_time) tuples

    Returns:
        Session ID (e.g., "ses_xxx") or None

    Raises:
        typer.Exit: If multiple missions are active and user needs to choose
    """
    import time

    if not project_sessions:
        console.print(f"[red]Error: No OpenCode missions found for project {project_root.name}[/red]")
        raise typer.Exit(1)

    # Find missions modified in last 3 seconds (very recent activity)
    very_recent_missions = [(f, mt) for f, mt in project_sessions if time.time() - mt < 3]

    if len(very_recent_missions) == 1:
        # Only one session active in the last 3 seconds - must be us!
        mission_id = very_recent_missions[0][0].stem
        logger.debug("session_auto_detected_single_active", mission_id=mission_id)
        return mission_id

    elif len(very_recent_missions) > 1:
        # Multiple missions active - need user to specify
        console.print("[yellow]Multiple active OpenCode missions detected for this project.[/yellow]")
        console.print("[yellow]Please specify which session to rename:[/yellow]\n")

        for session_file, mtime in sorted(very_recent_missions, key=lambda x: x[1], reverse=True):
            try:
                with open(session_file) as f:
                    session_data = json.load(f)
                title = session_data.get("title", "Untitled")
                slug = session_data.get("slug", "")
                age = int(time.time() - mtime)
                console.print(f"  [green]{session_file.stem}[/green] ({slug}) - {age}s ago")
                console.print(f"    {title}\n")
            except Exception:
                pass

        console.print("[yellow]Run with: s9 mission rename-tui <name> <role> --session-id <id>[/yellow]")
        console.print("[yellow]Or use: s9 mission list-opencode-sessions (to see all missions)[/yellow]")
        raise typer.Exit(1)

    else:
        # No very recent activity - use most recent
        import time

        most_recent = max(project_sessions, key=lambda x: x[1])
        mission_id = most_recent[0].stem
        mtime = most_recent[1]
        age = int(time.time() - mtime)
        console.print(f"[yellow]No session modified in last 3 seconds. Using most recent ({age}s ago).[/yellow]")
        console.print(f"[yellow]Session: {mission_id}[/yellow]")
        console.print("[yellow]If this is wrong, pass --session-id explicitly[/yellow]\n")
        logger.debug("session_auto_detected_fallback", mission_id=mission_id, age_seconds=age)
        return mission_id


def _locate_session_file(
    mission_id: str,
    session_storage: Path,
) -> Path:
    """Locate the session JSON file for a given session ID

    Args:
        mission_id: OpenCode session ID (e.g., "ses_xxx")
        session_storage: Path to OpenCode session storage directory

    Returns:
        Path to the session JSON file

    Raises:
        typer.Exit: If session file is not found
    """
    for project_dir in session_storage.iterdir():
        if not project_dir.is_dir():
            continue
        candidate = project_dir / f"{mission_id}.json"
        # Use try/except to handle race condition if file is deleted
        try:
            if candidate.exists():
                return candidate
        except (FileNotFoundError, PermissionError):
            # File was deleted or became inaccessible between check and access
            continue

    console.print(f"[red]Session file not found for {mission_id}[/red]")
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
                mission_id=session_file.stem,
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


@app.command("generate-session-uuid")
def generate_session_uuid() -> None:
    """Generate a unique session UUID marker for reliable session detection

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
    import uuid

    # Generate a unique session marker
    session_uuid = f"session-marker-{uuid.uuid4().hex[:16]}"

    # Output the marker - OpenCode will capture this in the session data
    console.print(f"[bold green]Session UUID:[/bold green] {session_uuid}")
    console.print(f"[dim]Use this marker with: s9 mission rename-tui <name> <role> --uuid-marker {session_uuid}[/dim]")

    # Also output just the UUID for easy parsing
    console.print(session_uuid)

    logger.debug("session_uuid_generated", uuid=session_uuid)


@app.command("list-opencode-sessions")
def list_opencode_sessions() -> None:
    """List OpenCode TUI missions for the current project

    Shows session IDs and titles to help identify which session to rename.
    Use the session ID with: s9 mission rename-tui <name> <role> --session-id <id>
    """

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
    console.print(f"\n[cyan]OpenCode missions for {project_root.name}:[/cyan]\n")

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
                    mission_id = session_data.get("id", session_file.stem)
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

                    console.print(f"  [green]{mission_id}[/green] ({slug}) - modified {age}")
                    console.print(f"    {title}")
                    console.print()

            except (json.JSONDecodeError, FileNotFoundError, PermissionError):
                continue

    if not found_any:
        console.print("[yellow]No OpenCode missions found for this project.[/yellow]")
    else:
        console.print("[dim]To rename a session, use:[/dim]")
        console.print("[dim]  s9 mission rename-tui <name> <role> --session-id <session-id>[/dim]\n")


@app.command("rename-tui")
@handle_errors("Failed to rename OpenCode TUI session")
def rename_tui(
    name: str = typer.Argument(..., help="Persona name"),
    role: str = typer.Argument(..., help="Agent role"),
    mission_id: str | None = typer.Option(None, "--session-id", "-s", help="OpenCode session ID (e.g., ses_xxx)"),
    uuid_marker: str | None = typer.Option(
        None, "--uuid-marker", "-u", help="Session UUID marker from generate-session-uuid"
    ),
) -> None:
    """Rename the current OpenCode TUI session to match agent identity

    If --session-id is provided, renames that specific mission.
    If --uuid-marker is provided, searches session diffs for that marker (most reliable).
    Otherwise, attempts to auto-detect using content correlation and timestamps.
    """
    # Find the project root (contains .opencode directory)
    try:
        opencode_dir = get_opencode_dir()
        project_root = opencode_dir.parent
    except FileNotFoundError:
        console.print("[red]Error: .opencode directory not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    # Find OpenCode storage directories
    session_diff_storage, session_storage, part_storage = _find_opencode_storage()

    # Determine session ID: use provided or auto-detect
    current_mission_id = None
    multiple_sessions_detected = False
    if mission_id:
        current_mission_id = mission_id
        logger.debug("mission_id_provided", mission_id=mission_id)
    else:
        # Try UUID marker first (most reliable)
        if uuid_marker:
            current_mission_id = _detect_session_via_uuid_marker(
                uuid_marker, project_root, session_diff_storage, session_storage, part_storage
            )
            if not current_mission_id:
                console.print(f"[yellow]Warning: UUID marker '{uuid_marker}' not found in any recent sessions[/yellow]")
                console.print("[dim]Falling back to other detection methods...[/dim]")

        # Try content correlation as fallback
        if not current_mission_id:
            current_mission_id = _detect_session_via_diff_content(project_root, session_diff_storage, session_storage)

        # Fall back to timestamp-based detection if content correlation doesn't work
        if not current_mission_id:
            logger.debug("content_correlation_failed_fallback_to_timestamp")

            # Check for multiple active sessions (to warn the user)
            import time

            current_time = time.time()
            recent_threshold = 10
            diff_files = sorted(session_diff_storage.glob("ses_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            recent_project_count = 0
            for diff_file in diff_files:
                if current_time - diff_file.stat().st_mtime > recent_threshold:
                    break
                # Quick check if this might be for our project (full check is in _detect_session_via_diff_recency)
                recent_project_count += 1

            if recent_project_count > 1:
                multiple_sessions_detected = True

            # Use diff file recency as fallback
            current_mission_id = _detect_session_via_diff_recency(project_root, session_diff_storage, session_storage)

        # Final fallback to session file recency
        if not current_mission_id:
            logger.debug("diff_recency_failed_fallback_to_session_recency")
            project_missions = _find_project_sessions(project_root, session_storage)
            current_mission_id = _detect_session_via_recency(project_root, project_missions)

    # At this point, current_mission_id should be set (or we would have exited)
    if not current_mission_id:
        console.print("[red]Error: Failed to determine session ID[/red]")
        raise typer.Exit(1)

    # Locate the session file
    session_file = _locate_session_file(current_mission_id, session_storage)

    # Get mission codename from database
    # Query the most recent active mission for this persona
    manager = _get_manager()
    db_path = opencode_dir / "data" / "project.db"
    db = Database(db_path)

    # Get the most recent active mission for this persona
    missions = db.execute_query(
        """
        SELECT codename FROM missions 
        WHERE persona_name = :persona_name 
        AND end_time IS NULL 
        ORDER BY created_at DESC 
        LIMIT 1
        """,
        {"persona_name": name.lower()},
    )

    # Format title with codename if available
    if missions and missions[0]["codename"]:
        codename = missions[0]["codename"]
        new_title = f"Operation {codename}: {name.capitalize()} - {role}"
    else:
        # Fallback if no active mission found
        new_title = f"{name.capitalize()} - {role}"

    _update_session_title(session_file, new_title, project_root)

    # Warn if multiple sessions were active (potential race condition)
    if multiple_sessions_detected:
        console.print("[yellow]⚠ Warning: Multiple active sessions detected.[/yellow]")
        console.print("[dim]If the wrong session was renamed, run:[/dim]")
        console.print(f"[dim]  s9 mission list-opencode-sessions[/dim]")
        console.print(f"[dim]  s9 mission rename-tui {name} {role} --session-id <correct-session-id>[/dim]")
