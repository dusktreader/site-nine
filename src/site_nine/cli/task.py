"""Task management commands"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table
from typerdrive import handle_errors

from site_nine.core.database import Database
from site_nine.core.paths import get_opencode_dir, validate_path_within_project
from site_nine.tasks import TaskManager

app = typer.Typer(help="Manage tasks")
console = Console()


class Priority(str, Enum):
    """Task priority levels"""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

    @classmethod
    def from_string(cls, value: str) -> "Priority":
        """Convert string to Priority enum (case-insensitive)"""
        value_upper = value.upper()
        for member in cls:
            if member.value.upper() == value_upper:
                return member
        raise ValueError(f"Invalid priority: {value}. Valid values: {', '.join(m.value for m in cls)}")


class Role(str, Enum):
    """Agent roles"""

    ADMINISTRATOR = "Administrator"
    ARCHITECT = "Architect"
    BUILDER = "Builder"
    TESTER = "Tester"
    DOCUMENTARIAN = "Documentarian"
    DESIGNER = "Designer"
    INSPECTOR = "Inspector"
    OPERATOR = "Operator"
    HISTORIAN = "Historian"

    @classmethod
    def from_string(cls, value: str) -> "Role":
        """Convert string to Role enum (case-insensitive)"""
        _value_title = value.title()
        for member in cls:
            if member.value.lower() == value.lower():
                return member
        raise ValueError(f"Invalid role: {value}. Valid values: {', '.join(m.value for m in cls)}")


class Category(str, Enum):
    """Task categories"""

    FEATURE = "feature"
    BUG_FIX = "bug-fix"
    REFACTOR = "refactor"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    INFRASTRUCTURE = "infrastructure"
    SECURITY = "security"
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"
    MAINTENANCE = "maintenance"

    @classmethod
    def from_string(cls, value: str) -> "Category":
        """Convert string to Category enum (case-insensitive)"""
        value_lower = value.lower()
        for member in cls:
            if member.value.lower() == value_lower:
                return member
        raise ValueError(f"Invalid category: {value}. Valid values: {', '.join(m.value for m in cls)}")


def _get_manager() -> TaskManager:
    """Get task manager"""
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
    return TaskManager(db)


@app.command()
@handle_errors("Failed to list tasks")
def list(
    role: str | None = typer.Option(None, "--role", "-r", help="Filter by role"),
    status: str | None = typer.Option(None, "--status", "-s", help="Filter by status"),
    mission: int | None = typer.Option(None, "--mission", "-m", help="Filter by mission ID"),
) -> None:
    """List tasks"""
    manager = _get_manager()

    # Normalize role and status for case-insensitive filtering
    if role:
        role = role.title()
    if status:
        status = status.upper()

    tasks = manager.list_tasks(status=status, role=role, mission_id=mission)

    if not tasks:
        console.print("[yellow]No tasks found.[/yellow]")
        return

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

    console.print(table)
    logger.debug(f"Listed {len(tasks)} tasks")


@app.command()
@handle_errors("Failed to show task")
def show(
    task_id: str = typer.Argument(..., help="Task ID"),
) -> None:
    """Show task details"""
    manager = _get_manager()
    task = manager.get_task(task_id)

    if not task:
        console.print(f"[red]Error: Task '{task_id}' not found.[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Task {task.id}[/bold]")
    console.print(f"  Title: {task.title}")
    console.print(f"  Status: {task.status}")
    console.print(f"  Priority: {task.priority}")
    console.print(f"  Role: {task.role}")
    if task.category:
        console.print(f"  Category: {task.category}")
    if task.current_mission_id:
        console.print(f"  Mission: {task.current_mission_id}")
    if task.claimed_at:
        console.print(f"  Claimed: {task.claimed_at}")
    if task.closed_at:
        console.print(f"  Closed: {task.closed_at}")
    if task.description:
        console.print(f"  Description: {task.description}")
    if task.notes:
        console.print(f"  Notes: {task.notes}")
    console.print(f"  File: {task.file_path}")
    logger.debug(f"Displayed details for task {task_id}")


@app.command()
@handle_errors("Failed to claim task")
def claim(
    task_id: str = typer.Argument(..., help="Task ID"),
    mission: int | None = typer.Option(None, "--mission", "-m", help="Mission ID (current mission if not specified)"),
) -> None:
    """Claim a task"""
    manager = _get_manager()

    # Verify task exists
    task = manager.get_task(task_id)
    if not task:
        console.print(f"[red]Error: Task '{task_id}' not found.[/red]")
        raise typer.Exit(1)

    # Check if task is blocked by a pending review
    if task.blocks_on_review_id:
        from site_nine.reviews import ReviewManager

        opencode_dir = get_opencode_dir()
        db_path = opencode_dir / "data" / "project.db"
        db = Database(db_path)
        review_manager = ReviewManager(db)

        blocking_review = review_manager.check_task_blocked(task_id)
        if blocking_review:
            console.print(f"[red]✗ Task {task_id} is blocked by pending review #{blocking_review.id}[/red]")
            console.print(f"  Review: {blocking_review.title}")
            console.print(f"  Type: {blocking_review.type}")
            console.print()
            console.print(f"This task cannot be claimed until the review is approved.")
            console.print(f"Use [cyan]s9 review show {blocking_review.id}[/cyan] for details")
            console.print(f"Use [cyan]s9 review approve {blocking_review.id}[/cyan] to unblock this task")
            raise typer.Exit(1)

    manager.claim_task(task_id, mission)
    mission_text = f" for mission {mission}" if mission else ""
    console.print(f"[green]✓[/green] Task {task_id} claimed{mission_text}")
    logger.info(f"Task {task_id} claimed{mission_text}")


@app.command()
@handle_errors("Failed to update task")
def update(
    task_id: str = typer.Argument(..., help="Task ID"),
    status: str = typer.Option(..., "--status", "-s", help="New status"),
    notes: str | None = typer.Option(None, "--notes", "-n", help="Progress notes"),
) -> None:
    """Update task status"""
    manager = _get_manager()

    # Verify task exists
    task = manager.get_task(task_id)
    if not task:
        console.print(f"[red]Error: Task '{task_id}' not found.[/red]")
        raise typer.Exit(1)

    # Normalize status to uppercase for case-insensitive handling
    status_upper = status.upper()

    manager.update_status(task_id, status_upper, notes)
    console.print(f"[green]✓[/green] Task {task_id} updated to {status_upper}")
    logger.info(f"Task {task_id} updated to {status_upper}")


@app.command()
@handle_errors("Failed to close task")
def close(
    task_id: str = typer.Argument(..., help="Task ID"),
    status: str = typer.Option("COMPLETE", "--status", "-s", help="Completion status"),
    notes: str | None = typer.Option(None, "--notes", "-n", help="Closing notes"),
) -> None:
    """Close a task"""
    manager = _get_manager()

    # Verify task exists
    task = manager.get_task(task_id)
    if not task:
        console.print(f"[red]Error: Task '{task_id}' not found.[/red]")
        raise typer.Exit(1)

    # Normalize status to uppercase for case-insensitive comparison
    status_upper = status.upper()
    if status_upper not in ("COMPLETE", "ABORTED"):
        console.print(f"[red]Error: Invalid close status '{status}'. Use COMPLETE or ABORTED.[/red]")
        raise typer.Exit(1)

    manager.update_status(task_id, status_upper, notes)
    console.print(f"[green]✓[/green] Task {task_id} closed with status: {status_upper}")
    logger.info(f"Task {task_id} closed with status: {status_upper}")


@app.command()
@handle_errors("Failed to create task")
def create(
    title: str = typer.Option(
        ...,
        "--title",
        "-t",
        help="Brief task description (e.g., 'Add rate limiting to API endpoints')",
    ),
    role: str = typer.Option(
        ...,
        "--role",
        "-r",
        help="Agent role responsible for this task",
    ),
    priority: str = typer.Option(
        "MEDIUM",
        "--priority",
        "-p",
        help="Task priority (affects when it should be worked on)",
    ),
    category: str | None = typer.Option(
        None,
        "--category",
        "-c",
        help="Task category (what type of work is this?)",
    ),
    description: str | None = typer.Option(
        None,
        "--description",
        "-d",
        help="Detailed description of what needs to be done and why",
    ),
) -> None:
    """Create a new task (task ID auto-generated based on role and priority)"""
    manager = _get_manager()

    # Convert strings to enums (case-insensitive)
    try:
        role_enum = Role.from_string(role)
        priority_enum = Priority.from_string(priority)
        category_enum = Category.from_string(category) if category else None
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    # Auto-generate task ID based on role and priority
    task_id = manager.generate_task_id(role_enum.value, priority_enum.value)

    try:
        manager.create_task(
            task_id=task_id,
            title=title,
            role=role_enum.value,
            priority=priority_enum.value,
            category=category_enum.value if category_enum else None,
            description=description,
        )
        console.print(f"[green]✓[/green] Created task [cyan]{task_id}[/cyan]: {title}")
        logger.info(f"Created task {task_id}")
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            console.print(f"[red]Task '{task_id}' already exists[/red]")
            raise typer.Exit(1)
        raise


@app.command()
@handle_errors("Failed to list mission tasks")
def mine(
    mission: int = typer.Option(..., "--mission", "-m", help="Mission ID"),
) -> None:
    """Show tasks claimed by a mission"""
    manager = _get_manager()
    tasks = manager.list_tasks(mission_id=mission)

    if not tasks:
        console.print(f"[yellow]No tasks found for mission {mission}[/yellow]")
        return

    table = Table(title=f"Tasks for Mission {mission}")
    table.add_column("ID", style="cyan", justify="left")
    table.add_column("Title", style="magenta")
    table.add_column("Status", style="yellow")
    table.add_column("Priority", style="red")
    table.add_column("Role", style="green")

    for task in tasks:
        # Truncate long titles
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

    console.print(table)
    console.print(f"\nTotal: {len(tasks)} task(s)")
    logger.debug(f"Listed {len(tasks)} tasks for mission {mission}")


@app.command()
@handle_errors("Failed to generate task report")
def report(
    active_only: bool = typer.Option(
        False, "--active-only", help="Show only active tasks (excludes COMPLETE, ABORTED)"
    ),
    role: str | None = typer.Option(None, "--role", "-r", help="Filter by role"),
) -> None:
    """Generate task summary report"""
    try:
        opencode_dir = get_opencode_dir()
    except FileNotFoundError:
        console.print("[red]Error: .opencode directory not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    db_path = opencode_dir / "data" / "project.db"
    if not db_path.exists():
        console.print("[red]Error: project.db not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    from site_nine.core.database import Database

    db = Database(db_path)

    # Build query conditions
    conditions = []
    params = {}

    if active_only:
        conditions.append("status NOT IN ('COMPLETE', 'ABORTED')")

    if role:
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
        role_lower = role.lower()
        if role_lower not in valid_roles:
            console.print(f"[red]Invalid role: {role}. Valid values: {', '.join(valid_roles)}[/red]")
            raise typer.Exit(1)
        conditions.append("role = :role")
        params["role"] = role.title()

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
        SELECT id, title, status, priority, role, category, current_mission_id,
               claimed_at, closed_at, actual_hours, objective, created_at
        FROM tasks
        WHERE {where_clause}
        ORDER BY
            CASE priority
                WHEN 'CRITICAL' THEN 1
                WHEN 'HIGH' THEN 2
                WHEN 'MEDIUM' THEN 3
                WHEN 'LOW' THEN 4
            END,
            created_at ASC
    """

    tasks = db.execute_query(query, params)

    if not tasks:
        console.print("[yellow]No tasks found matching criteria[/yellow]")
        return

    # Display table format
    table = Table(title="Task Report")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Status", style="yellow")
    table.add_column("Priority", style="magenta")
    table.add_column("Role", style="green")
    table.add_column("Mission", style="blue")

    for task in tasks:
        # Truncate long titles
        title = task["title"]
        if len(title) > 40:
            title = title[:37] + "..."

        mission = str(task["current_mission_id"]) if task["current_mission_id"] else "-"

        table.add_row(
            task["id"],
            title,
            task["status"],
            task["priority"],
            task["role"],
            mission,
        )

    console.print(table)
    console.print(f"\nTotal: {len(tasks)} task(s)")
    logger.debug(f"Generated report for {len(tasks)} tasks")


@app.command()
@handle_errors("Failed to search tasks")
def search(
    keyword: str = typer.Argument(..., help="Keyword to search for"),
    active_only: bool = typer.Option(False, "--active-only", help="Show only active tasks"),
    role: str | None = typer.Option(None, "--role", "-r", help="Filter by role"),
) -> None:
    """Search tasks by keyword"""
    try:
        opencode_dir = get_opencode_dir()
    except FileNotFoundError:
        console.print("[red]Error: .opencode directory not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    db_path = opencode_dir / "data" / "project.db"
    if not db_path.exists():
        console.print("[red]Error: project.db not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    from site_nine.core.database import Database

    db = Database(db_path)

    # Build query conditions
    search_term = f"%{keyword}%"
    conditions = ["(title LIKE :search OR description LIKE :search OR notes LIKE :search)"]
    params = {"search": search_term}

    if active_only:
        conditions.append("status NOT IN ('COMPLETE', 'ABORTED')")

    if role:
        # Validate role if provided
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
        role_lower = role.lower()
        if role_lower not in valid_roles:
            console.print(f"[red]Invalid role: {role}. Valid values: {', '.join(valid_roles)}[/red]")
            raise typer.Exit(1)
        conditions.append("role = :role")
        params["role"] = role.title()

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT id, title, status, priority, role, current_mission_id, created_at
        FROM tasks
        WHERE {where_clause}
        ORDER BY
            CASE priority
                WHEN 'CRITICAL' THEN 1
                WHEN 'HIGH' THEN 2
                WHEN 'MEDIUM' THEN 3
                WHEN 'LOW' THEN 4
            END,
            created_at DESC
    """

    tasks = db.execute_query(query, params)

    if not tasks:
        console.print(f"[yellow]No tasks found matching '{keyword}'[/yellow]")
        return

    table = Table(title=f"Search Results: '{keyword}'")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Status", style="yellow")
    table.add_column("Priority", style="magenta")
    table.add_column("Role", style="green")

    for task in tasks:
        # Truncate long titles
        title = task["title"]
        if len(title) > 50:
            title = title[:47] + "..."

        table.add_row(
            task["id"],
            title,
            task["status"],
            task["priority"],
            task["role"],
        )

    console.print(table)
    console.print(f"\nTotal: {len(tasks)} task(s)")
    logger.debug(f"Search found {len(tasks)} tasks matching '{keyword}'")


@app.command()
@handle_errors("Failed to suggest next tasks")
def next(
    role: str | None = typer.Option(None, "--role", "-r", help="Filter by role"),
    count: int = typer.Option(3, "--count", "-c", help="Number of suggestions"),
) -> None:
    """Suggest next tasks to work on"""
    try:
        opencode_dir = get_opencode_dir()
    except FileNotFoundError:
        console.print("[red]Error: .opencode directory not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    db_path = opencode_dir / "data" / "project.db"
    if not db_path.exists():
        console.print("[red]Error: project.db not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    from site_nine.core.database import Database

    db = Database(db_path)

    # Validate role if provided
    role_param = None
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
        role_lower = role.lower()
        if role_lower not in valid_roles:
            console.print(f"[red]Invalid role: {role}. Valid values: {', '.join(valid_roles)}[/red]")
            raise typer.Exit(1)
        role_param = role.title()

    # Build query for TODO tasks with dependency check
    conditions = ["status = 'TODO'"]
    params = {"count": count}

    if role_param:
        conditions.append("role = :role")
        params["role"] = role_param

    where_clause = " AND ".join(conditions)

    # Get TODO tasks (simplified - not checking dependencies for now)
    query = f"""
        SELECT id, title, priority, role, objective, created_at
        FROM tasks
        WHERE {where_clause}
        ORDER BY
            CASE priority
                WHEN 'CRITICAL' THEN 1
                WHEN 'HIGH' THEN 2
                WHEN 'MEDIUM' THEN 3
                WHEN 'LOW' THEN 4
            END,
            created_at ASC
        LIMIT :count
    """

    todo_tasks = db.execute_query(query, params)

    # Get blocked/paused tasks
    blocked_conditions = ["status IN ('BLOCKED', 'PAUSED')"]
    blocked_params = {}

    if role_param:
        blocked_conditions.append("role = :role")
        blocked_params["role"] = role_param

    blocked_query = f"""
        SELECT id, title, priority, role, status, objective
        FROM tasks
        WHERE {" AND ".join(blocked_conditions)}
        ORDER BY
            CASE priority
                WHEN 'CRITICAL' THEN 1
                WHEN 'HIGH' THEN 2
                WHEN 'MEDIUM' THEN 3
                WHEN 'LOW' THEN 4
            END
        LIMIT 2
    """

    blocked_tasks = db.execute_query(blocked_query, blocked_params)

    if not todo_tasks and not blocked_tasks:
        if role:
            console.print(f"[yellow]No TODO or BLOCKED/PAUSED tasks for role '{role}'[/yellow]")
        else:
            console.print("[yellow]No TODO or BLOCKED/PAUSED tasks found[/yellow]")
        return

    # Show TODO tasks
    if todo_tasks:
        console.print("[bold green]📋 Suggested Tasks to Start:[/bold green]\n")

        for i, task in enumerate(todo_tasks, 1):
            priority_colors = {"CRITICAL": "red", "HIGH": "yellow", "MEDIUM": "blue", "LOW": "green"}
            priority_color = priority_colors.get(task["priority"], "white")

            console.print(f"[bold]{i}. [{priority_color}]{task['id']}[/{priority_color}][/bold] - {task['title']}")
            console.print(
                f"   Priority: [{priority_color}]{task['priority']}[/{priority_color}] | Role: [cyan]{task['role']}[/cyan]"
            )

            # Show truncated objective
            objective = task["objective"] if task["objective"] else "No objective specified"
            if len(objective) > 80:
                objective = objective[:77] + "..."
            console.print(f"   {objective}")
            console.print()

    # Show blocked tasks
    if blocked_tasks:
        console.print("[bold yellow]⚠️  Tasks Needing Attention:[/bold yellow]\n")

        for task in blocked_tasks:
            status_color = "red" if task["status"] == "BLOCKED" else "yellow"
            console.print(f"[bold][{status_color}]{task['id']}[/{status_color}][/bold] - {task['title']}")
            console.print(
                f"   Status: [{status_color}]{task['status']}[/{status_color}] | Priority: {task['priority']} | Role: [cyan]{task['role']}[/cyan]"
            )
            console.print()

    # Show command hints
    console.print("[dim]💡 To claim a task: [bold]s9 task claim <TASK_ID> --agent <name>[/bold][/dim]")
    console.print("[dim]💡 To see details: [bold]s9 task show <TASK_ID>[/bold][/dim]")
    logger.debug(f"Suggested {len(todo_tasks)} TODO tasks and {len(blocked_tasks)} blocked tasks")


@app.command(name="add-dependency")
@handle_errors("Failed to add task dependency")
def add_dependency(
    task_id: str = typer.Argument(..., help="Task ID"),
    depends_on: str = typer.Argument(..., help="Task ID this depends on"),
) -> None:
    """Add a task dependency"""
    try:
        opencode_dir = get_opencode_dir()
    except FileNotFoundError:
        console.print("[red]Error: .opencode directory not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    db_path = opencode_dir / "data" / "project.db"
    if not db_path.exists():
        console.print("[red]Error: project.db not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    db_path = opencode_dir / "data" / "project.db"
    if not db_path.exists():
        console.print("[red]Error: project.db not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    from site_nine.core.database import Database

    db = Database(db_path)

    # Validate both tasks exist
    for tid in [task_id, depends_on]:
        task = db.execute_query("SELECT id FROM tasks WHERE id = :id", {"id": tid})
        if not task:
            console.print(f"[red]Task {tid} does not exist[/red]")
            raise typer.Exit(1)

    try:
        db.execute_update(
            """
            INSERT INTO task_dependencies (task_id, depends_on_task_id)
            VALUES (:task_id, :depends_on)
            """,
            {"task_id": task_id, "depends_on": depends_on},
        )
        console.print(f"[green]✓[/green] Added dependency: {task_id} depends on {depends_on}")
        logger.info(f"Added dependency: {task_id} -> {depends_on}")
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            console.print("[yellow]Dependency already exists[/yellow]")
        else:
            raise


@app.command()
@handle_errors("Failed to sync task files")
def sync(
    task_id: str | None = typer.Option(None, "--task", "-t", help="Sync specific task (syncs all if not provided)"),
) -> None:
    """Synchronize task markdown files with database"""
    manager = _get_manager()
    try:
        opencode_dir = get_opencode_dir()
    except FileNotFoundError:
        console.print("[red]Error: .opencode directory not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    if task_id:
        # Sync specific task
        task = manager.get_task(task_id)
        if not task:
            console.print(f"[red]Error: Task {task_id} not found[/red]")
            raise typer.Exit(1)

        _sync_task_file(task, opencode_dir)
        console.print(f"[green]✓[/green] Synced task {task_id}")
        logger.info(f"Synced task file {task_id}")
    else:
        # Sync all tasks
        tasks = manager.list_tasks()
        for task in tasks:
            _sync_task_file(task, opencode_dir)

        console.print(f"[green]✓[/green] Synced {len(tasks)} task(s)")
        logger.info(f"Synced {len(tasks)} task files")


def _sync_task_file(task, opencode_dir: Path) -> None:
    """Helper to sync a single task file"""

    # Handle file_path which may include .opencode prefix
    if task.file_path.startswith(".opencode/"):
        file_path = Path(task.file_path)
    else:
        file_path = opencode_dir / task.file_path

    # Validate path to prevent directory traversal
    file_path = validate_path_within_project(file_path)

    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing body if file exists
    body = ""
    if file_path.exists():
        content = file_path.read_text()
        lines = content.split("\n")
        body_start_idx = 0
        for i, line in enumerate(lines):
            if line.startswith("## "):
                body_start_idx = i
                break
        if body_start_idx > 0:
            body = "\n".join(lines[body_start_idx:])

    # Build header
    category = task.category or ""
    mission_id = str(task.current_mission_id) if task.current_mission_id else ""
    claimed_at = task.claimed_at or ""
    actual_hours = f"~{task.actual_hours} hours" if task.actual_hours else ""
    closed_at = task.closed_at or ""
    paused_at = task.paused_at or ""

    header = f"""# Task {task.id}: {task.title}

**Status:** {task.status}
**Priority:** {task.priority}
**Role:** {task.role}
**Category:** {category}
**Mission:** {mission_id}
**Claimed:** {claimed_at}
**Actual Time:** {actual_hours}
**Closed:** {closed_at}
**Paused:** {paused_at}"""

    # Create default body if none exists
    if not body:
        notes_text = task.notes or "[Progress notes, questions, blockers]"
        description_text = task.description or "[Describe what this task aims to achieve]"
        body = f"""

## Objective

{description_text}

## Problem Statement

[Describe the problem or need - explain current state, why it's problematic, impact]

## Implementation Steps

[Chronological log of work done - update as you go, document decisions]

## Files Changed

### Created
- [file path] - [description]

### Modified
- [file path] - [description]

## Testing Performed

[Document test commands, results, verification]

## Notes

{notes_text}"""

    # Write combined content
    file_path.write_text(header + "\n" + body)
