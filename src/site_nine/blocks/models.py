from dataclasses import dataclass
from typing import Any, Self

import pendulum

from site_nine.core.utils import parse_timestamp


@dataclass
class Block:
    """
    External blocker data model

    Attributes:
        id: Block identifier
        task_id: Associated task ID
        block_type: Free text describing the type (e.g., "external-dependency", "waiting-for-access")
        description: Detailed description of the blocker
        created_at: Timestamp when the block was created
        resolved_at: Timestamp when the block was resolved, or None if still active
    """

    id: int
    task_id: str
    block_type: str
    description: str
    created_at: pendulum.DateTime
    resolved_at: pendulum.DateTime | None

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> Self:
        """
        Create Block from database row dictionary.

        Args:
            row: Database row dictionary

        Returns:
            Block instance with parsed timestamps
        """
        created_at_str = row["created_at"]
        resolved_at_str = row.get("resolved_at")

        created_at = parse_timestamp(created_at_str)

        resolved_at: pendulum.DateTime | None = None
        if resolved_at_str:
            resolved_at = parse_timestamp(resolved_at_str)

        return cls(
            id=int(row["id"]),
            task_id=str(row["task_id"]),
            block_type=str(row["block_type"]),
            description=str(row["description"]),
            created_at=created_at,
            resolved_at=resolved_at,
        )
