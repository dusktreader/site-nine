from dataclasses import dataclass
from typing import Self


@dataclass
class TaskDependency:
    """
    Task dependency relationship.

    Attributes:
        task_id: Task that depends on another task
        depends_on_task_id: Task that must be completed first
    """

    task_id: str
    depends_on_task_id: str

    @classmethod
    def from_db_row(cls, row: dict) -> Self:
        """Create TaskDependency from database row"""
        return cls(
            task_id=row["task_id"],
            depends_on_task_id=row["depends_on_task_id"],
        )
