"""Review management"""

from site_nine.core.database import Database
from site_nine.reviews.models import Review
from site_nine.reviews.types import ReviewStatus, ReviewType


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
        # Convert enum to string if needed
        if isinstance(type, ReviewType):
            type = type.value

        result = self.db.execute_insert(
            """
            INSERT INTO reviews (
                type, title, description, task_id, 
                requested_by, artifact_path
            )
            VALUES (
                :type, :title, :description, :task_id,
                :requested_by, :artifact_path
            )
            """,
            {
                "type": type,
                "title": title,
                "description": description,
                "task_id": task_id,
                "requested_by": requested_by,
                "artifact_path": artifact_path,
            },
        )
        return result

    def get_review(self, review_id: int) -> Review | None:
        """Get review by ID"""
        rows = self.db.execute_query(
            "SELECT * FROM reviews WHERE id = :id",
            {"id": review_id},
        )
        return Review(**rows[0]) if rows else None

    def list_reviews(
        self,
        status: ReviewStatus | str | None = None,
        type: ReviewType | str | None = None,
    ) -> list[Review]:
        """
        List reviews with optional filtering.

        Args:
            status: Filter by status (pending, approved, rejected)
            type: Filter by type (code, task_completion, design, general)

        Returns:
            List of reviews ordered by requested_at descending
        """
        query = "SELECT * FROM reviews WHERE 1=1"
        params = {}

        if status:
            # Convert enum to string if needed
            if isinstance(status, ReviewStatus):
                status = status.value
            query += " AND status = :status"
            params["status"] = status

        if type:
            # Convert enum to string if needed
            if isinstance(type, ReviewType):
                type = type.value
            query += " AND type = :type"
            params["type"] = type

        query += " ORDER BY requested_at DESC"

        rows = self.db.execute_query(query, params)
        return [Review(**row) for row in rows]

    def get_pending_reviews(self) -> list[Review]:
        """Get all pending reviews (for Administrator startup display)"""
        return self.list_reviews(status=ReviewStatus.PENDING)

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
        self.db.execute_update(
            """
            UPDATE reviews
            SET status = :status,
                reviewed_by = :reviewed_by,
                reviewed_at = datetime('now'),
                outcome_reason = :reason
            WHERE id = :review_id
            """,
            {
                "review_id": review_id,
                "status": ReviewStatus.APPROVED.value,
                "reviewed_by": reviewed_by,
                "reason": reason,
            },
        )

        # Note: Tasks blocked by this review will be automatically unblocked
        # because the application logic checks review status when claiming

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
        self.db.execute_update(
            """
            UPDATE reviews
            SET status = :status,
                reviewed_by = :reviewed_by,
                reviewed_at = datetime('now'),
                outcome_reason = :reason
            WHERE id = :review_id
            """,
            {
                "review_id": review_id,
                "status": ReviewStatus.REJECTED.value,
                "reviewed_by": reviewed_by,
                "reason": reason,
            },
        )

    def get_blocked_tasks(self) -> list[tuple[str, Review]]:
        """
        Get tasks blocked by pending reviews.

        Returns:
            List of tuples (task_id, blocking_review)
        """
        rows = self.db.execute_query(
            """
            SELECT t.id as blocked_task_id, r.*
            FROM tasks t
            INNER JOIN reviews r ON t.blocks_on_review_id = r.id
            WHERE r.status = :status
            ORDER BY r.requested_at DESC
            """,
            {"status": ReviewStatus.PENDING.value},
        )

        result = []
        for row in rows:
            # Extract blocked_task_id and create Review object from remaining columns
            blocked_task_id = row["blocked_task_id"]
            review_data = {k: v for k, v in row.items() if k != "blocked_task_id"}
            review = Review(**review_data)
            result.append((blocked_task_id, review))

        return result

    def check_task_blocked(self, task_id: str) -> Review | None:
        """
        Check if a task is blocked by a pending review.

        Args:
            task_id: Task ID to check

        Returns:
            The blocking Review if task is blocked, None otherwise
        """
        rows = self.db.execute_query(
            """
            SELECT r.*
            FROM tasks t
            INNER JOIN reviews r ON t.blocks_on_review_id = r.id
            WHERE t.id = :task_id AND r.status = :status
            """,
            {"task_id": task_id, "status": ReviewStatus.PENDING.value},
        )

        return Review(**rows[0]) if rows else None

    def block_task_on_review(self, task_id: str, review_id: int) -> None:
        """
        Block a task until a review is approved.

        Args:
            task_id: Task ID to block
            review_id: Review that must be approved first
        """
        self.db.execute_update(
            """
            UPDATE tasks
            SET blocks_on_review_id = :review_id,
                updated_at = datetime('now')
            WHERE id = :task_id
            """,
            {"task_id": task_id, "review_id": review_id},
        )

    def unblock_task(self, task_id: str) -> None:
        """
        Remove review blocking from a task.

        Args:
            task_id: Task ID to unblock
        """
        self.db.execute_update(
            """
            UPDATE tasks
            SET blocks_on_review_id = NULL,
                updated_at = datetime('now')
            WHERE id = :task_id
            """,
            {"task_id": task_id},
        )
