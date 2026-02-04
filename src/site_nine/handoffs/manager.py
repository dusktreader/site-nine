"""Handoff management"""

import json

from site_nine.core.database import Database
from site_nine.handoffs.models import Handoff
from site_nine.handoffs.types import HandoffStatus


class HandoffManager:
    """Manages work handoffs between missions and roles"""

    def __init__(self, db: Database) -> None:
        self.db = db

    def create_handoff(
        self,
        task_id: str,
        from_mission_id: int,
        to_role: str,
        summary: str,
        files: list[str] | None = None,
        acceptance_criteria: str | None = None,
        notes: str | None = None,
    ) -> int:
        """
        Create a new handoff.

        Args:
            task_id: Task being handed off
            from_mission_id: Mission creating the handoff
            to_role: Role that should receive the handoff
            summary: Brief summary of what's being handed off
            files: List of relevant file paths
            acceptance_criteria: What defines completion
            notes: Additional context or instructions

        Returns:
            Handoff ID of created handoff
        """
        # Convert files list to JSON if provided
        files_json = json.dumps(files) if files else None

        result = self.db.execute_insert(
            """
            INSERT INTO handoffs (
                task_id, from_mission_id, to_role, summary,
                files, acceptance_criteria, notes
            )
            VALUES (
                :task_id, :from_mission_id, :to_role, :summary,
                :files, :acceptance_criteria, :notes
            )
            """,
            {
                "task_id": task_id,
                "from_mission_id": from_mission_id,
                "to_role": to_role,
                "summary": summary,
                "files": files_json,
                "acceptance_criteria": acceptance_criteria,
                "notes": notes,
            },
        )
        return result

    def get_handoff(self, handoff_id: int) -> Handoff | None:
        """Get handoff by ID"""
        rows = self.db.execute_query(
            "SELECT * FROM handoffs WHERE id = :id",
            {"id": handoff_id},
        )
        return Handoff(**rows[0]) if rows else None

    def list_handoffs(
        self,
        to_role: str | None = None,
        status: HandoffStatus | str | None = None,
        from_mission_id: int | None = None,
        to_mission_id: int | None = None,
    ) -> list[Handoff]:
        """
        List handoffs with optional filtering.

        Args:
            to_role: Filter by target role
            status: Filter by status (pending, accepted, completed, cancelled)
            from_mission_id: Filter by source mission
            to_mission_id: Filter by accepting mission

        Returns:
            List of handoffs ordered by created_at descending
        """
        query = "SELECT * FROM handoffs WHERE 1=1"
        params = {}

        if to_role:
            query += " AND to_role = :to_role"
            params["to_role"] = to_role

        if status:
            # Convert enum to string if needed
            if isinstance(status, HandoffStatus):
                status = status.value
            query += " AND status = :status"
            params["status"] = status

        if from_mission_id is not None:
            query += " AND from_mission_id = :from_mission_id"
            params["from_mission_id"] = from_mission_id

        if to_mission_id is not None:
            query += " AND to_mission_id = :to_mission_id"
            params["to_mission_id"] = to_mission_id

        query += " ORDER BY created_at DESC"

        rows = self.db.execute_query(query, params)
        return [Handoff(**row) for row in rows]

    def accept_handoff(self, handoff_id: int, mission_id: int) -> None:
        """
        Accept a handoff.

        Args:
            handoff_id: Handoff to accept
            mission_id: Mission accepting the handoff
        """
        self.db.execute_update(
            """
            UPDATE handoffs
            SET status = :status,
                to_mission_id = :mission_id,
                accepted_at = datetime('now')
            WHERE id = :handoff_id AND status = 'pending'
            """,
            {
                "status": HandoffStatus.ACCEPTED.value,
                "mission_id": mission_id,
                "handoff_id": handoff_id,
            },
        )

    def complete_handoff(self, handoff_id: int) -> None:
        """
        Mark a handoff as completed.

        Args:
            handoff_id: Handoff to complete
        """
        self.db.execute_update(
            """
            UPDATE handoffs
            SET status = :status,
                completed_at = datetime('now')
            WHERE id = :handoff_id AND status = 'accepted'
            """,
            {
                "status": HandoffStatus.COMPLETED.value,
                "handoff_id": handoff_id,
            },
        )

    def cancel_handoff(self, handoff_id: int) -> None:
        """
        Cancel a handoff.

        Args:
            handoff_id: Handoff to cancel
        """
        self.db.execute_update(
            """
            UPDATE handoffs
            SET status = :status
            WHERE id = :handoff_id AND status IN ('pending', 'accepted')
            """,
            {
                "status": HandoffStatus.CANCELLED.value,
                "handoff_id": handoff_id,
            },
        )

    def get_pending_handoffs_for_role(self, role: str) -> list[Handoff]:
        """Get all pending handoffs for a specific role"""
        return self.list_handoffs(to_role=role, status=HandoffStatus.PENDING)
