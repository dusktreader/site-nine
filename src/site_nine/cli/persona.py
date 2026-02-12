from typing import Annotated

import typer
from rich.table import Table
from snick import conjoin
from typerdrive import handle_errors, terminal_message

from site_nine.cli.json_utils import format_json_response, output_json
from site_nine.cli.utils import abort, abort_unless, require_db_path
from site_nine.core.database import Database
from site_nine.core.roles import Role

app = typer.Typer(help="Manage personas")


def _validate_role(role: str) -> str:
    """Validate role name (case-insensitive), returns title case"""
    try:
        Role.from_string(role)
    except ValueError:
        valid_roles_str = ", ".join(Role.all_values())
        abort(f"Invalid role: {role}. Valid values: {valid_roles_str}")
    return role.title()


@app.command()
@handle_errors("Failed to add persona")
def add(
    name: Annotated[str, typer.Argument(help="Persona name (lowercase)")],
    role: Annotated[str, typer.Option("--role", "-r", help="Primary role for this persona")],
    mythology: Annotated[str, typer.Option("--mythology", "-m", help="Mythology origin (e.g., Greek, Roman, Norse)")],
    description: Annotated[str, typer.Option("--description", "-d", help="Brief description of the deity/figure")],
) -> None:
    """Add a new persona (typically used by: humans)"""
    name = name.lower()
    role = _validate_role(role)

    db_path = require_db_path()

    with Database(db_path) as db:
        try:
            db.execute_update(
                """
                INSERT INTO personas (name, role, mythology, description)
                VALUES (:name, :role, :mythology, :description)
                """,
                {"name": name, "role": role, "mythology": mythology, "description": description},
            )
            terminal_message(
                f"Added persona: {name} ({role}, {mythology})",
                subject="Success",
                subject_color="green",
            )
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                abort(f"Persona '{name}' already exists")
            raise


@app.command()
@handle_errors("Failed to list personas")
def list(
    role: Annotated[str | None, typer.Option("--role", "-r", help="Filter by role")] = None,
    unused_only: Annotated[bool, typer.Option("--unused-only", help="Show only unused personas")] = False,
    by_usage: Annotated[bool, typer.Option("--by-usage", help="Sort by mission count")] = False,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """List personas (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
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
                return
            terminal_message("No personas found", subject="Empty", subject_color="yellow")
            return

        if json_output:
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

        terminal_message(table, indent=False)
        terminal_message(f"Total: {len(personas)} persona(s)", subject="Count")


@app.command()
@handle_errors("Failed to suggest personas")
def suggest(
    role: Annotated[str, typer.Argument(help="Role to suggest persona for")],
    count: Annotated[int, typer.Option("--count", "-c", help="Number of suggestions")] = 3,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Suggest unused personas for a role (typically used by: agents)"""
    role = _validate_role(role)

    db_path = require_db_path()

    with Database(db_path) as db:
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
                return
            terminal_message(
                conjoin(
                    f"No personas found for role: {role}",
                    "Tip: Add personas with 's9 persona add'",
                ),
                subject="Empty",
                subject_color="yellow",
            )
            return

        if json_output:
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
            return

        body_parts = [f"Suggested personas for {role.title()}:", ""]
        for idx, persona in enumerate(suggestions, 1):
            usage_str = "unused" if persona["mission_count"] == 0 else f"{persona['mission_count']} mission(s)"
            body_parts.append(f"{idx}. {persona['name']} ({persona['mythology']}) - {usage_str}")
            body_parts.append(f"   {persona['description']}")
            body_parts.append("")

        terminal_message(conjoin(*body_parts), subject="Suggestions")


@app.command()
@handle_errors("Failed to show persona usage")
def usage(
    name: Annotated[str, typer.Argument(help="Persona name to check")],
) -> None:
    """Show usage history for a persona (typically used by: both)"""
    name = name.lower()

    db_path = require_db_path()

    with Database(db_path) as db:
        # Get persona info
        persona_results = db.execute_query(
            "SELECT * FROM personas WHERE name = :name",
            {"name": name},
        )

        abort_unless(persona_results, f"Persona '{name}' not found")

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
        body_parts = [
            f"Persona: {persona['name']}",
            f"Role:          {persona['role']}",
            f"Mythology:     {persona['mythology']}",
            f"Description:   {persona['description']}",
            f"Mission Count: {persona['mission_count']}",
        ]
        if persona["last_mission_at"]:
            body_parts.append(f"Last Mission:  {persona['last_mission_at'][:10]}")

        terminal_message(conjoin(*body_parts), subject="Persona Info")

        # Display missions
        if missions:
            table = Table(title=f"Missions ({len(missions)})")
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

            terminal_message(table, indent=False)
        else:
            terminal_message(
                "No missions found for this persona",
                subject="Empty",
                subject_color="yellow",
            )


@app.command()
@handle_errors("Failed to show persona")
def show(
    name: Annotated[str, typer.Argument(help="Persona name to display")],
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Show persona details including whimsical bio (typically used by: both)"""
    name = name.lower()

    db_path = require_db_path()

    with Database(db_path) as db:
        # Get persona info
        persona_results = db.execute_query(
            "SELECT * FROM personas WHERE name = :name",
            {"name": name},
        )

        abort_unless(persona_results, f"Persona '{name}' not found")

        persona = persona_results[0]

        if json_output:
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
            return

        # Display basic info
        body_parts = [
            f"Role: {persona['role']}",
            f"Mythology: {persona['mythology']}",
            f"Description: {persona['description']}",
        ]

        # Display whimsical bio if available
        if persona.get("whimsical_bio"):
            body_parts.extend(["", "About me...", "", persona["whimsical_bio"]])
        else:
            body_parts.extend(["", "No whimsical bio available yet. Generate one during session-start!"])

        terminal_message(conjoin(*body_parts), subject=persona["name"].title())


@app.command()
@handle_errors("Failed to set persona bio")
def set_bio(
    name: Annotated[str, typer.Argument(help="Persona name")],
    bio: Annotated[str, typer.Argument(help="Whimsical bio text (3-5 sentences, first person, playful tone)")],
) -> None:
    """Set whimsical bio for a persona (typically used by: agents)"""
    name = name.lower()

    db_path = require_db_path()

    with Database(db_path) as db:
        # Check if persona exists
        persona_results = db.execute_query(
            "SELECT name FROM personas WHERE name = :name",
            {"name": name},
        )

        abort_unless(persona_results, f"Persona '{name}' not found")

        # Update bio
        db.execute_update(
            "UPDATE personas SET whimsical_bio = :bio WHERE name = :name",
            {"name": name, "bio": bio},
        )

        terminal_message(f"Updated bio for {name}", subject="Success", subject_color="green")
