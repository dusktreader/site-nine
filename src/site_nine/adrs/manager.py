import re
from pathlib import Path

from buzz import enforce_defined, require_condition

from site_nine.adrs.exceptions import ADRError
from site_nine.adrs.models import ArchitectureDoc
from site_nine.adrs.types import ADRStatus
from site_nine.core.database import Database
from site_nine.core.paths import resolve_opencode_path
from site_nine.core.utils import utc_now


def parse_adr_id(file_path: str) -> str | None:
    """Extract ADR ID from filename (e.g., 'ADR-001' from 'ADR-001-adapter-pattern.md')"""
    match = re.match(r"(ADR-\d+)", Path(file_path).name)
    return match.group(1) if match else None


def parse_adr_title(file_path: Path) -> str | None:
    """Extract title from ADR markdown file"""
    try:
        content = file_path.read_text()
        match = re.search(r"#\s+ADR-\d+:\s+(.+)", content)
        if match:
            return match.group(1).strip()
        match = re.search(r"#\s+(.+)", content)
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return None


def parse_adr_status(file_path: Path) -> str:
    """Extract status from ADR markdown file, defaults to PROPOSED"""
    try:
        content = file_path.read_text()
        match = re.search(r"\*\*Status:\*\*\s+(\w+)", content)
        if match:
            status = match.group(1).upper()
            if status in [s.value for s in ADRStatus]:
                return status
    except Exception:
        pass
    return "PROPOSED"


class ADRManager:
    """Manages Architecture Decision Records (ADRs)"""

    def __init__(self, db: Database) -> None:
        self.db = db

    def next_adr_id(self) -> str:
        existing_adrs = self.list_adrs()
        if existing_adrs:
            last_num = max(int(adr.id.split("-")[1]) for adr in existing_adrs)
            next_num = last_num + 1
        else:
            next_num = 1
        return f"ADR-{next_num:03d}"

    @staticmethod
    def adr_file_path(adr_id: str, title: str) -> str:
        filename_base = title.lower().replace(" ", "-").replace("_", "-")
        filename_base = re.sub(r"[^a-z0-9-]", "", filename_base)
        return f".opencode/docs/adrs/{adr_id}-{filename_base}.md"

    ADR_TEMPLATE = """\
# {adr_id}: {title}

**Status:** {status}
**Date:** {date}
**Deciders:** [To be filled]
**Related Tasks:** [To be filled]

## Context

[Describe the issue that motivates this decision]

## Decision

[Describe the decision and how it addresses the issue]

## Alternatives Considered

### Alternative 1: [Name]

**Approach:** [Description]

**Pros:**
- [Pro 1]
- [Pro 2]

**Cons:**
- [Con 1]
- [Con 2]

**Rejected because:** [Reason]

## Consequences

### Positive

- ✅ [Benefit 1]
- ✅ [Benefit 2]

### Negative

- ⚠️ [Trade-off 1]
- ⚠️ [Trade-off 2]

### Risks & Mitigation

| Risk | Mitigation |
|------|-----------|
| [Risk 1] | [Mitigation 1] |
| [Risk 2] | [Mitigation 2] |

## References

- [Related documents, tasks, or external resources]

## Notes

[Additional notes or context]
"""

    def create_adr(
        self,
        title: str,
        status: ADRStatus = ADRStatus.PROPOSED,
    ) -> ArchitectureDoc:
        adr_id = self.next_adr_id()
        file_path = self.adr_file_path(adr_id, title)
        full_path = resolve_opencode_path(file_path)

        rows = enforce_defined(
            self.db.execute_query(
                """
                INSERT INTO architecture_docs (id, title, status, file_path)
                VALUES (:id, :title, :status, :file_path)
                RETURNING *
                """,
                {
                    "id": adr_id,
                    "title": title,
                    "status": status.value,
                    "file_path": file_path,
                },
            ),
            f"Failed to create ADR {adr_id}",
            raise_exc_class=ADRError,
        )

        adr = ArchitectureDoc.from_db_row(rows[0])

        full_path.parent.mkdir(parents=True, exist_ok=True)
        content = self.ADR_TEMPLATE.format(
            adr_id=adr_id,
            title=title,
            status=status.value,
            date=str(adr.created_at)[:10],
        )
        full_path.write_text(content)

        return adr

    def import_adr(
        self,
        adr_id: str,
        title: str,
        file_path: str,
        status: ADRStatus | str = ADRStatus.PROPOSED,
    ) -> ArchitectureDoc:
        """Import an existing ADR file into the database (used by sync)."""
        status_value = status.value if isinstance(status, ADRStatus) else status
        rows = enforce_defined(
            self.db.execute_query(
                """
                INSERT INTO architecture_docs (id, title, status, file_path)
                VALUES (:id, :title, :status, :file_path)
                RETURNING *
                """,
                {
                    "id": adr_id,
                    "title": title,
                    "status": status_value,
                    "file_path": file_path,
                },
            ),
            f"Failed to import ADR {adr_id}",
            raise_exc_class=ADRError,
        )
        return ArchitectureDoc.from_db_row(rows[0])

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
        return ArchitectureDoc.from_db_row(rows[0])

    def list_adrs(self, status: ADRStatus | str | None = None) -> list[ArchitectureDoc]:
        """
        List ADRs with optional status filter.

        Args:
            status: Filter by status (PROPOSED, ACCEPTED, REJECTED, SUPERSEDED, DEPRECATED).
                   Can be ADRStatus enum or string.

        Returns:
            List of ArchitectureDoc instances
        """
        query = "SELECT * FROM architecture_docs WHERE 1=1"
        params = {}

        if status:
            status_str = status.value if isinstance(status, ADRStatus) else status
            query += " AND status = :status"
            params["status"] = status_str

        query += " ORDER BY id"

        rows = self.db.execute_query(query, params)
        return [ArchitectureDoc.from_db_row(row) for row in rows]

    def update_adr(self, adr_id: str, **updates) -> ArchitectureDoc:
        """
        Update ADR fields.

        Args:
            adr_id: ADR identifier
            **updates: Fields to update (title, status, file_path)

        Returns:
            Updated ArchitectureDoc instance
        """
        update_fields = []
        params = {"adr_id": adr_id}

        for field, value in updates.items():
            require_condition(
                field in ArchitectureDoc.UPDATABLE_FIELDS,
                f"Cannot update field '{field}'",
                raise_exc_class=ADRError,
            )
            update_fields.append(f"{field} = :{field}")
            params[field] = value

        require_condition(update_fields, "No fields to update", raise_exc_class=ADRError)

        update_fields.append("updated_at = :now")
        params["now"] = utc_now()

        set_clause = ", ".join(update_fields)
        query = f"UPDATE architecture_docs SET {set_clause} WHERE id = :adr_id"
        self.db.execute_update(query, params)

        return enforce_defined(
            self.get_adr(adr_id),
            f"Failed to retrieve updated ADR {adr_id}",
            raise_exc_class=ADRError,
        )

    def link_to_epic(self, adr_id: str, epic_id: str) -> None:
        """
        Link an ADR to an epic.

        Args:
            adr_id: ADR identifier
            epic_id: Epic ID
        """
        enforce_defined(self.get_adr(adr_id), f"ADR {adr_id} not found", raise_exc_class=ADRError)

        result = self.db.execute_query(
            """
            INSERT INTO epic_architecture_docs (epic_id, adr_id, created_at)
            VALUES (:epic_id, :adr_id, :now)
            ON CONFLICT DO NOTHING
            RETURNING *
            """,
            {"epic_id": epic_id, "adr_id": adr_id, "now": utc_now()},
        )

        if not result:
            existing = self.db.execute_query(
                "SELECT 1 FROM epic_architecture_docs WHERE epic_id = :epic_id AND adr_id = :adr_id",
                {"epic_id": epic_id, "adr_id": adr_id},
            )
            enforce_defined(existing, f"Failed to link ADR {adr_id} to epic {epic_id}", raise_exc_class=ADRError)

    def unlink_from_epic(self, adr_id: str, epic_id: str) -> None:
        """
        Unlink an ADR from an epic.

        Args:
            adr_id: ADR identifier
            epic_id: Epic ID
        """
        enforce_defined(
            self.db.execute_query(
                "DELETE FROM epic_architecture_docs WHERE epic_id = :epic_id AND adr_id = :adr_id RETURNING *",
                {"epic_id": epic_id, "adr_id": adr_id},
            ),
            f"No link found between ADR {adr_id} and epic {epic_id}",
            raise_exc_class=ADRError,
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
        return [ArchitectureDoc.from_db_row(row) for row in rows]

    def link_to_task(self, adr_id: str, task_id: str) -> None:
        """
        Link an ADR to a task.

        Args:
            adr_id: ADR identifier
            task_id: Task ID
        """
        enforce_defined(self.get_adr(adr_id), f"ADR {adr_id} not found", raise_exc_class=ADRError)

        result = self.db.execute_query(
            """
            INSERT INTO task_architecture_docs (task_id, adr_id, created_at)
            VALUES (:task_id, :adr_id, :now)
            ON CONFLICT DO NOTHING
            RETURNING *
            """,
            {"task_id": task_id, "adr_id": adr_id, "now": utc_now()},
        )

        if not result:
            existing = self.db.execute_query(
                "SELECT 1 FROM task_architecture_docs WHERE task_id = :task_id AND adr_id = :adr_id",
                {"task_id": task_id, "adr_id": adr_id},
            )
            enforce_defined(existing, f"Failed to link ADR {adr_id} to task {task_id}", raise_exc_class=ADRError)

    def unlink_from_task(self, adr_id: str, task_id: str) -> None:
        """
        Unlink an ADR from a task.

        Args:
            adr_id: ADR identifier
            task_id: Task ID
        """
        enforce_defined(
            self.db.execute_query(
                "DELETE FROM task_architecture_docs WHERE task_id = :task_id AND adr_id = :adr_id RETURNING *",
                {"task_id": task_id, "adr_id": adr_id},
            ),
            f"No link found between ADR {adr_id} and task {task_id}",
            raise_exc_class=ADRError,
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
        return [ArchitectureDoc.from_db_row(row) for row in rows]

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
