"""Handoff management commands"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.text import Text
from typerdrive import handle_errors

from site_nine.core.database import Database
from site_nine.core.paths import get_opencode_dir
from site_nine.handoffs import HandoffManager, HandoffStatus
from site_nine.handoffs.types import HANDOFF_STATUS_DISPLAY

app = typer.Typer(help="Manage work handoffs between missions")
console = Console()


def _get_manager() -> HandoffManager:
    """Get handoff manager"""
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
    return HandoffManager(db)


@app.command()
@handle_errors("Failed to create handoff")
def create(
    task_id: str = typer.Option(..., "--task", "-t", help="Task ID being handed off"),
    from_mission: int = typer.Option(..., "--from-mission", "-f", help="Mission ID creating the handoff"),
    to_role: str = typer.Option(..., "--to-role", "-r", help="Role that should receive this handoff"),
    summary: str = typer.Option(..., "--summary", "-s", help="Brief summary of what's being handed off"),
    files: List[str] = typer.Option(None, "--file", help="Relevant file path (can specify multiple times)"),
    acceptance_criteria: str | None = typer.Option(None, "--criteria", "-c", help="What defines completion"),
    notes: str | None = typer.Option(None, "--notes", "-n", help="Additional context or instructions"),
) -> None:
    """Create a work handoff to another role"""
    manager = _get_manager()

    # Validate role
    valid_roles = [
        "Administrator",
        "Architect",
        "Builder",
        "Tester",
        "Documentarian",
        "Designer",
        "Inspector",
        "Operator",
        "Historian",
    ]
    if to_role not in valid_roles:
        console.print(f"[red]Error: Invalid role '{to_role}'. Valid roles: {', '.join(valid_roles)}[/red]")
        raise typer.Exit(1)

    # Create handoff
    handoff_id = manager.create_handoff(
        task_id=task_id,
        from_mission_id=from_mission,
        to_role=to_role,
        summary=summary,
        files=files if files else None,
        acceptance_criteria=acceptance_criteria,
        notes=notes,
    )

    console.print(f"[green]✓[/green] Created handoff #{handoff_id}")
    console.print(f"  Task: {task_id}")
    console.print(f"  To role: {to_role}")
    console.print(f"  Summary: {summary}")

    if files:
        console.print(f"  Files: {len(files)} file(s)")

    logger.info(f"Created handoff {handoff_id} for task {task_id} to {to_role}")


@app.command()
@handle_errors("Failed to list handoffs")
def list(
    role: str | None = typer.Option(None, "--role", "-r", help="Filter by target role"),
    status: str | None = typer.Option(None, "--status", "-s", help="Filter by status"),
    from_mission: int | None = typer.Option(None, "--from-mission", help="Filter by source mission"),
) -> None:
    """List handoffs"""
    manager = _get_manager()

    # Normalize status for filtering
    status_value = status.lower() if status else None

    handoffs = manager.list_handoffs(
        to_role=role,
        status=status_value,
        from_mission_id=from_mission,
    )

    if not handoffs:
        filter_msg = ""
        if role or status or from_mission:
            filter_parts = []
            if role:
                filter_parts.append(f"role={role}")
            if status:
                filter_parts.append(f"status={status}")
            if from_mission:
                filter_parts.append(f"from_mission={from_mission}")
            filter_msg = f" ({', '.join(filter_parts)})"
        console.print(f"[yellow]No handoffs found{filter_msg}.[/yellow]")
        return

    table = Table(title="Handoffs")
    table.add_column("ID", style="cyan", justify="right", width=4)
    table.add_column("Status", style="yellow", width=10)
    table.add_column("Task", style="magenta", width=12)
    table.add_column("To Role", style="blue", width=15)
    table.add_column("Summary", style="white", width=40)
    table.add_column("Created", style="dim", width=10)

    for handoff in handoffs:
        # Color-code status
        if handoff.status == HandoffStatus.COMPLETED.value:
            status_text = Text("completed", style="green")
        elif handoff.status == HandoffStatus.ACCEPTED.value:
            status_text = Text("accepted", style="blue")
        elif handoff.status == HandoffStatus.CANCELLED.value:
            status_text = Text("cancelled", style="red")
        else:
            status_text = Text("pending", style="yellow")

        # Format created_at as relative time
        from datetime import datetime

        try:
            created_dt = datetime.fromisoformat(handoff.created_at.replace("Z", "+00:00"))
            now = datetime.now(created_dt.tzinfo) if created_dt.tzinfo else datetime.now()
            delta = now - created_dt

            if delta.days > 0:
                created_str = f"{delta.days}d ago"
            elif delta.seconds >= 3600:
                created_str = f"{delta.seconds // 3600}h ago"
            elif delta.seconds >= 60:
                created_str = f"{delta.seconds // 60}m ago"
            else:
                created_str = "just now"
        except:
            created_str = handoff.created_at[:16]  # Fallback to date string

        table.add_row(
            str(handoff.id),
            status_text,
            handoff.task_id,
            handoff.to_role,
            handoff.summary[:60] + "..." if len(handoff.summary) > 60 else handoff.summary,
            created_str,
        )

    console.print(table)
    logger.debug(f"Listed {len(handoffs)} handoffs")


@app.command()
@handle_errors("Failed to show handoff")
def show(handoff_id: int = typer.Argument(..., help="Handoff ID")) -> None:
    """Show handoff details"""
    manager = _get_manager()

    handoff = manager.get_handoff(handoff_id)
    if not handoff:
        console.print(f"[red]Error: Handoff #{handoff_id} not found.[/red]")
        raise typer.Exit(1)

    # Create details display
    console.print()
    console.print(f"[bold cyan]Handoff #{handoff.id}[/bold cyan]")
    console.print()

    # Status with color
    if handoff.status == HandoffStatus.COMPLETED.value:
        status_display = "[green]✓ Completed[/green]"
    elif handoff.status == HandoffStatus.ACCEPTED.value:
        status_display = "[blue]→ Accepted[/blue]"
    elif handoff.status == HandoffStatus.CANCELLED.value:
        status_display = "[red]✗ Cancelled[/red]"
    else:
        status_display = "[yellow]⏳ Pending[/yellow]"

    console.print(f"Status:       {status_display}")
    console.print(f"Task:         {handoff.task_id}")
    console.print(f"To Role:      {handoff.to_role}")
    console.print(f"From Mission: {handoff.from_mission_id}")

    if handoff.to_mission_id:
        console.print(f"To Mission:   {handoff.to_mission_id}")

    console.print()
    console.print("[bold]Summary:[/bold]")
    console.print(handoff.summary)

    if handoff.acceptance_criteria:
        console.print()
        console.print("[bold]Acceptance Criteria:[/bold]")
        console.print(handoff.acceptance_criteria)

    if handoff.files:
        console.print()
        console.print("[bold]Relevant Files:[/bold]")
        files = json.loads(handoff.files)
        for file in files:
            console.print(f"  • {file}")

    if handoff.notes:
        console.print()
        console.print("[bold]Notes:[/bold]")
        console.print(handoff.notes)

    console.print()
    console.print(f"Created:  {handoff.created_at}")

    if handoff.accepted_at:
        console.print(f"Accepted: {handoff.accepted_at}")

    if handoff.completed_at:
        console.print(f"Completed: {handoff.completed_at}")

    console.print()

    logger.debug(f"Displayed details for handoff {handoff_id}")


@app.command()
@handle_errors("Failed to accept handoff")
def accept(
    handoff_id: int = typer.Argument(..., help="Handoff ID"),
    mission: int = typer.Option(..., "--mission", "-m", help="Mission ID accepting the handoff"),
) -> None:
    """Accept a handoff"""
    manager = _get_manager()

    # Check handoff exists and is pending
    handoff = manager.get_handoff(handoff_id)
    if not handoff:
        console.print(f"[red]Error: Handoff #{handoff_id} not found.[/red]")
        raise typer.Exit(1)

    if handoff.status != HandoffStatus.PENDING.value:
        console.print(f"[yellow]Warning: Handoff #{handoff_id} is already {handoff.status}.[/yellow]")
        return

    # Accept the handoff
    manager.accept_handoff(handoff_id, mission)

    console.print(f"[green]✓[/green] Accepted handoff #{handoff_id}")
    console.print(f"  Task: {handoff.task_id}")
    console.print(f"  Mission: {mission}")

    logger.info(f"Mission {mission} accepted handoff {handoff_id}")


@app.command()
@handle_errors("Failed to complete handoff")
def complete(
    handoff_id: int = typer.Argument(..., help="Handoff ID"),
) -> None:
    """Mark a handoff as completed"""
    manager = _get_manager()

    # Check handoff exists and is accepted
    handoff = manager.get_handoff(handoff_id)
    if not handoff:
        console.print(f"[red]Error: Handoff #{handoff_id} not found.[/red]")
        raise typer.Exit(1)

    if handoff.status != HandoffStatus.ACCEPTED.value:
        console.print(
            f"[yellow]Warning: Handoff #{handoff_id} must be accepted before it can be completed (current: {handoff.status}).[/yellow]"
        )
        return

    # Complete the handoff
    manager.complete_handoff(handoff_id)

    console.print(f"[green]✓[/green] Completed handoff #{handoff_id}")
    console.print(f"  Task: {handoff.task_id}")

    logger.info(f"Completed handoff {handoff_id}")


@app.command()
@handle_errors("Failed to cancel handoff")
def cancel(
    handoff_id: int = typer.Argument(..., help="Handoff ID"),
) -> None:
    """Cancel a handoff"""
    manager = _get_manager()

    # Check handoff exists
    handoff = manager.get_handoff(handoff_id)
    if not handoff:
        console.print(f"[red]Error: Handoff #{handoff_id} not found.[/red]")
        raise typer.Exit(1)

    if handoff.status in [HandoffStatus.COMPLETED.value, HandoffStatus.CANCELLED.value]:
        console.print(f"[yellow]Warning: Handoff #{handoff_id} is already {handoff.status}.[/yellow]")
        return

    # Cancel the handoff
    manager.cancel_handoff(handoff_id)

    console.print(f"[red]✗[/red] Cancelled handoff #{handoff_id}")
    console.print(f"  Task: {handoff.task_id}")

    logger.info(f"Cancelled handoff {handoff_id}")
