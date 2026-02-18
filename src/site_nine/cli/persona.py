from typing import Annotated

import typer
from rich.table import Table
from snick import conjoin
from typerdrive import handle_errors, terminal_message

from site_nine.cli.json_utils import format_json_response, output_json
from site_nine.cli.utils import CLIError, require_db_path
from site_nine.core.database import Database
from site_nine.exceptions import SiteNineError
from site_nine.personas import PersonaManager

app = typer.Typer(help="Manage personas")


@app.command()
@handle_errors("Failed to add persona", handle_exc_class=SiteNineError)
def add(
    name: Annotated[str, typer.Argument(help="Persona name (lowercase)")],
    role: Annotated[str, typer.Option("--role", "-r", help="Primary role for this persona")],
    mythology: Annotated[str, typer.Option("--mythology", "-m", help="Mythology origin (e.g., Greek, Roman, Norse)")],
    description: Annotated[str, typer.Option("--description", "-d", help="Brief description of the deity/figure")],
) -> None:
    """Add a new persona (typically used by: humans)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        mgr = PersonaManager(db)
        persona = mgr.add_persona(name, role, mythology, description)

        terminal_message(
            f"Added persona: {persona.name} ({persona.role}, {persona.mythology})",
            subject="Success",
            subject_color="green",
        )


@app.command()
@handle_errors("Failed to list personas", handle_exc_class=SiteNineError)
def list(
    role: Annotated[str | None, typer.Option("--role", "-r", help="Filter by role")] = None,
    unused_only: Annotated[bool, typer.Option("--unused-only", help="Show only unused personas")] = False,
    by_usage: Annotated[bool, typer.Option("--by-usage", help="Sort by mission count")] = False,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """List personas (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        mgr = PersonaManager(db)
        personas = mgr.list_personas(role=role, unused_only=unused_only, by_usage=by_usage)

        if not personas:
            if json_output:
                output_json(format_json_response([]))
                return
            terminal_message("No personas found", subject="Empty", subject_color="yellow")
            return

        if json_output:
            output_json(format_json_response([p.to_dict() for p in personas]))
            return

        table = Table(title="Personas")
        table.add_column("Name", style="cyan")
        table.add_column("Role", style="green")
        table.add_column("Mythology", style="magenta")
        table.add_column("Description", style="white")
        table.add_column("Missions", style="yellow")
        table.add_column("Last Mission", style="dim")

        for persona in personas:
            last_mission = persona.last_mission_at.format("YYYY-MM-DD") if persona.last_mission_at else "Never"
            desc = persona.description
            desc_display = desc[:40] + "..." if len(desc) > 40 else desc

            table.add_row(
                persona.name,
                persona.role,
                persona.mythology,
                desc_display,
                str(persona.mission_count),
                last_mission,
            )

        terminal_message(table, indent=False)
        terminal_message(f"Total: {len(personas)} persona(s)", subject="Count")


@app.command()
@handle_errors("Failed to suggest personas", handle_exc_class=SiteNineError)
def suggest(
    role: Annotated[str, typer.Argument(help="Role to suggest persona for")],
    count: Annotated[int, typer.Option("--count", "-c", help="Number of suggestions")] = 3,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Suggest unused personas for a role (typically used by: agents)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        mgr = PersonaManager(db)
        suggestions = mgr.suggest_for_role(role, count=count)

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
            output_json(format_json_response([p.to_dict() for p in suggestions]))
            return

        body_parts = [f"Suggested personas for {role.title()}:", ""]
        for idx, persona in enumerate(suggestions, 1):
            usage_str = "unused" if persona.mission_count == 0 else f"{persona.mission_count} mission(s)"
            body_parts.append(f"{idx}. {persona.name} ({persona.mythology}) - {usage_str}")
            body_parts.append(f"   {persona.description}")
            body_parts.append("")

        terminal_message(conjoin(*body_parts), subject="Suggestions")


@app.command()
@handle_errors("Failed to show persona usage", handle_exc_class=SiteNineError)
def usage(
    name: Annotated[str, typer.Argument(help="Persona name to check")],
) -> None:
    """Show usage history for a persona (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        mgr = PersonaManager(db)
        persona = CLIError.enforce_defined(mgr.get_persona(name), f"Persona '{name}' not found")

        missions = mgr.get_persona_missions(name)

        body_parts = [
            f"Persona: {persona.name}",
            f"Role:          {persona.role}",
            f"Mythology:     {persona.mythology}",
            f"Description:   {persona.description}",
            f"Mission Count: {persona.mission_count}",
        ]
        if persona.last_mission_at:
            body_parts.append(f"Last Mission:  {persona.last_mission_at.format('YYYY-MM-DD')}")

        terminal_message(conjoin(*body_parts), subject="Persona Info")

        if missions:
            table = Table(title=f"Missions ({len(missions)})")
            table.add_column("ID", style="cyan")
            table.add_column("Codename", style="yellow")
            table.add_column("Role", style="green")
            table.add_column("Date", style="white")
            table.add_column("Status", style="magenta")

            for mission in missions:
                status = "Active" if mission.is_active else "Complete"
                table.add_row(
                    str(mission.id),
                    mission.codename,
                    mission.role or "?",
                    mission.start_date or "?",
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
@handle_errors("Failed to show persona", handle_exc_class=SiteNineError)
def show(
    name: Annotated[str, typer.Argument(help="Persona name to display")],
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Show persona details including whimsical bio (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        mgr = PersonaManager(db)
        persona = CLIError.enforce_defined(mgr.get_persona(name), f"Persona '{name}' not found")

        if json_output:
            output_json(format_json_response(persona.to_dict()))
            return

        body_parts = [
            f"Role: {persona.role}",
            f"Mythology: {persona.mythology}",
            f"Description: {persona.description}",
        ]

        if persona.whimsical_bio:
            body_parts.extend(["", "About me...", "", persona.whimsical_bio])
        else:
            body_parts.extend(["", "No whimsical bio available yet. Generate one during session-start!"])

        terminal_message(conjoin(*body_parts), subject=persona.name.title())


@app.command()
@handle_errors("Failed to set persona bio", handle_exc_class=SiteNineError)
def set_bio(
    name: Annotated[str, typer.Argument(help="Persona name")],
    bio: Annotated[str, typer.Argument(help="Whimsical bio text (3-5 sentences, first person, playful tone)")],
) -> None:
    """Set whimsical bio for a persona (typically used by: agents)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        mgr = PersonaManager(db)
        mgr.set_bio(name, bio)

        terminal_message(f"Updated bio for {name.lower()}", subject="Success", subject_color="green")
