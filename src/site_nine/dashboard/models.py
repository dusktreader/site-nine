"""Dashboard data models.

These are view models for aggregated dashboard data. The dashboard has no
dedicated database table — it coordinates data from tasks, missions, and epics.
"""

from dataclasses import dataclass, field

from site_nine.epics.models import Epic
from site_nine.missions.models import Mission
from site_nine.tasks.models import Task


@dataclass
class MissionEntry:
    """A mission with its display status for the dashboard."""

    mission: Mission


@dataclass
class DashboardStats:
    """Quick stats for the full dashboard view."""

    active_missions: int
    idle_missions: int
    active_personas: int
    total_tasks: int
    in_progress: int
    completed: int
    blocked_by_reviews: int
    # Messaging stats (last 24h)
    active_conversations: int = 0
    open_discussions: int = 0
    messages_sent_24h: int = 0
    unread_messages: int = 0


@dataclass
class FullDashboardData:
    """Aggregated data for the full (unfiltered) dashboard view."""

    active_epics: list[Epic] = field(default_factory=list)
    available_tasks: list[Task] = field(default_factory=list)
    mission_entries: list[MissionEntry] = field(default_factory=list)
    stats: DashboardStats = field(
        default_factory=lambda: DashboardStats(
            active_missions=0,
            idle_missions=0,
            active_personas=0,
            total_tasks=0,
            in_progress=0,
            completed=0,
            blocked_by_reviews=0,
            active_conversations=0,
            open_discussions=0,
            messages_sent_24h=0,
            unread_messages=0,
        )
    )


@dataclass
class RoleDashboardData:
    """Aggregated data for the role-filtered dashboard view."""

    role: str
    available_tasks: list[Task] = field(default_factory=list)


@dataclass
class EpicDashboardData:
    """Aggregated data for the epic-filtered dashboard view."""

    epic: Epic
    subtasks: list[Task] = field(default_factory=list)


DashboardData = FullDashboardData | RoleDashboardData | EpicDashboardData
