"""Reset project data with safety confirmations"""

from __future__ import annotations

from typing import Annotated

import typer
from rich.prompt import Confirm
from snick import conjoin
from typerdrive import handle_errors, terminal_message

from site_nine.cli.utils import CLIError, require_opencode_dir
from site_nine.core.database import Database
from site_nine.exceptions import SiteNineError
from site_nine.reset import ResetManager


@handle_errors("Failed to reset project", handle_exc_class=SiteNineError)
def reset_command(
    yes: Annotated[
        bool, typer.Option("--yes", "-y", help="Skip first confirmation (still requires typing confirmation)")
    ] = False,
) -> None:
    """Reset project data - DANGEROUS! (typically used by: humans)

    This command will DELETE:
    - All missions (database records and mission files)
    - All tasks (database records and task files)
    - All task dependencies
    - All persona mission counts (reset to 0)

    This command will PRESERVE:
    - Personas list (but mission counts reset to 0)
    - Task templates
    - Configuration files
    - Documentation files

    Requires DOUBLE confirmation to prevent accidental data loss.
    """
    opencode_dir = require_opencode_dir()

    db_path = opencode_dir / "data" / "project.db"

    CLIError.require_condition(db_path.exists(), "project.db not found. Run 's9 init' first.")

    terminal_message(
        conjoin(
            "This will permanently DELETE:",
            "  - All missions (database + files)",
            "  - All tasks (database + files)",
            "  - All task dependencies",
            "  - Persona mission counts",
            "",
            "This CANNOT be undone without a backup!",
        ),
        subject="WARNING: DESTRUCTIVE OPERATION",
        subject_color="red",
    )

    with Database(db_path) as db:
        manager = ResetManager(db)
        counts = manager.get_counts()

        terminal_message(
            conjoin(
                "Data to be deleted:",
                f"  - {counts.missions} missions",
                f"  - {counts.tasks} tasks",
                f"  - {counts.dependencies} task dependencies",
            ),
            subject="Summary",
            subject_color="yellow",
        )

        if counts.is_empty:
            terminal_message("No data to delete. Database is already clean.", subject="Clean", subject_color="green")
            return

        if not yes:
            if not Confirm.ask("Are you absolutely sure you want to reset the project?", default=False):
                terminal_message("Cancelled. No changes made.", subject="Cancelled", subject_color="green")
                raise typer.Exit(0)

        terminal_message(
            "To confirm, type exactly: DELETE ALL DATA",
            subject="Second Confirmation Required",
            subject_color="red",
        )

        confirmation = typer.prompt("Confirmation")

        if confirmation != "DELETE ALL DATA":
            terminal_message(
                "Cancelled. Confirmation text did not match.",
                subject="Cancelled",
                subject_color="green",
            )
            raise typer.Exit(0)

        terminal_message("Proceeding with reset...", subject="Reset", subject_color="red")

        result = manager.reset(opencode_dir)

        for warning in result.warnings:
            terminal_message(warning, subject="Warning", subject_color="yellow")

        terminal_message(
            conjoin(
                "Deleted:",
                f"  - {result.mission_files} mission files",
                f"  - {result.task_files} task files",
                f"  - {result.mission_records} mission records",
                f"  - {result.task_records} task records",
                f"  - {result.dependency_records} dependencies",
                "",
                "Your project is now in a fresh state.",
            ),
            subject="Reset complete",
            subject_color="green",
        )
