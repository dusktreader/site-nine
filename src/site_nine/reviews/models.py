"""Review data models"""

from dataclasses import dataclass
from typing import Self

import pendulum

from site_nine.core.utils import parse_timestamp


@dataclass
class Review:
    """
    Review data model.

    Attributes:
        id: Review identifier
        type: Type of review (code, task_completion, design, general)
        outcome: Review outcome (pending, approved, rejected)
        task_id: Associated task ID (optional)
        title: Brief title of what's being reviewed
        description: Detailed description of review request
        requested_by: Name of who requested review
        requested_at: Request timestamp
        reviewed_by: Name of who reviewed (None if pending)
        reviewed_at: Review timestamp (None if pending)
        outcome_reason: Reason for approval/rejection
        artifact_path: Path to artifact being reviewed
    """

    id: int
    type: str
    outcome: str
    task_id: str | None
    title: str
    description: str | None
    requested_by: str | None
    requested_at: pendulum.DateTime
    reviewed_by: str | None
    reviewed_at: pendulum.DateTime | None
    outcome_reason: str | None
    artifact_path: str | None

    @classmethod
    def from_db_row(cls, row: dict) -> Self:
        """Create Review from database row"""
        requested_at = parse_timestamp(row["requested_at"])

        reviewed_at = None
        if row.get("reviewed_at"):
            reviewed_at = parse_timestamp(row["reviewed_at"])

        return cls(
            id=row["id"],
            type=row["type"],
            outcome=row["status"],
            task_id=row.get("task_id"),
            title=row["title"],
            description=row.get("description"),
            requested_by=row.get("requested_by"),
            requested_at=requested_at,
            reviewed_by=row.get("reviewed_by"),
            reviewed_at=reviewed_at,
            outcome_reason=row.get("outcome_reason"),
            artifact_path=row.get("artifact_path"),
        )
