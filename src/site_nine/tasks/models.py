from dataclasses import dataclass
from typing import Self

import pendulum

from site_nine.core.utils import parse_timestamp
from site_nine.tasks.types import TaskStatus


@dataclass
class Task:
    """
    Task data.

    Attributes:
        id: Task ID (format: {role_prefix}-{priority_code}-{number})
        title: Task title
        status: Work status (TODO, UNDERWAY, COMPLETE, ABORTED)
        priority: Priority level (LOW, MEDIUM, HIGH, CRITICAL)
        role: Role responsible for task
        category: Optional category
        current_mission_id: ID of mission that claimed this task
        claimed_at: Timestamp when task was claimed
        closed_at: Timestamp when task was closed
        actual_hours: Hours spent on task
        description: Task description
        notes: Task notes
        created_at: Creation timestamp
        updated_at: Last update timestamp
        file_path: Path to task file
        epic_id: ID of epic this task belongs to
    """

    id: str
    title: str
    status: TaskStatus
    priority: str
    role: str
    category: str | None
    current_mission_id: int | None
    claimed_at: pendulum.DateTime | None
    closed_at: pendulum.DateTime | None
    actual_hours: float | None
    description: str | None
    notes: str | None
    created_at: pendulum.DateTime
    updated_at: pendulum.DateTime
    file_path: str
    epic_id: str | None = None

    @staticmethod
    def _parse_status(value: str | TaskStatus) -> TaskStatus:
        """Parse status string to TaskStatus enum"""
        if isinstance(value, TaskStatus):
            return value
        return TaskStatus[value]

    @classmethod
    def from_db_row(cls, row: dict) -> Self:
        """Create Task from database row"""
        claimed_at_str = row.get("claimed_at")
        claimed_at: pendulum.DateTime | None = None
        if claimed_at_str:
            claimed_at = parse_timestamp(claimed_at_str)

        closed_at_str = row.get("closed_at")
        closed_at: pendulum.DateTime | None = None
        if closed_at_str:
            closed_at = parse_timestamp(closed_at_str)

        created_at = parse_timestamp(row["created_at"])
        updated_at = parse_timestamp(row["updated_at"])

        return cls(
            id=row["id"],
            title=row["title"],
            status=cls._parse_status(row["status"]),
            priority=row["priority"],
            role=row["role"],
            category=row["category"],
            current_mission_id=row["current_mission_id"],
            claimed_at=claimed_at,
            closed_at=closed_at,
            actual_hours=row["actual_hours"],
            description=row["description"],
            notes=row["notes"],
            created_at=created_at,
            updated_at=updated_at,
            file_path=row["file_path"],
            epic_id=row.get("epic_id"),
        )
