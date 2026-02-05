"""Architecture Decision Record management"""

from site_nine.adrs.models import ArchitectureDoc
from site_nine.core.database import Database


class ADRManager:
    """Manages Architecture Decision Records (ADRs)"""

    def __init__(self, db: Database) -> None:
        self.db = db

    def create_adr(self, adr_id: str, title: str, file_path: str, status: str = "PROPOSED") -> ArchitectureDoc:
        """
        Create new ADR.

        Args:
            adr_id: ADR identifier (e.g., 'ADR-001')
            title: ADR title
            file_path: Path to markdown file
            status: ADR status (default: PROPOSED)

        Returns:
            Created ArchitectureDoc instance
        """
        self.db.execute_update(
            """
            INSERT INTO architecture_docs (id, title, status, file_path, created_at, updated_at)
            VALUES (:id, :title, :status, :file_path, datetime('now'), datetime('now'))
            """,
            {"id": adr_id, "title": title, "status": status, "file_path": file_path},
        )

        adr = self.get_adr(adr_id)
        if not adr:
            raise RuntimeError(f"Failed to retrieve created ADR {adr_id}")
        return adr

    def get_adr(self, adr_id: str) -> ArchitectureDoc | None:
        """
        Get ADR by ID.

        Args:
            adr_id: ADR identifier

        Returns:
            ArchitectureDoc instance or None if not found
        """
        rows = self.db.execute_query("SELECT * FROM architecture_docs WHERE id = :id", {"id": adr_id})
        if not rows:
            return None
        return ArchitectureDoc(**rows[0])

    def list_adrs(self, status: str | None = None) -> list[ArchitectureDoc]:
        """
        List ADRs with optional status filter.

        Args:
            status: Filter by status (PROPOSED, ACCEPTED, REJECTED, SUPERSEDED, DEPRECATED)

        Returns:
            List of ArchitectureDoc instances
        """
        query = "SELECT * FROM architecture_docs WHERE 1=1"
        params = {}

        if status:
            query += " AND status = :status"
            params["status"] = status

        query += " ORDER BY id"

        rows = self.db.execute_query(query, params)
        return [ArchitectureDoc(**row) for row in rows]

    def update_adr(self, adr_id: str, **updates) -> ArchitectureDoc:
        """
        Update ADR fields.

        Args:
            adr_id: ADR identifier
            **updates: Fields to update (title, status, file_path)

        Returns:
            Updated ArchitectureDoc instance
        """
        allowed_fields = {"title", "status", "file_path"}
        update_fields = []
        params = {"adr_id": adr_id}

        for field, value in updates.items():
            if field not in allowed_fields:
                raise ValueError(f"Cannot update field '{field}'")
            update_fields.append(f"{field} = :{field}")
            params[field] = value

        if not update_fields:
            raise ValueError("No fields to update")

        update_fields.append("updated_at = datetime('now')")

        query = f"UPDATE architecture_docs SET {', '.join(update_fields)} WHERE id = :adr_id"
        self.db.execute_update(query, params)

        adr = self.get_adr(adr_id)
        if not adr:
            raise RuntimeError(f"Failed to retrieve updated ADR {adr_id}")
        return adr

    def link_to_epic(self, adr_id: str, epic_id: str) -> None:
        """
        Link an ADR to an epic.

        Args:
            adr_id: ADR identifier
            epic_id: Epic ID
        """
        # Verify ADR exists
        adr = self.get_adr(adr_id)
        if not adr:
            raise ValueError(f"ADR {adr_id} not found")

        # Create link (ignore if already exists)
        self.db.execute_update(
            """
            INSERT OR IGNORE INTO epic_architecture_docs (epic_id, adr_id, created_at)
            VALUES (:epic_id, :adr_id, datetime('now'))
            """,
            {"epic_id": epic_id, "adr_id": adr_id},
        )

    def unlink_from_epic(self, adr_id: str, epic_id: str) -> None:
        """
        Unlink an ADR from an epic.

        Args:
            adr_id: ADR identifier
            epic_id: Epic ID
        """
        self.db.execute_update(
            "DELETE FROM epic_architecture_docs WHERE epic_id = :epic_id AND adr_id = :adr_id",
            {"epic_id": epic_id, "adr_id": adr_id},
        )

    def get_epic_adrs(self, epic_id: str) -> list[ArchitectureDoc]:
        """
        Get all ADRs linked to an epic.

        Args:
            epic_id: Epic ID

        Returns:
            List of ArchitectureDoc instances
        """
        rows = self.db.execute_query(
            """
            SELECT a.* FROM architecture_docs a
            JOIN epic_architecture_docs ea ON a.id = ea.adr_id
            WHERE ea.epic_id = :epic_id
            ORDER BY a.id
            """,
            {"epic_id": epic_id},
        )
        return [ArchitectureDoc(**row) for row in rows]

    def link_to_task(self, adr_id: str, task_id: str) -> None:
        """
        Link an ADR to a task.

        Args:
            adr_id: ADR identifier
            task_id: Task ID
        """
        # Verify ADR exists
        adr = self.get_adr(adr_id)
        if not adr:
            raise ValueError(f"ADR {adr_id} not found")

        # Create link (ignore if already exists)
        self.db.execute_update(
            """
            INSERT OR IGNORE INTO task_architecture_docs (task_id, adr_id, created_at)
            VALUES (:task_id, :adr_id, datetime('now'))
            """,
            {"task_id": task_id, "adr_id": adr_id},
        )

    def unlink_from_task(self, adr_id: str, task_id: str) -> None:
        """
        Unlink an ADR from a task.

        Args:
            adr_id: ADR identifier
            task_id: Task ID
        """
        self.db.execute_update(
            "DELETE FROM task_architecture_docs WHERE task_id = :task_id AND adr_id = :adr_id",
            {"task_id": task_id, "adr_id": adr_id},
        )

    def get_task_adrs(self, task_id: str) -> list[ArchitectureDoc]:
        """
        Get all ADRs linked to a task.

        Args:
            task_id: Task ID

        Returns:
            List of ArchitectureDoc instances
        """
        rows = self.db.execute_query(
            """
            SELECT a.* FROM architecture_docs a
            JOIN task_architecture_docs ta ON a.id = ta.adr_id
            WHERE ta.task_id = :task_id
            ORDER BY a.id
            """,
            {"task_id": task_id},
        )
        return [ArchitectureDoc(**row) for row in rows]

    def get_adr_epics(self, adr_id: str) -> list[str]:
        """
        Get all epic IDs linked to an ADR.

        Args:
            adr_id: ADR identifier

        Returns:
            List of epic IDs
        """
        rows = self.db.execute_query(
            "SELECT epic_id FROM epic_architecture_docs WHERE adr_id = :adr_id ORDER BY epic_id",
            {"adr_id": adr_id},
        )
        return [row["epic_id"] for row in rows]

    def get_adr_tasks(self, adr_id: str) -> list[str]:
        """
        Get all task IDs linked to an ADR.

        Args:
            adr_id: ADR identifier

        Returns:
            List of task IDs
        """
        rows = self.db.execute_query(
            "SELECT task_id FROM task_architecture_docs WHERE adr_id = :adr_id ORDER BY task_id",
            {"adr_id": adr_id},
        )
        return [row["task_id"] for row in rows]
