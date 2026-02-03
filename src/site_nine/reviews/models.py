"""Review data models"""

from dataclasses import dataclass


@dataclass
class Review:
    """Review data model"""

    id: int
    type: str
    status: str
    task_id: str | None
    title: str
    description: str | None
    requested_by: str | None
    requested_at: str
    reviewed_by: str | None
    reviewed_at: str | None
    outcome_reason: str | None
    artifact_path: str | None
