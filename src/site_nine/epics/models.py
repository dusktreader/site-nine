"""Epic data models"""

from dataclasses import dataclass


@dataclass
class Epic:
    """Epic data model

    Epics are organizational containers for grouping related tasks under larger initiatives.
    Epic status is auto-computed from subtask states via database triggers.
    """

    id: str  # EPC-H-0001 format
    title: str
    description: str | None
    status: str  # TODO, UNDERWAY, COMPLETE, ABORTED (computed from subtasks)
    priority: str  # CRITICAL, HIGH, MEDIUM, LOW
    aborted_reason: str | None
    created_at: str
    updated_at: str
    completed_at: str | None
    aborted_at: str | None
    file_path: str

    # Computed properties (not stored in DB, populated by manager queries)
    subtask_count: int | None = None
    completed_count: int | None = None

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

    @property
    def is_closed(self) -> bool:
        """Check if epic is closed"""
        return self.status in ("COMPLETE", "ABORTED")
