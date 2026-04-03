from typing import Any

import pendulum

from site_nine.core.database import Database
from site_nine.core.roles import Role
from site_nine.core.utils import utc_now
from site_nine.daemons.exceptions import DaemonError
from site_nine.daemons.models import Daemon


class DaemonManager:
    """Manages daemon CRUD operations and queries."""

    # 3-day LRU threshold for summon selection
    SUMMON_THRESHOLD_DAYS = 3

    def __init__(self, db: Database) -> None:
        self.db = db

    def validate_role(self, role: str) -> str:
        """
        Validate role name (case-insensitive) and return title case.

        Args:
            role: Role name to validate

        Returns:
            Title-cased role name

        Raises:
            DaemonError: If the role is invalid
        """
        try:
            Role.from_string(role)
        except ValueError:
            valid_roles_str = ", ".join(Role.all_values())
            raise DaemonError(f"Invalid role: {role}. Valid values: {valid_roles_str}")
        return role.title()

    def add_daemon(
        self,
        name: str,
        role: str,
        daemonology: str | None = None,
        personality: str | None = None,
    ) -> Daemon:
        """
        Add a new daemon.

        Args:
            name: Daemon name (will be lowercased)
            role: Primary role (will be validated and title-cased)
            daemonology: Optional whimsical first-person bio
            personality: Optional terse trait string

        Returns:
            The created Daemon

        Raises:
            DaemonError: If the daemon already exists or the role is invalid
        """
        name = name.lower()
        role = self.validate_role(role)

        try:
            rows = self.db.execute_query(
                """
                INSERT INTO daemons (name, role, daemonology, personality)
                VALUES (:name, :role, :daemonology, :personality)
                RETURNING *
                """,
                {"name": name, "role": role, "daemonology": daemonology, "personality": personality},
            )
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                raise DaemonError(f"Daemon '{name}' already exists")
            raise

        DaemonError.require_condition(len(rows) > 0, f"Failed to create daemon '{name}'")
        return Daemon.from_db_row(rows[0])

    def get_daemon(self, name: str) -> Daemon | None:
        """
        Get a daemon by name.

        Args:
            name: Daemon name (case-insensitive)

        Returns:
            Daemon if found, None otherwise
        """
        rows = self.db.execute_query(
            "SELECT * FROM daemons WHERE lower(name) = :name",
            {"name": name.lower()},
        )
        return Daemon.from_db_row(rows[0]) if rows else None

    def list_daemons(
        self,
        role: str | None = None,
        unused_only: bool = False,
        by_usage: bool = False,
    ) -> list[Daemon]:
        """
        List daemons with optional filtering and sorting.

        Args:
            role: Filter by role (validated, case-insensitive)
            unused_only: Show only daemons with zero incarnations
            by_usage: Sort by incarnation count descending

        Returns:
            List of matching Daemons
        """
        conditions = []
        params: dict[str, Any] = {}

        if role:
            role = self.validate_role(role)
            conditions.append("role = :role")
            params["role"] = role

        if unused_only:
            conditions.append("incarnations = 0")

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        order_by = "incarnations DESC, name ASC" if by_usage else "role ASC, name ASC"

        query = f"""
            SELECT *
            FROM daemons
            WHERE {where_clause}
            ORDER BY {order_by}
        """

        rows = self.db.execute_query(query, params)
        return [Daemon.from_db_row(row) for row in rows]

    def suggest_for_role(self, role: str, count: int = 3) -> list[Daemon]:
        """
        Suggest least-used daemons for a role (3-day LRU ordering).

        Returns daemons not summoned in the last 3 days first, ordered by
        incarnation count ascending. If all have been summoned recently,
        returns the least-recently-used ones.

        Args:
            role: Role to suggest daemons for (validated, case-insensitive)
            count: Maximum number of suggestions

        Returns:
            List of daemons ordered by least recently used first
        """
        role = self.validate_role(role)
        threshold = pendulum.now("UTC").subtract(days=self.SUMMON_THRESHOLD_DAYS).to_iso8601_string()

        rows = self.db.execute_query(
            """
            SELECT *
            FROM daemons
            WHERE role = :role
            ORDER BY
                CASE WHEN last_possession IS NULL OR last_possession < :threshold THEN 0 ELSE 1 END ASC,
                incarnations ASC,
                last_possession ASC NULLS FIRST,
                name ASC
            LIMIT :count
            """,
            {"role": role, "count": count, "threshold": threshold},
        )
        return [Daemon.from_db_row(row) for row in rows]

    def set_daemonology(self, name: str, daemonology: str) -> Daemon:
        """
        Set daemonology (whimsical bio) for a daemon.

        Args:
            name: Daemon name
            daemonology: Whimsical first-person bio text

        Returns:
            Updated Daemon

        Raises:
            DaemonError: If daemon not found
        """
        name = name.lower()

        rows = self.db.execute_query(
            """
            UPDATE daemons SET daemonology = :daemonology
            WHERE lower(name) = :name
            RETURNING *
            """,
            {"name": name, "daemonology": daemonology},
        )
        DaemonError.require_condition(len(rows) > 0, f"Daemon '{name}' not found")
        return Daemon.from_db_row(rows[0])

    def set_personality(self, name: str, personality: str) -> Daemon:
        """
        Set personality trait string for a daemon.

        Args:
            name: Daemon name
            personality: Terse trait string (e.g., 'methodical, blunt')

        Returns:
            Updated Daemon

        Raises:
            DaemonError: If daemon not found
        """
        name = name.lower()

        rows = self.db.execute_query(
            """
            UPDATE daemons SET personality = :personality
            WHERE lower(name) = :name
            RETURNING *
            """,
            {"name": name, "personality": personality},
        )
        DaemonError.require_condition(len(rows) > 0, f"Daemon '{name}' not found")
        return Daemon.from_db_row(rows[0])

    def summon_daemon(self, role: str) -> Daemon | None:
        """
        Atomically summon the least-recently-used daemon for a role.

        Uses 3-day LRU threshold: prefers daemons not summoned within 3 days.
        Within eligible daemons, selects by fewest incarnations, then
        oldest last_possession, then alphabetically.

        Returns None if no daemons exist for the role OR if all daemons for
        the role have been summoned within the last 3 days (caller should
        invent a new daemon name via the invent_required flow).

        Args:
            role: Role to summon daemon for (validated, case-insensitive)

        Returns:
            The summoned Daemon with updated incarnations and last_possession,
            or None if no daemons exist or all were recently summoned.

        Raises:
            DaemonError: If database error occurs
        """
        role = self.validate_role(role)
        now = utc_now()
        threshold = pendulum.now("UTC").subtract(days=self.SUMMON_THRESHOLD_DAYS).to_iso8601_string()

        # Check if all daemons for this role have been summoned within the threshold.
        # If so, return None to signal that invention is required.
        count_rows = self.db.execute_query(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN last_possession IS NOT NULL AND last_possession >= :threshold THEN 1 ELSE 0 END) AS recent
            FROM daemons
            WHERE role = :role
            """,
            {"role": role, "threshold": threshold},
        )
        if count_rows:
            total = count_rows[0]["total"]
            recent = count_rows[0]["recent"]
            if total == 0 or (total > 0 and recent >= total):
                return None

        rows = self.db.execute_query(
            """
            UPDATE daemons
            SET incarnations = incarnations + 1,
                last_possession = :now
            WHERE name = (
                SELECT name
                FROM daemons
                WHERE role = :role
                ORDER BY
                    CASE WHEN last_possession IS NULL OR last_possession < :threshold THEN 0 ELSE 1 END ASC,
                    incarnations ASC,
                    last_possession ASC NULLS FIRST,
                    name ASC
                LIMIT 1
            )
            RETURNING *
            """,
            {"role": role, "now": now, "threshold": threshold},
        )

        if not rows:
            return None
        return Daemon.from_db_row(rows[0])
