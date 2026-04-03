"""Dashboard manager — coordinates task, possession, and epic managers to produce dashboard views."""

from datetime import timedelta

from pendulum import now

from site_nine.core.database import Database
from site_nine.dashboard.exceptions import DashboardError
from site_nine.dashboard.models import (
    DashboardData,
    DashboardStats,
    EpicDashboardData,
    FullDashboardData,
    PossessionEntry,
    RoleDashboardData,
)
from site_nine.epics import EpicManager
from site_nine.messaging import MessageManager
from site_nine.possessions import PossessionManager
from site_nine.tasks import TaskManager
from site_nine.tasks.types import EffectiveStatus

from buzz import require_condition


class DashboardManager:
    """Produces aggregated dashboard views from task, possession, and epic data."""

    def __init__(self, db: Database) -> None:
        self.db = db
        self.task_manager = TaskManager(db)
        self.possession_manager = PossessionManager(db)
        self.epic_manager = EpicManager(db)
        self.message_manager = MessageManager(db)

    def get_dashboard(
        self,
        role: str | None = None,
        epic: str | None = None,
    ) -> DashboardData:
        """
        Build the appropriate dashboard view based on the provided filters.

        Epic filter takes precedence over role filter.

        Args:
            role: Optional role filter.
            epic: Optional epic ID filter.

        Returns:
            The appropriate dashboard data variant.

        Raises:
            DashboardError: If an epic filter is provided but the epic is not found.
        """
        if epic:
            return self.get_epic_dashboard(epic)
        elif role:
            return self.get_role_dashboard(role)
        else:
            return self.get_full_dashboard()

    def get_full_dashboard(self, role: str | None = None) -> FullDashboardData:
        """
        Build the full (unfiltered) dashboard view.

        Args:
            role: Optional role filter applied to task counts.

        Returns:
            FullDashboardData with active epics, available tasks, possession statuses, and stats.
        """
        all_tasks = self.task_manager.list_tasks(role=role)
        active_possessions = self.possession_manager.list_possessions(active_only=True)
        active_epics = self.epic_manager.list_epics(status="TODO") + self.epic_manager.list_epics(status="UNDERWAY")

        effective_counts = self.task_manager.count_tasks_by_effective_status(role=role)
        blocked_by_review_count = effective_counts.get(EffectiveStatus.BLOCKED_REVIEW.value, 0)

        possession_entries = [PossessionEntry(possession=p) for p in active_possessions]

        # Available individual tasks: TODO or UNDERWAY, not linked to an epic
        available_tasks = [t for t in all_tasks if t.status in ("TODO", "UNDERWAY") and t.epic_id is None]

        stats = DashboardStats(
            active_possessions=len(active_possessions),
            active_daemons=len({p.daemon_name for p in active_possessions}),
            total_tasks=sum(effective_counts.values()),
            in_progress=effective_counts.get("UNDERWAY", 0),
            completed=effective_counts.get("COMPLETE", 0),
            blocked_by_reviews=blocked_by_review_count,
            active_conversations=self._get_active_conversations_count(),
            open_discussions=self._get_open_discussions_count(),
            messages_sent_24h=self._get_messages_sent_last_24h(),
            unread_messages=self._get_total_unread_messages(),
        )

        return FullDashboardData(
            active_epics=active_epics,
            available_tasks=available_tasks,
            possession_entries=possession_entries,
            stats=stats,
        )

    def get_role_dashboard(self, role: str) -> RoleDashboardData:
        """
        Build the role-filtered dashboard view.

        Args:
            role: Role to filter tasks by.

        Returns:
            RoleDashboardData with available tasks for the specified role.
        """
        all_tasks = self.task_manager.list_tasks(role=role)
        available_tasks = [t for t in all_tasks if t.status in ("TODO", "UNDERWAY")]
        return RoleDashboardData(role=role, available_tasks=available_tasks)

    def get_epic_dashboard(self, epic_id: str) -> EpicDashboardData:
        """
        Build the epic-filtered dashboard view.

        Args:
            epic_id: Epic ID to display.

        Returns:
            EpicDashboardData with the epic and its subtasks.

        Raises:
            DashboardError: If the epic is not found.
        """
        epic = self.epic_manager.get_epic(epic_id)
        require_condition(
            epic is not None,
            f"Epic {epic_id} not found",
            raise_exc_class=DashboardError,
        )
        assert epic is not None  # for type narrowing after require_condition

        subtasks = self.epic_manager.get_subtasks(epic_id)
        return EpicDashboardData(epic=epic, subtasks=subtasks)

    # -----------------------------------------------------------------------
    # Messaging stats helpers
    # -----------------------------------------------------------------------

    def _get_active_conversations_count(self) -> int:
        """Count open conversations (type='conversation', status='open')."""
        rows = self.db.execute_query(
            "SELECT COUNT(*) AS cnt FROM conversations WHERE type = 'conversation' AND status = 'open'"
        )
        return rows[0]["cnt"] if rows else 0

    def _get_open_discussions_count(self) -> int:
        """Count open discussions (type='discussion', status='open')."""
        rows = self.db.execute_query(
            "SELECT COUNT(*) AS cnt FROM conversations WHERE type = 'discussion' AND status = 'open'"
        )
        return rows[0]["cnt"] if rows else 0

    def _get_messages_sent_last_24h(self) -> int:
        """Count messages created in the last 24 hours."""
        cutoff = (now("UTC") - timedelta(hours=24)).to_iso8601_string()
        rows = self.db.execute_query(
            "SELECT COUNT(*) AS cnt FROM messages WHERE created_at >= :cutoff",
            {"cutoff": cutoff},
        )
        return rows[0]["cnt"] if rows else 0

    def _get_total_unread_messages(self) -> int:
        """Count total unread messages across all active possessions.

        A message is "unread" for a possession if the conversation has no view
        record for that possession, or the view's last_viewed_at is older than
        the message's created_at.
        """
        rows = self.db.execute_query(
            """
            SELECT COUNT(DISTINCT m.id || '-' || p.possession_id) AS cnt
            FROM messages m
            JOIN conversations c ON m.conversation_id = c.id
            JOIN (
                SELECT participant_1_id AS possession_id, id AS conv_id FROM conversations WHERE type = 'conversation'
                UNION
                SELECT participant_2_id AS possession_id, id AS conv_id FROM conversations WHERE type = 'conversation'
            ) p ON p.conv_id = c.id
            LEFT JOIN conversation_views cv ON cv.conversation_id = c.id AND cv.possession_id = p.possession_id
            WHERE c.status = 'open'
            AND (cv.last_viewed_at IS NULL OR m.created_at > cv.last_viewed_at)
            AND m.from_possession_id != p.possession_id
            """
        )
        return rows[0]["cnt"] if rows else 0
