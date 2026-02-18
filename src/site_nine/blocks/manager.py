from buzz import enforce_defined

from site_nine.blocks.exceptions import BlockError
from site_nine.blocks.models import Block
from site_nine.core.database import Database
from site_nine.core.utils import utc_now


class BlockManager:
    """Manages external blockers for tasks"""

    def __init__(self, db: Database) -> None:
        self.db = db

    def create_block(
        self,
        task_id: str,
        block_type: str,
        description: str,
    ) -> int:
        """
        Create a new external blocker for a task.

        Args:
            task_id: Task ID being blocked
            block_type: Free-text type of blocker (e.g., "external-dependency", "waiting-for-access")
            description: Description of what's blocking the task

        Returns:
            Block ID of created block
        """
        rows = enforce_defined(
            self.db.execute_query(
                """
                INSERT INTO blocks (task_id, block_type, description)
                VALUES (:task_id, :block_type, :description)
                RETURNING *
                """,
                {
                    "task_id": task_id,
                    "block_type": block_type,
                    "description": description,
                },
            ),
            f"Failed to create block for task {task_id}",
            raise_exc_class=BlockError,
        )
        created_block = Block.from_db_row(rows[0])
        return created_block.id

    def get_block(self, block_id: int) -> Block | None:
        """Get block by ID"""
        rows = self.db.execute_query(
            "SELECT * FROM blocks WHERE id = :id",
            {"id": block_id},
        )
        return Block.from_db_row(rows[0]) if rows else None

    def list_blocks(
        self,
        task_id: str | None = None,
        resolved: bool | None = None,
    ) -> list[Block]:
        """
        List blocks with optional filtering.

        Args:
            task_id: Filter by task ID
            resolved: Filter by resolution status (True=resolved, False=unresolved, None=all)

        Returns:
            List of blocks ordered by created_at descending
        """
        query = "SELECT * FROM blocks WHERE 1=1"
        params = {}

        if task_id:
            query += " AND task_id = :task_id"
            params["task_id"] = task_id

        if resolved is not None:
            if resolved:
                query += " AND resolved_at IS NOT NULL"
            else:
                query += " AND resolved_at IS NULL"

        query += " ORDER BY created_at DESC"

        rows = self.db.execute_query(query, params)
        return [Block.from_db_row(row) for row in rows]

    def get_unresolved_blocks(self, task_id: str | None = None) -> list[Block]:
        """
        Get all unresolved blocks, optionally for a specific task.

        Args:
            task_id: Optional task ID to filter by

        Returns:
            List of unresolved blocks
        """
        return self.list_blocks(task_id=task_id, resolved=False)

    def resolve_block(self, block_id: int) -> None:
        """
        Mark a block as resolved.

        Args:
            block_id: ID of block to resolve
        """
        enforce_defined(
            self.db.execute_query(
                """
                UPDATE blocks
                SET resolved_at = :now
                WHERE id = :block_id
                RETURNING *
                """,
                {"block_id": block_id, "now": utc_now()},
            ),
            f"Block {block_id} not found",
            raise_exc_class=BlockError,
        )

    def delete_block(self, block_id: int) -> None:
        """
        Delete a block (for cases where block was created in error).

        Args:
            block_id: ID of block to delete
        """
        enforce_defined(
            self.db.execute_query(
                "DELETE FROM blocks WHERE id = :block_id RETURNING *",
                {"block_id": block_id},
            ),
            f"Block {block_id} not found",
            raise_exc_class=BlockError,
        )

    def check_task_blocked(self, task_id: str) -> list[Block]:
        """
        Check if a task has any unresolved external blockers.

        Args:
            task_id: Task ID to check

        Returns:
            List of unresolved blocks for the task (empty if not blocked)
        """
        return self.get_unresolved_blocks(task_id=task_id)
