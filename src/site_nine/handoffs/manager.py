"""Handoff management"""

import json

from buzz import enforce_defined

from site_nine.core.database import Database
from site_nine.core.utils import utc_now
from site_nine.handoffs.exceptions import HandoffError
from site_nine.handoffs.models import Handoff


class HandoffManager:
    """Manages ephemeral work handoffs between missions and roles"""

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
        files_json = json.dumps(files) if files else None

        result = enforce_defined(
            self.db.execute_query(
                """
                INSERT INTO handoffs (
                    task_id, from_mission_id, to_role, summary,
                    files, acceptance_criteria, notes
                )
                VALUES (
                    :task_id, :from_mission_id, :to_role, :summary,
                    :files, :acceptance_criteria, :notes
                )
                RETURNING id
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
            ),
            "Failed to create handoff",
            raise_exc_class=HandoffError,
        )
        return result[0]["id"]

    def get_handoff(self, handoff_id: int) -> Handoff | None:
        """Get handoff by ID (including soft-deleted)"""
        rows = self.db.execute_query(
            "SELECT * FROM handoffs WHERE id = :id",
            {"id": handoff_id},
        )
        return Handoff.from_db_row(rows[0]) if rows else None

    def list_handoffs(
        self,
        to_role: str | None = None,
        from_mission_id: int | None = None,
        include_deleted: bool = False,
    ) -> list[Handoff]:
        """
        List handoffs with optional filtering.

        Args:
            to_role: Filter by target role
            from_mission_id: Filter by source mission
            include_deleted: Include soft-deleted handoffs (default: False)

        Returns:
            List of handoffs ordered by created_at descending
        """
        query = "SELECT * FROM handoffs WHERE 1=1"
        params = {}

        if not include_deleted:
            query += " AND deleted_at IS NULL"

        if to_role:
            query += " AND to_role = :to_role"
            params["to_role"] = to_role

        if from_mission_id is not None:
            query += " AND from_mission_id = :from_mission_id"
            params["from_mission_id"] = from_mission_id

        query += " ORDER BY created_at DESC"

        rows = self.db.execute_query(query, params)
        return [Handoff.from_db_row(row) for row in rows]

    def delete_handoff(self, handoff_id: int) -> None:
        """
        Soft-delete a handoff (mark as deleted).

        Args:
            handoff_id: Handoff to delete
        """
        enforce_defined(
            self.db.execute_query(
                """
                UPDATE handoffs
                SET deleted_at = :now
                WHERE id = :handoff_id AND deleted_at IS NULL
                RETURNING *
                """,
                {"handoff_id": handoff_id, "now": utc_now()},
            ),
            f"Failed to delete handoff {handoff_id}",
            raise_exc_class=HandoffError,
        )

    def get_pending_handoffs_for_role(self, role: str) -> list[Handoff]:
        """Get all active (non-deleted) handoffs for a specific role"""
        return self.list_handoffs(to_role=role, include_deleted=False)
