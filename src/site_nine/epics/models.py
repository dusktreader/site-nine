from dataclasses import dataclass
from typing import Self

import pendulum

from site_nine.core.utils import parse_timestamp


@dataclass
class Epic:
    """
    Epic data model.

    Epics are organizational containers for grouping related tasks under larger initiatives.
    Epic status is computed from subtask states (not stored in DB).

    Attributes:
        id: Epic ID in EPC-H-0001 format
        title: Epic title
        description: Optional detailed description
        status_details: Free-form notes about epic progress/status
        priority: Priority level (CRITICAL, HIGH, MEDIUM, LOW)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        file_path: Path to epic file
        status: Computed status from subtasks (TODO, UNDERWAY, COMPLETE, ABORTED)
        subtask_count: Number of subtasks
        completed_count: Number of completed subtasks
    """

    id: str
    title: str
    description: str | None
    status_details: str | None
    priority: str
    created_at: pendulum.DateTime
    updated_at: pendulum.DateTime
    file_path: str
    status: str | None = None
    subtask_count: int | None = None
    completed_count: int | None = None

    @classmethod
    def from_db_row(cls, row: dict) -> Self:
        """Create Epic from database row"""
        created_at = parse_timestamp(row["created_at"])
        updated_at = parse_timestamp(row["updated_at"])

        return cls(
            id=row["id"],
            title=row["title"],
            description=row.get("description"),
            status_details=row.get("status_details"),
            priority=row["priority"],
            created_at=created_at,
            updated_at=updated_at,
            file_path=row["file_path"],
            status=row.get("status"),
            subtask_count=row.get("subtask_count"),
            completed_count=row.get("completed_count"),
        )

    @property
    def progress_percent(self) -> int:
        """Calculate completion percentage from subtask counts"""
        if not self.subtask_count or self.subtask_count == 0:
            return 0
        if not self.completed_count:
            return 0
        return int((self.completed_count / self.subtask_count) * 100)

    @property
    def is_active(self) -> bool:
        """Check if epic has active work"""
        return self.status in ("TODO", "UNDERWAY")
