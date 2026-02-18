"""Handoff data models"""

from dataclasses import dataclass
from typing import Self

import pendulum

from site_nine.core.utils import parse_timestamp


@dataclass
class Handoff:
    """
    Represents an ephemeral work handoff between missions.

    Attributes:
        id: Handoff identifier
        task_id: Task being handed off
        from_mission_id: Source mission ID
        to_role: Target role for handoff
        summary: Brief summary of handoff
        files: JSON string of relevant file paths
        acceptance_criteria: What defines completion
        notes: Additional context or instructions
        created_at: Creation timestamp
        deleted_at: Soft delete timestamp (None if active)
    """

    id: int
    task_id: str
    from_mission_id: int
    to_role: str
    summary: str
    files: str | None
    acceptance_criteria: str | None
    notes: str | None
    created_at: pendulum.DateTime
    deleted_at: pendulum.DateTime | None

    @classmethod
    def from_db_row(cls, row: dict) -> Self:
        """Create Handoff from database row"""
        created_at = parse_timestamp(row["created_at"])

        deleted_at = None
        if row.get("deleted_at"):
            deleted_at = parse_timestamp(row["deleted_at"])

        return cls(
            id=row["id"],
            task_id=row["task_id"],
            from_mission_id=row["from_mission_id"],
            to_role=row["to_role"],
            summary=row["summary"],
            files=row.get("files"),
            acceptance_criteria=row.get("acceptance_criteria"),
            notes=row.get("notes"),
            created_at=created_at,
            deleted_at=deleted_at,
        )
