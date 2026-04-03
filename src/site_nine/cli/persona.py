from typing import Annotated

import typer
from rich.table import Table
from snick import conjoin
from typerdrive import handle_errors, terminal_message

from site_nine.cli.json_utils import format_json_response, output_json
from site_nine.cli.utils import CLIError, require_db_path
from site_nine.core.database import Database
from site_nine.exceptions import SiteNineError
from site_nine.daemons import DaemonManager
from site_nine.possessions.manager import PossessionManager

app = typer.Typer(help="Manage personas")


@app.command()
@handle_errors("Failed to add persona", handle_exc_class=SiteNineError)
def add(
    name: Annotated[str, typer.Argument(help="Persona name (lowercase)")],
    role: Annotated[str, typer.Option("--role", "-r", help="Primary role for this persona")],
    daemonology: Annotated[
        str | None,
        typer.Option("--daemonology", "-d", help="Whimsical first-person bio / daemonology text"),
    ] = None,
    personality: Annotated[
        str | None,
        typer.Option("--personality", "-p", help="Terse personality trait string"),
    ] = None,
) -> None:
    """Add a new persona (typically used by: humans)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        mgr = DaemonManager(db)
        daemon = mgr.add_daemon(name, role, daemonology=daemonology, personality=personality)

        terminal_message(
            f"Added persona: {daemon.name} ({daemon.role})",
            subject="Success",
            subject_color="green",
        )


@app.command()
@handle_errors("Failed to list personas", handle_exc_class=SiteNineError)
def list(
    role: Annotated[str | None, typer.Option("--role", "-r", help="Filter by role")] = None,
    unused_only: Annotated[bool, typer.Option("--unused-only", help="Show only unused personas")] = False,
    by_usage: Annotated[bool, typer.Option("--by-usage", help="Sort by incarnation count")] = False,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """List personas (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        mgr = DaemonManager(db)
        daemons = mgr.list_daemons(role=role, unused_only=unused_only, by_usage=by_usage)

        if not daemons:
            if json_output:
                output_json(format_json_response([]))
                return
            terminal_message("No personas found", subject="Empty", subject_color="yellow")
            return

        if json_output:
            output_json(format_json_response([d.to_dict() for d in daemons]))
            return

        table = Table(title="Personas")
        table.add_column("Name", style="cyan")
        table.add_column("Role", style="green")
        table.add_column("Incarnations", style="yellow")
        table.add_column("Last Possession", style="dim")
        table.add_column("Daemonology", style="white")

        for daemon in daemons:
            last_possession = daemon.last_possession.format("YYYY-MM-DD") if daemon.last_possession else "Never"
            daemonology = daemon.daemonology or ""
            daemonology_display = daemonology[:40] + "..." if len(daemonology) > 40 else daemonology

            table.add_row(
                daemon.name,
                daemon.role,
                str(daemon.incarnations),
                last_possession,
                daemonology_display,
            )

        terminal_message(table, indent=False)
        terminal_message(f"Total: {len(daemons)} persona(s)", subject="Count")


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
        mgr = DaemonManager(db)
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
            output_json(format_json_response([d.to_dict() for d in suggestions]))
            return

        body_parts = [f"Suggested personas for {role.title()}:", ""]
        for idx, daemon in enumerate(suggestions, 1):
            usage_str = "unused" if daemon.incarnations == 0 else f"{daemon.incarnations} incarnation(s)"
            body_parts.append(f"{idx}. {daemon.name} - {usage_str}")
            if daemon.daemonology:
                body_parts.append(f"   {daemon.daemonology[:80]}")
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
        mgr = DaemonManager(db)
        daemon = CLIError.enforce_defined(mgr.get_daemon(name), f"Persona '{name}' not found")

        pmgr = PossessionManager(db)
        all_possessions = pmgr.list_possessions()
        possessions = [p for p in all_possessions if p.daemon_name == daemon.name]

        body_parts = [
            f"Persona: {daemon.name}",
            f"Role:          {daemon.role}",
            f"Incarnations:  {daemon.incarnations}",
        ]
        if daemon.last_possession:
            body_parts.append(f"Last Possession: {daemon.last_possession.format('YYYY-MM-DD')}")
        if daemon.daemonology:
            body_parts.extend(["", "Daemonology:", daemon.daemonology])

        terminal_message(conjoin(*body_parts), subject="Persona Info")

        if possessions:
            table = Table(title=f"Possessions ({len(possessions)})")
            table.add_column("ID", style="cyan")
            table.add_column("Role", style="green")
            table.add_column("Started", style="white")
            table.add_column("Status", style="magenta")

            for possession in possessions:
                table.add_row(
                    str(possession.id),
                    possession.role,
                    possession.start_time[:10] if possession.start_time else "?",
                    possession.status.value,
                )

            terminal_message(table, indent=False)
        else:
            terminal_message(
                "No possessions found for this persona",
                subject="Empty",
                subject_color="yellow",
            )


@app.command()
@handle_errors("Failed to show persona", handle_exc_class=SiteNineError)
def show(
    name: Annotated[str, typer.Argument(help="Persona name to display")],
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Show persona details including daemonology bio (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        mgr = DaemonManager(db)
        daemon = CLIError.enforce_defined(mgr.get_daemon(name), f"Persona '{name}' not found")

        if json_output:
            output_json(format_json_response(daemon.to_dict()))
            return

        body_parts = [
            f"Role: {daemon.role}",
            f"Incarnations: {daemon.incarnations}",
        ]
        if daemon.personality:
            body_parts.append(f"Personality: {daemon.personality}")

        if daemon.daemonology:
            body_parts.extend(["", "About me...", "", daemon.daemonology])
        else:
            body_parts.extend(["", "No daemonology available yet. Generate one during session-start!"])

        terminal_message(conjoin(*body_parts), subject=daemon.name.title())


@app.command()
@handle_errors("Failed to set persona bio", handle_exc_class=SiteNineError)
def set_bio(
    name: Annotated[str, typer.Argument(help="Persona name")],
    bio: Annotated[str, typer.Argument(help="Daemonology text (3-5 sentences, first person, playful tone)")],
) -> None:
    """Set daemonology bio for a persona (typically used by: agents)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        mgr = DaemonManager(db)
        mgr.set_daemonology(name, bio)

        terminal_message(f"Updated daemonology for {name.lower()}", subject="Success", subject_color="green")
