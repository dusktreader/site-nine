from dataclasses import dataclass, field
from typing import Self

import pendulum

from site_nine.core.utils import parse_timestamp
from site_nine.missions.types import MissionStatus


@dataclass
class FileChange:
    """A file change from git history."""

    status: str
    file: str


@dataclass
class TaskSummary:
    """A task summary for mission reporting."""

    id: str
    title: str
    status: str


@dataclass
class MissionSummary:
    """Summary of a mission's activity."""

    mission: "Mission"
    files_changed: list[FileChange] = field(default_factory=list)
    commits: list[str] = field(default_factory=list)
    tasks: list[TaskSummary] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class Mission:
    """
    Mission data.

    Attributes:
        id: Mission identifier
        persona_name: Name of persona assigned to mission
        role: Role for the mission
        codename: Generated mission codename
        mission_file: Path to mission file
        start_date: Mission start date
        start_time: Mission start time
        end_time: Mission end time (None if active)
        objective: Mission objective
        status: Lifecycle status (ACTIVE, IDLE, ENDED)
        last_active_at: Timestamp of last agent activity (heartbeat)
        epic_id: Epic ID for epic-scoped missions (None if not epic-scoped)
        desk_mode_active: Whether mission is in desk mode (available for questions)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: int | None
    persona_name: str
    role: str
    codename: str
    mission_file: str
    start_date: str
    start_time: str
    end_time: str | None
    objective: str
    status: MissionStatus
    last_active_at: pendulum.DateTime | None
    epic_id: str | None
    desk_mode_active: bool
    created_at: pendulum.DateTime
    updated_at: pendulum.DateTime

    @classmethod
    def from_db_row(cls, row: dict) -> Self:
        """Create Mission from database row"""
        created_at = parse_timestamp(row["created_at"])
        updated_at = parse_timestamp(row["updated_at"])
        last_active_at = parse_timestamp(row["last_active_at"]) if row.get("last_active_at") else None

        return cls(
            id=row["id"],
            persona_name=row["persona_name"],
            role=row["role"],
            codename=row["codename"],
            mission_file=row["mission_file"],
            start_date=row["start_date"],
            start_time=row["start_time"],
            end_time=row.get("end_time"),
            objective=row["objective"],
            status=MissionStatus(row.get("status", "ACTIVE")),
            last_active_at=last_active_at,
            epic_id=row.get("epic_id"),
            desk_mode_active=bool(row.get("desk_mode_active", 0)),
            created_at=created_at,
            updated_at=updated_at,
        )
