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
    agent_name: str | None
    agent_id: int | None
    claimed_at: str | None
    closed_at: str | None
    paused_at: str | None
    actual_hours: float | None
    description: str | None
    notes: str | None
    created_at: str
    updated_at: str
    file_path: str
