from __future__ import annotations

from pathlib import Path
from typing import Annotated

import pendulum
import typer
from rich.table import Table
from rich.text import Text
from snick import conjoin
from typerdrive import handle_errors, terminal_message

from site_nine.cli.json_utils import format_json_response, output_json
from site_nine.cli.utils import CLIError, require_db_path
from site_nine.core.database import Database
from site_nine.exceptions import SiteNineError
from site_nine.reviews import ReviewManager, ReviewOutcome, ReviewType

app = typer.Typer(help="Manage review requests")


@app.command()
@handle_errors("Failed to create review", handle_exc_class=SiteNineError)
def create(
    title: Annotated[str, typer.Option("--title", "-t", help="Review title")],
    type: Annotated[str, typer.Option("--type", help="Review type (code, task_completion, design, general)")],
    task_id: Annotated[str | None, typer.Option("--task", help="Associated task ID")] = None,
    description: Annotated[str | None, typer.Option("--description", "-d", help="Detailed description")] = None,
    artifact: Annotated[str | None, typer.Option("--artifact", "-a", help="Path to artifact being reviewed")] = None,
    requested_by: Annotated[str | None, typer.Option("--requested-by", help="Daemon name requesting review")] = None,
) -> None:
    """Create a review request (typically used by: agents)"""
    db_path = require_db_path()

    type_lower = type.lower()
    CLIError.require_condition(
        type_lower in [rt.value for rt in ReviewType],
        f"Invalid review type '{type}'. Valid types: {', '.join(rt.value for rt in ReviewType)}",
    )

    with Database(db_path) as db:
        manager = ReviewManager(db)
        review_id = manager.create_review(
            type=type_lower,
            title=title,
            description=description,
            task_id=task_id,
            requested_by=requested_by,
            artifact_path=artifact,
        )

    body_parts = [f"Created review #{review_id}"]
    if task_id:
        body_parts.append(f"Associated with task: {task_id}")
    body_parts.append(f"Type: {ReviewType(type_lower)}")
    body_parts.append(f"Title: {title}")

    terminal_message(conjoin(*body_parts), subject="Success", subject_color="green")


@app.command()
@handle_errors("Failed to list reviews", handle_exc_class=SiteNineError)
def list(
    outcome: Annotated[
        str | None, typer.Option("--status", "-s", help="Filter by outcome (pending, approved, rejected)")
    ] = None,
    type: Annotated[str | None, typer.Option("--type", "-t", help="Filter by type")] = None,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """List reviews (typically used by: both)"""
    db_path = require_db_path()

    outcome_value = outcome.lower() if outcome else None
    type_value = type.lower() if type else None

    with Database(db_path) as db:
        manager = ReviewManager(db)
        reviews = manager.list_reviews(outcome=outcome_value, type=type_value)

    if not reviews:
        if json_output:
            output_json(format_json_response([]))
            return

        filter_msg = ""
        if outcome or type:
            filter_parts = []
            if outcome:
                filter_parts.append(f"outcome={outcome}")
            if type:
                filter_parts.append(f"type={type}")
            filter_msg = f" ({', '.join(filter_parts)})"
        terminal_message(f"No reviews found{filter_msg}.", subject="Empty", subject_color="yellow")
        return

    if json_output:
        data = []
        for review in reviews:
            review_dict = {
                "id": review.id,
                "type": review.type,
                "status": review.outcome,
                "title": review.title,
                "description": review.description,
                "task_id": review.task_id,
                "requested_by": review.requested_by,
                "reviewed_by": review.reviewed_by,
                "artifact_path": review.artifact_path,
                "outcome_reason": review.outcome_reason,
                "requested_at": review.requested_at,
                "reviewed_at": review.reviewed_at,
            }
            data.append(review_dict)

        output_json(format_json_response(data))
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
        if review.outcome == ReviewOutcome.APPROVED.value:
            status_text = Text("approved", style="green")
        elif review.outcome == ReviewOutcome.REJECTED.value:
            status_text = Text("rejected", style="red")
        else:
            status_text = Text("pending", style="yellow")

        try:
            requested_at = str(review.requested_at)
            requested_dt = pendulum.parse(requested_at)
            requested_str = requested_dt.diff_for_humans()  # type: ignore[union-attr]
        except Exception:
            requested_str = str(review.requested_at)[:16]

        artifact_display = "-"
        if review.artifact_path:
            artifact_display = Path(review.artifact_path).name

        table.add_row(
            str(review.id),
            str(ReviewType(review.type)),
            status_text,
            review.task_id or "-",
            review.title[:50] + "..." if len(review.title) > 50 else review.title,
            artifact_display,
            requested_str,
        )

    terminal_message(table, indent=False)


@app.command()
@handle_errors("Failed to show review", handle_exc_class=SiteNineError)
def show(
    review_id: Annotated[int, typer.Argument(help="Review ID")],
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Show review details (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = ReviewManager(db)
        review = CLIError.enforce_defined(manager.get_review(review_id), f"Review #{review_id} not found.")

    if json_output:
        review_dict = {
            "id": review.id,
            "type": review.type,
            "status": review.outcome,
            "title": review.title,
            "description": review.description,
            "task_id": review.task_id,
            "requested_by": review.requested_by,
            "reviewed_by": review.reviewed_by,
            "artifact_path": review.artifact_path,
            "outcome_reason": review.outcome_reason,
            "requested_at": review.requested_at,
            "reviewed_at": review.reviewed_at,
        }

        output_json(format_json_response(review_dict))
        return

    if review.outcome == ReviewOutcome.APPROVED.value:
        status_display = "Approved"
    elif review.outcome == ReviewOutcome.REJECTED.value:
        status_display = "Rejected"
    else:
        status_display = "Pending"

    body_parts = [
        f"Status:       {status_display}",
        f"Type:         {ReviewType(review.type)}",
        f"Title:        {review.title}",
    ]

    if review.task_id:
        body_parts.append(f"Task:         {review.task_id}")

    if review.description:
        body_parts.extend(["", "Description:", review.description])

    body_parts.extend(
        [
            "",
            f"Requested by: {review.requested_by or 'Unknown'}",
            f"Requested at: {review.requested_at}",
        ]
    )

    if review.reviewed_by:
        body_parts.append(f"Reviewed by:  {review.reviewed_by}")
        body_parts.append(f"Reviewed at:  {review.reviewed_at}")

    if review.outcome_reason:
        body_parts.extend(["", "Outcome Reason:", review.outcome_reason])

    if review.artifact_path:
        body_parts.extend(["", f"Artifact: {review.artifact_path}"])

    terminal_message(conjoin(*body_parts), subject=f"Review #{review.id}")


@app.command()
@handle_errors("Failed to approve review", handle_exc_class=SiteNineError)
def approve(
    review_id: Annotated[int, typer.Argument(help="Review ID")],
    reason: Annotated[str | None, typer.Option("--reason", "-r", help="Approval reason")] = None,
    reviewed_by: Annotated[str, typer.Option("--reviewed-by", help="Who is approving")] = "Director",
) -> None:
    """Approve a review (typically used by: humans)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = ReviewManager(db)
        review = CLIError.enforce_defined(manager.get_review(review_id), f"Review #{review_id} not found.")

        if review.outcome != ReviewOutcome.PENDING.value:
            terminal_message(
                f"Review #{review_id} is already {review.outcome}.",
                subject="Warning",
                subject_color="yellow",
            )
            return

        manager.approve_review(review_id, reviewed_by=reviewed_by, reason=reason)

    body_parts = [f"Approved review #{review_id}"]
    if review.task_id:
        body_parts.append(f"Task {review.task_id} is now unblocked")

    terminal_message(conjoin(*body_parts), subject="Success", subject_color="green")


@app.command()
@handle_errors("Failed to reject review", handle_exc_class=SiteNineError)
def reject(
    review_id: Annotated[int, typer.Argument(help="Review ID")],
    reason: Annotated[str, typer.Option("--reason", "-r", help="Rejection reason (required)")],
    reviewed_by: Annotated[str, typer.Option("--reviewed-by", help="Who is rejecting")] = "Director",
) -> None:
    """Reject a review (typically used by: humans)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = ReviewManager(db)
        review = CLIError.enforce_defined(manager.get_review(review_id), f"Review #{review_id} not found.")

        if review.outcome != ReviewOutcome.PENDING.value:
            terminal_message(
                f"Review #{review_id} is already {review.outcome}.",
                subject="Warning",
                subject_color="yellow",
            )
            return

        manager.reject_review(review_id, reason=reason, reviewed_by=reviewed_by)

    terminal_message(
        conjoin(f"Rejected review #{review_id}", f"Reason: {reason}"),
        subject="Rejected",
        subject_color="red",
    )


@app.command()
@handle_errors("Failed to show blocked tasks", handle_exc_class=SiteNineError)
def blocked(
    review_id: Annotated[
        int | None, typer.Option("--review-id", "-r", help="Show tasks blocked by specific review")
    ] = None,
) -> None:
    """Show tasks blocked by reviews (typically used by: both)"""
    db_path = require_db_path()

    if review_id:
        with Database(db_path) as db:
            manager = ReviewManager(db)
            blocked_task_ids = manager.get_tasks_blocked_by_review(review_id)

        if not blocked_task_ids:
            terminal_message(
                f"No tasks are currently blocked by review #{review_id}.",
                subject="Clear",
                subject_color="green",
            )
            return

        body_parts = [f"Tasks blocked by review #{review_id}:"]
        for task_id in blocked_task_ids:
            body_parts.append(f"  - {task_id}")
        body_parts.append("")
        body_parts.append(f"{len(blocked_task_ids)} task(s) blocked by review #{review_id}")

        terminal_message(conjoin(*body_parts), subject="Blocked", subject_color="yellow")
    else:
        with Database(db_path) as db:
            manager = ReviewManager(db)
            pending_reviews = manager.get_pending_reviews()

        if not pending_reviews:
            terminal_message("No pending reviews.", subject="Clear", subject_color="green")
            return

        table = Table(title="Pending Reviews")
        table.add_column("Review ID", style="magenta", justify="right")
        table.add_column("Type", style="blue")
        table.add_column("Title", style="white")
        table.add_column("Requested", style="dim")

        for review in pending_reviews:
            table.add_row(
                str(review.id),
                str(ReviewType(review.type)),
                review.title[:50] + "..." if len(review.title) > 50 else review.title,
                str(review.requested_at)[:16],
            )

        terminal_message(table, indent=False)
        terminal_message(
            conjoin(
                f"{len(pending_reviews)} pending review(s).",
                "Use 's9 review approve <review-id>' to unblock tasks.",
            ),
            subject="Summary",
            subject_color="yellow",
        )
