"""Epic management"""

from pathlib import Path

import pendulum
from buzz import enforce_defined, require_condition

from site_nine.core.database import Database
from site_nine.core.paths import validate_path_within_project
from site_nine.core.utils import utc_now
from site_nine.epics.computed_status import compute_epic_status, get_all_epic_statuses
from site_nine.epics.epic_ids import format_epic_id, get_next_epic_number, parse_epic_id, validate_epic_id
from site_nine.epics.exceptions import EpicError
from site_nine.epics.models import Epic
from site_nine.epics.utils import generate_progress_bar
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
            require_condition(
                is_valid,
                f"Invalid epic ID '{epic_id}': {error}",
                raise_exc_class=EpicError,
            )

            # Verify priority matches ID
            parsed = parse_epic_id(epic_id)
            require_condition(
                parsed is not None,
                f"Could not parse epic ID: {epic_id}",
                raise_exc_class=EpicError,
            )

            id_priority, _ = parsed
            require_condition(
                id_priority == priority,
                f"Epic ID priority '{id_priority}' does not match provided priority '{priority}'",
                raise_exc_class=EpicError,
            )

        file_path = f".opencode/work/epics/{epic_id}.md"

        now_str = utc_now()
        rows = enforce_defined(
            self.db.execute_query(
                """
                INSERT INTO epics (
                    id, title, description, priority, status, file_path,
                    created_at, updated_at
                )
                VALUES (
                    :id, :title, :description, :priority, :status, :file_path,
                    :now, :now
                )
                RETURNING *
                """,
                {
                    "id": epic_id,
                    "title": title,
                    "description": description,
                    "priority": priority,
                    "status": "TODO",
                    "file_path": file_path,
                    "now": now_str,
                },
            ),
            f"Failed to create epic {epic_id}",
            raise_exc_class=EpicError,
        )

        epic_data = dict(rows[0])

        # Compute status from subtasks
        epic_data["status"] = compute_epic_status(self.db, epic_id)

        # Compute progress from subtasks
        progress = self._compute_progress(epic_id)
        epic_data["subtask_count"] = progress["subtask_count"]
        epic_data["completed_count"] = progress["completed_count"]

        return Epic.from_db_row(epic_data)

    def get_epic(self, epic_id: str) -> Epic | None:
        """
        Get epic by ID with computed status and progress data.

        Args:
            epic_id: Epic ID

        Returns:
            Epic instance or None if not found
        """
        rows = self.db.execute_query("SELECT * FROM epics WHERE id = :id", {"id": epic_id})
        if not rows:
            return None

        epic_data = dict(rows[0])

        # Compute status from subtasks
        epic_data["status"] = compute_epic_status(self.db, epic_id)

        # Compute progress from subtasks
        progress = self._compute_progress(epic_id)
        epic_data["subtask_count"] = progress["subtask_count"]
        epic_data["completed_count"] = progress["completed_count"]

        return Epic.from_db_row(epic_data)

    def list_epics(
        self,
        status: str | None = None,
        priority: str | None = None,
        include_progress: bool = True,
    ) -> list[Epic]:
        """
        List epics with optional filters.

        Args:
            status: Filter by computed status (TODO, UNDERWAY, COMPLETE, ABORTED)
            priority: Filter by priority (CRITICAL, HIGH, MEDIUM, LOW)
            include_progress: Include subtask progress data

        Returns:
            List of Epic instances
        """
        query = "SELECT * FROM epics WHERE 1=1"
        params = {}

        if priority:
            query += " AND priority = :priority"
            params["priority"] = priority

        query += " ORDER BY id"

        rows = self.db.execute_query(query, params)

        # Get all epic statuses efficiently
        all_statuses = get_all_epic_statuses(self.db)

        epics = []

        for row in rows:
            epic_data = dict(row)
            epic_id = epic_data["id"]

            # Add computed status
            epic_data["status"] = all_statuses.get(epic_id, "TODO")

            # Filter by status if requested
            if status and epic_data["status"] != status:
                continue

            if include_progress:
                progress = self._compute_progress(epic_id)
                epic_data["subtask_count"] = progress["subtask_count"]
                epic_data["completed_count"] = progress["completed_count"]
            else:
                epic_data["subtask_count"] = None
                epic_data["completed_count"] = None

            epics.append(Epic.from_db_row(epic_data))

        return epics

    def update_epic(self, epic_id: str, **updates) -> Epic:
        """
        Update epic fields.

        Args:
            epic_id: Epic ID
            **updates: Fields to update (title, description, priority, status_details)

        Returns:
            Updated Epic instance
        """
        allowed_fields = {"title", "description", "priority", "status_details"}
        update_fields = []
        params = {"epic_id": epic_id}

        for field, value in updates.items():
            require_condition(
                field in allowed_fields,
                f"Cannot update field '{field}'",
                raise_exc_class=EpicError,
            )
            update_fields.append(f"{field} = :{field}")
            params[field] = value

        require_condition(
            len(update_fields) > 0,
            "No fields to update",
            raise_exc_class=EpicError,
        )

        update_fields.append("updated_at = :now")
        params["now"] = utc_now()

        query = f"UPDATE epics SET {', '.join(update_fields)} WHERE id = :epic_id RETURNING *"
        rows = enforce_defined(
            self.db.execute_query(query, params),
            f"Failed to update epic {epic_id}",
            raise_exc_class=EpicError,
        )

        epic_data = dict(rows[0])

        # Compute status from subtasks
        epic_data["status"] = compute_epic_status(self.db, epic_id)

        # Compute progress from subtasks
        progress = self._compute_progress(epic_id)
        epic_data["subtask_count"] = progress["subtask_count"]
        epic_data["completed_count"] = progress["completed_count"]

        return Epic.from_db_row(epic_data)

    def abort_epic(self, epic_id: str, reason: str) -> None:
        """
        Abort epic by aborting all its non-terminal subtasks.

        Args:
            epic_id: Epic ID
            reason: Reason for aborting

        Note:
            This is a destructive operation that cascades to all subtasks.
            Caller should implement double confirmation (CLI prompt + agent asks user).
            Epic status will automatically become ABORTED after tasks are aborted.
        """
        # Update epic status_details with abort reason
        abort_note = f"Aborted on {pendulum.now('UTC').format('YYYY-MM-DD')}: {reason}"
        now_str = utc_now()
        enforce_defined(
            self.db.execute_query(
                """
                UPDATE epics
                SET status_details = :status_details,
                    updated_at = :now
                WHERE id = :epic_id
                RETURNING *
                """,
                {"epic_id": epic_id, "status_details": abort_note, "now": now_str},
            ),
            f"Failed to abort epic {epic_id}",
            raise_exc_class=EpicError,
        )

        # Abort all non-terminal subtasks (TODO, UNDERWAY)
        self.db.execute_query(
            """
            UPDATE tasks
            SET status = 'ABORTED',
                notes = COALESCE(notes || '\n\n', '') || :abort_note,
                closed_at = :now,
                updated_at = :now,
                current_mission_id = NULL
            WHERE epic_id = :epic_id
              AND status NOT IN ('COMPLETE', 'ABORTED')
            RETURNING *
            """,
            {"epic_id": epic_id, "abort_note": f"Aborted due to epic cancellation: {reason}", "now": now_str},
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
        return [Task.from_db_row(row) for row in rows]

    def link_task(self, task_id: str, epic_id: str) -> None:
        """
        Link a task to an epic.

        Args:
            task_id: Task ID
            epic_id: Epic ID
        """
        # Verify epic exists
        epic = self.get_epic(epic_id)
        require_condition(
            epic is not None,
            f"Epic {epic_id} not found",
            raise_exc_class=EpicError,
        )

        enforce_defined(
            self.db.execute_query(
                """
                UPDATE tasks
                SET epic_id = :epic_id,
                    updated_at = :now
                WHERE id = :task_id
                RETURNING *
                """,
                {"task_id": task_id, "epic_id": epic_id, "now": utc_now()},
            ),
            f"Failed to link task {task_id} to epic {epic_id}",
            raise_exc_class=EpicError,
        )

    def unlink_task(self, task_id: str) -> None:
        """
        Remove task from its epic.

        Args:
            task_id: Task ID
        """
        enforce_defined(
            self.db.execute_query(
                """
                UPDATE tasks
                SET epic_id = NULL,
                    updated_at = :now
                WHERE id = :task_id
                RETURNING *
                """,
                {"task_id": task_id, "now": utc_now()},
            ),
            f"Failed to unlink task {task_id}",
            raise_exc_class=EpicError,
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

    def sync_epic_file(self, epic: Epic, opencode_dir: Path) -> None:
        """
        Synchronize an epic's markdown file with current database state.

        Generates or updates the markdown file for an epic, including header
        metadata, progress bar, subtask table, and linked ADR table.

        Preserves any user-written content below the auto-generated header
        (i.e., sections starting with ``## ``).

        Args:
            epic: The Epic to sync
            opencode_dir: Path to the .opencode directory

        Raises:
            PathTraversalError: If the epic's file_path resolves outside the project root
        """
        from site_nine.adrs import ADRManager

        if epic.file_path.startswith(".opencode/"):
            file_path = Path(epic.file_path)
        else:
            file_path = opencode_dir / epic.file_path

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

        status_emoji = {
            "TODO": "\U0001f4cb",
            "UNDERWAY": "\U0001f6a7",
            "COMPLETE": "\u2705",
            "ABORTED": "\u274c",
        }.get(epic.status or "TODO", "\U0001f4cb")

        header_parts = [
            f"# Epic {epic.id}: {epic.title}",
            "",
            f"**Status:** {status_emoji} {epic.status or 'UNKNOWN'}",
            f"**Priority:** {epic.priority}",
            f"**Created:** {epic.created_at}",
            f"**Updated:** {epic.updated_at}",
        ]

        if epic.status_details:
            header_parts.append(f"**Status Notes:** {epic.status_details}")

        if epic.subtask_count and epic.subtask_count > 0:
            progress_bar = generate_progress_bar(epic.progress_percent)
            header_parts.extend(
                [
                    "",
                    "## Progress",
                    "",
                    f"**Tasks:** {epic.completed_count}/{epic.subtask_count} complete ({epic.progress_percent}%)",
                    f"{progress_bar}",
                ]
            )

        subtasks = self.get_subtasks(epic.id)
        if subtasks:
            header_parts.extend(["", "## Subtasks", ""])

            table_lines = [
                "| Task ID | Title | Status | Role | Priority |",
                "|---------|-------|--------|------|----------|",
            ]

            for task in subtasks:
                status_symbol = {
                    "TODO": "\u2b1c",
                    "UNDERWAY": "\U0001f535",
                    "COMPLETE": "\u2705",
                    "ABORTED": "\u274c",
                }.get(task.status, "\u2b1c")

                table_lines.append(
                    f"| {task.id} | {task.title} | {status_symbol} {task.status} | {task.role} | {task.priority} |"
                )

            header_parts.extend(table_lines)

        # Use the same DB connection (no second connection needed)
        adr_manager = ADRManager(self.db)
        linked_adrs = adr_manager.get_epic_adrs(epic.id)

        if linked_adrs:
            header_parts.extend(["", "## Related Architecture", ""])

            adr_table_lines = [
                "| ADR ID | Title | Status | Path |",
                "|--------|-------|--------|------|",
            ]

            for adr in linked_adrs:
                adr_table_lines.append(f"| {adr.id} | {adr.title} | {adr.status} | {adr.file_path} |")

            header_parts.extend(adr_table_lines)

        header = "\n".join(header_parts)

        if not body:
            description_text = epic.description or "[Describe the high-level goals and scope of this epic]"
            body = f"""

## Description

{description_text}

## Goals

- [Key objective 1]
- [Key objective 2]
- [Key objective 3]

## Success Criteria

- [What needs to be achieved for this epic to be considered complete?]

## Notes

[Epic-level notes, decisions, blockers, and context]
"""

        file_path.write_text(header + "\n" + body)
