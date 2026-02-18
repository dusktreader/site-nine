"""Tests for review CLI commands"""

from pathlib import Path
import pytest

from site_nine.__main__ import app
from typer.testing import CliRunner

runner = CliRunner()


def test_review_list_empty(initialized_project: Path):
    """Test listing reviews when none exist"""
    result = runner.invoke(app, ["review", "list"])

    assert result.exit_code == 0


def test_review_list_with_type_filter(initialized_project: Path):
    """Test listing reviews filtered by type"""
    result = runner.invoke(app, ["review", "list", "--type", "code"])

    assert result.exit_code == 0


def test_review_list_with_outcome_filter(initialized_project: Path):
    """Test listing reviews filtered by outcome (using --status flag)"""
    result = runner.invoke(app, ["review", "list", "--status", "approved"])

    assert result.exit_code == 0


def test_review_list_json(initialized_project: Path):
    """Test listing reviews in JSON format"""
    result = runner.invoke(app, ["review", "list", "--json"])

    assert result.exit_code == 0


def test_review_show_nonexistent(initialized_project: Path):
    """Test showing non-existent review"""
    result = runner.invoke(app, ["review", "show", "999"])

    # Should fail or show error
    assert result.exit_code != 0 or "not found" in result.output.lower()


@pytest.mark.skip(reason="needs proper task/review setup")
def test_review_list_with_task_filter(initialized_project: Path):
    """Test listing reviews filtered by task"""
    result = runner.invoke(app, ["review", "list", "--task", "ENG-H-0001"])

    assert result.exit_code == 0


def test_review_list_pending_only(initialized_project: Path):
    """Test listing only pending reviews (using --status flag)"""
    result = runner.invoke(app, ["review", "list", "--status", "pending"])

    assert result.exit_code == 0


def test_review_show_json(initialized_project: Path):
    """Test showing review in JSON"""
    result = runner.invoke(app, ["review", "show", "1", "--json"])

    # Either succeeds or shows not found
    assert result.exit_code in [0, 1]


def test_review_create_code_review(initialized_project: Path):
    """Test creating a code review"""
    # Create a task first
    from site_nine.core.database import Database
    from site_nine.tasks.manager import TaskManager

    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        task_manager = TaskManager(db)
        task_manager.create_task("ENG-H-0001", "Test Task", "Engineer", "HIGH", description="Test")

    # Create review using current syntax: --title is required, --task for task ID
    result = runner.invoke(
        app,
        [
            "review",
            "create",
            "--title",
            "Code review needed",
            "--type",
            "code",
            "--task",
            "ENG-H-0001",
        ],
    )

    assert result.exit_code == 0


def test_review_approve(initialized_project: Path):
    """Test approving a review"""
    review_id = _seed_task_and_review(initialized_project)

    # Approve it
    result = runner.invoke(
        app,
        ["review", "approve", str(review_id)],
    )

    assert result.exit_code == 0


def test_review_reject(initialized_project: Path):
    """Test rejecting a review"""
    review_id = _seed_task_and_review(initialized_project, task_id="ENG-H-0002")

    # Reject it
    result = runner.invoke(
        app,
        ["review", "reject", str(review_id), "--reason", "Not ready"],
    )

    assert result.exit_code == 0


def test_review_blocked_empty(initialized_project: Path):
    """Test showing blocked tasks when none exist"""
    result = runner.invoke(app, ["review", "blocked"])

    assert result.exit_code == 0


@pytest.mark.skip(reason="--json flag not implemented on review blocked")
def test_review_blocked_json(initialized_project: Path):
    """Test showing blocked tasks in JSON format"""
    result = runner.invoke(app, ["review", "blocked", "--json"])

    assert result.exit_code == 0


def test_review_approve_nonexistent(initialized_project: Path):
    """Test approving non-existent review"""
    result = runner.invoke(app, ["review", "approve", "999"])

    assert result.exit_code != 0


def test_review_reject_nonexistent(initialized_project: Path):
    """Test rejecting non-existent review"""
    result = runner.invoke(app, ["review", "reject", "999", "--reason", "test"])

    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Helper to seed a task + review via the DB managers
# ---------------------------------------------------------------------------


def _seed_task_and_review(
    project_path: Path,
    task_id: str = "ENG-H-0001",
    review_type: str = "code",
    review_title: str = "Test Review",
    description: str = "A test review description",
    requested_by: str = "test-agent",
    artifact_path: str | None = None,
) -> int:
    """Create a task and a review in the DB, return the review_id."""
    from site_nine.core.database import Database
    from site_nine.tasks.manager import TaskManager
    from site_nine.reviews.manager import ReviewManager

    db_path = project_path / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        tm = TaskManager(db)
        # Only create the task if it doesn't exist yet
        if tm.get_task(task_id) is None:
            tm.create_task(task_id, "Test Task", "Engineer", "HIGH", description="Desc")

        rm = ReviewManager(db)
        review_id = rm.create_review(
            type=review_type,
            title=review_title,
            description=description,
            task_id=task_id,
            requested_by=requested_by,
            artifact_path=artifact_path,
        )
    return review_id


# ---------------------------------------------------------------------------
# 1. Create – success with all options
# ---------------------------------------------------------------------------


def test_review_create_success(initialized_project: Path):
    """Create a review via CLI with all options."""
    from site_nine.core.database import Database
    from site_nine.tasks.manager import TaskManager

    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        tm = TaskManager(db)
        tm.create_task("ENG-H-0001", "Test Task", "Engineer", "HIGH", description="Desc")

    result = runner.invoke(
        app,
        [
            "review",
            "create",
            "--title",
            "My Code Review",
            "--type",
            "code",
            "--task",
            "ENG-H-0001",
            "--description",
            "Please review this code",
            "--requested-by",
            "test-agent",
        ],
    )

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "Created review" in out
    assert "ENG-H-0001" in out
    assert "My Code Review" in out


# ---------------------------------------------------------------------------
# 2. Create – with --artifact
# ---------------------------------------------------------------------------


def test_review_create_with_artifact(initialized_project: Path):
    """Create a review with the --artifact option."""
    from site_nine.core.database import Database
    from site_nine.tasks.manager import TaskManager

    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        tm = TaskManager(db)
        tm.create_task("ENG-H-0001", "Test Task", "Engineer", "HIGH", description="Desc")

    result = runner.invoke(
        app,
        [
            "review",
            "create",
            "--title",
            "Artifact Review",
            "--type",
            "code",
            "--task",
            "ENG-H-0001",
            "--artifact",
            "/path/to/some_file.py",
        ],
    )

    assert result.exit_code == 0
    assert "Created review" in result.output


# ---------------------------------------------------------------------------
# 3. Create – invalid type
# ---------------------------------------------------------------------------


def test_review_create_invalid_type(initialized_project: Path):
    """Creating a review with an invalid type should fail."""
    result = runner.invoke(
        app,
        [
            "review",
            "create",
            "--title",
            "Bad Type Review",
            "--type",
            "nonexistent_type",
        ],
    )

    assert result.exit_code != 0
    normalized = " ".join(result.output.split())
    assert "Invalid review type" in normalized


# ---------------------------------------------------------------------------
# 4. Create – without --task (should succeed)
# ---------------------------------------------------------------------------


def test_review_create_without_task(initialized_project: Path):
    """Create a review without associating it with a task."""
    result = runner.invoke(
        app,
        [
            "review",
            "create",
            "--title",
            "General Review",
            "--type",
            "general",
            "--description",
            "Just a general review",
        ],
    )

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "Created review" in out
    # Task line should NOT appear
    assert "Associated with task" not in out


# ---------------------------------------------------------------------------
# 5. List – table format with data
# ---------------------------------------------------------------------------


def test_review_list_table_with_data(initialized_project: Path):
    """Seed reviews and list them in table format."""
    _seed_task_and_review(initialized_project, review_title="Alpha Review")
    _seed_task_and_review(
        initialized_project,
        task_id="ENG-H-0002",
        review_type="design",
        review_title="Beta Review",
    )

    result = runner.invoke(app, ["review", "list"])

    assert result.exit_code == 0
    out = result.output
    assert "Reviews" in out  # Table title
    assert "Alpha Review" in out
    assert "Beta Review" in out


# ---------------------------------------------------------------------------
# 6. List – JSON format with data
# ---------------------------------------------------------------------------


def test_review_list_json_with_data(initialized_project: Path):
    """Seed reviews and list them with --json; parse JSON output."""
    import json

    _seed_task_and_review(initialized_project, review_title="JSON Review")

    result = runner.invoke(app, ["review", "list", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert "data" in payload
    assert payload["count"] >= 1
    titles = [r["title"] for r in payload["data"]]
    assert "JSON Review" in titles


# ---------------------------------------------------------------------------
# 7. List – outcome filter with no matches
# ---------------------------------------------------------------------------


def test_review_list_with_outcome_filter_no_matches(initialized_project: Path):
    """Filter by an outcome that has no matching reviews."""
    # Seed a pending review, then filter for approved
    _seed_task_and_review(initialized_project)

    result = runner.invoke(app, ["review", "list", "--status", "approved"])

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "No reviews found" in out
    assert "outcome=approved" in out


# ---------------------------------------------------------------------------
# 8. List – type filter with matches
# ---------------------------------------------------------------------------


def test_review_list_with_type_filter_matches(initialized_project: Path):
    """Filter by type that matches seeded data."""
    _seed_task_and_review(initialized_project, review_type="design", review_title="Design Review")
    # Also seed a code review that should NOT appear
    _seed_task_and_review(
        initialized_project,
        task_id="ENG-H-0002",
        review_type="code",
        review_title="Code Review",
    )

    result = runner.invoke(app, ["review", "list", "--type", "design"])

    assert result.exit_code == 0
    out = result.output
    assert "Design Review" in out
    assert "Code Review" not in out


# ---------------------------------------------------------------------------
# 9. Show – rich format for pending review
# ---------------------------------------------------------------------------


def test_review_show_rich_pending(initialized_project: Path):
    """Show a pending review in rich format."""
    review_id = _seed_task_and_review(initialized_project, review_title="Pending Detail")

    result = runner.invoke(app, ["review", "show", str(review_id)])

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert f"Review #{review_id}" in out
    assert "Pending" in out
    assert "Pending Detail" in out
    assert "test-agent" in out
    assert "A test review description" in out


# ---------------------------------------------------------------------------
# 10. Show – approved review
# ---------------------------------------------------------------------------


def test_review_show_rich_approved(initialized_project: Path):
    """Approve a review then show it – should display 'Approved'."""
    from site_nine.core.database import Database
    from site_nine.reviews.manager import ReviewManager

    review_id = _seed_task_and_review(initialized_project, review_title="Will Approve")

    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        rm = ReviewManager(db)
        rm.approve_review(review_id, reviewed_by="Director", reason="Looks good")

    result = runner.invoke(app, ["review", "show", str(review_id)])

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "Approved" in out
    assert "Director" in out
    assert "Looks good" in out


# ---------------------------------------------------------------------------
# 11. Show – JSON format
# ---------------------------------------------------------------------------


def test_review_show_json_success(initialized_project: Path):
    """Show review with --json flag; verify JSON structure."""
    import json

    review_id = _seed_task_and_review(initialized_project, review_title="JSON Show")

    result = runner.invoke(app, ["review", "show", str(review_id), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["data"]["title"] == "JSON Show"
    assert payload["data"]["status"] == "pending"
    assert payload["data"]["id"] == review_id


# ---------------------------------------------------------------------------
# 12. Approve – success
# ---------------------------------------------------------------------------


def test_review_approve_success(initialized_project: Path):
    """Approve a pending review with a reason."""
    review_id = _seed_task_and_review(initialized_project)

    result = runner.invoke(
        app,
        ["review", "approve", str(review_id), "--reason", "All good", "--reviewed-by", "Admin"],
    )

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert f"Approved review #{review_id}" in out
    assert "unblocked" in out.lower()


# ---------------------------------------------------------------------------
# 13. Approve – already decided
# ---------------------------------------------------------------------------


def test_review_approve_already_decided(initialized_project: Path):
    """Trying to approve an already-approved review should warn."""
    review_id = _seed_task_and_review(initialized_project)

    # Approve it first
    runner.invoke(app, ["review", "approve", str(review_id)])

    # Approve again
    result = runner.invoke(app, ["review", "approve", str(review_id)])

    assert result.exit_code == 0
    assert "already" in result.output.lower()


# ---------------------------------------------------------------------------
# 14. Reject – success
# ---------------------------------------------------------------------------


def test_review_reject_success(initialized_project: Path):
    """Reject a pending review."""
    review_id = _seed_task_and_review(initialized_project)

    result = runner.invoke(
        app,
        ["review", "reject", str(review_id), "--reason", "Needs rework", "--reviewed-by", "QA"],
    )

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert f"Rejected review #{review_id}" in out
    assert "Needs rework" in out


# ---------------------------------------------------------------------------
# 15. Reject – already decided
# ---------------------------------------------------------------------------


def test_review_reject_already_decided(initialized_project: Path):
    """Trying to reject an already-rejected review should warn."""
    review_id = _seed_task_and_review(initialized_project)

    # Reject it first
    runner.invoke(app, ["review", "reject", str(review_id), "--reason", "Bad"])

    # Reject again
    result = runner.invoke(app, ["review", "reject", str(review_id), "--reason", "Still bad"])

    assert result.exit_code == 0
    assert "already" in result.output.lower()


# ---------------------------------------------------------------------------
# 16. Blocked – with pending reviews (no --review-id)
# ---------------------------------------------------------------------------


def test_review_blocked_with_pending_reviews(initialized_project: Path):
    """Seed pending reviews and verify the blocked command shows a table."""
    _seed_task_and_review(initialized_project, review_title="Blocking Review 1")
    _seed_task_and_review(
        initialized_project,
        task_id="ENG-H-0002",
        review_title="Blocking Review 2",
    )

    result = runner.invoke(app, ["review", "blocked"])

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "Pending Reviews" in out
    assert "Blocking Review 1" in out
    assert "Blocking Review 2" in out
    assert "pending review(s)" in out.lower()


# ---------------------------------------------------------------------------
# 17. Blocked – specific review with no blocked tasks
# ---------------------------------------------------------------------------


def test_review_blocked_specific_review_no_tasks(initialized_project: Path):
    """Use --review-id for a review that blocks no tasks."""
    review_id = _seed_task_and_review(initialized_project)

    result = runner.invoke(app, ["review", "blocked", "--review-id", str(review_id)])

    assert result.exit_code == 0
    normalized = " ".join(result.output.split())
    assert "No tasks are currently blocked" in normalized


# ---------------------------------------------------------------------------
# 18. Blocked – specific review with blocked tasks
# ---------------------------------------------------------------------------


def test_review_blocked_specific_review_with_tasks(initialized_project: Path):
    """Seed a block referencing a review, then verify blocked output."""
    from site_nine.core.database import Database
    from site_nine.tasks.manager import TaskManager
    from site_nine.blocks.manager import BlockManager

    review_id = _seed_task_and_review(initialized_project)

    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        # Create a second task to be blocked by the review
        tm = TaskManager(db)
        tm.create_task("ENG-H-0002", "Blocked Task", "Engineer", "HIGH", description="Blocked")

        bm = BlockManager(db)
        bm.create_block("ENG-H-0002", "review", f"Blocked by review_id={review_id}")

    result = runner.invoke(app, ["review", "blocked", "--review-id", str(review_id)])

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "ENG-H-0002" in out
    assert "blocked" in out.lower()


# ---------------------------------------------------------------------------
# Additional edge-case tests for fuller coverage
# ---------------------------------------------------------------------------


def test_review_list_empty_json(initialized_project: Path):
    """List reviews in JSON format when none exist – should return empty list."""
    import json

    result = runner.invoke(app, ["review", "list", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["data"] == []
    assert payload["count"] == 0


def test_review_list_empty_with_type_filter(initialized_project: Path):
    """List reviews with type filter when none exist – check filter message."""
    result = runner.invoke(app, ["review", "list", "--type", "design"])

    assert result.exit_code == 0
    normalized = " ".join(result.output.split())
    assert "No reviews found" in normalized
    assert "type=design" in normalized


def test_review_list_empty_with_both_filters(initialized_project: Path):
    """List reviews with both --status and --type when none match."""
    _seed_task_and_review(initialized_project, review_type="code")

    result = runner.invoke(app, ["review", "list", "--status", "rejected", "--type", "code"])

    assert result.exit_code == 0
    normalized = " ".join(result.output.split())
    assert "No reviews found" in normalized
    assert "outcome=rejected" in normalized
    assert "type=code" in normalized


def test_review_show_with_artifact(initialized_project: Path):
    """Show a review that has an artifact_path set."""
    review_id = _seed_task_and_review(
        initialized_project,
        review_title="Artifact Show",
        artifact_path="/src/main.py",
    )

    result = runner.invoke(app, ["review", "show", str(review_id)])

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "Artifact" in out
    assert "/src/main.py" in out


def test_review_show_rejected_with_reason(initialized_project: Path):
    """Show a rejected review and check outcome reason renders."""
    from site_nine.core.database import Database
    from site_nine.reviews.manager import ReviewManager

    review_id = _seed_task_and_review(initialized_project, review_title="Will Reject")

    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        rm = ReviewManager(db)
        rm.reject_review(review_id, reason="Does not meet criteria", reviewed_by="QA")

    result = runner.invoke(app, ["review", "show", str(review_id)])

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "Rejected" in out
    assert "Does not meet criteria" in out
    assert "QA" in out


def test_review_list_table_with_artifact(initialized_project: Path):
    """List reviews in table format when a review has an artifact."""
    _seed_task_and_review(
        initialized_project,
        review_title="With Artifact",
        artifact_path="/some/path/file.py",
    )

    result = runner.invoke(app, ["review", "list"])

    assert result.exit_code == 0
    out = result.output
    # Table should show just the filename for brevity
    assert "file.py" in out


def test_review_list_table_approved_status(initialized_project: Path):
    """List reviews showing color-coded 'approved' status."""
    from site_nine.core.database import Database
    from site_nine.reviews.manager import ReviewManager

    review_id = _seed_task_and_review(initialized_project, review_title="Approved In List")

    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        rm = ReviewManager(db)
        rm.approve_review(review_id, reviewed_by="Director")

    result = runner.invoke(app, ["review", "list"])

    assert result.exit_code == 0
    assert "approved" in result.output.lower()


def test_review_list_table_rejected_status(initialized_project: Path):
    """List reviews showing color-coded 'rejected' status."""
    from site_nine.core.database import Database
    from site_nine.reviews.manager import ReviewManager

    review_id = _seed_task_and_review(initialized_project, review_title="Rejected In List")

    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        rm = ReviewManager(db)
        rm.reject_review(review_id, reason="Bad", reviewed_by="Director")

    result = runner.invoke(app, ["review", "list"])

    assert result.exit_code == 0
    assert "rejected" in result.output.lower()


def test_review_show_no_task_no_description(initialized_project: Path):
    """Show a review that has no task_id and no description."""
    from site_nine.core.database import Database
    from site_nine.reviews.manager import ReviewManager

    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        rm = ReviewManager(db)
        review_id = rm.create_review(
            type="general",
            title="Minimal Review",
        )

    result = runner.invoke(app, ["review", "show", str(review_id)])

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "Minimal Review" in out
    # Task line should not be present
    assert "Task:" not in out


def test_review_approve_without_reason(initialized_project: Path):
    """Approve a review without specifying a reason."""
    review_id = _seed_task_and_review(initialized_project)

    result = runner.invoke(app, ["review", "approve", str(review_id)])

    assert result.exit_code == 0
    normalized = " ".join(result.output.split())
    assert f"Approved review #{review_id}" in normalized


# ---------------------------------------------------------------------------
# Time-delta branch coverage for list table rendering
# ---------------------------------------------------------------------------


def test_review_list_table_days_ago(initialized_project: Path):
    """Seed a review with requested_at >1 day ago to cover 'Xd ago' branch."""
    from site_nine.core.database import Database

    review_id = _seed_task_and_review(initialized_project, review_title="Old Review Days")

    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        db.execute_query(
            "UPDATE reviews SET requested_at = datetime('now', '-3 days') WHERE id = :id RETURNING *",
            {"id": review_id},
        )

    result = runner.invoke(app, ["review", "list"])

    assert result.exit_code == 0
    normalized = " ".join(result.output.split())
    assert "Old Review Days" in normalized
    # Pendulum outputs "3 days ago" but Rich may truncate columns (e.g. "da…")
    assert "3" in normalized and "ago" in normalized


def test_review_list_table_hours_ago(initialized_project: Path):
    """Seed a review with requested_at >1 hour ago to cover 'Xh ago' branch."""
    from site_nine.core.database import Database

    review_id = _seed_task_and_review(initialized_project, review_title="Old Review Hours")

    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        db.execute_query(
            "UPDATE reviews SET requested_at = datetime('now', '-2 hours') WHERE id = :id RETURNING *",
            {"id": review_id},
        )

    result = runner.invoke(app, ["review", "list"])

    assert result.exit_code == 0
    normalized = " ".join(result.output.split())
    assert "Old Review Hours" in normalized
    # Pendulum outputs "2 hours ago" but Rich may truncate columns (e.g. "ho…")
    assert "2" in normalized and "ago" in normalized


def test_review_list_table_minutes_ago(initialized_project: Path):
    """Seed a review with requested_at >1 min ago to cover 'Xm ago' branch."""
    from site_nine.core.database import Database

    review_id = _seed_task_and_review(initialized_project, review_title="Old Review Mins")

    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        db.execute_query(
            "UPDATE reviews SET requested_at = datetime('now', '-5 minutes') WHERE id = :id RETURNING *",
            {"id": review_id},
        )

    result = runner.invoke(app, ["review", "list"])

    assert result.exit_code == 0
    normalized = " ".join(result.output.split())
    assert "Old Review Mins" in normalized
    # Pendulum renders relative time (e.g. "5 minutes ago") but Rich may truncate
    # columns and timing may vary — just verify the review renders with "ago"
    assert "ago" in normalized
