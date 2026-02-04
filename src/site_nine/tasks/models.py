"""Task data models"""

from dataclasses import dataclass


@dataclass
class Task:
    """Task data"""

    id: str
    title: str
    status: str
    priority: str
    role: str
    category: str | None
    current_mission_id: int | None
    claimed_at: str | None
    closed_at: str | None
    paused_at: str | None
    actual_hours: float | None
    description: str | None
    notes: str | None
    created_at: str
    updated_at: str
    file_path: str
    epic_id: str | None = None  # Epic this task belongs to (or None if standalone)
    blocks_on_review_id: int | None = None  # Review that must be approved before task can be claimed
