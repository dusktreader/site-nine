"""
Tests for desk mode lifecycle and status output (TST-M-0105).

Tests cover:
- MissionManager.set_desk_mode() unit tests (enable, disable, validation)
- CLI desk command lifecycle: start, stop, --mission flag, --start/--stop flags
- Desk mode scope inference: epic-scoped vs general missions
- JSON output structure: mission_id, desk_mode_active, scope, unread_count, unread_messages
- Auto-disable on mission end (both manager and CLI level)
- Ctrl+C / signal handler cleanup
- Validation: ended mission, nonexistent mission, no active mission
- Status output format during periodic checks
- Inbox integration during desk mode JSON output

Reference: ADR-009 Phase 3.
"""

import json
import signal
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from site_nine.__main__ import app
from site_nine.core.database import Database
from site_nine.messaging.manager import MessageManager
from site_nine.missions.exceptions import MissionError
from site_nine.missions.manager import MissionManager
from site_nine.missions.types import MissionStatus

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers for unit tests (test_db fixture)
# ---------------------------------------------------------------------------


def _create_mission(
    db: Database,
    *,
    persona: str = "test-persona",
    role: str = "Engineer",
    codename: str = "desk-test",
    epic_id: str | None = None,
    start_time: str = "10:00:00",
) -> int:
    """Insert a mission and return its ID."""
    return db.execute_insert(
        """
        INSERT INTO missions (
            persona_name, role, codename, mission_file,
            start_date, start_time, objective, epic_id
        )
        VALUES (
            :persona, :role, :codename,
            '.opencode/work/missions/desk-test.md',
            '2026-02-14', :start_time, 'Desk mode test mission', :epic_id
        )
        """,
        {
            "persona": persona,
            "role": role,
            "codename": codename,
            "start_time": start_time,
            "epic_id": epic_id,
        },
    )


def _create_epic(db: Database, epic_id: str = "EPC-H-0001", title: str = "Test Epic") -> None:
    """Insert a minimal epic."""
    db.execute_update(
        """
        INSERT INTO epics (id, title, priority, file_path, created_at)
        VALUES (:id, :title, 'HIGH', :file_path, datetime('now'))
        """,
        {"id": epic_id, "title": title, "file_path": f".opencode/work/epics/{epic_id}.md"},
    )


def _get_desk_mode(db: Database, mission_id: int) -> bool:
    """Read desk_mode_active from DB."""
    rows = db.execute_query(
        "SELECT desk_mode_active FROM missions WHERE id = :mid",
        {"mid": mission_id},
    )
    assert rows, f"Mission {mission_id} not found"
    return bool(rows[0]["desk_mode_active"])


def _set_desk_mode(db: Database, mission_id: int, active: bool) -> None:
    """Set desk_mode_active directly in DB."""
    db.execute_update(
        "UPDATE missions SET desk_mode_active = :active WHERE id = :mid",
        {"mid": mission_id, "active": 1 if active else 0},
    )


def _end_mission_raw(db: Database, mission_id: int) -> None:
    """End a mission directly via DB (no file updates)."""
    db.execute_update(
        """
        UPDATE missions
        SET end_time = '23:59:59', status = 'ENDED', desk_mode_active = 0
        WHERE id = :mid
        """,
        {"mid": mission_id},
    )


# ---------------------------------------------------------------------------
# Helpers for CLI tests (initialized_project fixture)
# ---------------------------------------------------------------------------


def _setup_desk_missions(project_dir: Path, *, epic_id: str | None = None) -> tuple[int, int]:
    """Create two missions for CLI tests.

    m2 has a later start_time so _get_current_mission_id returns m2.
    """
    db_path = project_dir / ".opencode" / "data" / "project.db"

    with Database(db_path) as db:
        db.execute_update(
            """
            INSERT OR IGNORE INTO personas (name, role, mythology, description)
            VALUES
                ('desk-alpha', 'Operator', 'Test', 'Desk alpha persona'),
                ('desk-beta', 'Tester', 'Test', 'Desk beta persona')
            """
        )

        if epic_id is not None:
            db.execute_update(
                """
                INSERT OR IGNORE INTO epics (id, title, priority, file_path, created_at)
                VALUES (:id, 'Test Epic', 'HIGH', '.opencode/work/epics/' || :id || '.md', datetime('now'))
                """,
                {"id": epic_id},
            )

        m1 = db.execute_insert(
            """
            INSERT INTO missions (
                persona_name, role, codename, mission_file,
                start_date, start_time, objective
            ) VALUES (
                'desk-alpha', 'Operator', 'desk-one',
                '.opencode/work/missions/desk-1.md',
                '2026-02-14', '10:00:00', 'Desk CLI test 1'
            )
            """
        )

        m2 = db.execute_insert(
            """
            INSERT INTO missions (
                persona_name, role, codename, mission_file,
                start_date, start_time, objective, epic_id
            ) VALUES (
                'desk-beta', 'Tester', 'desk-two',
                '.opencode/work/missions/desk-2.md',
                '2026-02-14', '11:00:00', 'Desk CLI test 2', :epic_id
            )
            """,
            {"epic_id": epic_id},
        )

    return m1, m2


def _get_desk_mode_in_project(project_dir: Path, mission_id: int) -> bool:
    """Read desk_mode_active from initialized_project DB."""
    db_path = project_dir / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        return _get_desk_mode(db, mission_id)


def _set_desk_mode_in_project(project_dir: Path, mission_id: int, active: bool) -> None:
    """Set desk_mode_active in initialized_project DB."""
    db_path = project_dir / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        _set_desk_mode(db, mission_id, active)


def _end_mission_in_project(project_dir: Path, mission_id: int) -> None:
    """End a mission in the initialized_project DB."""
    db_path = project_dir / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        _end_mission_raw(db, mission_id)


# ===========================================================================
# Unit tests: MissionManager.set_desk_mode()
# ===========================================================================


class TestSetDeskModeManager:
    """Unit tests for MissionManager.set_desk_mode()."""

    def test_enable_desk_mode(self, test_db: Database):
        """set_desk_mode(active=True) sets desk_mode_active to 1."""
        mid = _create_mission(test_db)
        mgr = MissionManager(test_db)

        mgr.set_desk_mode(mid, active=True)

        assert _get_desk_mode(test_db, mid) is True

    def test_disable_desk_mode(self, test_db: Database):
        """set_desk_mode(active=False) sets desk_mode_active to 0."""
        mid = _create_mission(test_db)
        mgr = MissionManager(test_db)

        mgr.set_desk_mode(mid, active=True)
        assert _get_desk_mode(test_db, mid) is True

        mgr.set_desk_mode(mid, active=False)
        assert _get_desk_mode(test_db, mid) is False

    def test_enable_idempotent(self, test_db: Database):
        """Enabling when already enabled does not raise."""
        mid = _create_mission(test_db)
        mgr = MissionManager(test_db)

        mgr.set_desk_mode(mid, active=True)
        mgr.set_desk_mode(mid, active=True)

        assert _get_desk_mode(test_db, mid) is True

    def test_disable_idempotent(self, test_db: Database):
        """Disabling when already disabled does not raise."""
        mid = _create_mission(test_db)
        mgr = MissionManager(test_db)

        mgr.set_desk_mode(mid, active=False)

        assert _get_desk_mode(test_db, mid) is False

    def test_error_on_ended_mission(self, test_db: Database):
        """Cannot enable desk mode on an ended mission."""
        mid = _create_mission(test_db)
        _end_mission_raw(test_db, mid)
        mgr = MissionManager(test_db)

        with pytest.raises(MissionError, match="Cannot change desk mode on an ended mission"):
            mgr.set_desk_mode(mid, active=True)

    def test_error_disable_on_ended_mission(self, test_db: Database):
        """Cannot disable desk mode on an ended mission either."""
        mid = _create_mission(test_db)
        _set_desk_mode(test_db, mid, True)
        _end_mission_raw(test_db, mid)
        mgr = MissionManager(test_db)

        with pytest.raises(MissionError, match="Cannot change desk mode on an ended mission"):
            mgr.set_desk_mode(mid, active=False)

    def test_error_on_nonexistent_mission(self, test_db: Database):
        """Cannot set desk mode on a nonexistent mission ID."""
        mgr = MissionManager(test_db)

        with pytest.raises(MissionError, match="not found"):
            mgr.set_desk_mode(99999, active=True)

    def test_default_is_false(self, test_db: Database):
        """Newly created missions have desk_mode_active=False."""
        mid = _create_mission(test_db)

        assert _get_desk_mode(test_db, mid) is False


# ===========================================================================
# Unit tests: auto-disable on mission end
# ===========================================================================


class TestAutoDisableOnMissionEnd:
    """Desk mode is automatically disabled when a mission ends."""

    def test_end_mission_clears_desk_mode(self, test_db: Database):
        """end_mission() sets desk_mode_active to 0."""
        mid = _create_mission(test_db)
        mgr = MissionManager(test_db)

        mgr.set_desk_mode(mid, active=True)
        assert _get_desk_mode(test_db, mid) is True

        with patch.object(mgr, "_update_mission_file_end_time"):
            mgr.end_mission(mid)

        assert _get_desk_mode(test_db, mid) is False

    def test_end_mission_without_desk_mode(self, test_db: Database):
        """end_mission() works fine when desk mode was never enabled."""
        mid = _create_mission(test_db)
        mgr = MissionManager(test_db)

        with patch.object(mgr, "_update_mission_file_end_time"):
            mgr.end_mission(mid)

        assert _get_desk_mode(test_db, mid) is False

    def test_end_mission_sets_ended_status(self, test_db: Database):
        """After end_mission(), status is ENDED and desk is off."""
        mid = _create_mission(test_db)
        mgr = MissionManager(test_db)
        mgr.set_desk_mode(mid, active=True)

        with patch.object(mgr, "_update_mission_file_end_time"):
            mgr.end_mission(mid)

        mission = mgr.get_mission(mid)
        assert mission is not None
        assert mission.status == MissionStatus.ENDED
        assert mission.desk_mode_active is False
        assert mission.end_time is not None

    def test_cannot_enable_desk_after_end(self, test_db: Database):
        """After ending, desk mode cannot be re-enabled."""
        mid = _create_mission(test_db)
        mgr = MissionManager(test_db)

        with patch.object(mgr, "_update_mission_file_end_time"):
            mgr.end_mission(mid)

        with pytest.raises(MissionError, match="Cannot change desk mode on an ended mission"):
            mgr.set_desk_mode(mid, active=True)


# ===========================================================================
# CLI tests: desk start (JSON mode — no polling loop)
# ===========================================================================


class TestCLIDeskStartJSON:
    """CLI tests for s9 comms desk --json (start, no polling)."""

    def test_start_json_basic(self, initialized_project: Path):
        """--json enables desk mode and returns desk_mode_active=True."""
        _setup_desk_missions(initialized_project)

        result = runner.invoke(app, ["comms", "desk", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)
        assert data["data"]["desk_mode_active"] is True

    def test_start_json_output_structure(self, initialized_project: Path):
        """JSON output contains all expected fields."""
        _setup_desk_missions(initialized_project)

        result = runner.invoke(app, ["comms", "desk", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)["data"]
        assert "mission_id" in data
        assert "desk_mode_active" in data
        assert "scope" in data
        assert "unread_count" in data
        assert "unread_messages" in data
        assert isinstance(data["unread_messages"], list)

    def test_start_json_scope_general(self, initialized_project: Path):
        """General mission (no epic_id) gets scope='all'."""
        _setup_desk_missions(initialized_project, epic_id=None)

        result = runner.invoke(app, ["comms", "desk", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)["data"]
        assert data["scope"] == "all"

    def test_start_json_scope_epic(self, initialized_project: Path):
        """Epic-scoped mission gets scope='epic <id>'."""
        _setup_desk_missions(initialized_project, epic_id="EPC-H-0099")

        result = runner.invoke(app, ["comms", "desk", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)["data"]
        assert data["scope"] == "epic EPC-H-0099"

    def test_start_json_no_unread(self, initialized_project: Path):
        """No unread messages -> unread_count=0, unread_messages=[]."""
        _setup_desk_missions(initialized_project)

        result = runner.invoke(app, ["comms", "desk", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)["data"]
        assert data["unread_count"] == 0
        assert data["unread_messages"] == []

    def test_start_json_with_explicit_start_flag(self, initialized_project: Path):
        """--start --json works the same as --json alone."""
        _setup_desk_missions(initialized_project)

        result = runner.invoke(app, ["comms", "desk", "--start", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)["data"]
        assert data["desk_mode_active"] is True

    def test_start_json_with_mission_flag(self, initialized_project: Path):
        """--json --mission <id> targets a specific mission."""
        m1, m2 = _setup_desk_missions(initialized_project)

        result = runner.invoke(app, ["comms", "desk", "--json", "--mission", str(m1)])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)["data"]
        assert data["desk_mode_active"] is True
        assert data["mission_id"] == m1

    def test_start_json_returns_correct_mission_id(self, initialized_project: Path):
        """Default mission (latest start_time) has correct mission_id in JSON."""
        m1, m2 = _setup_desk_missions(initialized_project)

        result = runner.invoke(app, ["comms", "desk", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)["data"]
        assert data["mission_id"] == m2  # m2 is latest


# ===========================================================================
# CLI tests: desk stop
# ===========================================================================


class TestCLIDeskStop:
    """CLI tests for s9 comms desk --stop."""

    def test_stop_json(self, initialized_project: Path):
        """--stop --json returns desk_mode_active=False."""
        _setup_desk_missions(initialized_project)

        result = runner.invoke(app, ["comms", "desk", "--stop", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)
        assert data["data"]["desk_mode_active"] is False
        assert "mission_id" in data["data"]

    def test_stop_text(self, initialized_project: Path):
        """--stop in text mode shows 'disabled'."""
        _setup_desk_missions(initialized_project)

        result = runner.invoke(app, ["comms", "desk", "--stop"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "disabled" in result.output.lower() or "Desk" in result.output

    def test_stop_with_mission_flag(self, initialized_project: Path):
        """--stop --mission <id> targets a specific mission."""
        m1, m2 = _setup_desk_missions(initialized_project)

        result = runner.invoke(app, ["comms", "desk", "--stop", "--mission", str(m1), "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)
        assert data["data"]["desk_mode_active"] is False
        assert data["data"]["mission_id"] == m1

    def test_stop_returns_correct_mission_id(self, initialized_project: Path):
        """Default mission (latest start_time) has correct mission_id in stop output."""
        m1, m2 = _setup_desk_missions(initialized_project)

        result = runner.invoke(app, ["comms", "desk", "--stop", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)["data"]
        assert data["mission_id"] == m2


# ===========================================================================
# CLI tests: desk mode persists in DB
# ===========================================================================


class TestCLIDeskPersistence:
    """Verify desk mode CLI commands persist state in the DB."""

    def test_start_sets_desk_mode_in_db(self, initialized_project: Path):
        """Starting desk via CLI sets desk_mode_active=1 in DB."""
        m1, m2 = _setup_desk_missions(initialized_project)

        result = runner.invoke(app, ["comms", "desk", "--json"])
        assert result.exit_code == 0

        assert _get_desk_mode_in_project(initialized_project, m2) is True

    def test_stop_clears_desk_mode_in_db(self, initialized_project: Path):
        """Stopping desk via CLI sets desk_mode_active=0 in DB."""
        m1, m2 = _setup_desk_missions(initialized_project)

        runner.invoke(app, ["comms", "desk", "--json"])
        result = runner.invoke(app, ["comms", "desk", "--stop", "--json"])
        assert result.exit_code == 0

        assert _get_desk_mode_in_project(initialized_project, m2) is False

    def test_start_stop_start_cycle(self, initialized_project: Path):
        """Full start -> stop -> start cycle persists correctly."""
        m1, m2 = _setup_desk_missions(initialized_project)

        runner.invoke(app, ["comms", "desk", "--json"])
        assert _get_desk_mode_in_project(initialized_project, m2) is True

        runner.invoke(app, ["comms", "desk", "--stop", "--json"])
        assert _get_desk_mode_in_project(initialized_project, m2) is False

        runner.invoke(app, ["comms", "desk", "--json"])
        assert _get_desk_mode_in_project(initialized_project, m2) is True


# ===========================================================================
# CLI tests: desk validation / error handling
# ===========================================================================


class TestCLIDeskValidation:
    """Tests for desk command validation and error cases."""

    def test_desk_on_ended_mission_fails(self, initialized_project: Path):
        """Starting desk mode on an ended mission fails."""
        m1, m2 = _setup_desk_missions(initialized_project)
        _end_mission_in_project(initialized_project, m2)

        result = runner.invoke(app, ["comms", "desk", "--mission", str(m2), "--json"])
        assert result.exit_code != 0

    def test_desk_stop_on_ended_mission_fails(self, initialized_project: Path):
        """Stopping desk mode on an ended mission fails."""
        m1, m2 = _setup_desk_missions(initialized_project)
        _end_mission_in_project(initialized_project, m2)

        result = runner.invoke(app, ["comms", "desk", "--stop", "--mission", str(m2)])
        assert result.exit_code != 0

    def test_desk_nonexistent_mission_fails(self, initialized_project: Path):
        """Targeting a nonexistent mission ID fails."""
        _setup_desk_missions(initialized_project)

        result = runner.invoke(app, ["comms", "desk", "--mission", "99999", "--json"])
        assert result.exit_code != 0

    def test_desk_no_active_mission_fails(self, initialized_project: Path):
        """When no active missions exist, desk fails."""
        result = runner.invoke(app, ["comms", "desk", "--json"])
        assert result.exit_code != 0


# ===========================================================================
# Signal handler / Ctrl+C cleanup
# ===========================================================================


class TestDeskModeSignalHandler:
    """Tests for Ctrl+C / SIGINT signal handler in desk command."""

    def test_sigint_handler_is_registered(self, initialized_project: Path):
        """Interactive desk mode registers a SIGINT handler."""
        _setup_desk_missions(initialized_project)

        handlers_registered = []
        original_signal = signal.signal

        def mock_signal(sig, handler):
            handlers_registered.append((sig, handler))
            return original_signal(sig, handler)

        with (
            patch("time.sleep", side_effect=SystemExit(0)),
            patch("signal.signal", side_effect=mock_signal),
        ):
            runner.invoke(app, ["comms", "desk"])

        sigint_handlers = [h for sig, h in handlers_registered if sig == signal.SIGINT]
        assert len(sigint_handlers) >= 1, "SIGINT handler should be registered"

    def test_cleanup_path_disables_desk_mode(self, test_db: Database):
        """The signal handler's cleanup logic (set_desk_mode(False)) works."""
        mid = _create_mission(test_db)
        mgr = MissionManager(test_db)

        mgr.set_desk_mode(mid, active=True)
        assert _get_desk_mode(test_db, mid) is True

        # Simulate the signal handler body
        mgr.set_desk_mode(mid, active=False)
        assert _get_desk_mode(test_db, mid) is False


# ===========================================================================
# Polling loop output format
# ===========================================================================


class TestPollingLoopOutput:
    """Tests for desk mode interactive polling loop output.

    We patch time.sleep to exit the loop after one iteration.
    """

    def test_startup_message_contains_scope(self, initialized_project: Path):
        """Startup message includes scope label."""
        _setup_desk_missions(initialized_project)

        with patch("time.sleep", side_effect=SystemExit(0)):
            result = runner.invoke(app, ["comms", "desk"])

        assert "Desk mode enabled for all" in result.output or "Desk Mode" in result.output

    def test_startup_message_contains_ctrl_c_hint(self, initialized_project: Path):
        """Startup message tells user about Ctrl+C."""
        _setup_desk_missions(initialized_project)

        with patch("time.sleep", side_effect=SystemExit(0)):
            result = runner.invoke(app, ["comms", "desk"])

        assert "Ctrl+C" in result.output

    def test_startup_message_epic_scope(self, initialized_project: Path):
        """Startup message shows epic ID when mission is epic-scoped."""
        _setup_desk_missions(initialized_project, epic_id="EPC-H-0077")

        with patch("time.sleep", side_effect=SystemExit(0)):
            result = runner.invoke(app, ["comms", "desk"])

        assert "EPC-H-0077" in result.output

    def test_no_messages_output(self, initialized_project: Path):
        """Polling prints 'No new messages' when inbox is empty."""
        _setup_desk_missions(initialized_project)

        call_count = 0

        def mock_sleep(seconds):
            nonlocal call_count
            call_count += 1
            # First sleep lets the loop body run; exit on second iteration
            if call_count >= 2:
                raise SystemExit(0)

        with patch("time.sleep", side_effect=mock_sleep):
            result = runner.invoke(app, ["comms", "desk"])

        assert "No new messages" in result.output

    def test_polling_with_unread_messages(self, initialized_project: Path):
        """Polling shows message summary when unread messages exist."""
        m1, m2 = _setup_desk_missions(initialized_project)

        db_path = initialized_project / ".opencode" / "data" / "project.db"
        with Database(db_path) as db:
            msg_mgr = MessageManager(db)
            msg_mgr.send_conversation_message(
                from_mission_id=m1,
                to_mission_id=m2,
                body="Urgent question about deployment",
            )

        call_count = 0

        def mock_sleep(seconds):
            nonlocal call_count
            call_count += 1
            # First sleep lets the loop body run; exit on second iteration
            if call_count >= 2:
                raise SystemExit(0)

        with patch("time.sleep", side_effect=mock_sleep):
            result = runner.invoke(app, ["comms", "desk"])

        assert "new message" in result.output or f"Mission #{m1}" in result.output


# ===========================================================================
# Inbox integration during desk mode
# ===========================================================================


class TestDeskInboxIntegration:
    """Tests that desk mode JSON output correctly reports inbox state."""

    def test_unread_message_has_required_fields(self, initialized_project: Path):
        """Each unread message has message_id, from_mission_id, subject, priority, conversation_id."""
        m1, m2 = _setup_desk_missions(initialized_project)

        db_path = initialized_project / ".opencode" / "data" / "project.db"
        with Database(db_path) as db:
            msg_mgr = MessageManager(db)
            msg_mgr.send_conversation_message(
                from_mission_id=m1,
                to_mission_id=m2,
                body="Integration test message",
            )

        result = runner.invoke(app, ["comms", "desk", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)["data"]
        assert data["unread_count"] == 1

        msg = data["unread_messages"][0]
        required = {"message_id", "from_mission_id", "subject", "priority", "conversation_id"}
        assert required.issubset(msg.keys()), f"Missing: {required - msg.keys()}"

    def test_own_messages_excluded(self, initialized_project: Path):
        """Own outgoing messages are excluded from desk JSON unread list."""
        m1, m2 = _setup_desk_missions(initialized_project)

        db_path = initialized_project / ".opencode" / "data" / "project.db"
        with Database(db_path) as db:
            msg_mgr = MessageManager(db)
            msg_mgr.send_conversation_message(
                from_mission_id=m2,
                to_mission_id=m1,
                body="Outgoing message from desk agent",
            )

        result = runner.invoke(app, ["comms", "desk", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)["data"]
        assert data["unread_count"] == 0
        assert data["unread_messages"] == []

    def test_multiple_senders_all_listed(self, initialized_project: Path):
        """Unread messages from different missions are all included."""
        m1, m2 = _setup_desk_missions(initialized_project)

        db_path = initialized_project / ".opencode" / "data" / "project.db"
        with Database(db_path) as db:
            db.execute_update(
                """
                INSERT OR IGNORE INTO personas (name, role, mythology, description)
                VALUES ('desk-gamma', 'Engineer', 'Test', 'Desk gamma')
                """
            )
            m3 = db.execute_insert(
                """
                INSERT INTO missions (
                    persona_name, role, codename, mission_file,
                    start_date, start_time, objective
                ) VALUES (
                    'desk-gamma', 'Engineer', 'desk-three',
                    '.opencode/work/missions/desk-3.md',
                    '2026-02-14', '09:00:00', 'Desk CLI test 3'
                )
                """
            )
            msg_mgr = MessageManager(db)
            msg_mgr.send_conversation_message(from_mission_id=m1, to_mission_id=m2, body="From m1")
            msg_mgr.send_conversation_message(from_mission_id=m3, to_mission_id=m2, body="From m3")

        result = runner.invoke(app, ["comms", "desk", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)["data"]
        assert data["unread_count"] == 2
        sender_ids = {msg["from_mission_id"] for msg in data["unread_messages"]}
        assert sender_ids == {m1, m3}

    def test_start_json_with_unread_messages(self, initialized_project: Path):
        """JSON output includes unread message details when messages exist."""
        m1, m2 = _setup_desk_missions(initialized_project)

        db_path = initialized_project / ".opencode" / "data" / "project.db"
        with Database(db_path) as db:
            msg_mgr = MessageManager(db)
            msg_mgr.send_conversation_message(
                from_mission_id=m1,
                to_mission_id=m2,
                body="Question for desk agent",
            )

        result = runner.invoke(app, ["comms", "desk", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)["data"]
        assert data["unread_count"] == 1
        assert len(data["unread_messages"]) == 1
        assert data["unread_messages"][0]["from_mission_id"] == m1


# ===========================================================================
# Scope / epic edge cases
# ===========================================================================


class TestDeskScopeEdgeCases:
    """Tests for desk mode scope behavior with various mission configs."""

    def test_general_mission_desk_mode(self, test_db: Database):
        """General mission (no epic_id) can enter desk mode."""
        mid = _create_mission(test_db, epic_id=None)
        mgr = MissionManager(test_db)

        mgr.set_desk_mode(mid, active=True)
        mission = mgr.get_mission(mid)
        assert mission is not None
        assert mission.epic_id is None
        assert mission.desk_mode_active is True

    def test_epic_scoped_mission_desk_mode(self, test_db: Database):
        """Epic-scoped mission can enter desk mode; epic_id preserved."""
        _create_epic(test_db, "EPC-H-0042")
        mid = _create_mission(test_db, epic_id="EPC-H-0042")
        mgr = MissionManager(test_db)

        mgr.set_desk_mode(mid, active=True)
        mission = mgr.get_mission(mid)
        assert mission is not None
        assert mission.epic_id == "EPC-H-0042"
        assert mission.desk_mode_active is True

    def test_desk_toggle_does_not_change_epic_id(self, test_db: Database):
        """Toggling desk mode does not alter epic_id."""
        _create_epic(test_db, "EPC-M-0010")
        mid = _create_mission(test_db, epic_id="EPC-M-0010")
        mgr = MissionManager(test_db)

        mgr.set_desk_mode(mid, active=True)
        mgr.set_desk_mode(mid, active=False)
        mgr.set_desk_mode(mid, active=True)

        mission = mgr.get_mission(mid)
        assert mission is not None
        assert mission.epic_id == "EPC-M-0010"

    def test_multiple_missions_independent(self, test_db: Database):
        """Desk mode on one mission doesn't affect another."""
        mid1 = _create_mission(test_db, persona="test-persona", codename="desk-a", start_time="10:00:00")
        mid2 = _create_mission(test_db, persona="persona1", codename="desk-b", start_time="11:00:00")
        mgr = MissionManager(test_db)

        mgr.set_desk_mode(mid1, active=True)

        assert _get_desk_mode(test_db, mid1) is True
        assert _get_desk_mode(test_db, mid2) is False

    def test_idle_mission_can_enter_desk_mode(self, test_db: Database):
        """An IDLE mission can enter desk mode."""
        mid = _create_mission(test_db)
        test_db.execute_update(
            "UPDATE missions SET status = :s WHERE id = :mid",
            {"s": MissionStatus.IDLE.value, "mid": mid},
        )
        mgr = MissionManager(test_db)

        mgr.set_desk_mode(mid, active=True)
        assert _get_desk_mode(test_db, mid) is True

    def test_desk_mode_persists_across_reads(self, test_db: Database):
        """Desk mode is correctly retrieved on subsequent get_mission() calls."""
        mid = _create_mission(test_db)
        mgr = MissionManager(test_db)

        mgr.set_desk_mode(mid, active=True)

        mission = mgr.get_mission(mid)
        assert mission is not None
        assert mission.desk_mode_active is True

    def test_heartbeat_preserves_desk_mode(self, test_db: Database):
        """Heartbeat (updating last_active_at) does not affect desk_mode_active."""
        mid = _create_mission(test_db)
        mgr = MissionManager(test_db)

        mgr.set_desk_mode(mid, active=True)
        mgr.heartbeat(mid)

        assert _get_desk_mode(test_db, mid) is True


# ===========================================================================
# Auto-disable via CLI (end mission while desk mode active)
# ===========================================================================


class TestAutoDisableOnMissionEndCLI:
    """Test that ending a mission via CLI clears desk mode."""

    def test_end_mission_clears_desk_mode(self, initialized_project: Path):
        """s9 mission end on a desk-active mission clears desk_mode_active."""
        m1, m2 = _setup_desk_missions(initialized_project)
        _set_desk_mode_in_project(initialized_project, m2, True)

        result = runner.invoke(app, ["mission", "end", str(m2)])
        assert result.exit_code == 0, f"End mission failed: {result.output}"

        assert _get_desk_mode_in_project(initialized_project, m2) is False

    def test_end_mission_without_desk_mode(self, initialized_project: Path):
        """Ending a mission without desk mode active also works."""
        m1, m2 = _setup_desk_missions(initialized_project)
        assert _get_desk_mode_in_project(initialized_project, m2) is False

        result = runner.invoke(app, ["mission", "end", str(m2)])
        assert result.exit_code == 0, f"End mission failed: {result.output}"

        assert _get_desk_mode_in_project(initialized_project, m2) is False
