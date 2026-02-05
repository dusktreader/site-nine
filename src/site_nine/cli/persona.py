"""Persona management commands"""

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table
from typerdrive import handle_errors

from site_nine.cli.json_utils import format_json_response, output_json
from site_nine.core.database import Database
from site_nine.core.paths import get_opencode_dir

app = typer.Typer(help="Manage personas")
console = Console()

# Valid roles matching config.py defaults
VALID_ROLES = [
    "administrator",
    "architect",
    "engineer",
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
@handle_errors("Failed to add persona")
def add(
    name: str = typer.Argument(..., help="Persona name (lowercase)"),
    role: str = typer.Option(..., "--role", "-r", help="Primary role for this persona"),
    mythology: str = typer.Option(..., "--mythology", "-m", help="Mythology origin (e.g., Greek, Roman, Norse)"),
    description: str = typer.Option(..., "--description", "-d", help="Brief description of the deity/figure"),
) -> None:
    """Add a new persona (typically used by: humans)"""
    name = name.lower()
    role = _validate_role(role)

    db = _get_db()

    try:
        db.execute_update(
            """
            INSERT INTO personas (name, role, mythology, description)
            VALUES (:name, :role, :mythology, :description)
            """,
            {"name": name, "role": role, "mythology": mythology, "description": description},
        )
        console.print(f"[green]✓[/green] Added persona: {name} ({role}, {mythology})")
        logger.info(f"Added persona: {name} ({role}, {mythology})")
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            console.print(f"[red]Persona '{name}' already exists[/red]")
            raise typer.Exit(1)
        raise


@app.command()
@handle_errors("Failed to list personas")
def list(
    role: str | None = typer.Option(None, "--role", "-r", help="Filter by role"),
    unused_only: bool = typer.Option(False, "--unused-only", help="Show only unused personas"),
    by_usage: bool = typer.Option(False, "--by-usage", help="Sort by mission count"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format"),
) -> None:
    """List personas (typically used by: both)"""
    db = _get_db()

    # Build query
    conditions = []
    params = {}

    if role:
        role = _validate_role(role)
        conditions.append("role = :role")
        params["role"] = role

    if unused_only:
        conditions.append("mission_count = 0")

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    order_by = "mission_count DESC, name ASC" if by_usage else "role ASC, name ASC"

    query = f"""
        SELECT name, role, mythology, description, mission_count, last_mission_at
        FROM personas
        WHERE {where_clause}
        ORDER BY {order_by}
    """

    personas = db.execute_query(query, params)

    if not personas:
        if json_output:
            output_json(format_json_response([]))
            logger.debug("Listed 0 personas (JSON)")
            return
        console.print("[yellow]No personas found[/yellow]")
        return

    if json_output:
        # Build JSON data
        data = []
        for persona in personas:
            persona_dict = {
                "name": persona["name"],
                "role": persona["role"],
                "mythology": persona["mythology"],
                "description": persona["description"],
                "mission_count": persona["mission_count"],
                "last_mission_at": persona["last_mission_at"],
            }
            data.append(persona_dict)

        output_json(format_json_response(data))
        logger.debug(f"Listed {len(personas)} personas (JSON)")
        return

    # Display table
    table = Table(title="Personas")
    table.add_column("Name", style="cyan")
    table.add_column("Role", style="green")
    table.add_column("Mythology", style="magenta")
    table.add_column("Description", style="white")
    table.add_column("Missions", style="yellow")
    table.add_column("Last Mission", style="dim")

    for persona in personas:
        last_mission = persona["last_mission_at"][:10] if persona["last_mission_at"] else "Never"
        desc = persona["description"]
        desc_display = desc[:40] + "..." if len(desc) > 40 else desc

        table.add_row(
            persona["name"],
            persona["role"],
            persona["mythology"],
            desc_display,
            str(persona["mission_count"]),
            last_mission,
        )

    console.print(table)
    console.print(f"\nTotal: {len(personas)} persona(s)")
    logger.debug(f"Listed {len(personas)} personas")


@app.command()
@handle_errors("Failed to suggest personas")
def suggest(
    role: str = typer.Argument(..., help="Role to suggest persona for"),
    count: int = typer.Option(3, "--count", "-c", help="Number of suggestions"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format"),
) -> None:
    """Suggest unused personas for a role (typically used by: agents)"""
    role = _validate_role(role)

    db = _get_db()

    # Find unused or least-used personas for this role
    suggestions = db.execute_query(
        """
        SELECT name, mythology, description, mission_count
        FROM personas
        WHERE role = :role
        ORDER BY mission_count ASC, name ASC
        LIMIT :count
        """,
        {"role": role, "count": count},
    )

    if not suggestions:
        if json_output:
            output_json(format_json_response([]))
            logger.debug("Suggested 0 personas (JSON)")
            return
        console.print(f"[yellow]No personas found for role: {role}[/yellow]")
        console.print("[dim]Tip: Add personas with 's9 persona add'[/dim]")
        return

    if json_output:
        # Build JSON data
        data = []
        for persona in suggestions:
            persona_dict = {
                "name": persona["name"],
                "mythology": persona["mythology"],
                "description": persona["description"],
                "mission_count": persona["mission_count"],
            }
            data.append(persona_dict)

        output_json(format_json_response(data))
        logger.debug(f"Suggested {len(suggestions)} personas (JSON)")
        return

    console.print(f"\n[bold]Suggested personas for {role.title()}:[/bold]\n")
    for idx, persona in enumerate(suggestions, 1):
        usage_str = "unused" if persona["mission_count"] == 0 else f"{persona['mission_count']} mission(s)"
        console.print(f"{idx}. [cyan]{persona['name']}[/cyan] ({persona['mythology']}) - {usage_str}")
        console.print(f"   {persona['description']}\n")

    logger.debug(f"Suggested {len(suggestions)} personas for role {role}")


@app.command()
@handle_errors("Failed to show persona usage")
def usage(
    name: str = typer.Argument(..., help="Persona name to check"),
) -> None:
    """Show usage history for a persona (typically used by: both)"""
    name = name.lower()

    db = _get_db()

    # Get persona info
    persona_results = db.execute_query(
        "SELECT * FROM personas WHERE name = :name",
        {"name": name},
    )

    if not persona_results:
        console.print(f"[red]Persona '{name}' not found[/red]")
        raise typer.Exit(1)

    persona = persona_results[0]

    # Get missions for this persona
    missions = db.execute_query(
        """
        SELECT id, persona_name, role, codename, start_date, start_time, end_time
        FROM missions
        WHERE persona_name = :name
        ORDER BY start_date DESC, start_time DESC
        """,
        {"name": name},
    )

    # Display persona info
    console.print(f"\n[bold]Persona: {persona['name']}[/bold]")
    console.print(f"Role:          {persona['role']}")
    console.print(f"Mythology:     {persona['mythology']}")
    console.print(f"Description:   {persona['description']}")
    console.print(f"Mission Count: {persona['mission_count']}")
    if persona["last_mission_at"]:
        console.print(f"Last Mission:  {persona['last_mission_at'][:10]}")

    # Display missions
    if missions:
        console.print(f"\n[bold]Missions ({len(missions)}):[/bold]\n")
        table = Table()
        table.add_column("ID", style="cyan")
        table.add_column("Codename", style="yellow")
        table.add_column("Role", style="green")
        table.add_column("Date", style="white")
        table.add_column("Status", style="magenta")

        for mission in missions:
            status = "Active" if mission["end_time"] is None else "Complete"
            table.add_row(
                str(mission["id"]),
                mission["codename"],
                mission["role"] or "?",
                mission["start_date"] or "?",
                status,
            )

        console.print(table)
    else:
        console.print("\n[yellow]No missions found for this persona[/yellow]")

    logger.debug(f"Displayed usage for persona: {name}")


@app.command()
@handle_errors("Failed to show persona")
def show(
    name: str = typer.Argument(..., help="Persona name to display"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output in JSON format"),
) -> None:
    """Show persona details including whimsical bio (typically used by: both)"""
    name = name.lower()

    db = _get_db()

    # Get persona info
    persona_results = db.execute_query(
        "SELECT * FROM personas WHERE name = :name",
        {"name": name},
    )

    if not persona_results:
        console.print(f"[red]Persona '{name}' not found[/red]")
        raise typer.Exit(1)

    persona = persona_results[0]

    if json_output:
        # Build JSON data
        persona_dict = {
            "name": persona["name"],
            "role": persona["role"],
            "mythology": persona["mythology"],
            "description": persona["description"],
            "whimsical_bio": persona.get("whimsical_bio"),
            "mission_count": persona.get("mission_count"),
            "last_mission_at": persona.get("last_mission_at"),
        }

        output_json(format_json_response(persona_dict))
        logger.debug(f"Displayed persona {name} (JSON)")
        return

    # Display basic info
    console.print(f"\n[bold cyan]{persona['name'].title()}[/bold cyan]")
    console.print(f"[bold]Role:[/bold] {persona['role']}")
    console.print(f"[bold]Mythology:[/bold] {persona['mythology']}")
    console.print(f"[bold]Description:[/bold] {persona['description']}")

    # Display whimsical bio if available
    if persona.get("whimsical_bio"):
        console.print(f"\n📖 [bold]About me...[/bold]\n")
        console.print(persona["whimsical_bio"])
    else:
        console.print(f"\n[dim]No whimsical bio available yet. Generate one during session-start![/dim]")

    logger.debug(f"Displayed persona: {name}")


@app.command()
@handle_errors("Failed to set persona bio")
def set_bio(
    name: str = typer.Argument(..., help="Persona name"),
    bio: str = typer.Argument(..., help="Whimsical bio text (3-5 sentences, first person, playful tone)"),
) -> None:
    """Set whimsical bio for a persona (typically used by: agents)"""
    name = name.lower()

    db = _get_db()

    # Check if persona exists
    persona_results = db.execute_query(
        "SELECT name FROM personas WHERE name = :name",
        {"name": name},
    )

    if not persona_results:
        console.print(f"[red]Persona '{name}' not found[/red]")
        raise typer.Exit(1)

    # Update bio
    db.execute_update(
        "UPDATE personas SET whimsical_bio = :bio WHERE name = :name",
        {"name": name, "bio": bio},
    )

    console.print(f"[green]✓[/green] Updated bio for {name}")
    logger.info(f"Updated bio for persona: {name}")
