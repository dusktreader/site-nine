from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class SessionInfo:
    """Information about an OpenCode session."""

    session_id: str
    title: str
    slug: str
    directory: str
    age_seconds: float
    session_file: Path | None = None

    @property
    def age_display(self) -> str:
        if self.age_seconds < 60:
            return f"{int(self.age_seconds)}s ago"
        elif self.age_seconds < 3600:
            return f"{int(self.age_seconds / 60)}m ago"
        else:
            return f"{int(self.age_seconds / 3600)}h ago"


@dataclass
class SessionDetectionResult:
    """Result of attempting to detect the current OpenCode session."""

    session_id: str | None
    method: str
    warning: str | None = None
    multiple_active: bool = False


@dataclass
class SessionUpdateResult:
    """Result of updating a session title."""

    session_id: str
    old_title: str
    new_title: str
    warning: str | None = None
