from __future__ import annotations

import subprocess
from pathlib import Path

import pendulum
from buzz import enforce_defined, require_condition
from loguru import logger

from site_nine.core.database import Database
from site_nine.core.paths import validate_path_within_project
from site_nine.core.templates import TemplateRenderer
from site_nine.core.utils import utc_now
from site_nine.daemons.manager import DaemonManager
from site_nine.possessions.exceptions import PossessionError
from site_nine.possessions.models import FileChange, Possession, PossessionSummary, TaskSummary
from site_nine.possessions.types import PossessionStatus

GIT_STATUS_MAP = {"M": "modified", "A": "added", "D": "deleted", "R": "renamed"}


class PossessionManager:
    """Manages possessions"""

    def __init__(self, db: Database) -> None:
        self.db = db

    def start_possession(
        self,
        role: str,
        daemon_name: str | None = None,
        possession_log: str | None = None,
        epic_id: str | None = None,
    ) -> int:
        """Start a new possession.

        Args:
            role: Role for the possession
            daemon_name: Name of the daemon to use (if None, uses 3-day LRU selection)
            possession_log: Optional custom possession log path
            epic_id: Optional epic ID for epic-scoped possessions

        Returns:
            Possession ID
        """
        daemon_manager = DaemonManager(self.db)

        if daemon_name is None:
            summoned = daemon_manager.summon_daemon(role)
            if summoned is None:
                raise PossessionError(
                    f"No available daemons for role '{role}' within the 3-day LRU window. "
                    "A new daemon must be invented (ENG-H-0244)."
                )
            daemon_name = summoned.name
            logger.info("daemon_auto_summoned_for_possession", role=role, daemon=daemon_name)
        else:
            # Manually provided — normalize to lowercase, validate exists, increment incarnations
            daemon_name = daemon_name.lower()
            exists = self.db.execute_query(
                "SELECT name FROM daemons WHERE lower(name) = :name",
                {"name": daemon_name},
            )
            if not exists:
                raise PossessionError(
                    f"Daemon '{daemon_name}' not found. "
                    "Use 's9 daemon list' to see available daemons or invent a new one."
                )
            now_str = utc_now()
            self.db.execute_update(
                """
                UPDATE daemons
                SET incarnations = incarnations + 1,
                    last_possession = :now
                WHERE lower(name) = :name
                """,
                {"name": daemon_name, "now": now_str},
            )

        now = pendulum.now("UTC")
        date_str = now.format("YYYY-MM-DD")
        time_str = now.format("HH-mm-ss")

        if not possession_log:
            possession_log = f".opencode/work/possessions/{date_str}.{time_str}.{role.lower()}.{daemon_name}.md"

        now_str = utc_now()
        result = enforce_defined(
            self.db.execute_query(
                """
                INSERT INTO possessions (
                    daemon_name, role, possession_log,
                    start_time, epic_id,
                    status, last_heartbeat_at,
                    created_at, updated_at
                )
                VALUES (
                    :daemon_name, :role, :possession_log,
                    :start_time, :epic_id,
                    :status, :now,
                    :now, :now
                )
                RETURNING id
                """,
                {
                    "daemon_name": daemon_name,
                    "role": role,
                    "possession_log": possession_log,
                    "epic_id": epic_id,
                    "status": PossessionStatus.ACTIVE.value,
                    "start_time": now_str,
                    "now": now_str,
                },
            ),
            "Failed to create possession",
            raise_exc_class=PossessionError,
        )

        possession_id = result[0]["id"]

        self._create_possession_log(
            possession_log=possession_log,
            daemon_name=daemon_name,
            role=role,
        )

        return possession_id

    def _create_possession_log(
        self,
        possession_log: str,
        daemon_name: str,
        role: str,
    ) -> None:
        """Create initial possession log file."""
        from site_nine.core.paths import get_opencode_dir

        opencode_dir = get_opencode_dir()
        project_root = opencode_dir.parent
        log_path = project_root / possession_log

        log_path.parent.mkdir(parents=True, exist_ok=True)

        now = pendulum.now("UTC")
        start_time = now.format("HH:mm:ss")

        renderer = TemplateRenderer()
        renderer.render_to_file(
            "internal/possession.md.jinja",
            log_path,
            daemon_name=daemon_name,
            role=role,
            start_time=start_time,
        )

    def exorcise(self, possession_id: int) -> None:
        """Exorcise (end) a possession and update both database and log file."""
        possession = enforce_defined(
            self.get_possession(possession_id),
            f"Possession {possession_id} not found",
            raise_exc_class=PossessionError,
        )

        end_time = utc_now()
        enforce_defined(
            self.db.execute_query(
                """
                UPDATE possessions
                SET end_time = :end_time,
                    status = :status,
                    minion_mode_active = 0,
                    updated_at = :now
                WHERE id = :possession_id
                RETURNING *
                """,
                {
                    "possession_id": possession_id,
                    "end_time": end_time,
                    "status": PossessionStatus.EXORCISED.value,
                    "now": end_time,
                },
            ),
            f"Failed to exorcise possession {possession_id}",
            raise_exc_class=PossessionError,
        )

        if not possession.possession_log:
            return

        log_path = validate_path_within_project(possession.possession_log)
        if log_path.exists():
            self._update_log_end_time(log_path, end_time)

    def _update_log_end_time(self, log_path: Path, end_time: str) -> None:
        """Update end time in possession log markdown."""
        content = log_path.read_text()
        updated = content.replace("**End:** TBD", f"**End:** {end_time}")
        updated = updated.replace("**Duration:** TBD", "**Duration:** Complete")
        log_path.write_text(updated)

    def list_possessions(
        self,
        active_only: bool = False,
        role: str | None = None,
        epic_id: str | None = None,
    ) -> list[Possession]:
        """List possessions."""
        query = "SELECT * FROM possessions WHERE 1=1"
        params: dict = {}

        if active_only:
            query += " AND status != :exorcised"
            params["exorcised"] = PossessionStatus.EXORCISED.value

        if role:
            query += " AND role = :role"
            params["role"] = role

        if epic_id:
            query += " AND epic_id = :epic_id"
            params["epic_id"] = epic_id

        query += " ORDER BY created_at DESC"

        rows = self.db.execute_query(query, params)
        return [Possession.from_db_row(row) for row in rows]

    def get_possession(self, possession_id: int) -> Possession | None:
        """Get possession by ID."""
        rows = self.db.execute_query("SELECT * FROM possessions WHERE id = :id", {"id": possession_id})
        return Possession.from_db_row(rows[0]) if rows else None

    def update_possession(self, possession_id: int, role: str | None = None) -> None:
        """Update possession metadata."""
        update_fields = ["updated_at = :now"]
        params: dict = {"possession_id": possession_id, "now": utc_now()}

        if role is not None:
            update_fields.append("role = :role")
            params["role"] = role

        set_clause = ", ".join(update_fields)
        query = f"UPDATE possessions SET {set_clause} WHERE id = :possession_id RETURNING *"
        enforce_defined(
            self.db.execute_query(query, params),
            f"Failed to update possession {possession_id}",
            raise_exc_class=PossessionError,
        )

    def set_minion_mode(self, possession_id: int, active: bool) -> None:
        """Enable or disable minion mode for a possession.

        Args:
            possession_id: Possession ID.
            active: True to enable minion mode, False to disable.

        Raises:
            PossessionError: If possession not found or already exorcised.
        """
        possession = enforce_defined(
            self.get_possession(possession_id),
            f"Possession {possession_id} not found",
            raise_exc_class=PossessionError,
        )
        require_condition(
            possession.status != PossessionStatus.EXORCISED,
            "Cannot change minion mode on an exorcised possession",
            raise_exc_class=PossessionError,
        )

        self.db.execute_update(
            """
            UPDATE possessions
            SET minion_mode_active = :active, updated_at = :now
            WHERE id = :possession_id
            """,
            {"possession_id": possession_id, "active": 1 if active else 0, "now": utc_now()},
        )

    def heartbeat(self, possession_id: int) -> None:
        """Update last_heartbeat_at timestamp (agent heartbeat).

        Args:
            possession_id: Possession ID.

        Raises:
            PossessionError: If possession not found or already exorcised.
        """
        possession = enforce_defined(
            self.get_possession(possession_id),
            f"Possession {possession_id} not found",
            raise_exc_class=PossessionError,
        )
        require_condition(
            possession.status != PossessionStatus.EXORCISED,
            "Cannot heartbeat an exorcised possession",
            raise_exc_class=PossessionError,
        )

        now_str = utc_now()
        self.db.execute_update(
            """
            UPDATE possessions
            SET last_heartbeat_at = :now,
                status = :status,
                updated_at = :now
            WHERE id = :possession_id
            """,
            {
                "possession_id": possession_id,
                "status": PossessionStatus.ACTIVE.value,
                "now": now_str,
            },
        )

    def set_status(self, possession_id: int, status: PossessionStatus) -> None:
        """Set possession lifecycle status.

        Args:
            possession_id: Possession ID.
            status: New status.

        Raises:
            PossessionError: If possession not found.
        """
        enforce_defined(
            self.get_possession(possession_id),
            f"Possession {possession_id} not found",
            raise_exc_class=PossessionError,
        )

        self.db.execute_update(
            """
            UPDATE possessions
            SET status = :status, updated_at = :now
            WHERE id = :possession_id
            """,
            {"possession_id": possession_id, "status": status.value, "now": utc_now()},
        )

    def suspend_possession(self, possession_id: int, reason: str | None = None) -> None:
        """Suspend a possession.

        Args:
            possession_id: Possession ID.
            reason: Optional reason for suspension.

        Raises:
            PossessionError: If possession not found or already exorcised.
        """
        possession = enforce_defined(
            self.get_possession(possession_id),
            f"Possession {possession_id} not found",
            raise_exc_class=PossessionError,
        )

        require_condition(
            possession.status != PossessionStatus.EXORCISED,
            f"Cannot suspend possession {possession_id}: already exorcised",
            raise_exc_class=PossessionError,
        )

        now_str = utc_now()
        self.db.execute_update(
            """
            UPDATE possessions
            SET status = :status,
                suspension_time = :suspension_time,
                suspension_reason = :suspension_reason,
                updated_at = :now
            WHERE id = :possession_id
            """,
            {
                "possession_id": possession_id,
                "status": PossessionStatus.SUSPENDED.value,
                "suspension_time": now_str,
                "suspension_reason": reason or "Suspended by user",
                "now": now_str,
            },
        )

    def resume_possession(self, possession_id: int) -> None:
        """Resume a suspended possession.

        Args:
            possession_id: Possession ID.

        Raises:
            PossessionError: If possession not found or not suspended.
        """
        possession = enforce_defined(
            self.get_possession(possession_id),
            f"Possession {possession_id} not found",
            raise_exc_class=PossessionError,
        )

        require_condition(
            possession.status == PossessionStatus.SUSPENDED,
            f"Cannot resume possession {possession_id}: not suspended (current status: {possession.status})",
            raise_exc_class=PossessionError,
        )

        now_str = utc_now()
        self.db.execute_update(
            """
            UPDATE possessions
            SET status = :status,
                suspension_time = NULL,
                suspension_reason = NULL,
                updated_at = :now
            WHERE id = :possession_id
            """,
            {
                "possession_id": possession_id,
                "status": PossessionStatus.ACTIVE.value,
                "now": now_str,
            },
        )

    def generate_summary(self, possession_id: int) -> PossessionSummary:
        """Generate a summary of a possession's activity.

        Args:
            possession_id: Possession ID.

        Returns:
            PossessionSummary with files changed, commits, and tasks.

        Raises:
            PossessionError: If possession not found.
        """
        possession = self.get_possession(possession_id)
        PossessionError.require_condition(possession is not None, f"Possession #{possession_id} not found")

        summary = PossessionSummary(possession=possession)  # type: ignore[arg-type]

        self._collect_tasks(summary, possession_id)
        self._collect_file_changes(summary)
        self._collect_commits(summary)

        return summary

    def _collect_tasks(self, summary: PossessionSummary, possession_id: int) -> None:
        """Collect tasks claimed for a possession."""
        try:
            from site_nine.tasks import TaskManager

            task_manager = TaskManager(self.db)
            task_list = task_manager.list_tasks(possession_id=possession_id)  # type: ignore[call-arg]

            if task_list:
                for task in task_list:
                    summary.tasks.append(TaskSummary(id=task.id, title=task.title, status=task.status))
        except Exception as e:
            summary.warnings.append(f"Could not retrieve tasks: {e}")

    def _collect_file_changes(self, summary: PossessionSummary) -> None:
        """Collect file changes from git history since possession start."""
        possession = summary.possession
        try:
            result = subprocess.run(
                ["git", "diff", "--name-status", f"@{{'{possession.start_time}'}}", "HEAD"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0 and result.stdout.strip():
                self._parse_file_changes(result.stdout, summary)
            else:
                result = subprocess.run(
                    ["git", "log", "--name-status", "--pretty=format:", f"--since={possession.start_time}"],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if result.returncode == 0 and result.stdout.strip():
                    self._parse_file_changes_dedup(result.stdout, summary)

        except Exception as e:
            summary.warnings.append(f"Could not retrieve git history: {e}")

    def _collect_commits(self, summary: PossessionSummary) -> None:
        """Collect commits from git history since possession start."""
        possession = summary.possession
        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    "--oneline",
                    f"--since={possession.start_time}",
                    f"--grep={possession.daemon_name}",
                    "--grep=Possession:",
                    "--perl-regexp",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split("\n"):
                    summary.commits.append(line)
            else:
                result = subprocess.run(
                    ["git", "log", "--oneline", f"--since={possession.start_time}", "-10"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode == 0 and result.stdout.strip():
                    for line in result.stdout.strip().split("\n"):
                        summary.commits.append(line)

        except Exception as e:
            summary.warnings.append(f"Could not retrieve commits: {e}")

    @staticmethod
    def _parse_file_changes(output: str, summary: PossessionSummary) -> None:
        """Parse git diff --name-status output into FileChange objects."""
        for line in output.strip().split("\n"):
            parts = line.split("\t", 1)
            if len(parts) == 2:
                status, filepath = parts
                status_display = GIT_STATUS_MAP.get(status[0], status)
                summary.files_changed.append(FileChange(status=status_display, file=filepath))

    @staticmethod
    def _parse_file_changes_dedup(output: str, summary: PossessionSummary) -> None:
        """Parse git log --name-status output, deduplicating files."""
        files_seen: set[str] = set()
        for line in output.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                status, filepath = parts
                if filepath not in files_seen:
                    files_seen.add(filepath)
                    status_display = GIT_STATUS_MAP.get(status[0], status)
                    summary.files_changed.append(FileChange(status=status_display, file=filepath))
