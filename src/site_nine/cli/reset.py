"""Reset project data with safety confirmations"""

from __future__ import annotations

from typing import Annotated

import typer
from rich.prompt import Confirm
from snick import conjoin
from typerdrive import handle_errors, terminal_message

from site_nine.cli.utils import abort, abort_unless, require_opencode_dir
from site_nine.core.database import Database


@handle_errors("Failed to reset project")
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

    abort_unless(db_path.exists(), "project.db not found. Run 's9 init' first.")

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

    # Get counts before deletion
    with Database(db_path) as db:
        mission_count = db.execute_query("SELECT COUNT(*) as count FROM missions")[0]["count"]
        task_count = db.execute_query("SELECT COUNT(*) as count FROM tasks")[0]["count"]
        dep_count = db.execute_query("SELECT COUNT(*) as count FROM task_dependencies")[0]["count"]

        terminal_message(
            conjoin(
                "Data to be deleted:",
                f"  - {mission_count} missions",
                f"  - {task_count} tasks",
                f"  - {dep_count} task dependencies",
            ),
            subject="Summary",
            subject_color="yellow",
        )

        if mission_count == 0 and task_count == 0:
            terminal_message("No data to delete. Database is already clean.", subject="Clean", subject_color="green")
            return

        # First confirmation
        if not yes:
            if not Confirm.ask("Are you absolutely sure you want to reset the project?", default=False):
                terminal_message("Cancelled. No changes made.", subject="Cancelled", subject_color="green")
                raise typer.Exit(0)

        # Second confirmation - require typing
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

        # Delete mission files
        missions_dir = opencode_dir / "work" / "missions"
        deleted_mission_files = 0
        mission_warnings: list[str] = []

        if missions_dir.exists():
            for mission_file in missions_dir.glob("*.md"):
                # Skip README and TEMPLATE files
                if mission_file.name in ("README.md", "TEMPLATE.md"):
                    continue
                try:
                    mission_file.unlink()
                    deleted_mission_files += 1
                except Exception as e:
                    mission_warnings.append(f"Failed to delete {mission_file.name}: {e}")

        # Delete handoff files
        handoffs_dir = opencode_dir / "work" / "missions" / "handoffs"
        deleted_handoff_files = 0

        if handoffs_dir.exists():
            for handoff_file in handoffs_dir.glob("*.md"):
                try:
                    handoff_file.unlink()
                    deleted_handoff_files += 1
                except Exception as e:
                    mission_warnings.append(f"Failed to delete {handoff_file.name}: {e}")

        # Delete task files
        tasks_dir = opencode_dir / "work" / "tasks"
        deleted_task_files = 0

        if tasks_dir.exists():
            for task_file in tasks_dir.glob("*.md"):
                # Skip README if it exists
                if task_file.name == "README.md":
                    continue
                try:
                    task_file.unlink()
                    deleted_task_files += 1
                except Exception as e:
                    mission_warnings.append(f"Failed to delete {task_file.name}: {e}")

        # Delete database records
        # Delete task dependencies first (foreign key constraint)
        db.execute_update("DELETE FROM task_dependencies")
        db.execute_update("DELETE FROM tasks")
        db.execute_update("DELETE FROM missions")

        # Reset persona mission counts
        db.execute_update("UPDATE personas SET mission_count = 0, last_mission_at = NULL")

        # Vacuum database to reclaim space
        vacuum_warning = None
        try:
            db.execute_update("VACUUM")
        except Exception as e:
            vacuum_warning = f"Failed to vacuum database: {e}"

        # Report warnings
        for warning in mission_warnings:
            terminal_message(warning, subject="Warning", subject_color="yellow")
        if vacuum_warning:
            terminal_message(vacuum_warning, subject="Warning", subject_color="yellow")

        # Final summary
        terminal_message(
            conjoin(
                "Deleted:",
                f"  - {deleted_mission_files} mission files",
                f"  - {deleted_handoff_files} handoff files",
                f"  - {deleted_task_files} task files",
                f"  - {mission_count} mission records",
                f"  - {task_count} task records",
                f"  - {dep_count} dependencies",
                "",
                "Your project is now in a fresh state.",
            ),
            subject="Reset complete",
            subject_color="green",
        )
