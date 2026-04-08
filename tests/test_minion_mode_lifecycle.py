"""
Tests for minion mode lifecycle and status output (TST-M-0105).

Tests cover:
- PossessionManager.set_minion_mode() unit tests (enable, disable, validation)
- CLI minion command lifecycle: start, stop, --mission flag, --start/--stop flags
- Minion mode scope inference: epic-scoped vs general possessions
- JSON output structure: mission_id, minion_mode_active, scope, unread_count, unread_messages
- Auto-disable on possession exorcism (both manager and CLI level)
- Ctrl+C / signal handler cleanup
- Validation: exorcised possession, nonexistent possession, no active possession
- Status output format during periodic checks
- Inbox integration during minion mode JSON output

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
from site_nine.possessions.exceptions import PossessionError
from site_nine.possessions.manager import PossessionManager
from site_nine.possessions.types import PossessionStatus

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers for unit tests (test_db fixture)
# ---------------------------------------------------------------------------


def _create_possession(
    db: Database,
    *,
    daemon: str = "test-daemon",
    role: str = "Engineer",
    epic_id: str | None = None,
    start_time: str = "10:00:00",
) -> int:
    """Insert a possession and return its ID."""
    # Ensure daemon exists
    db.execute_update(
        "INSERT OR IGNORE INTO daemons (name, role, incarnations) VALUES (:name, :role, 0)",
        {"name": daemon, "role": role},
    )
    return db.execute_insert(
        """
        INSERT INTO possessions (
            daemon_name, role, possession_log,
            start_time, epic_id,
            status, last_heartbeat_at,
            created_at, updated_at
        )
        VALUES (
            :daemon, :role,
            '.opencode/work/possessions/minion-test.md',
            :start_time, :epic_id,
            'ACTIVE', datetime('now'),
            datetime('now'), datetime('now')
        )
        """,
        {
            "daemon": daemon,
            "role": role,
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


def _get_minion_mode(db: Database, possession_id: int) -> bool:
    """Read minion_mode_active from DB."""
    rows = db.execute_query(
        "SELECT minion_mode_active FROM possessions WHERE id = :mid",
        {"mid": possession_id},
    )
    assert rows, f"Possession {possession_id} not found"
    return bool(rows[0]["minion_mode_active"])


def _set_minion_mode(db: Database, possession_id: int, active: bool) -> None:
    """Set minion_mode_active directly in DB."""
    db.execute_update(
        "UPDATE possessions SET minion_mode_active = :active WHERE id = :mid",
        {"mid": possession_id, "active": 1 if active else 0},
    )


def _end_possession_raw(db: Database, possession_id: int) -> None:
    """Exorcise a possession directly via DB (no file updates)."""
    db.execute_update(
        """
        UPDATE possessions
        SET end_time = datetime('now'), status = 'EXORCISED', minion_mode_active = 0
        WHERE id = :mid
        """,
        {"mid": possession_id},
    )


# ---------------------------------------------------------------------------
# Helpers for CLI tests (initialized_project fixture)
# ---------------------------------------------------------------------------


def _setup_minion_missions(project_dir: Path, *, epic_id: str | None = None) -> tuple[int, int]:
    """Create two possessions for CLI tests.

    m2 has a later start_time so _get_current_possession_id returns m2.
    """
    db_path = project_dir / ".opencode" / "data" / "project.db"

    with Database(db_path) as db:
        db.execute_update(
            """
            INSERT OR IGNORE INTO daemons (name, role, incarnations)
            VALUES
                ('minion-alpha', 'Operator', 0),
                ('minion-beta', 'Tester', 0)
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
            INSERT INTO possessions (
                daemon_name, role, possession_log,
                start_time, status, last_heartbeat_at,
                created_at, updated_at
            ) VALUES (
                'minion-alpha', 'Operator',
                '.opencode/work/possessions/minion-1.md',
                '10:00:00', 'ACTIVE', datetime('now'),
                datetime('now'), datetime('now')
            )
            """
        )

        m2 = db.execute_insert(
            """
            INSERT INTO possessions (
                daemon_name, role, possession_log,
                start_time, epic_id,
                status, last_heartbeat_at,
                created_at, updated_at
            ) VALUES (
                'minion-beta', 'Tester',
                '.opencode/work/possessions/minion-2.md',
                '11:00:00', :epic_id,
                'ACTIVE', datetime('now'),
                datetime('now'), datetime('now')
            )
            """,
            {"epic_id": epic_id},
        )

    return m1, m2


def _get_minion_mode_in_project(project_dir: Path, possession_id: int) -> bool:
    """Read minion_mode_active from initialized_project DB."""
    db_path = project_dir / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        return _get_minion_mode(db, possession_id)


def _set_minion_mode_in_project(project_dir: Path, possession_id: int, active: bool) -> None:
    """Set minion_mode_active in initialized_project DB."""
    db_path = project_dir / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        _set_minion_mode(db, possession_id, active)


def _end_possession_in_project(project_dir: Path, possession_id: int) -> None:
    """Exorcise a possession in the initialized_project DB."""
    db_path = project_dir / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        _end_possession_raw(db, possession_id)


# ===========================================================================
# Unit tests: PossessionManager.set_minion_mode()
# ===========================================================================


class TestSetMinionMode:
    """Unit tests for PossessionManager.set_minion_mode()."""

    def test_enable_minion_mode(self, test_db: Database):
        """set_minion_mode(active=True) sets minion_mode_active to 1."""
        mid = _create_possession(test_db)
        mgr = PossessionManager(test_db)

        mgr.set_minion_mode(mid, active=True)

        assert _get_minion_mode(test_db, mid) is True

    def test_disable_minion_mode(self, test_db: Database):
        """set_minion_mode(active=False) sets minion_mode_active to 0."""
        mid = _create_possession(test_db)
        mgr = PossessionManager(test_db)

        mgr.set_minion_mode(mid, active=True)
        assert _get_minion_mode(test_db, mid) is True

        mgr.set_minion_mode(mid, active=False)
        assert _get_minion_mode(test_db, mid) is False

    def test_enable_idempotent(self, test_db: Database):
        """Enabling when already enabled does not raise."""
        mid = _create_possession(test_db)
        mgr = PossessionManager(test_db)

        mgr.set_minion_mode(mid, active=True)
        mgr.set_minion_mode(mid, active=True)

        assert _get_minion_mode(test_db, mid) is True

    def test_disable_idempotent(self, test_db: Database):
        """Disabling when already disabled does not raise."""
        mid = _create_possession(test_db)
        mgr = PossessionManager(test_db)

        mgr.set_minion_mode(mid, active=False)

        assert _get_minion_mode(test_db, mid) is False

    def test_error_on_exorcised_possession(self, test_db: Database):
        """Cannot enable minion mode on an exorcised possession."""
        mid = _create_possession(test_db)
        _end_possession_raw(test_db, mid)
        mgr = PossessionManager(test_db)

        with pytest.raises(PossessionError, match="Cannot change minion mode on an exorcised possession"):
            mgr.set_minion_mode(mid, active=True)

    def test_error_disable_on_exorcised_possession(self, test_db: Database):
        """Cannot disable minion mode on an exorcised possession either."""
        mid = _create_possession(test_db)
        _set_minion_mode(test_db, mid, True)
        _end_possession_raw(test_db, mid)
        mgr = PossessionManager(test_db)

        with pytest.raises(PossessionError, match="Cannot change minion mode on an exorcised possession"):
            mgr.set_minion_mode(mid, active=False)

    def test_error_on_nonexistent_possession(self, test_db: Database):
        """Cannot set minion mode on a nonexistent possession ID."""
        mgr = PossessionManager(test_db)

        with pytest.raises(PossessionError, match="not found"):
            mgr.set_minion_mode(99999, active=True)

    def test_default_is_false(self, test_db: Database):
        """Newly created possessions have minion_mode_active=False."""
        mid = _create_possession(test_db)

        assert _get_minion_mode(test_db, mid) is False


# ===========================================================================
# Unit tests: auto-disable on possession exorcism
# ===========================================================================


class TestAutoDisableOnPossessionExorcism:
    """Minion mode is automatically disabled when a possession is exorcised."""

    def test_exorcise_clears_minion_mode(self, test_db: Database):
        """exorcise() sets minion_mode_active to 0."""
        mid = _create_possession(test_db)
        mgr = PossessionManager(test_db)

        mgr.set_minion_mode(mid, active=True)
        assert _get_minion_mode(test_db, mid) is True

        mgr.exorcise(mid)

        assert _get_minion_mode(test_db, mid) is False

    def test_exorcise_without_minion_mode(self, test_db: Database):
        """exorcise() works fine when minion mode was never enabled."""
        mid = _create_possession(test_db)
        mgr = PossessionManager(test_db)

        mgr.exorcise(mid)

        assert _get_minion_mode(test_db, mid) is False

    def test_exorcise_sets_exorcised_status(self, test_db: Database):
        """After exorcise(), status is EXORCISED and minion is off."""
        mid = _create_possession(test_db)
        mgr = PossessionManager(test_db)
        mgr.set_minion_mode(mid, active=True)

        mgr.exorcise(mid)

        possession = mgr.get_possession(mid)
        assert possession is not None
        assert possession.status == PossessionStatus.EXORCISED
        assert possession.minion_mode_active is False
        assert possession.end_time is not None

    def test_cannot_enable_minion_after_exorcism(self, test_db: Database):
        """After exorcising, minion mode cannot be re-enabled."""
        mid = _create_possession(test_db)
        mgr = PossessionManager(test_db)

        mgr.exorcise(mid)

        with pytest.raises(PossessionError, match="Cannot change minion mode on an exorcised possession"):
            mgr.set_minion_mode(mid, active=True)


# ===========================================================================
# CLI tests: minion start (JSON mode — no polling loop)
# ===========================================================================


class TestCLIMinionStartJSON:
    """CLI tests for s9 comms minion --json (start, no polling)."""

    def test_start_json_basic(self, initialized_project: Path):
        """--json enables minion mode and returns minion_mode_active=True."""
        _setup_minion_missions(initialized_project)

        result = runner.invoke(app, ["comms", "minion", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)
        assert data["data"]["minion_mode_active"] is True

    def test_start_json_output_structure(self, initialized_project: Path):
        """JSON output contains all expected fields."""
        _setup_minion_missions(initialized_project)

        result = runner.invoke(app, ["comms", "minion", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)["data"]
        assert "mission_id" in data
        assert "minion_mode_active" in data
        assert "scope" in data
        assert "unread_count" in data
        assert "unread_messages" in data
        assert isinstance(data["unread_messages"], list)

    def test_start_json_scope_general(self, initialized_project: Path):
        """General possession (no epic_id) gets scope='all'."""
        _setup_minion_missions(initialized_project, epic_id=None)

        result = runner.invoke(app, ["comms", "minion", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)["data"]
        assert data["scope"] == "all"

    def test_start_json_scope_epic(self, initialized_project: Path):
        """Epic-scoped possession gets scope='epic <id>'."""
        _setup_minion_missions(initialized_project, epic_id="EPC-H-0099")

        result = runner.invoke(app, ["comms", "minion", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)["data"]
        assert data["scope"] == "epic EPC-H-0099"

    def test_start_json_no_unread(self, initialized_project: Path):
        """No unread messages -> unread_count=0, unread_messages=[]."""
        _setup_minion_missions(initialized_project)

        result = runner.invoke(app, ["comms", "minion", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)["data"]
        assert data["unread_count"] == 0
        assert data["unread_messages"] == []

    def test_start_json_with_explicit_start_flag(self, initialized_project: Path):
        """--start --json works the same as --json alone."""
        _setup_minion_missions(initialized_project)

        result = runner.invoke(app, ["comms", "minion", "--start", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)["data"]
        assert data["minion_mode_active"] is True

    def test_start_json_with_mission_flag(self, initialized_project: Path):
        """--json --mission <id> targets a specific possession."""
        m1, m2 = _setup_minion_missions(initialized_project)

        result = runner.invoke(app, ["comms", "minion", "--json", "--mission", str(m1)])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)["data"]
        assert data["minion_mode_active"] is True
        assert data["mission_id"] == m1

    def test_start_json_returns_correct_mission_id(self, initialized_project: Path):
        """Default possession (latest start_time) has correct mission_id in JSON."""
        m1, m2 = _setup_minion_missions(initialized_project)

        result = runner.invoke(app, ["comms", "minion", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)["data"]
        assert data["mission_id"] == m2  # m2 is latest


# ===========================================================================
# CLI tests: minion stop
# ===========================================================================


class TestCLIMinionStop:
    """CLI tests for s9 comms minion --stop."""

    def test_stop_json(self, initialized_project: Path):
        """--stop --json returns minion_mode_active=False."""
        _setup_minion_missions(initialized_project)

        result = runner.invoke(app, ["comms", "minion", "--stop", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)
        assert data["data"]["minion_mode_active"] is False
        assert "mission_id" in data["data"]

    def test_stop_text(self, initialized_project: Path):
        """--stop in text mode shows 'disabled'."""
        _setup_minion_missions(initialized_project)

        result = runner.invoke(app, ["comms", "minion", "--stop"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "disabled" in result.output.lower() or "Minion" in result.output

    def test_stop_with_mission_flag(self, initialized_project: Path):
        """--stop --mission <id> targets a specific possession."""
        m1, m2 = _setup_minion_missions(initialized_project)

        result = runner.invoke(app, ["comms", "minion", "--stop", "--mission", str(m1), "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)
        assert data["data"]["minion_mode_active"] is False
        assert data["data"]["mission_id"] == m1

    def test_stop_returns_correct_mission_id(self, initialized_project: Path):
        """Default possession (latest start_time) has correct mission_id in stop output."""
        m1, m2 = _setup_minion_missions(initialized_project)

        result = runner.invoke(app, ["comms", "minion", "--stop", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)["data"]
        assert data["mission_id"] == m2


# ===========================================================================
# CLI tests: minion mode persists in DB
# ===========================================================================


class TestCLIMinionPersistence:
    """Verify minion mode CLI commands persist state in the DB."""

    def test_start_sets_minion_mode_in_db(self, initialized_project: Path):
        """Starting minion via CLI sets minion_mode_active=1 in DB."""
        m1, m2 = _setup_minion_missions(initialized_project)

        result = runner.invoke(app, ["comms", "minion", "--json"])
        assert result.exit_code == 0

        assert _get_minion_mode_in_project(initialized_project, m2) is True

    def test_stop_clears_minion_mode_in_db(self, initialized_project: Path):
        """Stopping minion via CLI sets minion_mode_active=0 in DB."""
        m1, m2 = _setup_minion_missions(initialized_project)

        runner.invoke(app, ["comms", "minion", "--json"])
        result = runner.invoke(app, ["comms", "minion", "--stop", "--json"])
        assert result.exit_code == 0

        assert _get_minion_mode_in_project(initialized_project, m2) is False

    def test_start_stop_start_cycle(self, initialized_project: Path):
        """Full start -> stop -> start cycle persists correctly."""
        m1, m2 = _setup_minion_missions(initialized_project)

        runner.invoke(app, ["comms", "minion", "--json"])
        assert _get_minion_mode_in_project(initialized_project, m2) is True

        runner.invoke(app, ["comms", "minion", "--stop", "--json"])
        assert _get_minion_mode_in_project(initialized_project, m2) is False

        runner.invoke(app, ["comms", "minion", "--json"])
        assert _get_minion_mode_in_project(initialized_project, m2) is True


# ===========================================================================
# CLI tests: minion validation / error handling
# ===========================================================================


class TestCLIMinionValidation:
    """Tests for minion command validation and error cases."""

    def test_minion_on_exorcised_possession_fails(self, initialized_project: Path):
        """Starting minion mode on an exorcised possession fails."""
        m1, m2 = _setup_minion_missions(initialized_project)
        _end_possession_in_project(initialized_project, m2)

        result = runner.invoke(app, ["comms", "minion", "--mission", str(m2), "--json"])
        assert result.exit_code != 0

    def test_minion_stop_on_exorcised_possession_fails(self, initialized_project: Path):
        """Stopping minion mode on an exorcised possession fails."""
        m1, m2 = _setup_minion_missions(initialized_project)
        _end_possession_in_project(initialized_project, m2)

        result = runner.invoke(app, ["comms", "minion", "--stop", "--mission", str(m2)])
        assert result.exit_code != 0

    def test_minion_nonexistent_possession_fails(self, initialized_project: Path):
        """Targeting a nonexistent possession ID fails."""
        _setup_minion_missions(initialized_project)

        result = runner.invoke(app, ["comms", "minion", "--mission", "99999", "--json"])
        assert result.exit_code != 0

    def test_minion_no_active_possession_fails(self, initialized_project: Path):
        """When no active possessions exist, minion fails."""
        result = runner.invoke(app, ["comms", "minion", "--json"])
        assert result.exit_code != 0


# ===========================================================================
# Signal handler / Ctrl+C cleanup
# ===========================================================================


class TestMinionModeSignalHandler:
    """Tests for Ctrl+C / SIGINT signal handler in minion command."""

    def test_sigint_handler_is_registered(self, initialized_project: Path):
        """Interactive minion mode registers a SIGINT handler."""
        _setup_minion_missions(initialized_project)

        handlers_registered = []
        original_signal = signal.signal

        def mock_signal(sig, handler):
            handlers_registered.append((sig, handler))
            return original_signal(sig, handler)

        with (
            patch("time.sleep", side_effect=SystemExit(0)),
            patch("signal.signal", side_effect=mock_signal),
        ):
            runner.invoke(app, ["comms", "minion"])

        sigint_handlers = [h for sig, h in handlers_registered if sig == signal.SIGINT]
        assert len(sigint_handlers) >= 1, "SIGINT handler should be registered"

    def test_cleanup_path_disables_minion_mode(self, test_db: Database):
        """The signal handler's cleanup logic (set_minion_mode(False)) works."""
        mid = _create_possession(test_db)
        mgr = PossessionManager(test_db)

        mgr.set_minion_mode(mid, active=True)
        assert _get_minion_mode(test_db, mid) is True

        # Simulate the signal handler body
        mgr.set_minion_mode(mid, active=False)
        assert _get_minion_mode(test_db, mid) is False


# ===========================================================================
# Polling loop output format
# ===========================================================================


class TestPollingLoopOutput:
    """Tests for minion mode interactive polling loop output.

    We patch time.sleep to exit the loop after one iteration.
    """

    def test_startup_message_contains_scope(self, initialized_project: Path):
        """Startup message includes scope label."""
        _setup_minion_missions(initialized_project)

        with patch("time.sleep", side_effect=SystemExit(0)):
            result = runner.invoke(app, ["comms", "minion"])

        assert "Minion mode enabled for all" in result.output or "Minion Mode" in result.output

    def test_startup_message_contains_ctrl_c_hint(self, initialized_project: Path):
        """Startup message tells user about Ctrl+C."""
        _setup_minion_missions(initialized_project)

        with patch("time.sleep", side_effect=SystemExit(0)):
            result = runner.invoke(app, ["comms", "minion"])

        assert "Ctrl+C" in result.output

    def test_startup_message_epic_scope(self, initialized_project: Path):
        """Startup message shows epic ID when possession is epic-scoped."""
        _setup_minion_missions(initialized_project, epic_id="EPC-H-0077")

        with patch("time.sleep", side_effect=SystemExit(0)):
            result = runner.invoke(app, ["comms", "minion"])

        assert "EPC-H-0077" in result.output

    def test_no_messages_output(self, initialized_project: Path):
        """Polling prints 'No new messages' when inbox is empty."""
        _setup_minion_missions(initialized_project)

        call_count = 0

        def mock_sleep(seconds):
            nonlocal call_count
            call_count += 1
            # First sleep lets the loop body run; exit on second iteration
            if call_count >= 2:
                raise SystemExit(0)

        with patch("time.sleep", side_effect=mock_sleep):
            result = runner.invoke(app, ["comms", "minion"])

        assert "No new messages" in result.output

    def test_polling_with_unread_messages(self, initialized_project: Path):
        """Polling shows message summary when unread messages exist."""
        m1, m2 = _setup_minion_missions(initialized_project)

        db_path = initialized_project / ".opencode" / "data" / "project.db"
        with Database(db_path) as db:
            msg_mgr = MessageManager(db)
            msg_mgr.send_conversation_message(
                from_possession_id=m1,
                to_possession_id=m2,
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
            result = runner.invoke(app, ["comms", "minion"])

        assert "new message" in result.output or f"Mission #{m1}" in result.output


# ===========================================================================
# Inbox integration during minion mode
# ===========================================================================


class TestMinionInboxIntegration:
    """Tests that minion mode JSON output correctly reports inbox state."""

    def test_unread_message_has_required_fields(self, initialized_project: Path):
        """Each unread message has message_id, from_mission_id, subject, priority, conversation_id."""
        m1, m2 = _setup_minion_missions(initialized_project)

        db_path = initialized_project / ".opencode" / "data" / "project.db"
        with Database(db_path) as db:
            msg_mgr = MessageManager(db)
            msg_mgr.send_conversation_message(
                from_possession_id=m1,
                to_possession_id=m2,
                body="Integration test message",
            )

        result = runner.invoke(app, ["comms", "minion", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)["data"]
        assert data["unread_count"] == 1

        msg = data["unread_messages"][0]
        required = {"message_id", "from_mission_id", "subject", "priority", "conversation_id"}
        assert required.issubset(msg.keys()), f"Missing: {required - msg.keys()}"

    def test_own_messages_excluded(self, initialized_project: Path):
        """Own outgoing messages are excluded from minion JSON unread list."""
        m1, m2 = _setup_minion_missions(initialized_project)

        db_path = initialized_project / ".opencode" / "data" / "project.db"
        with Database(db_path) as db:
            msg_mgr = MessageManager(db)
            msg_mgr.send_conversation_message(
                from_possession_id=m2,
                to_possession_id=m1,
                body="Outgoing message from minion agent",
            )

        result = runner.invoke(app, ["comms", "minion", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)["data"]
        assert data["unread_count"] == 0
        assert data["unread_messages"] == []

    def test_multiple_senders_all_listed(self, initialized_project: Path):
        """Unread messages from different possessions are all included."""
        m1, m2 = _setup_minion_missions(initialized_project)

        db_path = initialized_project / ".opencode" / "data" / "project.db"
        with Database(db_path) as db:
            db.execute_update(
                """
                INSERT OR IGNORE INTO daemons (name, role, incarnations)
                VALUES ('minion-gamma', 'Engineer', 0)
                """
            )
            m3 = db.execute_insert(
                """
                INSERT INTO possessions (
                    daemon_name, role, possession_log,
                    start_time, status, last_heartbeat_at,
                    created_at, updated_at
                ) VALUES (
                    'minion-gamma', 'Engineer',
                    '.opencode/work/possessions/minion-3.md',
                    '09:00:00', 'ACTIVE', datetime('now'),
                    datetime('now'), datetime('now')
                )
                """
            )
            msg_mgr = MessageManager(db)
            msg_mgr.send_conversation_message(from_possession_id=m1, to_possession_id=m2, body="From m1")
            msg_mgr.send_conversation_message(from_possession_id=m3, to_possession_id=m2, body="From m3")

        result = runner.invoke(app, ["comms", "minion", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)["data"]
        assert data["unread_count"] == 2
        sender_ids = {msg["from_mission_id"] for msg in data["unread_messages"]}
        assert sender_ids == {m1, m3}

    def test_start_json_with_unread_messages(self, initialized_project: Path):
        """JSON output includes unread message details when messages exist."""
        m1, m2 = _setup_minion_missions(initialized_project)

        db_path = initialized_project / ".opencode" / "data" / "project.db"
        with Database(db_path) as db:
            msg_mgr = MessageManager(db)
            msg_mgr.send_conversation_message(
                from_possession_id=m1,
                to_possession_id=m2,
                body="Question for minion agent",
            )

        result = runner.invoke(app, ["comms", "minion", "--json"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        data = json.loads(result.output)["data"]
        assert data["unread_count"] == 1
        assert len(data["unread_messages"]) == 1
        assert data["unread_messages"][0]["from_mission_id"] == m1


# ===========================================================================
# Scope / epic edge cases
# ===========================================================================


class TestMinionScopeEdgeCases:
    """Tests for minion mode scope behavior with various possession configs."""

    def test_general_possession_minion_mode(self, test_db: Database):
        """General possession (no epic_id) can enter minion mode."""
        mid = _create_possession(test_db, epic_id=None)
        mgr = PossessionManager(test_db)

        mgr.set_minion_mode(mid, active=True)
        possession = mgr.get_possession(mid)
        assert possession is not None
        assert possession.epic_id is None
        assert possession.minion_mode_active is True

    def test_epic_scoped_possession_minion_mode(self, test_db: Database):
        """Epic-scoped possession can enter minion mode; epic_id preserved."""
        _create_epic(test_db, "EPC-H-0042")
        mid = _create_possession(test_db, epic_id="EPC-H-0042")
        mgr = PossessionManager(test_db)

        mgr.set_minion_mode(mid, active=True)
        possession = mgr.get_possession(mid)
        assert possession is not None
        assert possession.epic_id == "EPC-H-0042"
        assert possession.minion_mode_active is True

    def test_minion_toggle_does_not_change_epic_id(self, test_db: Database):
        """Toggling minion mode does not alter epic_id."""
        _create_epic(test_db, "EPC-M-0010")
        mid = _create_possession(test_db, epic_id="EPC-M-0010")
        mgr = PossessionManager(test_db)

        mgr.set_minion_mode(mid, active=True)
        mgr.set_minion_mode(mid, active=False)
        mgr.set_minion_mode(mid, active=True)

        possession = mgr.get_possession(mid)
        assert possession is not None
        assert possession.epic_id == "EPC-M-0010"

    def test_multiple_possessions_independent(self, test_db: Database):
        """Minion mode on one possession doesn't affect another."""
        mid1 = _create_possession(test_db, daemon="test-daemon-a", start_time="10:00:00")
        mid2 = _create_possession(test_db, daemon="test-daemon-b", start_time="11:00:00")
        mgr = PossessionManager(test_db)

        mgr.set_minion_mode(mid1, active=True)

        assert _get_minion_mode(test_db, mid1) is True
        assert _get_minion_mode(test_db, mid2) is False

    def test_active_possession_can_enter_minion_mode(self, test_db: Database):
        """An ACTIVE possession can enter minion mode."""
        mid = _create_possession(test_db)
        mgr = PossessionManager(test_db)

        mgr.set_minion_mode(mid, active=True)
        assert _get_minion_mode(test_db, mid) is True

    def test_minion_mode_persists_across_reads(self, test_db: Database):
        """Minion mode is correctly retrieved on subsequent get_possession() calls."""
        mid = _create_possession(test_db)
        mgr = PossessionManager(test_db)

        mgr.set_minion_mode(mid, active=True)

        possession = mgr.get_possession(mid)
        assert possession is not None
        assert possession.minion_mode_active is True

    def test_heartbeat_preserves_minion_mode(self, test_db: Database):
        """Heartbeat (updating last_heartbeat_at) does not affect minion_mode_active."""
        mid = _create_possession(test_db)
        mgr = PossessionManager(test_db)

        mgr.set_minion_mode(mid, active=True)
        mgr.heartbeat(mid)

        assert _get_minion_mode(test_db, mid) is True


# ===========================================================================
# Auto-disable via CLI (end possession while minion mode active)
# ===========================================================================


class TestAutoDisableOnPossessionExorcismCLI:
    """Test that ending a possession via CLI clears minion mode."""

    def test_end_possession_clears_minion_mode(self, initialized_project: Path):
        """s9 mission end on a minion-active possession clears minion_mode_active."""
        m1, m2 = _setup_minion_missions(initialized_project)
        _set_minion_mode_in_project(initialized_project, m2, True)

        result = runner.invoke(app, ["mission", "end", str(m2)])
        assert result.exit_code == 0, f"End possession failed: {result.output}"

        assert _get_minion_mode_in_project(initialized_project, m2) is False

    def test_end_possession_without_minion_mode(self, initialized_project: Path):
        """Ending a possession without minion mode active also works."""
        m1, m2 = _setup_minion_missions(initialized_project)
        assert _get_minion_mode_in_project(initialized_project, m2) is False

        result = runner.invoke(app, ["mission", "end", str(m2)])
        assert result.exit_code == 0, f"End possession failed: {result.output}"

        assert _get_minion_mode_in_project(initialized_project, m2) is False
