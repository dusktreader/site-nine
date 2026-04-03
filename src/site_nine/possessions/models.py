from dataclasses import dataclass, field
from typing import Self

import pendulum

from site_nine.core.utils import parse_timestamp
from site_nine.possessions.types import PossessionStatus


@dataclass
class FileChange:
    """A file change from git history."""

    status: str
    file: str


@dataclass
class TaskSummary:
    """A task summary for possession reporting."""

    id: str
    title: str
    status: str


@dataclass
class PossessionSummary:
    """Summary of a possession's activity."""

    possession: "Possession"
    files_changed: list[FileChange] = field(default_factory=list)
    commits: list[str] = field(default_factory=list)
    tasks: list[TaskSummary] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class Possession:
    """
    Possession data.

    Attributes:
        id: Possession identifier
        daemon_name: Name of daemon assigned to possession
        role: Role for the possession
        possession_log: Path to possession log file
        start_time: Possession start time (ISO timestamp)
        end_time: Possession end time (None if active)
        status: Lifecycle status
        last_heartbeat_at: Timestamp of last agent heartbeat
        epic_id: Epic ID for epic-scoped possessions (None if not epic-scoped)
        desk_mode_active: Whether possession is in desk mode
        mode: Interaction mode ('interactive' or 'desk')
        opencode_session_id: Linked OpenCode session ID
        suspension_time: When possession was suspended
        suspension_reason: Why possession was suspended
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: int | None
    daemon_name: str
    role: str
    possession_log: str
    start_time: str
    end_time: str | None
    status: PossessionStatus
    last_heartbeat_at: pendulum.DateTime | None
    epic_id: str | None
    desk_mode_active: bool
    mode: str
    opencode_session_id: str | None
    suspension_time: str | None
    suspension_reason: str | None
    created_at: pendulum.DateTime
    updated_at: pendulum.DateTime

    @classmethod
    def from_db_row(cls, row: dict) -> Self:
        """Create Possession from database row"""
        created_at = parse_timestamp(row["created_at"])
        updated_at = parse_timestamp(row["updated_at"])
        last_heartbeat_at = parse_timestamp(row["last_heartbeat_at"]) if row.get("last_heartbeat_at") else None

        return cls(
            id=row["id"],
            daemon_name=row["daemon_name"],
            role=row["role"],
            possession_log=row["possession_log"],
            start_time=row["start_time"],
            end_time=row.get("end_time"),
            status=PossessionStatus(row.get("status", "ACTIVE")),
            last_heartbeat_at=last_heartbeat_at,
            epic_id=row.get("epic_id"),
            desk_mode_active=bool(row.get("desk_mode_active", 0)),
            mode=row.get("mode", "interactive"),
            opencode_session_id=row.get("opencode_session_id"),
            suspension_time=row.get("suspension_time"),
            suspension_reason=row.get("suspension_reason"),
            created_at=created_at,
            updated_at=updated_at,
        )
