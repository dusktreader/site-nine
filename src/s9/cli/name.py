"""Daemon name management commands"""

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table
from typerdrive import handle_errors

from s9.core.database import Database
from s9.core.paths import get_opencode_dir

app = typer.Typer(help="Manage daemon names")
console = Console()

# Valid roles matching config.py defaults
VALID_ROLES = [
    "administrator",
    "architect",
    "builder",
    "tester",
    "documentarian",
    "designer",
    "inspector",
    "operator",
]


def _get_db() -> Database:
    """Get database instance"""
    try:
        opencode_dir = get_opencode_dir()
    except FileNotFoundError:
        console.print("[red]Error: .opencode directory not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    db_path = opencode_dir / "data" / "project.db"
    if not db_path.exists():
        console.print("[red]Error: project.db not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    return Database(db_path)


def _validate_role(role: str) -> str:
    """Validate role name (case-insensitive), returns title case"""
    role_lower = role.lower()
    if role_lower not in VALID_ROLES:
        valid_roles_str = ", ".join(VALID_ROLES)
        console.print(f"[red]Invalid role: {role}. Valid values: {valid_roles_str}[/red]")
        raise typer.Exit(1)
    # Return title case to match database format
    return role.title()


@app.command()
@handle_errors("Failed to add daemon name")
def add(
    name: str = typer.Argument(..., help="Daemon name (lowercase)"),
    role: str = typer.Option(..., "--role", "-r", help="Primary role for this name"),
    mythology: str = typer.Option(..., "--mythology", "-m", help="Mythology origin (e.g., Greek, Roman, Norse)"),
    description: str = typer.Option(..., "--description", "-d", help="Brief description of the deity/daemon"),
) -> None:
    """Add a new daemon name"""
    name = name.lower()
    role = _validate_role(role)

    db = _get_db()

    try:
        db.execute_update(
            """
            INSERT INTO daemon_names (name, role, mythology, description)
            VALUES (:name, :role, :mythology, :description)
            """,
            {"name": name, "role": role, "mythology": mythology, "description": description},
        )
        console.print(f"[green]✓[/green] Added daemon name: {name} ({role}, {mythology})")
        logger.info(f"Added daemon name: {name} ({role}, {mythology})")
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            console.print(f"[red]Name '{name}' already exists[/red]")
            raise typer.Exit(1)
        raise


@app.command()
@handle_errors("Failed to list daemon names")
def list(
    role: str | None = typer.Option(None, "--role", "-r", help="Filter by role"),
    unused_only: bool = typer.Option(False, "--unused-only", help="Show only unused names"),
    by_usage: bool = typer.Option(False, "--by-usage", help="Sort by usage count"),
) -> None:
    """List daemon names"""
    db = _get_db()

    # Build query
    conditions = []
    params = {}

    if role:
        role = _validate_role(role)
        conditions.append("role = :role")
        params["role"] = role

    if unused_only:
        conditions.append("usage_count = 0")

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    order_by = "usage_count DESC, name ASC" if by_usage else "role ASC, name ASC"

    query = f"""
        SELECT name, role, mythology, description, usage_count, last_used_at
        FROM daemon_names
        WHERE {where_clause}
        ORDER BY {order_by}
    """

    names = db.execute_query(query, params)

    if not names:
        console.print("[yellow]No daemon names found[/yellow]")
        return

    # Display table
    table = Table(title="Daemon Names")
    table.add_column("Name", style="cyan")
    table.add_column("Role", style="green")
    table.add_column("Mythology", style="magenta")
    table.add_column("Description", style="white")
    table.add_column("Usage", style="yellow")
    table.add_column("Last Used", style="dim")

    for name_row in names:
        last_used = name_row["last_used_at"][:10] if name_row["last_used_at"] else "Never"
        desc = name_row["description"]
        desc_display = desc[:40] + "..." if len(desc) > 40 else desc

        table.add_row(
            name_row["name"],
            name_row["role"],
            name_row["mythology"],
            desc_display,
            str(name_row["usage_count"]),
            last_used,
        )

    console.print(table)
    console.print(f"\nTotal: {len(names)} name(s)")
    logger.debug(f"Listed {len(names)} daemon names")


@app.command()
@handle_errors("Failed to suggest daemon names")
def suggest(
    role: str = typer.Argument(..., help="Role to suggest name for"),
    count: int = typer.Option(3, "--count", "-c", help="Number of suggestions"),
) -> None:
    """Suggest unused daemon names for a role"""
    role = _validate_role(role)

    db = _get_db()

    # Find unused or least-used names for this role
    suggestions = db.execute_query(
        """
        SELECT name, mythology, description, usage_count
        FROM daemon_names
        WHERE role = :role
        ORDER BY usage_count ASC, name ASC
        LIMIT :count
        """,
        {"role": role, "count": count},
    )

    if not suggestions:
        console.print(f"[yellow]No names found for role: {role}[/yellow]")
        console.print("[dim]Tip: Add names with 's9 name add'[/dim]")
        return

    console.print(f"\n[bold]Suggested names for {role.title()}:[/bold]\n")
    for idx, name_row in enumerate(suggestions, 1):
        usage_str = "unused" if name_row["usage_count"] == 0 else f"used {name_row['usage_count']}x"
        console.print(f"{idx}. [cyan]{name_row['name']}[/cyan] ({name_row['mythology']}) - {usage_str}")
        console.print(f"   {name_row['description']}\n")

    logger.debug(f"Suggested {len(suggestions)} names for role {role}")


@app.command()
@handle_errors("Failed to show name usage")
def usage(
    name: str = typer.Argument(..., help="Daemon name to check"),
) -> None:
    """Show usage history for a daemon name"""
    name = name.lower()

    db = _get_db()

    # Get name info
    name_results = db.execute_query(
        "SELECT * FROM daemon_names WHERE name = :name",
        {"name": name},
    )

    if not name_results:
        console.print(f"[red]Name '{name}' not found[/red]")
        raise typer.Exit(1)

    name_row = name_results[0]

    # Get agent sessions using this name (base_name column stores the daemon name)
    sessions = db.execute_query(
        """
        SELECT id, name, role, status, session_date, start_time, end_time
        FROM agents
        WHERE base_name = :name
        ORDER BY session_date DESC, start_time DESC
        """,
        {"name": name},
    )

    # Display name info
    console.print(f"\n[bold]Name: {name_row['name']}[/bold]")
    console.print(f"Role:        {name_row['role']}")
    console.print(f"Mythology:   {name_row['mythology']}")
    console.print(f"Description: {name_row['description']}")
    console.print(f"Usage Count: {name_row['usage_count']}")
    if name_row["last_used_at"]:
        console.print(f"Last Used:   {name_row['last_used_at'][:10]}")

    # Display sessions
    if sessions:
        console.print(f"\n[bold]Agent Sessions ({len(sessions)}):[/bold]\n")
        table = Table()
        table.add_column("Name", style="cyan")
        table.add_column("Role", style="green")
        table.add_column("Date", style="white")
        table.add_column("Status", style="yellow")

        for session in sessions:
            table.add_row(
                session["name"],
                session["role"] or "?",
                session["session_date"] or "?",
                session["status"],
            )

        console.print(table)
    else:
        console.print("\n[yellow]No sessions found for this name[/yellow]")

    logger.debug(f"Displayed usage for daemon name: {name}")
