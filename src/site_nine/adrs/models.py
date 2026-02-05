"""Architecture Decision Record data models"""

from dataclasses import dataclass


@dataclass
class ArchitectureDoc:
    """Architecture Decision Record (ADR) data model

    ADRs are documents that capture important architectural decisions made during development.
    They can be linked to epics and tasks to show which decisions informed which work items.
    """

    id: str  # ADR-001 format
    title: str
    status: str  # PROPOSED, ACCEPTED, REJECTED, SUPERSEDED, DEPRECATED
    file_path: str
    created_at: str
    updated_at: str
