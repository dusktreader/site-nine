"""ADR (Architecture Decision Record) management commands"""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table
from typerdrive import handle_errors

from site_nine.adrs import ADRManager, ArchitectureDoc
from site_nine.core.database import Database
from site_nine.core.paths import get_opencode_dir

app = typer.Typer(help="Manage Architecture Decision Records (ADRs)")
console = Console()


class ADRStatus(str, Enum):
    """ADR status values"""

    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"
    DEPRECATED = "DEPRECATED"


def _get_manager() -> ADRManager:
    """Get ADR manager"""
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
    return ADRManager(db)


def _parse_adr_id(file_path: str) -> str | None:
    """Extract ADR ID from filename (e.g., 'ADR-001' from 'ADR-001-adapter-pattern.md')"""
    match = re.match(r"(ADR-\d+)", Path(file_path).name)
    return match.group(1) if match else None


def _parse_adr_title(file_path: Path) -> str | None:
    """Extract title from ADR markdown file"""
    try:
        content = file_path.read_text()
        # Look for "# ADR-XXX: Title" pattern
        match = re.search(r"#\s+ADR-\d+:\s+(.+)", content)
        if match:
            return match.group(1).strip()
        # Fallback: use first # heading
        match = re.search(r"#\s+(.+)", content)
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return None


def _parse_adr_status(file_path: Path) -> str:
    """Extract status from ADR markdown file"""
    try:
        content = file_path.read_text()
        # Look for "**Status:** XXXX" pattern
        match = re.search(r"\*\*Status:\*\*\s+(\w+)", content)
        if match:
            status = match.group(1).upper()
            if status in [s.value for s in ADRStatus]:
                return status
    except Exception:
        pass
    return "PROPOSED"  # Default


@app.command()
@handle_errors("Failed to create ADR")
def create(
    title: str = typer.Option(..., "--title", "-t", help="ADR title"),
    status: str = typer.Option("PROPOSED", "--status", "-s", help="ADR status (default: PROPOSED)"),
) -> None:
    """Create a new ADR (typically used by: both)"""
    manager = _get_manager()

    # Validate status
    try:
        status_upper = status.upper()
        if status_upper not in [s.value for s in ADRStatus]:
            raise ValueError(f"Invalid status: {status}. Valid values: {', '.join(s.value for s in ADRStatus)}")
        status = status_upper
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    # Get next ADR number
    existing_adrs = manager.list_adrs()
    if existing_adrs:
        last_num = max(int(adr.id.split("-")[1]) for adr in existing_adrs)
        next_num = last_num + 1
    else:
        next_num = 1

    adr_id = f"ADR-{next_num:03d}"

    # Generate filename from title
    filename_base = title.lower().replace(" ", "-").replace("_", "-")
    filename_base = re.sub(r"[^a-z0-9-]", "", filename_base)
    filename = f"{adr_id}-{filename_base}.md"

    opencode_dir = get_opencode_dir()
    file_path = f".opencode/docs/adrs/{filename}"
    full_path = opencode_dir / "docs" / "adrs" / filename

    # Create ADR in database
    adr = manager.create_adr(adr_id=adr_id, title=title, file_path=file_path, status=status)

    # Create markdown file
    full_path.parent.mkdir(parents=True, exist_ok=True)
    content = f"""# {adr_id}: {title}

**Status:** {status}
**Date:** {adr.created_at[:10]}
**Deciders:** [To be filled]
**Related Tasks:** [To be filled]

## Context

[Describe the issue that motivates this decision]

## Decision

[Describe the decision and how it addresses the issue]

## Alternatives Considered

### Alternative 1: [Name]

**Approach:** [Description]

**Pros:**
- [Pro 1]
- [Pro 2]

**Cons:**
- [Con 1]
- [Con 2]

**Rejected because:** [Reason]

## Consequences

### Positive

- ✅ [Benefit 1]
- ✅ [Benefit 2]

### Negative

- ⚠️ [Trade-off 1]
- ⚠️ [Trade-off 2]

### Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| [Risk 1] | [Mitigation 1] |
| [Risk 2] | [Mitigation 2] |

## References

- [Related documents, tasks, or external resources]

## Notes

[Additional notes or context]
"""
    full_path.write_text(content)

    console.print(f"[green]✓[/green] Created ADR {adr_id}")
    console.print(f"  Title: {title}")
    console.print(f"  Status: {status}")
    console.print(f"  File: {file_path}")

    logger.info(f"Created ADR {adr_id}: {title}")


@app.command("list")
@handle_errors("Failed to list ADRs")
def list_adrs(
    status: str | None = typer.Option(None, "--status", "-s", help="Filter by status"),
) -> None:
    """List all ADRs (typically used by: both)"""
    manager = _get_manager()

    # Validate status if provided
    if status:
        status_upper = status.upper()
        if status_upper not in [s.value for s in ADRStatus]:
            console.print(
                f"[red]Error: Invalid status: {status}. Valid values: {', '.join(s.value for s in ADRStatus)}[/red]"
            )
            raise typer.Exit(1)
        status = status_upper

    adrs = manager.list_adrs(status=status)

    if not adrs:
        if status:
            console.print(f"No ADRs found with status {status}.")
        else:
            console.print("No ADRs found.")
        return

    # Create table
    table = Table(title="Architecture Decision Records")
    table.add_column("ID", style="cyan")
    table.add_column("Title")
    table.add_column("Status", style="yellow")
    table.add_column("File Path", style="dim")

    for adr in adrs:
        table.add_row(adr.id, adr.title, adr.status, adr.file_path)

    console.print(table)
    logger.debug(f"Listed {len(adrs)} ADRs")


@app.command()
@handle_errors("Failed to show ADR")
def show(adr_id: str = typer.Argument(..., help="ADR ID (e.g., ADR-001)")) -> None:
    """Show ADR details (typically used by: both)"""
    manager = _get_manager()

    adr = manager.get_adr(adr_id)
    if not adr:
        console.print(f"[red]Error: ADR {adr_id} not found[/red]")
        raise typer.Exit(1)

    # Get linked epics and tasks
    epic_ids = manager.get_adr_epics(adr_id)
    task_ids = manager.get_adr_tasks(adr_id)

    console.print(f"[bold cyan]ADR {adr.id}[/bold cyan]")
    console.print(f"  Title: {adr.title}")
    console.print(f"  Status: [yellow]{adr.status}[/yellow]")
    console.print(f"  File: {adr.file_path}")
    console.print(f"  Created: {adr.created_at}")
    console.print(f"  Updated: {adr.updated_at}")

    if epic_ids:
        console.print(f"\n  Linked Epics: {', '.join(epic_ids)}")
    if task_ids:
        console.print(f"  Linked Tasks: {', '.join(task_ids)}")

    logger.debug(f"Displayed details for ADR {adr_id}")


@app.command()
@handle_errors("Failed to update ADR")
def update(
    adr_id: str = typer.Argument(..., help="ADR ID (e.g., ADR-001)"),
    title: str | None = typer.Option(None, "--title", "-t", help="New title"),
    status: str | None = typer.Option(None, "--status", "-s", help="New status"),
) -> None:
    """Update ADR metadata (typically used by: both)"""
    manager = _get_manager()

    # Check ADR exists
    adr = manager.get_adr(adr_id)
    if not adr:
        console.print(f"[red]Error: ADR {adr_id} not found[/red]")
        raise typer.Exit(1)

    updates = {}

    if title:
        updates["title"] = title

    if status:
        status_upper = status.upper()
        if status_upper not in [s.value for s in ADRStatus]:
            console.print(
                f"[red]Error: Invalid status: {status}. Valid values: {', '.join(s.value for s in ADRStatus)}[/red]"
            )
            raise typer.Exit(1)
        updates["status"] = status_upper

    if not updates:
        console.print("[yellow]No updates provided. Use --title or --status.[/yellow]")
        raise typer.Exit(1)

    # Update in database
    updated_adr = manager.update_adr(adr_id, **updates)

    console.print(f"[green]✓[/green] Updated ADR {adr_id}")
    for key, value in updates.items():
        console.print(f"  {key.title()}: {value}")

    logger.info(f"Updated ADR {adr_id}: {updates}")


@app.command()
@handle_errors("Failed to sync ADRs")
def sync() -> None:
    """Sync ADRs from filesystem to database (typically used by: both)"""
    manager = _get_manager()
    opencode_dir = get_opencode_dir()
    adrs_dir = opencode_dir / "docs" / "adrs"

    if not adrs_dir.exists():
        console.print("[yellow]No ADRs directory found (.opencode/docs/adrs/)[/yellow]")
        return

    # Get ADR files
    adr_files = sorted(adrs_dir.glob("ADR-*.md"))
    if not adr_files:
        console.print("No ADR files found in .opencode/docs/adrs/")
        return

    imported_count = 0
    updated_count = 0
    skipped_count = 0

    for adr_file in adr_files:
        adr_id = _parse_adr_id(str(adr_file))
        if not adr_id:
            console.print(f"[yellow]Warning: Could not parse ADR ID from {adr_file.name}[/yellow]")
            skipped_count += 1
            continue

        title = _parse_adr_title(adr_file)
        if not title:
            console.print(f"[yellow]Warning: Could not parse title from {adr_file.name}[/yellow]")
            skipped_count += 1
            continue

        status = _parse_adr_status(adr_file)
        file_path = f".opencode/docs/adrs/{adr_file.name}"

        # Check if ADR already exists
        existing_adr = manager.get_adr(adr_id)
        if existing_adr:
            # Update if changed
            if existing_adr.title != title or existing_adr.status != status:
                manager.update_adr(adr_id, title=title, status=status)
                console.print(f"  Updated {adr_id}: {title}")
                updated_count += 1
            else:
                skipped_count += 1
        else:
            # Import new ADR
            manager.create_adr(adr_id=adr_id, title=title, file_path=file_path, status=status)
            console.print(f"  Imported {adr_id}: {title}")
            imported_count += 1

    console.print(f"\n[green]✓[/green] Sync complete")
    console.print(f"  Imported: {imported_count}")
    console.print(f"  Updated: {updated_count}")
    console.print(f"  Skipped: {skipped_count}")

    logger.info(f"Synced ADRs: {imported_count} imported, {updated_count} updated, {skipped_count} skipped")
