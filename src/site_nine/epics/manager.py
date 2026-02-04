"""Epic management"""

from site_nine.core.database import Database
from site_nine.epics.epic_ids import format_epic_id, get_next_epic_number, parse_epic_id, validate_epic_id
from site_nine.epics.models import Epic
from site_nine.tasks.models import Task


class EpicManager:
    """Manages epic operations"""

    def __init__(self, db: Database) -> None:
        self.db = db

    def create_epic(
        self, title: str, priority: str, description: str | None = None, epic_id: str | None = None
    ) -> Epic:
        """
        Create new epic with auto-generated or provided ID.

        Args:
            title: Epic title
            priority: Priority level (CRITICAL, HIGH, MEDIUM, LOW)
            description: Optional description
            epic_id: Optional specific epic ID (for testing/migration)

        Returns:
            Created Epic instance
        """
        # Generate ID if not provided
        if not epic_id:
            next_num = get_next_epic_number(self.db)
            epic_id = format_epic_id(priority, next_num)
        else:
            # Validate provided ID
            is_valid, error = validate_epic_id(epic_id)
            if not is_valid:
                raise ValueError(f"Invalid epic ID '{epic_id}': {error}")

            # Verify priority matches ID
            parsed = parse_epic_id(epic_id)
            if not parsed:
                raise ValueError(f"Could not parse epic ID: {epic_id}")

            id_priority, _ = parsed
            if id_priority != priority:
                raise ValueError(f"Epic ID priority '{id_priority}' does not match provided priority '{priority}'")

        file_path = f".opencode/work/epics/{epic_id}.md"

        self.db.execute_update(
            """
            INSERT INTO epics (
                id, title, description, status, priority, file_path,
                created_at, updated_at
            )
            VALUES (
                :id, :title, :description, 'TODO', :priority, :file_path,
                datetime('now'), datetime('now')
            )
            """,
            {
                "id": epic_id,
                "title": title,
                "description": description,
                "priority": priority,
                "file_path": file_path,
            },
        )

        # Retrieve and return created epic
        epic = self.get_epic(epic_id)
        if not epic:
            raise RuntimeError(f"Failed to retrieve created epic {epic_id}")
        return epic

    def get_epic(self, epic_id: str) -> Epic | None:
        """
        Get epic by ID with progress data.

        Args:
            epic_id: Epic ID

        Returns:
            Epic instance or None if not found
        """
        rows = self.db.execute_query("SELECT * FROM epics WHERE id = :id", {"id": epic_id})
        if not rows:
            return None

        epic_data = dict(rows[0])

        # Compute progress from subtasks
        progress = self._compute_progress(epic_id)
        epic_data["subtask_count"] = progress["subtask_count"]
        epic_data["completed_count"] = progress["completed_count"]

        return Epic(**epic_data)

    def list_epics(
        self,
        status: str | None = None,
        priority: str | None = None,
        include_progress: bool = True,
    ) -> list[Epic]:
        """
        List epics with optional filters.

        Args:
            status: Filter by status (TODO, UNDERWAY, COMPLETE, ABORTED)
            priority: Filter by priority (CRITICAL, HIGH, MEDIUM, LOW)
            include_progress: Include subtask progress data

        Returns:
            List of Epic instances
        """
        query = "SELECT * FROM epics WHERE 1=1"
        params = {}

        if status:
            query += " AND status = :status"
            params["status"] = status

        if priority:
            query += " AND priority = :priority"
            params["priority"] = priority

        query += " ORDER BY id"

        rows = self.db.execute_query(query, params)
        epics = []

        for row in rows:
            epic_data = dict(row)

            if include_progress:
                progress = self._compute_progress(epic_data["id"])
                epic_data["subtask_count"] = progress["subtask_count"]
                epic_data["completed_count"] = progress["completed_count"]
            else:
                epic_data["subtask_count"] = None
                epic_data["completed_count"] = None

            epics.append(Epic(**epic_data))

        return epics

    def update_epic(self, epic_id: str, **updates) -> Epic:
        """
        Update epic fields.

        Args:
            epic_id: Epic ID
            **updates: Fields to update (title, description, priority)

        Returns:
            Updated Epic instance
        """
        allowed_fields = {"title", "description", "priority"}
        update_fields = []
        params = {"epic_id": epic_id}

        for field, value in updates.items():
            if field not in allowed_fields:
                raise ValueError(f"Cannot update field '{field}'")
            update_fields.append(f"{field} = :{field}")
            params[field] = value

        if not update_fields:
            raise ValueError("No fields to update")

        update_fields.append("updated_at = datetime('now')")

        query = f"UPDATE epics SET {', '.join(update_fields)} WHERE id = :epic_id"
        self.db.execute_update(query, params)

        # Retrieve and return updated epic
        epic = self.get_epic(epic_id)
        if not epic:
            raise RuntimeError(f"Failed to retrieve updated epic {epic_id}")
        return epic

    def abort_epic(self, epic_id: str, reason: str) -> None:
        """
        Abort epic and all its subtasks.

        Args:
            epic_id: Epic ID
            reason: Reason for aborting

        Note:
            This is a destructive operation that cascades to all subtasks.
            Caller should implement double confirmation (CLI prompt + agent asks user).
        """
        # Update epic status
        self.db.execute_update(
            """
            UPDATE epics
            SET status = 'ABORTED',
                aborted_reason = :reason,
                aborted_at = datetime('now'),
                updated_at = datetime('now')
            WHERE id = :epic_id
            """,
            {"epic_id": epic_id, "reason": reason},
        )

        # Abort all subtasks
        self.db.execute_update(
            """
            UPDATE tasks
            SET status = 'ABORTED',
                closed_at = datetime('now'),
                updated_at = datetime('now'),
                agent_name = NULL,
                agent_id = NULL
            WHERE epic_id = :epic_id
            """,
            {"epic_id": epic_id},
        )

    def get_subtasks(self, epic_id: str) -> list[Task]:
        """
        Get all tasks belonging to epic.

        Args:
            epic_id: Epic ID

        Returns:
            List of Task instances
        """
        rows = self.db.execute_query(
            "SELECT * FROM tasks WHERE epic_id = :epic_id ORDER BY id",
            {"epic_id": epic_id},
        )
        return [Task(**row) for row in rows]

    def link_task(self, task_id: str, epic_id: str) -> None:
        """
        Link a task to an epic.

        Args:
            task_id: Task ID
            epic_id: Epic ID
        """
        # Verify epic exists
        epic = self.get_epic(epic_id)
        if not epic:
            raise ValueError(f"Epic {epic_id} not found")

        self.db.execute_update(
            """
            UPDATE tasks
            SET epic_id = :epic_id,
                updated_at = datetime('now')
            WHERE id = :task_id
            """,
            {"task_id": task_id, "epic_id": epic_id},
        )

    def unlink_task(self, task_id: str) -> None:
        """
        Remove task from its epic.

        Args:
            task_id: Task ID
        """
        self.db.execute_update(
            """
            UPDATE tasks
            SET epic_id = NULL,
                updated_at = datetime('now')
            WHERE id = :task_id
            """,
            {"task_id": task_id},
        )

    def _compute_progress(self, epic_id: str) -> dict:
        """
        Compute epic progress from subtasks.

        Args:
            epic_id: Epic ID

        Returns:
            Dict with subtask_count and completed_count
        """
        result = self.db.execute_query(
            """
            SELECT 
                COUNT(*) as subtask_count,
                SUM(CASE WHEN status = 'COMPLETE' THEN 1 ELSE 0 END) as completed_count
            FROM tasks
            WHERE epic_id = :epic_id
            """,
            {"epic_id": epic_id},
        )

        if result:
            return {
                "subtask_count": result[0]["subtask_count"] or 0,
                "completed_count": result[0]["completed_count"] or 0,
            }

        return {"subtask_count": 0, "completed_count": 0}
