"""DataLoader — async thin wrapper over existing synchronous managers.

Executes DB calls in a thread pool via asyncio.to_thread() to keep the TUI
event loop responsive while SQLite operations run on a background thread.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from site_nine.adrs import ADRManager
from site_nine.adrs.models import ArchitectureDoc
from site_nine.core.database import Database
from site_nine.dashboard import DashboardManager
from site_nine.dashboard.models import FullDashboardData
from site_nine.messaging import MessageManager
from site_nine.messaging.models import Conversation, Message
from site_nine.missions import MissionManager
from site_nine.missions.models import Mission
from site_nine.missions.types import MissionStatus
from site_nine.tasks import TaskManager
from site_nine.tasks.models import Task


class DataLoader:
    """
    Async thin wrapper over existing synchronous managers.

    All public methods are async and use asyncio.to_thread() to execute
    synchronous DB operations without blocking the Textual event loop.

    Instantiate once per SiteNineApp and pass to screens as needed.
    """

    def __init__(self, db: Database) -> None:
        self._db = db
        self._task_manager = TaskManager(db)
        self._mission_manager = MissionManager(db)
        self._message_manager = MessageManager(db)
        self._adr_manager = ADRManager(db)
        self._dashboard_manager = DashboardManager(db)

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    async def load_tasks(
        self,
        role: str | None = None,
        status: str | None = None,
        epic_id: str | None = None,
        active_only: bool = False,
    ) -> list[Task]:
        """Load tasks with optional filtering. Returns priority-sorted list."""

        def _load() -> list[Task]:
            tasks = self._task_manager.list_tasks(status=status, role=role)
            if epic_id:
                tasks = [t for t in tasks if t.epic_id == epic_id]
            if active_only:
                tasks = [t for t in tasks if t.status.value not in ("COMPLETE", "ABORTED")]
            return tasks

        return await asyncio.to_thread(_load)

    async def load_task(self, task_id: str) -> Task | None:
        """Load a single task by ID."""
        return await asyncio.to_thread(self._task_manager.get_task, task_id)

    # ------------------------------------------------------------------
    # Missions
    # ------------------------------------------------------------------

    async def load_missions(self, active_only: bool = True) -> list[Mission]:
        """Load missions. If active_only=True, returns ACTIVE and IDLE missions only."""

        def _load() -> list[Mission]:
            missions = self._mission_manager.list_missions()
            if active_only:
                active_statuses = {MissionStatus.ACTIVE, MissionStatus.IDLE}
                missions = [m for m in missions if m.status in active_statuses]
            return missions

        return await asyncio.to_thread(_load)

    async def load_ended_missions(self) -> list[Mission]:
        """Load ended (historical) missions."""

        def _load() -> list[Mission]:
            missions = self._mission_manager.list_missions()
            return [m for m in missions if m.status == MissionStatus.ENDED]

        return await asyncio.to_thread(_load)

    async def load_mission(self, mission_id: int) -> Mission | None:
        """Load a single mission by ID."""
        return await asyncio.to_thread(self._mission_manager.get_mission, mission_id)

    # ------------------------------------------------------------------
    # Messages / Conversations
    # ------------------------------------------------------------------

    async def load_conversations(self, mission_id: int | None = None) -> list[Conversation]:
        """
        Load conversations. If mission_id is provided, loads conversations
        where that mission is a participant.
        """

        def _load() -> list[Conversation]:
            if mission_id is not None:
                return self._message_manager.list_conversations(mission_id=mission_id)
            return self._message_manager.list_conversations()

        return await asyncio.to_thread(_load)

    async def load_messages(self, conversation_id: str) -> list[Message]:
        """Load all messages in a conversation, chronologically ordered."""
        return await asyncio.to_thread(
            self._message_manager.list_messages,
            conversation_id=conversation_id,
        )

    # ------------------------------------------------------------------
    # ADRs
    # ------------------------------------------------------------------

    async def load_adrs(self) -> list[ArchitectureDoc]:
        """Load all Architecture Decision Records."""
        return await asyncio.to_thread(self._adr_manager.list_adrs)

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    async def load_dashboard(self) -> FullDashboardData:
        """Load aggregated full dashboard data."""

        def _load() -> FullDashboardData:
            data = self._dashboard_manager.get_dashboard()
            # get_dashboard() returns DashboardData union — we want FullDashboardData
            if isinstance(data, FullDashboardData):
                return data
            # Fallback: return empty dashboard
            return FullDashboardData()

        return await asyncio.to_thread(_load)

    # ------------------------------------------------------------------
    # File content
    # ------------------------------------------------------------------

    async def load_file_content(self, path: Path | str) -> str:
        """
        Read a file's text content asynchronously.

        Returns empty string if the file does not exist or cannot be read.
        """

        def _read() -> str:
            p = Path(path)
            if not p.exists():
                return f"*File not found: {path}*"
            try:
                return p.read_text(encoding="utf-8")
            except Exception as exc:
                return f"*Error reading file: {exc}*"

        return await asyncio.to_thread(_read)
