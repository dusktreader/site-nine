from buzz import enforce_defined, require_condition

from site_nine.core.database import Database
from site_nine.dependencies.exceptions import DependencyError
from site_nine.dependencies.models import TaskDependency


class DependencyManager:
    """Manages task dependencies"""

    def __init__(self, db: Database) -> None:
        self.db = db

    def add_dependency(self, task_id: str, depends_on_task_id: str) -> TaskDependency:
        """
        Add a dependency between two tasks.

        Args:
            task_id: Task that depends on another
            depends_on_task_id: Task that must be completed first

        Returns:
            Created TaskDependency

        Raises:
            DependencyError: If task depends on itself or dependency already exists
        """
        require_condition(
            task_id != depends_on_task_id,
            f"Task cannot depend on itself: {task_id}",
            raise_exc_class=DependencyError,
        )

        existing = self.db.execute_query(
            """
            SELECT * FROM task_dependencies
            WHERE task_id = :task_id AND depends_on_task_id = :depends_on
            """,
            {"task_id": task_id, "depends_on": depends_on_task_id},
        )
        if existing:
            return TaskDependency.from_db_row(existing[0])

        rows = enforce_defined(
            self.db.execute_query(
                """
                INSERT INTO task_dependencies (task_id, depends_on_task_id)
                VALUES (:task_id, :depends_on)
                RETURNING *
                """,
                {"task_id": task_id, "depends_on": depends_on_task_id},
            ),
            f"Failed to create dependency: {task_id} -> {depends_on_task_id}",
            raise_exc_class=DependencyError,
        )

        return TaskDependency.from_db_row(rows[0])

    def remove_dependency(self, task_id: str, depends_on_task_id: str) -> None:
        """
        Remove a dependency between two tasks.

        Args:
            task_id: Task that depends on another
            depends_on_task_id: Task dependency to remove
        """
        self.db.execute_query(
            """
            DELETE FROM task_dependencies
            WHERE task_id = :task_id AND depends_on_task_id = :depends_on
            RETURNING *
            """,
            {"task_id": task_id, "depends_on": depends_on_task_id},
        )

    def get_dependencies(self, task_id: str) -> list[str]:
        """
        Get all task IDs that a task depends on.

        Args:
            task_id: Task to get dependencies for

        Returns:
            List of task IDs this task depends on
        """
        rows = self.db.execute_query(
            """
            SELECT depends_on_task_id FROM task_dependencies
            WHERE task_id = :task_id
            ORDER BY depends_on_task_id
            """,
            {"task_id": task_id},
        )
        return [row["depends_on_task_id"] for row in rows]

    def get_dependents(self, task_id: str) -> list[str]:
        """
        Get all task IDs that depend on this task.

        Args:
            task_id: Task to get dependents for

        Returns:
            List of task IDs that depend on this task
        """
        rows = self.db.execute_query(
            """
            SELECT task_id FROM task_dependencies
            WHERE depends_on_task_id = :task_id
            ORDER BY task_id
            """,
            {"task_id": task_id},
        )
        return [row["task_id"] for row in rows]

    def check_task_blocked_by_dependencies(self, task_id: str) -> list[str]:
        """
        Check if a task is blocked by incomplete dependencies.

        Args:
            task_id: Task ID to check

        Returns:
            List of incomplete task IDs this task depends on (empty if not blocked)
        """
        rows = self.db.execute_query(
            """
            SELECT td.depends_on_task_id
            FROM task_dependencies td
            INNER JOIN tasks t ON td.depends_on_task_id = t.id
            WHERE td.task_id = :task_id
            AND t.status != 'COMPLETE'
            ORDER BY td.depends_on_task_id
            """,
            {"task_id": task_id},
        )
        return [row["depends_on_task_id"] for row in rows]

    def list_all_dependencies(self) -> list[TaskDependency]:
        """
        List all task dependencies in the system.

        Returns:
            List of all task dependency relationships
        """
        rows = self.db.execute_query(
            """
            SELECT task_id, depends_on_task_id FROM task_dependencies
            ORDER BY task_id, depends_on_task_id
            """
        )
        return [TaskDependency.from_db_row(row) for row in rows]
