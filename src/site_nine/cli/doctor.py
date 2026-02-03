"""Database health check and repair commands"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import typer
from loguru import logger
from rich.console import Console
from typerdrive import handle_errors

from site_nine.core.database import Database
from site_nine.core.paths import get_opencode_dir, validate_path_within_project

console = Console()


@handle_errors("Failed to run health checks")
def doctor_command(
    fix: bool = typer.Option(False, "--fix", help="Apply fixes automatically"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
) -> None:
    """Run health checks and validate data integrity

    Performs comprehensive checks on the database to identify:
    - Invalid foreign key references
    - Inconsistent task states
    - Agent session data issues
    - Incorrect usage counters
    - Missing files

    By default, only reports issues. Use --fix to automatically repair safe issues.
    """
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

    console.print()
    console.print("🔍 [bold cyan]Running diagnostics...[/bold cyan]")
    console.print()

    issues_found: list[tuple[str, str, str, Callable[[], None] | None]] = []
    issues_fixed: list[str] = []

    # Check 1: Foreign Key Integrity
    console.print("[bold]1. Checking foreign key integrity...[/bold]")

    # Check agents.base_name → daemon_names.name
    invalid_agents = db.execute_query("""
        SELECT a.id, a.name, a.base_name
        FROM agents a
        LEFT JOIN daemon_names dn ON a.base_name = dn.name
        WHERE dn.name IS NULL
    """)

    if invalid_agents:
        for agent in invalid_agents:
            issue = (
                f"Agent #{agent['id']} ({agent['name']}): base_name '{agent['base_name']}' not found in daemon_names"
            )
            issues_found.append(("foreign_key", "error", issue, None))
            if verbose:
                console.print(f"  [red]✗[/red] {issue}")
        console.print(f"  [yellow]⚠[/yellow]  Found {len(invalid_agents)} invalid agent references")
    else:
        console.print("  [green]✓[/green] All agent base_names are valid")

    # Check tasks.agent_id → agents.id
    orphaned_tasks = db.execute_query("""
        SELECT t.id, t.title, t.agent_id
        FROM tasks t
        WHERE t.agent_id IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM agents WHERE id = t.agent_id)
    """)

    if orphaned_tasks:
        for task in orphaned_tasks:
            issue = f"Task {task['id']}: references non-existent agent_id {task['agent_id']}"
            task_id = task["id"]

            def fix_fn():
                db.execute_update("UPDATE tasks SET agent_id = NULL WHERE id = :id", {"id": task_id})

            issues_found.append(("foreign_key", "fixable", issue, fix_fn))
            if verbose:
                console.print(f"  [yellow]⚠[/yellow] {issue}")
        console.print(f"  [yellow]⚠[/yellow]  Found {len(orphaned_tasks)} orphaned task references")
    else:
        console.print("  [green]✓[/green] All task agent_ids are valid")

    # Check task_dependencies
    invalid_deps = db.execute_query("""
        SELECT td.task_id, td.depends_on_task_id
        FROM task_dependencies td
        WHERE NOT EXISTS (SELECT 1 FROM tasks WHERE id = td.task_id)
           OR NOT EXISTS (SELECT 1 FROM tasks WHERE id = td.depends_on_task_id)
    """)

    if invalid_deps:
        for dep in invalid_deps:
            issue = f"Dependency: {dep['task_id']} → {dep['depends_on_task_id']} references non-existent task(s)"
            task_id = dep["task_id"]
            depends_on = dep["depends_on_task_id"]

            def fix_fn():
                db.execute_update(
                    "DELETE FROM task_dependencies WHERE task_id = :task_id AND depends_on_task_id = :depends_on",
                    {"task_id": task_id, "depends_on": depends_on},
                )

            issues_found.append(("foreign_key", "fixable", issue, fix_fn))
            if verbose:
                console.print(f"  [yellow]⚠[/yellow] {issue}")
        console.print(f"  [yellow]⚠[/yellow]  Found {len(invalid_deps)} invalid dependencies")
    else:
        console.print("  [green]✓[/green] All task dependencies are valid")

    console.print()

    # Check 2: Task State Consistency
    console.print("[bold]2. Checking task state consistency...[/bold]")

    # Tasks marked COMPLETE/ABORTED should have closed_at
    unclosed_tasks = db.execute_query("""
        SELECT id, title, status
        FROM tasks
        WHERE status IN ('COMPLETE', 'ABORTED')
        AND closed_at IS NULL
    """)

    if unclosed_tasks:
        for task in unclosed_tasks:
            issue = f"Task {task['id']}: status is {task['status']} but missing closed_at timestamp"
            now = datetime.now(timezone.utc).isoformat()
            task_id = task["id"]
            timestamp = now

            def fix_fn():
                db.execute_update(
                    "UPDATE tasks SET closed_at = :timestamp WHERE id = :id", {"timestamp": timestamp, "id": task_id}
                )

            issues_found.append(("task_state", "fixable", issue, fix_fn))
            if verbose:
                console.print(f"  [yellow]⚠[/yellow] {issue}")
        console.print(f"  [yellow]⚠[/yellow]  Found {len(unclosed_tasks)} tasks missing closed_at")
    else:
        console.print("  [green]✓[/green] All completed/aborted tasks have closed_at")

    # Tasks marked UNDERWAY should have agent_name and claimed_at
    incomplete_underway = db.execute_query("""
        SELECT id, title, agent_name, claimed_at
        FROM tasks
        WHERE status = 'UNDERWAY'
        AND (agent_name IS NULL OR claimed_at IS NULL)
    """)

    if incomplete_underway:
        for task in incomplete_underway:
            if task.get("agent_name") is None:
                issue = f"Task {task['id']}: status is UNDERWAY but missing agent_name"
            else:
                issue = f"Task {task['id']}: status is UNDERWAY but missing claimed_at timestamp"
            issues_found.append(("task_state", "warning", issue, None))
            if verbose:
                console.print(f"  [yellow]⚠[/yellow] {issue}")
        console.print(f"  [yellow]⚠[/yellow]  Found {len(incomplete_underway)} incomplete UNDERWAY tasks")
    else:
        console.print("  [green]✓[/green] All UNDERWAY tasks have agent_name and claimed_at")

    console.print()

    # Check 3: Agent Session Consistency
    console.print("[bold]3. Checking agent session consistency...[/bold]")

    # Completed/failed/aborted sessions should have end_time
    unended_sessions = db.execute_query("""
        SELECT id, name, status
        FROM agents
        WHERE status IN ('completed', 'failed', 'aborted')
        AND end_time IS NULL
    """)

    if unended_sessions:
        for session in unended_sessions:
            issue = f"Agent #{session['id']} ({session['name']}): status is {session['status']} but missing end_time"
            now = datetime.now(timezone.utc).isoformat()
            session_id = session["id"]
            timestamp = now

            def fix_fn():
                db.execute_update(
                    "UPDATE agents SET end_time = :timestamp WHERE id = :id", {"timestamp": timestamp, "id": session_id}
                )

            issues_found.append(("agent_session", "fixable", issue, fix_fn))
            if verbose:
                console.print(f"  [yellow]⚠[/yellow] {issue}")
        console.print(f"  [yellow]⚠[/yellow]  Found {len(unended_sessions)} sessions missing end_time")
    else:
        console.print("  [green]✓[/green] All ended sessions have end_time")

    # In-progress/paused sessions should NOT have end_time
    wrongly_ended = db.execute_query("""
        SELECT id, name, status
        FROM agents
        WHERE status IN ('in-progress', 'paused')
        AND end_time IS NOT NULL
    """)

    if wrongly_ended:
        for session in wrongly_ended:
            issue = f"Agent #{session['id']} ({session['name']}): status is {session['status']} but has end_time"
            session_id = session["id"]

            def fix_fn():
                db.execute_update("UPDATE agents SET end_time = NULL WHERE id = :id", {"id": session_id})

            issues_found.append(("agent_session", "fixable", issue, fix_fn))
            if verbose:
                console.print(f"  [yellow]⚠[/yellow] {issue}")
        console.print(f"  [yellow]⚠[/yellow]  Found {len(wrongly_ended)} active sessions with end_time set")
    else:
        console.print("  [green]✓[/green] Active/paused sessions have no end_time")

    # Check session files exist
    all_sessions = db.execute_query("SELECT id, name, session_file FROM agents")
    missing_files = []

    for session in all_sessions:
        if session.get("session_file"):
            session_path = opencode_dir / session["session_file"]
            if not session_path.exists():
                issue = f"Agent #{session['id']} ({session['name']}): session file not found: {session['session_file']}"
                issues_found.append(("agent_session", "error", issue, None))
                missing_files.append(session)
                if verbose:
                    console.print(f"  [red]✗[/red] {issue}")

    if missing_files:
        console.print(f"  [red]✗[/red] Found {len(missing_files)} missing session files")
    else:
        console.print("  [green]✓[/green] All session files exist")

    console.print()

    # Check 4: Daemon Name Usage Counts
    console.print("[bold]4. Checking daemon name usage counts...[/bold]")

    wrong_counts = db.execute_query("""
        SELECT dn.name, dn.usage_count, COUNT(a.id) as actual_count
        FROM daemon_names dn
        LEFT JOIN agents a ON dn.name = a.base_name
        GROUP BY dn.name
        HAVING dn.usage_count != COUNT(a.id)
    """)

    if wrong_counts:
        for name_info in wrong_counts:
            issue = f"Name '{name_info['name']}': usage_count is {name_info['usage_count']} but actual count is {name_info['actual_count']}"
            name = name_info["name"]
            count = name_info["actual_count"]

            def fix_fn():
                db.execute_update(
                    "UPDATE daemon_names SET usage_count = :count WHERE name = :name", {"count": count, "name": name}
                )

            issues_found.append(("usage_count", "fixable", issue, fix_fn))
            if verbose:
                console.print(f"  [yellow]⚠[/yellow] {issue}")
        console.print(f"  [yellow]⚠[/yellow]  Found {len(wrong_counts)} incorrect usage counts")
    else:
        console.print("  [green]✓[/green] All usage counts are correct")

    # Check last_used_at matches most recent session
    wrong_dates = db.execute_query("""
        SELECT dn.name, dn.last_used_at, MAX(a.created_at) as actual_last_used
        FROM daemon_names dn
        LEFT JOIN agents a ON dn.name = a.base_name
        GROUP BY dn.name
        HAVING (dn.last_used_at IS NULL AND actual_last_used IS NOT NULL)
            OR (dn.last_used_at IS NOT NULL AND dn.last_used_at != actual_last_used)
    """)

    if wrong_dates:
        for name_info in wrong_dates:
            issue = f"Name '{name_info['name']}': last_used_at doesn't match actual usage"
            name = name_info["name"]
            date = name_info["actual_last_used"]

            def fix_fn():
                db.execute_update(
                    "UPDATE daemon_names SET last_used_at = :date WHERE name = :name", {"date": date, "name": name}
                )

            issues_found.append(("usage_count", "fixable", issue, fix_fn))
            if verbose:
                console.print(f"  [yellow]⚠[/yellow] {issue}")
        console.print(f"  [yellow]⚠[/yellow]  Found {len(wrong_dates)} incorrect last_used_at timestamps")
    else:
        console.print("  [green]✓[/green] All last_used_at timestamps are correct")

    console.print()

    # Check 5: Task Files Exist
    console.print("[bold]5. Checking task files...[/bold]")

    tasks_with_files = db.execute_query("SELECT id, title, file_path FROM tasks WHERE file_path IS NOT NULL")
    missing_task_files = []

    for task in tasks_with_files:
        if task.get("file_path"):
            # Handle file_path which may include .opencode prefix
            file_path_str = task["file_path"]
            if file_path_str.startswith(".opencode/"):
                task_path = Path(file_path_str)
            else:
                task_path = opencode_dir / file_path_str

            # Validate path to prevent directory traversal
            task_path = validate_path_within_project(task_path)

            if not task_path.exists():
                issue = f"Task {task['id']}: file not found: {task['file_path']}"
                issues_found.append(("task_file", "warning", issue, None))
                missing_task_files.append(task)
                if verbose:
                    console.print(f"  [yellow]⚠[/yellow] {issue}")

    if missing_task_files:
        console.print(f"  [yellow]⚠[/yellow]  Found {len(missing_task_files)} missing task files")
        console.print("  [cyan]💡 Run 's9 task sync' to regenerate missing files[/cyan]")
    else:
        console.print("  [green]✓[/green] All task files exist")

    console.print()
    console.print("═" * 70)

    # Summary
    fixable_issues = [i for i in issues_found if i[1] == "fixable" and i[3] is not None]
    warning_issues = [i for i in issues_found if i[1] == "warning"]
    error_issues = [i for i in issues_found if i[1] == "error"]

    if not issues_found:
        console.print("[bold green]✅ All checks passed! No issues found.[/bold green]")
        logger.info("Doctor: All health checks passed")
    else:
        console.print("[bold yellow]Summary:[/bold yellow]")
        console.print(f"  • {len(fixable_issues)} fixable issues")
        console.print(f"  • {len(warning_issues)} warnings")
        console.print(f"  • {len(error_issues)} errors requiring manual fix")
        console.print()

        if fixable_issues and not fix:
            console.print("[cyan]💡 Run with --fix to automatically repair fixable issues[/cyan]")

        if error_issues:
            console.print("[red]⚠  Some issues require manual intervention[/red]")

        logger.warning(
            f"Doctor: Found {len(issues_found)} issues ({len(fixable_issues)} fixable, {len(warning_issues)} warnings, {len(error_issues)} errors)"
        )

    # Apply fixes if requested
    if fix and fixable_issues:
        console.print()
        console.print("🔧 [bold cyan]Applying fixes...[/bold cyan]")
        console.print()

        for category, severity, issue, fix_func in fixable_issues:
            if fix_func is not None:
                try:
                    fix_func()
                    issues_fixed.append(issue)
                    console.print(f"[green]✓[/green] Fixed: {issue}")
                except Exception as e:
                    console.print(f"[red]✗[/red] Failed to fix: {issue}")
                    console.print(f"    Error: {e}")
                    logger.error(f"Doctor: Failed to fix issue: {issue} - {e}")

        console.print()
        console.print(f"[bold green]✅ Fixed {len(issues_fixed)} issues[/bold green]")
        logger.info(f"Doctor: Applied {len(issues_fixed)} fixes")

        if len(issues_fixed) < len(fixable_issues):
            failed_count = len(fixable_issues) - len(issues_fixed)
            console.print(f"[yellow]⚠  {failed_count} fixes failed[/yellow]")
            logger.warning(f"Doctor: {failed_count} fixes failed")

    console.print()
