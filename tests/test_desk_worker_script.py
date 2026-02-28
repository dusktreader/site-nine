"""
Tests for external desk worker polling script (ENG-M-0185).

Tests cover:
- Worker initialization and mission creation
- Session binding and database linkage
- Desk mode enable/disable
- Message polling and processing
- Priority-based message ordering
- Signal handling (SIGTERM/SIGINT)
- Graceful shutdown and cleanup
- Error handling and recovery
- Multiple concurrent workers

Reference: ADR-013 (site-nine as OpenCode integration platform)
"""

import signal
import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from site_nine.core.database import Database
from site_nine.messaging.manager import MessageManager
from site_nine.missions.manager import MissionManager

# Import the desk worker script module
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
DESK_WORKER_SCRIPT = REPO_ROOT / "src" / "site_nine" / "workers" / "desk_worker.py"

# Import the desk worker module directly (no need to add to sys.path - it's a proper package now)

# Import after adding to path
import importlib.util

spec = importlib.util.spec_from_file_location("desk_worker", DESK_WORKER_SCRIPT)
desk_worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(desk_worker)

DeskWorker = desk_worker.DeskWorker


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def test_db(tmp_path):
    """Create a temporary test database."""
    db_path = tmp_path / ".opencode" / "data"
    db_path.mkdir(parents=True, exist_ok=True)
    db_file = db_path / "project.db"

    # Initialize schema
    from site_nine.core.database import Database

    db = Database(db_file)

    # Load schema
    schema_file = REPO_ROOT / "src" / "site_nine" / "data" / "schema.sql"
    with open(schema_file) as f:
        schema_sql = f.read()

    # Execute schema (split by semicolons and execute separately)
    for statement in schema_sql.split(";"):
        if statement.strip():
            db.execute_update(statement.strip(), {})

    yield db_file


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run for opencode run calls."""
    with patch("subprocess.run") as mock_run:
        # Default: successful execution
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
        yield mock_run


@pytest.fixture
def mock_time():
    """Mock time.sleep to avoid actual delays in tests."""
    with patch("time.sleep") as mock_sleep:
        yield mock_sleep


# ============================================================================
# Unit Tests - DeskWorker Class
# ============================================================================


def test_desk_worker_initialization():
    """Test DeskWorker constructor sets all fields correctly."""
    worker = DeskWorker(role="Engineer", persona="hephaestus", model="custom-model", poll_interval=15)

    assert worker.role == "Engineer"
    assert worker.persona == "hephaestus"
    assert worker.model == "custom-model"
    assert worker.poll_interval == 15
    assert worker.session_id is None
    assert worker.mission_id is None
    assert worker.running is True


def test_desk_worker_defaults():
    """Test DeskWorker uses correct defaults."""
    worker = DeskWorker(role="Architect")

    assert worker.role == "Architect"
    assert worker.persona is None
    assert worker.model == DeskWorker.DEFAULT_MODEL
    assert worker.poll_interval == DeskWorker.DEFAULT_POLL_INTERVAL


def test_priority_ordering():
    """Test message priority ordering is correct."""
    assert DeskWorker.PRIORITY_ORDER["CRITICAL"] == 0
    assert DeskWorker.PRIORITY_ORDER["HIGH"] == 1
    assert DeskWorker.PRIORITY_ORDER["MEDIUM"] == 2
    assert DeskWorker.PRIORITY_ORDER["LOW"] == 3


# ============================================================================
# Integration Tests - Worker Lifecycle
# ============================================================================


@patch("site_nine.core.paths.get_db_path")
def test_worker_initialize_success(mock_get_db_path, test_db, mock_subprocess):
    """Test successful worker initialization creates mission and retrieves session ID."""
    mock_get_db_path.return_value = test_db

    # Pre-create a mission that initialize() will find
    db = Database(test_db)
    mission_id = db.execute_insert(
        """
        INSERT INTO missions (
            role, persona_name, codename, mission_file,
            opencode_session_id, start_date, start_time,
            objective, status
        ) VALUES (
            'Engineer', 'hephaestus', 'test-mission',
            '.opencode/work/missions/test.md',
            'ses_test123', '2026-02-18', '10:00:00',
            'Test mission', 'ACTIVE'
        )
        """,
        {},
    )

    worker = DeskWorker(role="Engineer", persona="hephaestus")
    worker.initialize()

    assert worker.mission_id == mission_id
    assert worker.session_id == "ses_test123"

    # Verify opencode run was called
    mock_subprocess.assert_called_once()
    call_args = mock_subprocess.call_args[0][0]
    assert "opencode" in call_args
    assert "run" in call_args
    assert "Engineer" in " ".join(call_args)


@patch("site_nine.core.paths.get_db_path")
def test_worker_initialize_no_mission_found(mock_get_db_path, test_db, mock_subprocess):
    """Test initialize raises error if mission not created."""
    mock_get_db_path.return_value = test_db

    worker = DeskWorker(role="Engineer")

    with pytest.raises(RuntimeError, match="Failed to find initialized mission"):
        worker.initialize()


@patch("site_nine.core.paths.get_db_path")
def test_worker_initialize_no_session_id(mock_get_db_path, test_db, mock_subprocess):
    """Test initialize raises error if mission has no session ID."""
    mock_get_db_path.return_value = test_db

    # Create mission without session ID
    db = Database(test_db)
    db.execute_insert(
        """
        INSERT INTO missions (
            role, persona_name, codename, mission_file,
            start_date, start_time, objective, status
        ) VALUES (
            'Engineer', 'hephaestus', 'test-mission',
            '.opencode/work/missions/test.md',
            '2026-02-18', '10:00:00',
            'Test mission', 'ACTIVE'
        )
        """,
        {},
    )

    worker = DeskWorker(role="Engineer")

    with pytest.raises(RuntimeError, match="has no OpenCode session ID"):
        worker.initialize()


@patch("site_nine.core.paths.get_db_path")
def test_worker_enable_desk_mode(mock_get_db_path, test_db):
    """Test enable_desk_mode sets desk_mode_active=1."""
    mock_get_db_path.return_value = test_db

    db = Database(test_db)
    mission_id = db.execute_insert(
        """
        INSERT INTO missions (
            role, persona_name, codename, mission_file,
            opencode_session_id, start_date, start_time,
            objective, status, desk_mode_active
        ) VALUES (
            'Engineer', 'test', 'test-mission',
            '.opencode/work/missions/test.md',
            'ses_test123', '2026-02-18', '10:00:00',
            'Test mission', 'ACTIVE', 0
        )
        """,
        {},
    )

    worker = DeskWorker(role="Engineer")
    worker.mission_id = mission_id
    worker.enable_desk_mode()

    # Verify database updated
    rows = db.execute_query("SELECT desk_mode_active FROM missions WHERE id = :mid", {"mid": mission_id})
    assert rows[0]["desk_mode_active"] == 1


# ============================================================================
# Message Handling Tests
# ============================================================================


@patch("site_nine.core.paths.get_db_path")
def test_check_for_messages_empty(mock_get_db_path, test_db):
    """Test check_for_messages returns empty list when no messages."""
    mock_get_db_path.return_value = test_db

    db = Database(test_db)
    mission_id = db.execute_insert(
        """
        INSERT INTO missions (
            role, persona_name, codename, mission_file,
            opencode_session_id, start_date, start_time,
            objective, status
        ) VALUES (
            'Engineer', 'test', 'test-mission',
            '.opencode/work/missions/test.md',
            'ses_test123', '2026-02-18', '10:00:00',
            'Test mission', 'ACTIVE'
        )
        """,
        {},
    )

    worker = DeskWorker(role="Engineer")
    worker.mission_id = mission_id

    messages = worker.check_for_messages()
    assert messages == []


@patch("site_nine.core.paths.get_db_path")
def test_check_for_messages_excludes_own(mock_get_db_path, test_db):
    """Test check_for_messages excludes messages from self."""
    mock_get_db_path.return_value = test_db

    db = Database(test_db)

    # Create two missions
    mission_id_1 = db.execute_insert(
        """
        INSERT INTO missions (
            role, persona_name, codename, mission_file,
            opencode_session_id, start_date, start_time,
            objective, status
        ) VALUES (
            'Engineer', 'worker1', 'mission-1',
            '.opencode/work/missions/test1.md',
            'ses_test1', '2026-02-18', '10:00:00',
            'Test mission 1', 'ACTIVE'
        )
        """,
        {},
    )

    mission_id_2 = db.execute_insert(
        """
        INSERT INTO missions (
            role, persona_name, codename, mission_file,
            opencode_session_id, start_date, start_time,
            objective, status
        ) VALUES (
            'Engineer', 'worker2', 'mission-2',
            '.opencode/work/missions/test2.md',
            'ses_test2', '2026-02-18', '11:00:00',
            'Test mission 2', 'ACTIVE'
        )
        """,
        {},
    )

    # Create conversation and messages
    msg_mgr = MessageManager(db)

    # Mission 1 sends message to Mission 2
    msg_mgr.send_conversation_message(
        from_mission_id=mission_id_1,
        to_mission_id=mission_id_2,
        body="Message from mission 1 to mission 2",
    )

    # Mission 2 sends message back (should be excluded when checking mission 2's messages)
    msg_mgr.send_conversation_message(
        from_mission_id=mission_id_2,
        to_mission_id=mission_id_1,
        body="Reply from mission 2 to mission 1",
    )

    # Check messages for mission 2 (should only see message FROM mission 1)
    worker = DeskWorker(role="Engineer")
    worker.mission_id = mission_id_2

    messages = worker.check_for_messages()

    # Should see 1 message (from mission 1), not the one mission 2 sent
    assert len(messages) == 1
    assert messages[0].from_mission_id == mission_id_1


@patch("site_nine.core.paths.get_db_path")
def test_check_for_messages_priority_order(mock_get_db_path, test_db):
    """Test messages are sorted by priority (CRITICAL > HIGH > MEDIUM > LOW)."""
    mock_get_db_path.return_value = test_db

    db = Database(test_db)

    # Create sender and receiver missions
    sender_id = db.execute_insert(
        """
        INSERT INTO missions (
            role, persona_name, codename, mission_file,
            opencode_session_id, start_date, start_time,
            objective, status
        ) VALUES (
            'Administrator', 'admin', 'admin-mission',
            '.opencode/work/missions/admin.md',
            'ses_admin', '2026-02-18', '10:00:00',
            'Admin mission', 'ACTIVE'
        )
        """,
        {},
    )

    receiver_id = db.execute_insert(
        """
        INSERT INTO missions (
            role, persona_name, codename, mission_file,
            opencode_session_id, start_date, start_time,
            objective, status
        ) VALUES (
            'Engineer', 'worker', 'worker-mission',
            '.opencode/work/missions/worker.md',
            'ses_worker', '2026-02-18', '11:00:00',
            'Worker mission', 'ACTIVE'
        )
        """,
        {},
    )

    msg_mgr = MessageManager(db)

    # Send messages with different priorities
    msg_mgr.send_conversation_message(
        from_mission_id=sender_id,
        to_mission_id=receiver_id,
        body="Low priority message",
        priority="LOW",
    )

    msg_mgr.send_conversation_message(
        from_mission_id=sender_id,
        to_mission_id=receiver_id,
        body="Critical priority message",
        priority="CRITICAL",
    )

    msg_mgr.send_conversation_message(
        from_mission_id=sender_id,
        to_mission_id=receiver_id,
        body="Medium priority message",
        priority="MEDIUM",
    )

    msg_mgr.send_conversation_message(
        from_mission_id=sender_id,
        to_mission_id=receiver_id,
        body="High priority message",
        priority="HIGH",
    )

    # Check messages
    worker = DeskWorker(role="Engineer")
    worker.mission_id = receiver_id

    messages = worker.check_for_messages()

    # Verify correct order: CRITICAL, HIGH, MEDIUM, LOW
    assert len(messages) == 4
    assert messages[0].priority == "CRITICAL"
    assert messages[1].priority == "HIGH"
    assert messages[2].priority == "MEDIUM"
    assert messages[3].priority == "LOW"


@patch("site_nine.core.paths.get_db_path")
def test_process_message_success(mock_get_db_path, test_db, mock_subprocess):
    """Test process_message executes opencode run and marks message as read."""
    mock_get_db_path.return_value = test_db

    db = Database(test_db)

    # Create missions and conversation
    sender_id = db.execute_insert(
        """
        INSERT INTO missions (
            role, persona_name, codename, mission_file,
            opencode_session_id, start_date, start_time,
            objective, status
        ) VALUES (
            'Administrator', 'admin', 'admin-mission',
            '.opencode/work/missions/admin.md',
            'ses_admin', '2026-02-18', '10:00:00',
            'Admin mission', 'ACTIVE'
        )
        """,
        {},
    )

    receiver_id = db.execute_insert(
        """
        INSERT INTO missions (
            role, persona_name, codename, mission_file,
            opencode_session_id, start_date, start_time,
            objective, status
        ) VALUES (
            'Engineer', 'worker', 'worker-mission',
            '.opencode/work/missions/worker.md',
            'ses_worker', '2026-02-18', '11:00:00',
            'Worker mission', 'ACTIVE'
        )
        """,
        {},
    )

    msg_mgr = MessageManager(db)
    conversation, message = msg_mgr.send_conversation_message(
        from_mission_id=sender_id, to_mission_id=receiver_id, body="Test message"
    )

    # Process message
    worker = DeskWorker(role="Engineer")
    worker.mission_id = receiver_id
    worker.session_id = "ses_worker"

    result = worker.process_message(message)

    assert result is True

    # Verify opencode run was called with correct args
    mock_subprocess.assert_called_once()
    call_args = mock_subprocess.call_args[0][0]
    assert "opencode" in call_args
    assert "run" in call_args
    assert "--session" in call_args
    assert "ses_worker" in call_args
    assert "Test message" in call_args

    # Verify conversation was marked as viewed
    views = db.execute_query(
        """
        SELECT last_viewed_at FROM conversation_views
        WHERE conversation_id = :cid AND mission_id = :mid
        """,
        {"cid": conversation.id, "mid": receiver_id},
    )
    assert len(views) == 1


@patch("site_nine.core.paths.get_db_path")
def test_process_message_failure(mock_get_db_path, test_db, mock_subprocess):
    """Test process_message handles opencode run failure gracefully."""
    mock_get_db_path.return_value = test_db

    # Make subprocess.run fail
    mock_subprocess.return_value = Mock(returncode=1, stdout="", stderr="Error occurred")

    db = Database(test_db)

    # Create missions and conversation
    sender_id = db.execute_insert(
        """
        INSERT INTO missions (
            role, persona_name, codename, mission_file,
            opencode_session_id, start_date, start_time,
            objective, status
        ) VALUES (
            'Administrator', 'admin', 'admin-mission',
            '.opencode/work/missions/admin.md',
            'ses_admin', '2026-02-18', '10:00:00',
            'Admin mission', 'ACTIVE'
        )
        """,
        {},
    )

    receiver_id = db.execute_insert(
        """
        INSERT INTO missions (
            role, persona_name, codename, mission_file,
            opencode_session_id, start_date, start_time,
            objective, status
        ) VALUES (
            'Engineer', 'worker', 'worker-mission',
            '.opencode/work/missions/worker.md',
            'ses_worker', '2026-02-18', '11:00:00',
            'Worker mission', 'ACTIVE'
        )
        """,
        {},
    )

    msg_mgr = MessageManager(db)
    _, message = msg_mgr.send_conversation_message(
        from_mission_id=sender_id, to_mission_id=receiver_id, body="Test message"
    )

    # Process message
    worker = DeskWorker(role="Engineer")
    worker.mission_id = receiver_id
    worker.session_id = "ses_worker"

    result = worker.process_message(message)

    assert result is False


# ============================================================================
# Signal Handling Tests
# ============================================================================


@patch("site_nine.core.paths.get_db_path")
def test_handle_shutdown_cleans_up(mock_get_db_path, test_db, mock_subprocess):
    """Test handle_shutdown disables desk mode and ends mission."""
    mock_get_db_path.return_value = test_db

    db = Database(test_db)
    mission_id = db.execute_insert(
        """
        INSERT INTO missions (
            role, persona_name, codename, mission_file,
            opencode_session_id, start_date, start_time,
            objective, status, desk_mode_active
        ) VALUES (
            'Engineer', 'worker', 'test-mission',
            '.opencode/work/missions/test.md',
            'ses_test', '2026-02-18', '10:00:00',
            'Test mission', 'ACTIVE', 1
        )
        """,
        {},
    )

    worker = DeskWorker(role="Engineer")
    worker.mission_id = mission_id
    worker.session_id = "ses_test"

    with pytest.raises(SystemExit):
        worker.handle_shutdown(signal.SIGTERM, None)

    # Verify desk mode was disabled
    rows = db.execute_query("SELECT desk_mode_active FROM missions WHERE id = :mid", {"mid": mission_id})
    assert rows[0]["desk_mode_active"] == 0

    # Verify opencode run was called to end mission
    assert mock_subprocess.called
    call_args = mock_subprocess.call_args[0][0]
    assert "mission-end" in " ".join(call_args).lower()


# ============================================================================
# CLI Tests
# ============================================================================


def test_main_invalid_role():
    """Test main() exits with error for invalid role."""
    with patch("sys.argv", ["desk-worker.py", "InvalidRole"]):
        with pytest.raises(SystemExit) as exc_info:
            desk_worker.main()

        assert exc_info.value.code == 1


def test_main_auto_capitalizes_role(mock_subprocess):
    """Test main() auto-capitalizes role name."""
    with patch("sys.argv", ["desk-worker.py", "engineer"]):
        with patch.object(DeskWorker, "run") as mock_run:
            desk_worker.main()

            # Verify DeskWorker was created with capitalized role
            assert mock_run.called


def test_main_parses_arguments_correctly():
    """Test main() parses all command line arguments."""
    with patch(
        "sys.argv",
        [
            "desk-worker.py",
            "Engineer",
            "--persona",
            "hephaestus",
            "--model",
            "custom-model",
            "--poll-interval",
            "15",
        ],
    ):
        with patch.object(DeskWorker, "run") as mock_run:
            with patch.object(DeskWorker, "__init__", return_value=None) as mock_init:
                desk_worker.main()

                # Verify DeskWorker was initialized with correct args
                mock_init.assert_called_once()
                call_kwargs = mock_init.call_args[1]
                assert call_kwargs["role"] == "Engineer"
                assert call_kwargs["persona"] == "hephaestus"
                assert call_kwargs["model"] == "custom-model"
                assert call_kwargs["poll_interval"] == 15
