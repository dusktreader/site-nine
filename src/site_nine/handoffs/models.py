"""Handoff data models"""

from dataclasses import dataclass


@dataclass
class Handoff:
    """Represents a work handoff between missions"""

    id: int
    task_id: str
    from_mission_id: int
    to_role: str
    to_mission_id: int | None
    status: str
    summary: str
    files: str | None
    acceptance_criteria: str | None
    notes: str | None
    created_at: str
    accepted_at: str | None
    completed_at: str | None
