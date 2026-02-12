"""Dashboard CLI command — thin layer over dashboard manager and rendering."""

from typing import Annotated

import typer
from typerdrive import handle_errors, terminal_message

from site_nine.cli.json_utils import format_json_response, output_json
from site_nine.cli.utils import require_db_path
from site_nine.core.database import Database
from site_nine.dashboard import DashboardManager
from site_nine.dashboard.rendering import dashboard_to_json, render_dashboard
from site_nine.exceptions import SiteNineError


@handle_errors("Failed to show dashboard", handle_exc_class=SiteNineError)
def dashboard_command(
    role: Annotated[str | None, typer.Option("--role", "-r", help="Filter tasks by role")] = None,
    epic: Annotated[str | None, typer.Option("--epic", "-e", help="Filter tasks by epic ID")] = None,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Show project dashboard with overview of missions and tasks (typically used by: humans)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = DashboardManager(db)
        data = manager.get_dashboard(role=role, epic=epic)

        if json_output:
            output_json(format_json_response(dashboard_to_json(data)))
            return

        for item in render_dashboard(data, manager.epic_manager.get_subtasks):
            terminal_message(item, indent=False)
