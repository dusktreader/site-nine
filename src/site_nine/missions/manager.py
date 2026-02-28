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
from site_nine.missions.exceptions import MissionError
from site_nine.missions.models import FileChange, Mission, MissionSummary, TaskSummary
from site_nine.missions.types import MissionStatus
from site_nine.personas.manager import PersonaManager

GIT_STATUS_MAP = {"M": "modified", "A": "added", "D": "deleted", "R": "renamed"}

ADJECTIVES = [
    "swift",
    "silent",
    "bold",
    "clever",
    "quantum",
    "stellar",
    "epic",
    "crimson",
    "azure",
    "phantom",
    "iron",
    "silver",
    "rogue",
    "cosmic",
    "electric",
    "shadow",
    "titanium",
    "mystic",
    "storm",
    "ghost",
    "crystal",
    "rapid",
    "omega",
    "void",
    "neon",
    "plasma",
    "razor",
    "cyber",
    "dark",
    "chrome",
    "gamma",
]  # 31 entries (prime)

NOUNS = [
    "thunder",
    "phoenix",
    "shadow",
    "dragon",
    "nexus",
    "vortex",
    "cipher",
    "falcon",
    "sentinel",
    "tempest",
    "wraith",
    "cascade",
    "apex",
    "forge",
    "blade",
    "comet",
    "prism",
    "quasar",
    "raven",
    "typhoon",
    "vector",
    "aurora",
    "blaze",
    "echo",
    "griffin",
    "helix",
    "kraken",
    "nebula",
    "zenith",
    "matrix",
    "pulse",
    "specter",
    "vertex",
    "enigma",
    "hydra",
    "photon",
    "titan",
]  # 37 entries (prime)


def generate_mission_codename(mission_id: int) -> str:
    """
    Generate deterministic codename from mission ID using prime modulo.

    Using coprime prime numbers (31 and 37) ensures maximum distribution
    before collisions occur. First collision happens at mission #1,147.

    31 × 37 = 1,147 unique combinations
    """
    adjective = ADJECTIVES[mission_id % len(ADJECTIVES)]
    noun = NOUNS[mission_id % len(NOUNS)]
    return f"{adjective}-{noun}"


class MissionManager:
    """Manages missions"""

    def __init__(self, db: Database) -> None:
        self.db = db

    def start_mission(
        self,
        role: str,
        objective: str,
        persona_name: str | None = None,
        mission_file: str | None = None,
        epic_id: str | None = None,
    ) -> int:
        """Start a new mission

        Args:
            role: Role for the mission
            objective: Mission objective/task summary
            persona_name: Name of the persona to use (if None, atomically claims least-used persona)
            mission_file: Optional custom mission file path
            epic_id: Optional epic ID for epic-scoped missions

        Returns:
            Mission ID
        """
        # Auto-claim persona if not provided
        if persona_name is None:
            persona_manager = PersonaManager(self.db)
            claimed_persona = persona_manager.claim_persona(role)
            persona_name = claimed_persona.name
            persona_auto_claimed = True
            logger.info("persona_auto_claimed_for_mission", role=role, persona=persona_name)
        else:
            persona_auto_claimed = False

        if not mission_file:
            now = pendulum.now("UTC")
            date_str = now.format("YYYY-MM-DD")
            time_str = now.format("HH:mm:ss")
            mission_file = f".opencode/work/missions/{date_str}.{time_str}.{role.lower()}.{persona_name}.md"

        now_str = utc_now()
        result = enforce_defined(
            self.db.execute_query(
                """
                INSERT INTO missions (
                    persona_name, role, codename, mission_file,
                    start_date, start_time, objective, epic_id,
                    status, last_active_at,
                    created_at, updated_at
                )
                VALUES (
                    :persona_name, :role, NULL, :mission_file,
                    :start_date, :start_time, :objective, :epic_id,
                    :status, :now,
                    :now, :now
                )
                RETURNING id
                """,
                {
                    "persona_name": persona_name,
                    "role": role,
                    "mission_file": mission_file,
                    "objective": objective,
                    "epic_id": epic_id,
                    "status": MissionStatus.ACTIVE.value,
                    "start_date": pendulum.now("UTC").format("YYYY-MM-DD"),
                    "start_time": pendulum.now("UTC").format("HH:mm:ss"),
                    "now": now_str,
                },
            ),
            "Failed to create mission",
            raise_exc_class=MissionError,
        )

        mission_id = result[0]["id"]

        codename = generate_mission_codename(mission_id)
        enforce_defined(
            self.db.execute_query(
                "UPDATE missions SET codename = :codename WHERE id = :id RETURNING *",
                {"codename": codename, "id": mission_id},
            ),
            f"Failed to update codename for mission {mission_id}",
            raise_exc_class=MissionError,
        )

        # Only update persona stats if it was manually selected (auto-claim already did this)
        if not persona_auto_claimed:
            self.db.execute_query(
                """
                UPDATE personas
                SET mission_count = mission_count + 1,
                    last_mission_at = :now
                WHERE name = :persona_name
                RETURNING *
                """,
                {"persona_name": persona_name, "now": now_str},
            )

        self._create_mission_file(
            mission_file=mission_file,
            persona_name=persona_name,
            role=role,
            codename=codename,
            objective=objective,
        )

        return mission_id

    def _create_mission_file(
        self,
        mission_file: str,
        persona_name: str,
        role: str,
        codename: str,
        objective: str,
    ) -> None:
        """Create initial mission file with frontmatter and structure"""
        from site_nine.core.paths import get_opencode_dir

        opencode_dir = get_opencode_dir()
        project_root = opencode_dir.parent
        mission_path = project_root / mission_file

        mission_path.parent.mkdir(parents=True, exist_ok=True)

        now = pendulum.now("UTC")
        start_date = now.format("YYYY-MM-DD")
        start_time = now.format("HH:mm:ss")

        persona_info = self.db.execute_query(
            "SELECT mythology, description FROM personas WHERE name = :name", {"name": persona_name}
        )
        mythology = persona_info[0]["mythology"] if persona_info else "Unknown"
        description = persona_info[0]["description"] if persona_info else ""

        renderer = TemplateRenderer()
        renderer.render_to_file(
            "internal/mission.md.jinja",
            mission_path,
            codename=codename,
            persona_name=persona_name,
            mythology=mythology,
            description=description,
            role=role,
            start_date=start_date,
            start_time=start_time,
            objective=objective,
        )

    def end_mission(self, mission_id: int) -> None:
        """End a mission and update both database and mission file"""
        mission = enforce_defined(
            self.get_mission(mission_id),
            f"Mission {mission_id} not found",
            raise_exc_class=MissionError,
        )

        end_time = pendulum.now("UTC").format("HH:mm:ss")

        now_str = utc_now()
        enforce_defined(
            self.db.execute_query(
                """
                UPDATE missions
                SET end_time = :end_time,
                    status = :status,
                    desk_mode_active = 0,
                    updated_at = :now
                WHERE id = :mission_id
                RETURNING *
                """,
                {"mission_id": mission_id, "end_time": end_time, "status": MissionStatus.ENDED.value, "now": now_str},
            ),
            f"Failed to end mission {mission_id}",
            raise_exc_class=MissionError,
        )

        if not mission.mission_file:
            return

        mission_path = validate_path_within_project(mission.mission_file)
        if mission_path.exists():
            self._update_mission_file_end_time(mission_path, end_time)

    def _update_mission_file_end_time(self, mission_path: Path, end_time: str) -> None:
        """Update end time in mission file markdown"""
        content = mission_path.read_text()

        updated_content = content.replace("**End:** TBD", f"**End:** {end_time}")
        updated_content = updated_content.replace("**Duration:** TBD", f"**Duration:** Complete")

        mission_path.write_text(updated_content)

    def list_missions(
        self, active_only: bool = False, role: str | None = None, epic_id: str | None = None
    ) -> list[Mission]:
        """List missions"""
        query = "SELECT * FROM missions WHERE 1=1"
        params = {}

        if active_only:
            query += " AND end_time IS NULL"

        if role:
            query += " AND role = :role"
            params["role"] = role

        if epic_id:
            query += " AND epic_id = :epic_id"
            params["epic_id"] = epic_id

        query += " ORDER BY created_at DESC"

        rows = self.db.execute_query(query, params)
        return [Mission.from_db_row(row) for row in rows]

    def get_mission(self, mission_id: int) -> Mission | None:
        """Get mission by ID"""
        rows = self.db.execute_query("SELECT * FROM missions WHERE id = :id", {"id": mission_id})
        return Mission.from_db_row(rows[0]) if rows else None

    def get_mission_by_codename(self, codename: str) -> Mission | None:
        """Get mission by codename.

        Args:
            codename: Mission codename (e.g., 'bold-comet')

        Returns:
            Mission object or None if not found
        """
        rows = self.db.execute_query("SELECT * FROM missions WHERE codename = :codename", {"codename": codename})
        return Mission.from_db_row(rows[0]) if rows else None

    def get_active_codename(self, persona_name: str) -> str | None:
        """Get the codename for the most recent active mission for a persona.

        Args:
            persona_name: Persona name (case-insensitive, stored lowercase).

        Returns:
            Codename string or None if no active mission found.
        """
        rows = self.db.execute_query(
            """
            SELECT codename FROM missions
            WHERE persona_name = :persona_name
            AND end_time IS NULL
            ORDER BY created_at DESC
            LIMIT 1
            """,
            {"persona_name": persona_name.lower()},
        )
        if rows and rows[0]["codename"]:
            return rows[0]["codename"]
        return None

    def update_mission(self, mission_id: int, objective: str | None = None, role: str | None = None) -> None:
        """Update mission metadata"""
        update_fields = ["updated_at = :now"]
        params: dict[str, int | str] = {"mission_id": mission_id, "now": utc_now()}

        if objective is not None:
            update_fields.append("objective = :objective")
            params["objective"] = objective

        if role is not None:
            update_fields.append("role = :role")
            params["role"] = role

        set_clause = ", ".join(update_fields)
        query = f"UPDATE missions SET {set_clause} WHERE id = :mission_id RETURNING *"
        enforce_defined(
            self.db.execute_query(query, params),
            f"Failed to update mission {mission_id}",
            raise_exc_class=MissionError,
        )

    def set_desk_mode(self, mission_id: int, active: bool) -> None:
        """Enable or disable desk mode for a mission.

        Args:
            mission_id: Mission ID.
            active: True to enable desk mode, False to disable.

        Raises:
            MissionError: If mission not found or already ended.
        """
        mission = enforce_defined(
            self.get_mission(mission_id),
            f"Mission {mission_id} not found",
            raise_exc_class=MissionError,
        )
        require_condition(
            mission.end_time is None,
            "Cannot change desk mode on an ended mission",
            raise_exc_class=MissionError,
        )

        self.db.execute_update(
            """
            UPDATE missions
            SET desk_mode_active = :active, updated_at = :now
            WHERE id = :mission_id
            """,
            {"mission_id": mission_id, "active": 1 if active else 0, "now": utc_now()},
        )

    def heartbeat(self, mission_id: int) -> None:
        """Update last_active_at timestamp for a mission (agent heartbeat).

        Should be called periodically by agents to indicate they are still active.
        Also sets status to ACTIVE if the mission was IDLE.

        Args:
            mission_id: Mission ID.

        Raises:
            MissionError: If mission not found or already ended.
        """
        mission = enforce_defined(
            self.get_mission(mission_id),
            f"Mission {mission_id} not found",
            raise_exc_class=MissionError,
        )
        require_condition(
            mission.status != MissionStatus.ENDED,
            "Cannot heartbeat an ended mission",
            raise_exc_class=MissionError,
        )

        now_str = utc_now()
        self.db.execute_update(
            """
            UPDATE missions
            SET last_active_at = :now,
                status = :status,
                updated_at = :now
            WHERE id = :mission_id
            """,
            {"mission_id": mission_id, "status": MissionStatus.ACTIVE.value, "now": now_str},
        )

    def set_status(self, mission_id: int, status: MissionStatus) -> None:
        """Set mission lifecycle status.

        Args:
            mission_id: Mission ID.
            status: New status.

        Raises:
            MissionError: If mission not found.
        """
        enforce_defined(
            self.get_mission(mission_id),
            f"Mission {mission_id} not found",
            raise_exc_class=MissionError,
        )

        self.db.execute_update(
            """
            UPDATE missions
            SET status = :status, updated_at = :now
            WHERE id = :mission_id
            """,
            {"mission_id": mission_id, "status": status.value, "now": utc_now()},
        )

    def suspend_mission(self, mission_id: int, reason: str | None = None) -> None:
        """Suspend a mission (ADR-013).

        Transitions mission to SUSPENDED status and records suspension time and reason.
        Typically called by the OpenCode plugin when a session closes unexpectedly,
        or manually by the Director.

        Args:
            mission_id: Mission ID.
            reason: Optional reason for suspension (e.g., "Session closed unexpectedly").

        Raises:
            MissionError: If mission not found or already ended.
        """
        mission = enforce_defined(
            self.get_mission(mission_id),
            f"Mission {mission_id} not found",
            raise_exc_class=MissionError,
        )

        require_condition(
            mission.status != MissionStatus.ENDED,
            f"Cannot suspend mission {mission_id}: already ended",
            raise_exc_class=MissionError,
        )

        now_str = utc_now()
        self.db.execute_update(
            """
            UPDATE missions
            SET status = :status,
                suspension_time = :suspension_time,
                suspension_reason = :suspension_reason,
                updated_at = :now
            WHERE id = :mission_id
            """,
            {
                "mission_id": mission_id,
                "status": MissionStatus.SUSPENDED.value,
                "suspension_time": now_str,
                "suspension_reason": reason or "Suspended by user",
                "now": now_str,
            },
        )

    def resume_mission(self, mission_id: int) -> None:
        """Resume a suspended mission (ADR-013).

        Transitions mission from SUSPENDED to ACTIVE status and clears suspension data.
        Typically called manually by the Director via s9 mission resume.

        Args:
            mission_id: Mission ID.

        Raises:
            MissionError: If mission not found or not suspended.
        """
        mission = enforce_defined(
            self.get_mission(mission_id),
            f"Mission {mission_id} not found",
            raise_exc_class=MissionError,
        )

        require_condition(
            mission.status == MissionStatus.SUSPENDED,
            f"Cannot resume mission {mission_id}: not suspended (current status: {mission.status})",
            raise_exc_class=MissionError,
        )

        now_str = utc_now()
        self.db.execute_update(
            """
            UPDATE missions
            SET status = :status,
                suspension_time = NULL,
                suspension_reason = NULL,
                updated_at = :now
            WHERE id = :mission_id
            """,
            {
                "mission_id": mission_id,
                "status": MissionStatus.ACTIVE.value,
                "now": now_str,
            },
        )

    def generate_summary(self, mission_id: int) -> MissionSummary:
        """Generate a summary of a mission's activity.

        Collects git file changes, commits, and claimed tasks for the mission.

        Args:
            mission_id: Mission ID.

        Returns:
            MissionSummary with files changed, commits, and tasks.

        Raises:
            MissionError: If mission not found.
        """
        mission = self.get_mission(mission_id)
        MissionError.require_condition(mission is not None, f"Mission #{mission_id} not found")

        summary = MissionSummary(mission=mission)  # type: ignore[arg-type]

        self._collect_tasks(summary, mission_id)
        self._collect_file_changes(summary)
        self._collect_commits(summary)

        return summary

    def _collect_tasks(self, summary: MissionSummary, mission_id: int) -> None:
        """Collect tasks claimed for a mission."""
        try:
            from site_nine.tasks import TaskManager

            task_manager = TaskManager(self.db)
            task_list = task_manager.list_tasks(mission_id=mission_id)

            if task_list:
                for task in task_list:
                    summary.tasks.append(TaskSummary(id=task.id, title=task.title, status=task.status))
        except Exception as e:
            summary.warnings.append(f"Could not retrieve tasks: {e}")

    def _collect_file_changes(self, summary: MissionSummary) -> None:
        """Collect file changes from git history since mission start."""
        mission = summary.mission
        try:
            result = subprocess.run(
                ["git", "diff", "--name-status", f"@{{'{mission.start_time}'}}", "HEAD"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0 and result.stdout.strip():
                self._parse_file_changes(result.stdout, summary)
            else:
                result = subprocess.run(
                    ["git", "log", "--name-status", "--pretty=format:", f"--since={mission.start_time}"],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                if result.returncode == 0 and result.stdout.strip():
                    self._parse_file_changes_dedup(result.stdout, summary)

        except Exception as e:
            summary.warnings.append(f"Could not retrieve git history: {e}")

    def _collect_commits(self, summary: MissionSummary) -> None:
        """Collect commits from git history since mission start."""
        mission = summary.mission
        try:
            result = subprocess.run(
                [
                    "git",
                    "log",
                    "--oneline",
                    f"--since={mission.start_time}",
                    f"--grep={mission.persona_name}",
                    "--grep=Mission:",
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
                    ["git", "log", "--oneline", f"--since={mission.start_time}", "-10"],
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
    def _parse_file_changes(output: str, summary: MissionSummary) -> None:
        """Parse git diff --name-status output into FileChange objects."""
        for line in output.strip().split("\n"):
            parts = line.split("\t", 1)
            if len(parts) == 2:
                status, filepath = parts
                status_display = GIT_STATUS_MAP.get(status[0], status)
                summary.files_changed.append(FileChange(status=status_display, file=filepath))

    @staticmethod
    def _parse_file_changes_dedup(output: str, summary: MissionSummary) -> None:
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
