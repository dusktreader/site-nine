"""Review management"""

from buzz import enforce_defined

from site_nine.core.database import Database
from site_nine.core.utils import utc_now
from site_nine.reviews.exceptions import ReviewError
from site_nine.reviews.models import Review
from site_nine.reviews.types import ReviewOutcome, ReviewType


class ReviewManager:
    """Manages review requests for task approval workflow"""

    def __init__(self, db: Database) -> None:
        self.db = db

    def create_review(
        self,
        type: ReviewType | str,
        title: str,
        description: str | None = None,
        task_id: str | None = None,
        requested_by: str | None = None,
        artifact_path: str | None = None,
    ) -> int:
        """
        Create a new review request.

        Args:
            type: Type of review (code, task_completion, design, general)
            title: Brief title of what's being reviewed
            description: Detailed description of review request
            task_id: Associated task ID (optional)
            requested_by: Daemon name who requested review
            artifact_path: Path to artifact being reviewed

        Returns:
            Review ID of created review
        """
        if isinstance(type, ReviewType):
            type = type.value

        result = enforce_defined(
            self.db.execute_query(
                """
                INSERT INTO reviews (
                    type, title, description, task_id, 
                    requested_by, artifact_path
                )
                VALUES (
                    :type, :title, :description, :task_id,
                    :requested_by, :artifact_path
                )
                RETURNING id
                """,
                {
                    "type": type,
                    "title": title,
                    "description": description,
                    "task_id": task_id,
                    "requested_by": requested_by,
                    "artifact_path": artifact_path,
                },
            ),
            "Failed to create review",
            raise_exc_class=ReviewError,
        )
        return result[0]["id"]

    def get_review(self, review_id: int) -> Review | None:
        """Get review by ID"""
        rows = self.db.execute_query(
            "SELECT * FROM reviews WHERE id = :id",
            {"id": review_id},
        )
        return Review.from_db_row(rows[0]) if rows else None

    def list_reviews(
        self,
        outcome: ReviewOutcome | str | None = None,
        type: ReviewType | str | None = None,
    ) -> list[Review]:
        """
        List reviews with optional filtering.

        Args:
            outcome: Filter by outcome (pending, approved, rejected)
            type: Filter by type (code, task_completion, design, general)

        Returns:
            List of reviews ordered by requested_at descending
        """
        query = "SELECT * FROM reviews WHERE 1=1"
        params = {}

        if outcome:
            if isinstance(outcome, ReviewOutcome):
                outcome = outcome.value
            query += " AND outcome = :outcome"
            params["outcome"] = outcome

        if type:
            if isinstance(type, ReviewType):
                type = type.value
            query += " AND type = :type"
            params["type"] = type

        query += " ORDER BY requested_at DESC"

        rows = self.db.execute_query(query, params)
        return [Review.from_db_row(row) for row in rows]

    def get_pending_reviews(self) -> list[Review]:
        """Get all pending reviews (for Administrator startup display)"""
        return self.list_reviews(outcome=ReviewOutcome.PENDING)

    def approve_review(
        self,
        review_id: int,
        reviewed_by: str = "Director",
        reason: str | None = None,
    ) -> None:
        """
        Approve a review and unblock any dependent tasks.

        Args:
            review_id: ID of review to approve
            reviewed_by: Who approved the review (default: Director)
            reason: Optional reason for approval
        """
        enforce_defined(
            self.db.execute_query(
                """
                UPDATE reviews
                SET outcome = :outcome,
                    reviewed_by = :reviewed_by,
                    reviewed_at = :now,
                    outcome_reason = :reason
                WHERE id = :review_id
                RETURNING *
                """,
                {
                    "review_id": review_id,
                    "outcome": ReviewOutcome.APPROVED.value,
                    "reviewed_by": reviewed_by,
                    "reason": reason,
                    "now": utc_now(),
                },
            ),
            f"Failed to approve review {review_id}",
            raise_exc_class=ReviewError,
        )

        # Note: Tasks blocked by this review will be automatically unblocked
        # because the application logic checks review outcome when claiming

    def reject_review(
        self,
        review_id: int,
        reason: str,
        reviewed_by: str = "Director",
    ) -> None:
        """
        Reject a review.

        Args:
            review_id: ID of review to reject
            reason: Reason for rejection (required)
            reviewed_by: Who rejected the review (default: Director)
        """
        enforce_defined(
            self.db.execute_query(
                """
                UPDATE reviews
                SET outcome = :outcome,
                    reviewed_by = :reviewed_by,
                    reviewed_at = :now,
                    outcome_reason = :reason
                WHERE id = :review_id
                RETURNING *
                """,
                {
                    "review_id": review_id,
                    "outcome": ReviewOutcome.REJECTED.value,
                    "reviewed_by": reviewed_by,
                    "reason": reason,
                    "now": utc_now(),
                },
            ),
            f"Failed to reject review {review_id}",
            raise_exc_class=ReviewError,
        )

    def get_tasks_blocked_by_review(self, review_id: int) -> list[str]:
        """
        Get task IDs blocked by a specific review.

        Args:
            review_id: Review ID to check

        Returns:
            List of task IDs blocked by this review
        """
        rows = self.db.execute_query(
            """
            SELECT t.id
            FROM tasks t
            INNER JOIN blocks b ON t.id = b.task_id
            WHERE b.block_type = 'review'
            AND b.description LIKE :review_ref
            AND b.resolved_at IS NULL
            ORDER BY t.id
            """,
            {"review_ref": f"%review_id={review_id}%"},
        )
        return [row["id"] for row in rows]
