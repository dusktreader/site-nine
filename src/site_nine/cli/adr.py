from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table
from snick import conjoin
from typerdrive import handle_errors, terminal_message

from site_nine.adrs import ADRError, ADRManager, ADRStatus, parse_adr_id, parse_adr_status, parse_adr_title
from site_nine.cli.utils import CLIError, open_in_editor, require_db_path, require_opencode_dir
from site_nine.core.database import Database
from site_nine.core.paths import get_opencode_dir
from site_nine.exceptions import SiteNineError

app = typer.Typer(help="Manage Architecture Decision Records (ADRs)")


@app.command()
@handle_errors("Failed to create ADR", handle_exc_class=SiteNineError)
def create(
    title: Annotated[str, typer.Option("--title", "-t", help="ADR title")],
    status: Annotated[
        ADRStatus, typer.Option("--status", "-s", case_sensitive=False, help="ADR status")
    ] = ADRStatus.PROPOSED,
) -> None:
    """Create a new ADR (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = ADRManager(db)
        adr = manager.create_adr(title=title, status=status)

    terminal_message(
        f"Title: {adr.title}\nStatus: {adr.status.value}\nFile: {adr.file_path}",
        subject=f"Created ADR {adr.id}",
    )


@app.command("list")
@handle_errors("Failed to list ADRs", handle_exc_class=SiteNineError)
def list_adrs(
    status: Annotated[
        ADRStatus | None, typer.Option("--status", "-s", case_sensitive=False, help="Filter by status")
    ] = None,
) -> None:
    """List all ADRs (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = ADRManager(db)
        adrs = manager.list_adrs(status=status)

    if not adrs:
        msg = f"No ADRs found with status {status.value}." if status else "No ADRs found."
        terminal_message(msg)
        return

    table = Table(title="Architecture Decision Records")
    table.add_column("ID", style="cyan")
    table.add_column("Title")
    table.add_column("Status", style="yellow")
    table.add_column("File Path", style="dim")

    for adr in adrs:
        table.add_row(adr.id, adr.title, adr.status.value, adr.file_path)

    terminal_message(table, indent=False)


@app.command()
@handle_errors("Failed to show ADR", handle_exc_class=SiteNineError)
def show(adr_id: Annotated[str, typer.Argument(help="ADR ID (e.g., ADR-001)")]) -> None:
    """Show ADR details (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = ADRManager(db)
        adr = CLIError.enforce_defined(manager.get_adr(adr_id), f"ADR {adr_id} not found")

        epic_ids = manager.get_adr_epics(adr_id)
        task_ids = manager.get_adr_tasks(adr_id)

    details = [
        f"Title: {adr.title}",
        f"Status: {adr.status.value}",
        f"File: {adr.file_path}",
        f"Created: {adr.created_at}",
        f"Updated: {adr.updated_at}",
    ]

    if epic_ids:
        details.append(f"Linked Epics: {', '.join(epic_ids)}")
    if task_ids:
        details.append(f"Linked Tasks: {', '.join(task_ids)}")

    terminal_message(conjoin(*details), subject=f"ADR {adr.id}")


@app.command()
@handle_errors("Failed to update ADR", handle_exc_class=SiteNineError)
def update(
    adr_id: Annotated[str, typer.Argument(help="ADR ID (e.g., ADR-001)")],
    title: Annotated[str | None, typer.Option("--title", "-t", help="New title")] = None,
    status: Annotated[ADRStatus | None, typer.Option("--status", "-s", case_sensitive=False, help="New status")] = None,
) -> None:
    """Update ADR metadata (typically used by: both)"""
    db_path = require_db_path()

    updates = {}

    if title:
        updates["title"] = title

    if status:
        updates["status"] = status.value

    CLIError.require_condition(bool(updates), "No updates provided. Use --title or --status.")

    with Database(db_path) as db:
        manager = ADRManager(db)
        CLIError.enforce_defined(manager.get_adr(adr_id), f"ADR {adr_id} not found")

        manager.update_adr(adr_id, **updates)

    terminal_message(
        conjoin(*(f"{key.title()}: {value}" for key, value in updates.items())),
        subject=f"Updated ADR {adr_id}",
    )


@app.command()
@handle_errors("Failed to sync ADRs", handle_exc_class=SiteNineError)
def sync() -> None:
    """Sync ADRs from filesystem to database (typically used by: both)"""
    db_path = require_db_path()
    opencode_dir = get_opencode_dir()
    adrs_dir = opencode_dir / "docs" / "adrs"

    CLIError.require_condition(adrs_dir.exists(), "No ADRs directory found (.opencode/docs/adrs/)")

    adr_files = sorted(adrs_dir.glob("ADR-*.md"))
    CLIError.require_condition(bool(adr_files), "No ADR files found in .opencode/docs/adrs/")

    imported_count = 0
    updated_count = 0
    skipped_count = 0

    with Database(db_path) as db:
        manager = ADRManager(db)

        for adr_file in adr_files:
            adr_id = parse_adr_id(str(adr_file))
            if not adr_id:
                terminal_message(
                    f"Could not parse ADR ID from {adr_file.name}", subject="Warning", subject_color="yellow"
                )
                skipped_count += 1
                continue

            title = parse_adr_title(adr_file)
            if not title:
                terminal_message(
                    f"Could not parse title from {adr_file.name}", subject="Warning", subject_color="yellow"
                )
                skipped_count += 1
                continue

            status = parse_adr_status(adr_file)
            file_path = f".opencode/docs/adrs/{adr_file.name}"

            existing_adr = manager.get_adr(adr_id)
            if existing_adr:
                if existing_adr.title != title or existing_adr.status != status:
                    manager.update_adr(adr_id, title=title, status=status)
                    terminal_message(f"Updated {adr_id}: {title}")
                    updated_count += 1
                else:
                    skipped_count += 1
            else:
                manager.import_adr(adr_id=adr_id, title=title, file_path=file_path, status=status)
                terminal_message(f"Imported {adr_id}: {title}")
                imported_count += 1

    terminal_message(
        conjoin(
            f"Imported: {imported_count}",
            f"Updated: {updated_count}",
            f"Skipped: {skipped_count}",
        ),
        subject="Sync complete",
    )


@app.command()
@handle_errors("Failed to edit ADR", handle_exc_class=SiteNineError)
def edit(adr_id: Annotated[str, typer.Argument(help="ADR ID (e.g., ADR-001)")]) -> None:
    """Open ADR file in $EDITOR for editing (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = ADRManager(db)
        adr = CLIError.enforce_defined(manager.get_adr(adr_id), f"ADR {adr_id} not found")

    opencode_dir = require_opencode_dir()
    adr_file = Path(adr.file_path)
    if not adr_file.is_absolute():
        adr_file = opencode_dir / adr_file

    open_in_editor(f"ADR {adr_id}", adr_file)
    terminal_message(
        f"Run 's9 adr sync' to update the database from the edited file.",
        subject="Tip",
        subject_color="cyan",
    )


@app.command()
@handle_errors("Failed to accept ADR", handle_exc_class=SiteNineError)
def accept(adr_id: Annotated[str, typer.Argument(help="ADR ID (e.g., ADR-001)")]) -> None:
    """Mark ADR as accepted (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = ADRManager(db)
        CLIError.enforce_defined(manager.get_adr(adr_id), f"ADR {adr_id} not found")
        manager.update_adr(adr_id, status=ADRStatus.ACCEPTED.value)

    terminal_message(
        f"ADR {adr_id} has been accepted.",
        subject=f"Accepted ADR {adr_id}",
        subject_color="green",
    )


@app.command()
@handle_errors("Failed to reject ADR", handle_exc_class=SiteNineError)
def reject(
    adr_id: Annotated[str, typer.Argument(help="ADR ID (e.g., ADR-001)")],
    reason: Annotated[str | None, typer.Option("--reason", "-r", help="Reason for rejection")] = None,
) -> None:
    """Mark ADR as rejected (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = ADRManager(db)
        CLIError.enforce_defined(manager.get_adr(adr_id), f"ADR {adr_id} not found")
        manager.update_adr(adr_id, status=ADRStatus.REJECTED.value)

    msg = f"ADR {adr_id} has been rejected."
    if reason:
        msg += f"\nReason: {reason}"

    terminal_message(msg, subject=f"Rejected ADR {adr_id}", subject_color="red")


@app.command()
@handle_errors("Failed to supersede ADR", handle_exc_class=SiteNineError)
def supersede(
    adr_id: Annotated[str, typer.Argument(help="ADR ID to supersede (e.g., ADR-001)")],
    by: Annotated[str, typer.Option("--by", help="ID of the new ADR that supersedes this one")],
) -> None:
    """Mark ADR as superseded by a newer decision (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = ADRManager(db)
        CLIError.enforce_defined(manager.get_adr(adr_id), f"ADR {adr_id} not found")
        CLIError.enforce_defined(manager.get_adr(by), f"Superseding ADR {by} not found")
        manager.update_adr(adr_id, status=ADRStatus.SUPERSEDED.value)

    terminal_message(
        f"ADR {adr_id} has been superseded by {by}.",
        subject=f"Superseded ADR {adr_id}",
        subject_color="yellow",
    )
