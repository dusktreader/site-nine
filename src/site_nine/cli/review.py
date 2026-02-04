"""Review management commands"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table
from rich.text import Text
from typerdrive import handle_errors

from site_nine.core.database import Database
from site_nine.core.paths import get_opencode_dir
from site_nine.reviews import ReviewManager, ReviewStatus, ReviewType
from site_nine.reviews.types import REVIEW_TYPE_DISPLAY

app = typer.Typer(help="Manage review requests")
console = Console()


def _get_manager() -> ReviewManager:
    """Get review manager"""
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
    return ReviewManager(db)


@app.command()
@handle_errors("Failed to create review")
def create(
    title: str = typer.Option(..., "--title", "-t", help="Review title"),
    type: str = typer.Option(..., "--type", help="Review type (code, task_completion, design, general)"),
    task_id: str | None = typer.Option(None, "--task", help="Associated task ID"),
    description: str | None = typer.Option(None, "--description", "-d", help="Detailed description"),
    artifact: str | None = typer.Option(None, "--artifact", "-a", help="Path to artifact being reviewed"),
    requested_by: str | None = typer.Option(None, "--requested-by", help="Daemon name requesting review"),
) -> None:
    """Create a review request"""
    manager = _get_manager()

    # Validate review type
    type_lower = type.lower()
    if type_lower not in [rt.value for rt in ReviewType]:
        console.print(
            f"[red]Error: Invalid review type '{type}'. Valid types: {', '.join(rt.value for rt in ReviewType)}[/red]"
        )
        raise typer.Exit(1)

    # Create review
    review_id = manager.create_review(
        type=type_lower,
        title=title,
        description=description,
        task_id=task_id,
        requested_by=requested_by,
        artifact_path=artifact,
    )

    console.print(f"[green]✓[/green] Created review #{review_id}")

    if task_id:
        console.print(f"  Associated with task: {task_id}")

    console.print(f"  Type: {REVIEW_TYPE_DISPLAY.get(ReviewType(type_lower), type)}")
    console.print(f"  Title: {title}")

    logger.info(f"Created review {review_id}: {title}")


@app.command()
@handle_errors("Failed to list reviews")
def list(
    status: str | None = typer.Option(None, "--status", "-s", help="Filter by status (pending, approved, rejected)"),
    type: str | None = typer.Option(None, "--type", "-t", help="Filter by type"),
) -> None:
    """List reviews"""
    manager = _get_manager()

    # Normalize status and type for filtering
    status_value = status.lower() if status else None
    type_value = type.lower() if type else None

    reviews = manager.list_reviews(status=status_value, type=type_value)

    if not reviews:
        filter_msg = ""
        if status or type:
            filter_parts = []
            if status:
                filter_parts.append(f"status={status}")
            if type:
                filter_parts.append(f"type={type}")
            filter_msg = f" ({', '.join(filter_parts)})"
        console.print(f"[yellow]No reviews found{filter_msg}.[/yellow]")
        return

    table = Table(title="Reviews")
    table.add_column("ID", style="cyan", justify="right", width=4)
    table.add_column("Type", style="blue", width=18)
    table.add_column("Status", style="yellow", width=9)
    table.add_column("Task", style="magenta", width=11)
    table.add_column("Title", style="white", width=25)
    table.add_column("Artifact", style="green", width=20)
    table.add_column("Requested", style="dim", width=10)

    for review in reviews:
        # Color-code status
        if review.status == ReviewStatus.APPROVED.value:
            status_text = Text("approved", style="green")
        elif review.status == ReviewStatus.REJECTED.value:
            status_text = Text("rejected", style="red")
        else:
            status_text = Text("pending", style="yellow")

        # Format requested_at as relative time
        from datetime import datetime

        try:
            requested_dt = datetime.fromisoformat(review.requested_at.replace("Z", "+00:00"))
            now = datetime.now(requested_dt.tzinfo) if requested_dt.tzinfo else datetime.now()
            delta = now - requested_dt

            if delta.days > 0:
                requested_str = f"{delta.days}d ago"
            elif delta.seconds >= 3600:
                requested_str = f"{delta.seconds // 3600}h ago"
            elif delta.seconds >= 60:
                requested_str = f"{delta.seconds // 60}m ago"
            else:
                requested_str = "just now"
        except:
            requested_str = review.requested_at[:16]  # Fallback to date string

        # Format artifact path to show just the filename for brevity
        artifact_display = "-"
        if review.artifact_path:
            from pathlib import Path

            artifact_display = Path(review.artifact_path).name

        table.add_row(
            str(review.id),
            REVIEW_TYPE_DISPLAY.get(ReviewType(review.type), review.type),
            status_text,
            review.task_id or "-",
            review.title[:50] + "..." if len(review.title) > 50 else review.title,
            artifact_display,
            requested_str,
        )

    console.print(table)
    logger.debug(f"Listed {len(reviews)} reviews")


@app.command()
@handle_errors("Failed to show review")
def show(review_id: int = typer.Argument(..., help="Review ID")) -> None:
    """Show review details"""
    manager = _get_manager()

    review = manager.get_review(review_id)
    if not review:
        console.print(f"[red]Error: Review #{review_id} not found.[/red]")
        raise typer.Exit(1)

    # Create details display
    console.print()
    console.print(f"[bold cyan]Review #{review.id}[/bold cyan]")
    console.print()

    # Status with color
    if review.status == ReviewStatus.APPROVED.value:
        status_display = "[green]✓ Approved[/green]"
    elif review.status == ReviewStatus.REJECTED.value:
        status_display = "[red]✗ Rejected[/red]"
    else:
        status_display = "[yellow]⏳ Pending[/yellow]"

    console.print(f"Status:      {status_display}")
    console.print(f"Type:        {REVIEW_TYPE_DISPLAY.get(ReviewType(review.type), review.type)}")
    console.print(f"Title:       {review.title}")

    if review.task_id:
        console.print(f"Task:        {review.task_id}")

    if review.description:
        console.print()
        console.print("[bold]Description:[/bold]")
        console.print(review.description)

    console.print()
    console.print(f"Requested by: {review.requested_by or 'Unknown'}")
    console.print(f"Requested at: {review.requested_at}")

    if review.reviewed_by:
        console.print(f"Reviewed by:  {review.reviewed_by}")
        console.print(f"Reviewed at:  {review.reviewed_at}")

    if review.outcome_reason:
        console.print()
        console.print(f"[bold]Outcome Reason:[/bold]")
        console.print(review.outcome_reason)

    if review.artifact_path:
        console.print()
        console.print(f"Artifact: {review.artifact_path}")

    console.print()

    logger.debug(f"Displayed details for review {review_id}")


@app.command()
@handle_errors("Failed to approve review")
def approve(
    review_id: int = typer.Argument(..., help="Review ID"),
    reason: str | None = typer.Option(None, "--reason", "-r", help="Approval reason"),
    reviewed_by: str = typer.Option("Director", "--reviewed-by", help="Who is approving"),
) -> None:
    """Approve a review"""
    manager = _get_manager()

    # Check review exists and is pending
    review = manager.get_review(review_id)
    if not review:
        console.print(f"[red]Error: Review #{review_id} not found.[/red]")
        raise typer.Exit(1)

    if review.status != ReviewStatus.PENDING.value:
        console.print(f"[yellow]Warning: Review #{review_id} is already {review.status}.[/yellow]")
        return

    # Approve the review
    manager.approve_review(review_id, reviewed_by=reviewed_by, reason=reason)

    console.print(f"[green]✓[/green] Approved review #{review_id}")
    if review.task_id:
        console.print(f"  Task {review.task_id} is now unblocked")

    logger.info(f"Approved review {review_id}")


@app.command()
@handle_errors("Failed to reject review")
def reject(
    review_id: int = typer.Argument(..., help="Review ID"),
    reason: str = typer.Option(..., "--reason", "-r", help="Rejection reason (required)"),
    reviewed_by: str = typer.Option("Director", "--reviewed-by", help="Who is rejecting"),
) -> None:
    """Reject a review"""
    manager = _get_manager()

    # Check review exists and is pending
    review = manager.get_review(review_id)
    if not review:
        console.print(f"[red]Error: Review #{review_id} not found.[/red]")
        raise typer.Exit(1)

    if review.status != ReviewStatus.PENDING.value:
        console.print(f"[yellow]Warning: Review #{review_id} is already {review.status}.[/yellow]")
        return

    # Reject the review
    manager.reject_review(review_id, reason=reason, reviewed_by=reviewed_by)

    console.print(f"[red]✗[/red] Rejected review #{review_id}")
    console.print(f"  Reason: {reason}")

    logger.info(f"Rejected review {review_id}: {reason}")


@app.command()
@handle_errors("Failed to show blocked tasks")
def blocked() -> None:
    """Show tasks blocked by pending reviews"""
    manager = _get_manager()

    blocked_tasks = manager.get_blocked_tasks()

    if not blocked_tasks:
        console.print("[green]No tasks are currently blocked by reviews.[/green]")
        return

    table = Table(title="Blocked Tasks")
    table.add_column("Task ID", style="cyan")
    table.add_column("Review ID", style="magenta", justify="right")
    table.add_column("Review Type", style="blue")
    table.add_column("Review Title", style="white")

    for task_id, review in blocked_tasks:
        table.add_row(
            task_id,
            str(review.id),
            REVIEW_TYPE_DISPLAY.get(ReviewType(review.type), review.type),
            review.title[:60] + "..." if len(review.title) > 60 else review.title,
        )

    console.print(table)
    console.print()
    console.print(f"[yellow]{len(blocked_tasks)} task(s) are blocked by pending reviews.[/yellow]")
    console.print("Use [cyan]s9 review approve <review-id>[/cyan] to unblock tasks.")

    logger.debug(f"Displayed {len(blocked_tasks)} blocked tasks")
