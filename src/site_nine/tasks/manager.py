"""Task management"""

from site_nine.core.database import Database
from site_nine.tasks.models import Task
from site_nine.tasks.task_ids import (
    format_task_id,
    get_next_task_number,
    parse_task_id,
    validate_task_id,
)


class TaskManager:
    """Manages tasks"""

    def __init__(self, db: Database) -> None:
        self.db = db

    def list_tasks(
        self,
        status: str | None = None,
        role: str | None = None,
        agent_name: str | None = None,
    ) -> list[Task]:
        """
        List tasks with optional filtering.

        Tasks are ordered by:
        1. Priority (descending): CRITICAL > HIGH > MEDIUM > LOW
        2. Role prefix (alphabetical)
        3. Sequential number
        """
        query = "SELECT * FROM tasks WHERE 1=1"
        params = {}

        if status:
            query += " AND status = :status"
            params["status"] = status

        if role:
            query += " AND role = :role"
            params["role"] = role

        if agent_name:
            query += " AND agent_name = :agent_name"
            params["agent_name"] = agent_name

        # Fetch tasks - we'll sort them in Python using task ID sorting
        query += " ORDER BY id"

        rows = self.db.execute_query(query, params)
        tasks = [Task(**row) for row in rows]

        # Sort by priority (descending), then by task ID components
        from site_nine.tasks.task_ids import PRIORITY_CODES, ROLE_PREFIXES, TASK_ID_PATTERN

        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

        def task_sort_key(task: Task) -> tuple:
            # Parse task ID for sorting
            match = TASK_ID_PATTERN.match(task.id)
            if match:
                prefix, priority_code, number = match.groups()
                return (priority_order.get(task.priority, 999), prefix, int(number))
            # Fallback for non-matching IDs (shouldn't happen with new format)
            return (priority_order.get(task.priority, 999), task.id, 0)

        return sorted(tasks, key=task_sort_key)

    def get_task(self, task_id: str) -> Task | None:
        """Get task by ID"""
        rows = self.db.execute_query("SELECT * FROM tasks WHERE id = :id", {"id": task_id})
        return Task(**rows[0]) if rows else None

    def claim_task(self, task_id: str, agent_name: str, agent_id: int | None = None) -> None:
        """Claim a task for an agent"""
        self.db.execute_update(
            """
            UPDATE tasks
            SET agent_name = :agent_name,
                agent_id = :agent_id,
                claimed_at = datetime('now'),
                status = 'UNDERWAY',
                updated_at = datetime('now')
            WHERE id = :task_id
            """,
            {"task_id": task_id, "agent_name": agent_name, "agent_id": agent_id},
        )

    def update_status(self, task_id: str, status: str, notes: str | None = None) -> None:
        """Update task status"""
        update_fields = ["status = :status", "updated_at = datetime('now')"]
        params = {"task_id": task_id, "status": status}

        # Set closed_at for terminal statuses
        if status in ("COMPLETE", "ABORTED"):
            update_fields.append("closed_at = datetime('now')")

        # Set paused_at for paused status
        if status == "PAUSED":
            update_fields.append("paused_at = datetime('now')")

        # Update notes if provided
        if notes:
            update_fields.append("notes = :notes")
            params["notes"] = notes

        query = f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = :task_id"
        self.db.execute_update(query, params)

    def create_task(
        self,
        task_id: str,
        title: str,
        role: str,
        priority: str = "MEDIUM",
        category: str | None = None,
        description: str | None = None,
        file_path: str | None = None,
    ) -> None:
        """Create a new task"""
        # Validate task ID format
        is_valid, error = validate_task_id(task_id)
        if not is_valid:
            raise ValueError(f"Invalid task ID '{task_id}': {error}")

        # Verify role and priority match task ID
        parsed = parse_task_id(task_id)
        if not parsed:
            raise ValueError(f"Could not parse task ID: {task_id}")

        id_role, id_priority, _ = parsed
        if id_role != role:
            raise ValueError(f"Task ID role '{id_role}' does not match provided role '{role}'")
        if id_priority != priority:
            raise ValueError(f"Task ID priority '{id_priority}' does not match provided priority '{priority}'")

        if not file_path:
            file_path = f".opencode/work/tasks/{task_id}.md"

        self.db.execute_update(
            """
            INSERT INTO tasks (
                id, title, status, priority, role, category,
                description, file_path,
                created_at, updated_at
            )
            VALUES (
                :id, :title, 'TODO', :priority, :role, :category,
                :description, :file_path,
                datetime('now'), datetime('now')
            )
            """,
            {
                "id": task_id,
                "title": title,
                "priority": priority,
                "role": role,
                "category": category,
                "description": description,
                "file_path": file_path,
            },
        )

    def generate_task_id(self, role: str, priority: str) -> str:
        """
        Generate next task ID for role and priority.

        Args:
            role: Role name (e.g., "Operator")
            priority: Priority level (e.g., "HIGH")

        Returns:
            Generated task ID (e.g., "OPR-H-0007")
        """
        next_num = get_next_task_number(self.db)
        return format_task_id(role, priority, next_num)
