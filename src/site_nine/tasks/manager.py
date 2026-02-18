from pathlib import Path

from buzz import enforce_defined, require_condition

from site_nine.core.database import Database
from site_nine.core.paths import validate_path_within_project
from site_nine.core.roles import Role
from site_nine.core.utils import utc_now
from site_nine.tasks.exceptions import TaskError
from site_nine.tasks.models import Task
from site_nine.tasks.task_ids import (
    format_task_id,
    get_next_task_number,
    parse_task_id,
    validate_task_id,
)
from site_nine.tasks.types import EffectiveStatus, TaskStatus

PRIORITY_ORDER_SQL = """
    CASE priority
        WHEN 'CRITICAL' THEN 1
        WHEN 'HIGH' THEN 2
        WHEN 'MEDIUM' THEN 3
        WHEN 'LOW' THEN 4
    END
"""


class TaskManager:
    """Manages tasks"""

    def __init__(self, db: Database) -> None:
        self.db = db

    @staticmethod
    def validate_role(role: str) -> str:
        """
        Validate and normalize a role string.

        Returns the title-case role name.

        Raises:
            TaskError: If the role is invalid
        """
        try:
            return Role.from_string(role).title_case
        except ValueError:
            valid_roles_str = ", ".join(Role.all_values())
            raise TaskError(f"Invalid role: {role}. Valid values: {valid_roles_str}")

    def list_tasks(
        self,
        status: str | None = None,
        role: str | None = None,
        mission_id: int | None = None,
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

        if mission_id:
            query += " AND current_mission_id = :mission_id"
            params["mission_id"] = mission_id

        query += " ORDER BY id"

        rows = self.db.execute_query(query, params)
        tasks = [Task.from_db_row(row) for row in rows]

        from site_nine.tasks.task_ids import TASK_ID_PATTERN

        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

        def task_sort_key(task: Task) -> tuple:
            match = TASK_ID_PATTERN.match(task.id)
            if match:
                prefix, priority_code, number = match.groups()
                return (priority_order.get(task.priority, 999), prefix, int(number))
            return (priority_order.get(task.priority, 999), task.id, 0)

        return sorted(tasks, key=task_sort_key)

    def get_task(self, task_id: str) -> Task | None:
        """Get task by ID"""
        rows = self.db.execute_query("SELECT * FROM tasks WHERE id = :id", {"id": task_id})
        return Task.from_db_row(rows[0]) if rows else None

    def get_next_epic_task(self, mission_id: int) -> Task | None:
        """
        Get the next TODO task in the mission's epic matching the mission's role.

        Used by 's9 task next' command to auto-select the next task for
        epic-scoped missions.

        Args:
            mission_id: Mission ID to get next task for

        Returns:
            Next available task, or None if no tasks available

        Raises:
            TaskError: If mission has no epic_id (not epic-scoped)
        """
        # Get mission's epic and role
        mission_rows = self.db.execute_query(
            "SELECT epic_id, role FROM missions WHERE id = :mission_id",
            {"mission_id": mission_id},
        )
        require_condition(
            mission_rows,
            f"Mission {mission_id} not found",
            raise_exc_class=TaskError,
        )

        mission_epic_id = mission_rows[0]["epic_id"]
        mission_role = mission_rows[0]["role"]

        require_condition(
            mission_epic_id is not None,
            f"Mission {mission_id} is not epic-scoped. Use 's9 mission start --epic EPIC_ID' to create epic-scoped mission.",
            raise_exc_class=TaskError,
        )

        # Find next TODO task in epic matching role
        # Order by: priority (CRITICAL > HIGH > MEDIUM > LOW), then created_at
        rows = self.db.execute_query(
            f"""
            SELECT * FROM tasks
            WHERE epic_id = :epic_id
            AND role = :role
            AND status = :status
            ORDER BY {PRIORITY_ORDER_SQL}, created_at ASC
            LIMIT 1
            """,
            {
                "epic_id": mission_epic_id,
                "role": mission_role,
                "status": TaskStatus.TODO.value,
            },
        )

        return Task.from_db_row(rows[0]) if rows else None

    def claim_task(self, task_id: str, mission_id: int, current_role: str) -> None:
        """
        Claim a task for current mission.

        If there's a pending handoff for this task targeting the current role,
        it will be automatically accepted and then deleted.

        Args:
            task_id: Task to claim
            mission_id: Mission claiming the task
            current_role: Role of the current mission (for handoff validation)

        Raises:
            TaskError: If the mission is epic-scoped and the task doesn't belong to that epic
        """
        # Validate epic scoping: if mission has epic_id, task must belong to same epic
        mission_rows = self.db.execute_query(
            "SELECT epic_id FROM missions WHERE id = :mission_id",
            {"mission_id": mission_id},
        )
        require_condition(
            mission_rows,
            f"Mission {mission_id} not found",
            raise_exc_class=TaskError,
        )
        mission_epic_id = mission_rows[0]["epic_id"]

        if mission_epic_id is not None:
            task_rows = self.db.execute_query(
                "SELECT epic_id FROM tasks WHERE id = :task_id",
                {"task_id": task_id},
            )
            require_condition(
                task_rows,
                f"Task {task_id} not found",
                raise_exc_class=TaskError,
            )
            task_epic_id = task_rows[0]["epic_id"]

            require_condition(
                task_epic_id == mission_epic_id,
                f"Cannot claim task {task_id} from epic {task_epic_id} when mission is scoped to epic {mission_epic_id}",
                raise_exc_class=TaskError,
            )

        handoff_rows = self.db.execute_query(
            """
            SELECT id FROM handoffs
            WHERE task_id = :task_id
            AND to_role = :role
            AND deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
            """,
            {"task_id": task_id, "role": current_role},
        )

        if handoff_rows:
            handoff_id = handoff_rows[0]["id"]
            enforce_defined(
                self.db.execute_query(
                    """
                    UPDATE handoffs
                    SET deleted_at = :now
                    WHERE id = :handoff_id
                    RETURNING *
                    """,
                    {"handoff_id": handoff_id, "now": utc_now()},
                ),
                f"Failed to delete handoff {handoff_id}",
                raise_exc_class=TaskError,
            )

        now_str = utc_now()
        enforce_defined(
            self.db.execute_query(
                """
                UPDATE tasks
                SET current_mission_id = :mission_id,
                    claimed_at = :now,
                    status = :status,
                    updated_at = :now
                WHERE id = :task_id
                RETURNING *
                """,
                {"task_id": task_id, "mission_id": mission_id, "status": TaskStatus.UNDERWAY.value, "now": now_str},
            ),
            f"Failed to claim task {task_id}",
            raise_exc_class=TaskError,
        )

    def release_task(self, task_id: str) -> None:
        """
        Release a task back to TODO state.

        Args:
            task_id: Task to release
        """
        enforce_defined(
            self.db.execute_query(
                """
                UPDATE tasks
                SET current_mission_id = NULL,
                    claimed_at = NULL,
                    status = :status,
                    updated_at = :now
                WHERE id = :task_id
                RETURNING *
                """,
                {"task_id": task_id, "status": TaskStatus.TODO.value, "now": utc_now()},
            ),
            f"Failed to release task {task_id}",
            raise_exc_class=TaskError,
        )

    def update_status(self, task_id: str, status: str, notes: str | None = None) -> None:
        """Update task work status (TODO, UNDERWAY, COMPLETE, ABORTED)"""
        now_str = utc_now()
        update_fields = ["status = :status", "updated_at = :now"]
        params = {"task_id": task_id, "status": status, "now": now_str}

        if status in ("COMPLETE", "ABORTED"):
            update_fields.append("closed_at = :now")

        if notes:
            update_fields.append("notes = :notes")
            params["notes"] = notes

        query = f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = :task_id RETURNING *"
        enforce_defined(
            self.db.execute_query(query, params),
            f"Failed to update status for task {task_id}",
            raise_exc_class=TaskError,
        )

    def update_task(self, task_id: str, **updates) -> None:
        """
        Update task fields (title, description, priority, category).

        Args:
            task_id: Task ID
            **updates: Fields to update (title, description, priority, category)
        """
        allowed_fields = {"title", "description", "priority", "category"}
        update_fields = []
        params = {"task_id": task_id}

        for field, value in updates.items():
            require_condition(
                field in allowed_fields,
                f"Cannot update field '{field}'. Allowed: {allowed_fields}",
                raise_exc_class=TaskError,
            )
            update_fields.append(f"{field} = :{field}")
            params[field] = value

        require_condition(
            len(update_fields) > 0,
            "No fields to update",
            raise_exc_class=TaskError,
        )

        update_fields.append("updated_at = :now")
        params["now"] = utc_now()

        query = f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = :task_id RETURNING *"
        enforce_defined(
            self.db.execute_query(query, params),
            f"Failed to update task {task_id}",
            raise_exc_class=TaskError,
        )

    def create_task(
        self,
        task_id: str,
        title: str,
        role: str,
        priority: str = "MEDIUM",
        category: str | None = None,
        description: str | None = None,
        file_path: str | None = None,
    ) -> Task:
        """Create a new task"""
        try:
            validate_task_id(task_id)
        except ValueError as e:
            raise TaskError(f"Invalid task ID '{task_id}': {e}") from e

        parsed = parse_task_id(task_id)
        require_condition(parsed is not None, f"Could not parse task ID: {task_id}", raise_exc_class=TaskError)

        assert parsed is not None
        id_role, id_priority, _ = parsed
        require_condition(
            id_role == role,
            f"Task ID role '{id_role}' does not match provided role '{role}'",
            raise_exc_class=TaskError,
        )
        require_condition(
            id_priority == priority,
            f"Task ID priority '{id_priority}' does not match provided priority '{priority}'",
            raise_exc_class=TaskError,
        )

        if not file_path:
            file_path = f".opencode/work/tasks/{task_id}.md"

        now_str = utc_now()
        rows = enforce_defined(
            self.db.execute_query(
                """
                INSERT INTO tasks (
                    id, title, status, priority, role, category,
                    description, file_path,
                    created_at, updated_at
                )
                VALUES (
                    :id, :title, :status, :priority, :role, :category,
                    :description, :file_path,
                    :now, :now
                )
                RETURNING *
                """,
                {
                    "id": task_id,
                    "title": title,
                    "status": TaskStatus.TODO.value,
                    "priority": priority,
                    "role": role,
                    "category": category,
                    "description": description,
                    "file_path": file_path,
                    "now": now_str,
                },
            ),
            f"Failed to create task {task_id}",
            raise_exc_class=TaskError,
        )

        return Task.from_db_row(rows[0])

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

    def get_effective_status(self, task_id: str) -> str:
        """
        Get the effective status for a task.

        Args:
            task_id: Task ID to check

        Returns:
            Effective status string

        Raises:
            ValueError: If task not found
        """
        rows = self.db.execute_query("SELECT effective_status FROM task_status_view WHERE id = :id", {"id": task_id})

        if not rows:
            raise ValueError(f"Task {task_id} not found")

        return rows[0]["effective_status"]

    def get_all_effective_statuses(self) -> dict[str, str]:
        """
        Get effective statuses for all tasks efficiently.

        Returns:
            Dictionary mapping task_id to effective_status
        """
        rows = self.db.execute_query("SELECT * FROM task_status_view")
        return {row["id"]: row["effective_status"] for row in rows}

    def count_tasks_by_effective_status(self, role: str | None = None) -> dict[str, int]:
        """
        Count tasks grouped by effective status.

        Args:
            role: Optional role filter

        Returns:
            Dictionary mapping effective_status to count
        """
        query = """
            SELECT v.effective_status, COUNT(*) as count
            FROM task_status_view v
        """

        params = {}
        if role:
            query += " INNER JOIN tasks t ON v.id = t.id WHERE t.role = :role"
            params["role"] = role

        query += " GROUP BY v.effective_status"

        rows = self.db.execute_query(query, params)
        counts = {row["effective_status"]: row["count"] for row in rows}

        for status in EffectiveStatus:
            if status.value not in counts:
                counts[status.value] = 0

        return counts

    def generate_report(
        self,
        active_only: bool = False,
        role: str | None = None,
    ) -> list[Task]:
        """
        Generate a priority-ordered task report.

        Args:
            active_only: Exclude COMPLETE and ABORTED tasks
            role: Filter by role (validated and normalized)

        Returns:
            Tasks ordered by priority (CRITICAL first), then creation date
        """
        conditions = []
        params: dict[str, str] = {}

        if active_only:
            conditions.append("status NOT IN ('COMPLETE', 'ABORTED')")

        if role:
            normalized_role = self.validate_role(role)
            conditions.append("role = :role")
            params["role"] = normalized_role

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT * FROM tasks
            WHERE {where_clause}
            ORDER BY {PRIORITY_ORDER_SQL}, created_at ASC
        """

        rows = self.db.execute_query(query, params)
        return [Task.from_db_row(row) for row in rows]

    def search_tasks(
        self,
        keyword: str,
        active_only: bool = False,
        role: str | None = None,
    ) -> list[Task]:
        """
        Search tasks by keyword across title, description, and notes.

        Args:
            keyword: Search term (case-insensitive LIKE match)
            active_only: Exclude COMPLETE and ABORTED tasks
            role: Filter by role (validated and normalized)

        Returns:
            Matching tasks ordered by priority, then creation date (newest first)
        """
        search_term = f"%{keyword}%"
        conditions = ["(title LIKE :search OR description LIKE :search OR notes LIKE :search)"]
        params: dict[str, str | int] = {"search": search_term}

        if active_only:
            conditions.append("status NOT IN ('COMPLETE', 'ABORTED')")

        if role:
            normalized_role = self.validate_role(role)
            conditions.append("role = :role")
            params["role"] = normalized_role

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT * FROM tasks
            WHERE {where_clause}
            ORDER BY {PRIORITY_ORDER_SQL}, created_at DESC
        """

        rows = self.db.execute_query(query, params)
        return [Task.from_db_row(row) for row in rows]

    def suggest_next_tasks(
        self,
        role: str | None = None,
        count: int = 3,
    ) -> list[Task]:
        """
        Suggest TODO tasks to work on next, ordered by priority.

        Args:
            role: Filter by role (validated and normalized)
            count: Maximum number of suggestions

        Returns:
            TODO tasks ordered by priority, then creation date (oldest first)
        """
        conditions = ["status = 'TODO'"]
        params: dict[str, str | int] = {"count": count}

        if role:
            normalized_role = self.validate_role(role)
            conditions.append("role = :role")
            params["role"] = normalized_role

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT * FROM tasks
            WHERE {where_clause}
            ORDER BY {PRIORITY_ORDER_SQL}, created_at ASC
            LIMIT :count
        """

        rows = self.db.execute_query(query, params)
        return [Task.from_db_row(row) for row in rows]

    def sync_task_file(self, task: Task, opencode_dir: Path) -> None:
        """
        Synchronize a task's markdown file with current database state.

        Generates or updates the markdown file for a task, including header
        metadata and linked ADR references.

        Preserves any user-written content below the auto-generated header
        (i.e., sections starting with ``## ``).

        Args:
            task: The Task to sync
            opencode_dir: Path to the .opencode directory

        Raises:
            PathTraversalError: If the task's file_path resolves outside the project root
        """
        from site_nine.adrs import ADRManager

        # Handle file_path which may include .opencode prefix
        if task.file_path.startswith(".opencode/"):
            file_path = Path(task.file_path)
        else:
            file_path = opencode_dir / task.file_path

        # Validate path to prevent directory traversal
        file_path = validate_path_within_project(file_path)

        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Preserve user-written body content (everything below auto-generated header)
        body = ""
        if file_path.exists():
            content = file_path.read_text()
            lines = content.split("\n")
            body_start_idx = 0
            for i, line in enumerate(lines):
                if line.startswith("## "):
                    body_start_idx = i
                    break
            if body_start_idx > 0:
                body = "\n".join(lines[body_start_idx:])

        category = task.category or ""
        mission_id = str(task.current_mission_id) if task.current_mission_id else ""
        claimed_at = task.claimed_at or ""
        actual_hours = f"~{task.actual_hours} hours" if task.actual_hours else ""
        closed_at = task.closed_at or ""

        # Use the same DB connection (no second connection needed)
        adr_manager = ADRManager(self.db)
        linked_adrs = adr_manager.get_task_adrs(task.id)

        adr_section = ""
        if linked_adrs:
            adr_lines = ["\n**Related Architecture:**"]
            for adr in linked_adrs:
                adr_lines.append(f"- [{adr.id}]({adr.file_path}): {adr.title} ({adr.status})")
            adr_section = "\n".join(adr_lines)

        header = f"""# Task {task.id}: {task.title}

**Status:** {task.status}
**Priority:** {task.priority}
**Role:** {task.role}
**Category:** {category}
**Mission:** {mission_id}
**Claimed:** {claimed_at}
**Actual Time:** {actual_hours}
**Closed:** {closed_at}{adr_section}"""

        if not body:
            notes_text = task.notes or "[Progress notes, questions, blockers]"
            description_text = task.description or "[Describe what this task aims to achieve]"
            body = f"""

## Objective

{description_text}

## Problem Statement

[Describe the problem or need - explain current state, why it's problematic, impact]

## Implementation Steps

[Chronological log of work done - update as you go, document decisions]

## Files Changed

### Created
- [file path] - [description]

### Modified
- [file path] - [description]

## Testing Performed

[Document test commands, results, verification]

## Notes

{notes_text}"""

        file_path.write_text(header + "\n" + body)
