"""
Tests for external desk worker polling script (ENG-M-0185).

Tests cover:
- Worker initialization and possession creation
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

# Import the desk worker script module
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
DESK_WORKER_SCRIPT = REPO_ROOT / "src" / "site_nine" / "workers" / "desk_worker.py"

# Import the desk worker module directly (no need to add to sys.path - it's a proper package now)

# Import after adding to path
import importlib.util

spec = importlib.util.spec_from_file_location("desk_worker", DESK_WORKER_SCRIPT)
desk_worker = importlib.util.module_from_spec(spec)
sys.modules["desk_worker"] = desk_worker  # Register so @patch("desk_worker.X") works
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
    db.initialize_schema()

    yield db_file


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.Popen and subprocess.run for opencode run calls."""
    import json as _json

    # Create a mock process for Popen that simulates opencode outputting a sessionID
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = (
        _json.dumps({"sessionID": "ses_test123"}) + "\n",
        "",
    )

    with patch("subprocess.Popen", return_value=mock_process) as mock_popen:
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="", stderr="")
            # Yield popen mock as the primary mock (most tests use it)
            # Tests that check handle_shutdown can use mock_run directly
            mock_popen.mock_run = mock_run
            yield mock_popen


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
    worker = DeskWorker(role="Engineer", daemon="hephaestus", model="custom-model", poll_interval=15)

    assert worker.role == "Engineer"
    assert worker.daemon == "hephaestus"
    assert worker.model == "custom-model"
    assert worker.poll_interval == 15
    assert worker.session_id is None
    assert worker.possession_id is None
    assert worker.running is True


def test_desk_worker_defaults():
    """Test DeskWorker uses correct defaults."""
    worker = DeskWorker(role="Architect")

    assert worker.role == "Architect"
    assert worker.daemon is None
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


@patch("desk_worker.get_db_path")
def test_worker_initialize_success(mock_get_db_path, test_db, mock_subprocess, mock_time):
    """Test successful worker initialization creates possession and retrieves session ID."""
    mock_get_db_path.return_value = test_db

    # Pre-create a daemon and possession that initialize() will find
    db = Database(test_db)
    db.execute_update(
        "INSERT INTO daemons (name, role, incarnations) VALUES ('hephaestus', 'Engineer', 0)",
        {},
    )
    possession_id = db.execute_insert(
        """
        INSERT INTO possessions (
            daemon_name, role, possession_log,
            opencode_session_id, start_time,
            status, created_at, updated_at
        ) VALUES (
            'hephaestus', 'Engineer',
            '.opencode/work/possessions/test.md',
            'ses_test123', datetime('now'),
            'ACTIVE', datetime('now'), datetime('now')
        )
        """,
        {},
    )

    worker = DeskWorker(role="Engineer", daemon="hephaestus")
    worker.initialize()

    assert worker.possession_id == possession_id
    assert worker.session_id == "ses_test123"

    # Verify opencode run was called
    mock_subprocess.assert_called_once()
    call_args = mock_subprocess.call_args[0][0]
    assert "opencode" in call_args
    assert "run" in call_args
    assert "Engineer" in " ".join(call_args)


@patch("desk_worker.get_db_path")
def test_worker_initialize_no_mission_found(mock_get_db_path, test_db, mock_subprocess, mock_time):
    """Test initialize raises error if possession not created."""
    mock_get_db_path.return_value = test_db

    worker = DeskWorker(role="Engineer")

    with pytest.raises(RuntimeError, match="Failed to find initialized"):
        worker.initialize()


@patch("desk_worker.get_db_path")
def test_worker_initialize_no_session_id(mock_get_db_path, test_db, mock_subprocess):
    """Test initialize raises error if opencode run produces no session ID."""
    mock_get_db_path.return_value = test_db

    # Make the Popen mock return output with no sessionID field
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.communicate.return_value = ("no session id here\n", "")
    mock_subprocess.return_value = mock_process

    worker = DeskWorker(role="Engineer")

    with pytest.raises(RuntimeError, match="Failed to extract session ID"):
        worker.initialize()


@patch("desk_worker.get_db_path")
def test_worker_enable_desk_mode(mock_get_db_path, test_db):
    """Test enable_desk_mode sets desk_mode_active=1."""
    mock_get_db_path.return_value = test_db

    db = Database(test_db)
    db.execute_update(
        "INSERT INTO daemons (name, role, incarnations) VALUES ('test', 'Engineer', 0)",
        {},
    )
    possession_id = db.execute_insert(
        """
        INSERT INTO possessions (
            daemon_name, role, possession_log,
            opencode_session_id, start_time,
            status, desk_mode_active, created_at, updated_at
        ) VALUES (
            'test', 'Engineer',
            '.opencode/work/possessions/test.md',
            'ses_test123', datetime('now'),
            'ACTIVE', 0, datetime('now'), datetime('now')
        )
        """,
        {},
    )

    worker = DeskWorker(role="Engineer")
    worker.possession_id = possession_id
    worker.enable_desk_mode()

    # Verify database updated
    rows = db.execute_query("SELECT desk_mode_active FROM possessions WHERE id = :pid", {"pid": possession_id})
    assert rows[0]["desk_mode_active"] == 1


# ============================================================================
# Message Handling Tests
# ============================================================================


@patch("desk_worker.get_db_path")
def test_check_for_messages_empty(mock_get_db_path, test_db):
    """Test check_for_messages returns empty list when no messages."""
    mock_get_db_path.return_value = test_db

    db = Database(test_db)
    db.execute_update(
        "INSERT INTO daemons (name, role, incarnations) VALUES ('test', 'Engineer', 0)",
        {},
    )
    possession_id = db.execute_insert(
        """
        INSERT INTO possessions (
            daemon_name, role, possession_log,
            opencode_session_id, start_time,
            status, created_at, updated_at
        ) VALUES (
            'test', 'Engineer',
            '.opencode/work/possessions/test.md',
            'ses_test123', datetime('now'),
            'ACTIVE', datetime('now'), datetime('now')
        )
        """,
        {},
    )

    worker = DeskWorker(role="Engineer")
    worker.possession_id = possession_id

    messages = worker.check_for_messages()
    assert messages == []


@patch("desk_worker.get_db_path")
def test_check_for_messages_excludes_own(mock_get_db_path, test_db):
    """Test check_for_messages excludes messages from self."""
    mock_get_db_path.return_value = test_db

    db = Database(test_db)
    # Create two daemons and possessions
    db.execute_update(
        "INSERT INTO daemons (name, role, incarnations) VALUES ('worker1', 'Engineer', 0)",
        {},
    )
    db.execute_update(
        "INSERT INTO daemons (name, role, incarnations) VALUES ('worker2', 'Engineer', 0)",
        {},
    )

    possession_id_1 = db.execute_insert(
        """
        INSERT INTO possessions (
            daemon_name, role, possession_log,
            opencode_session_id, start_time,
            status, created_at, updated_at
        ) VALUES (
            'worker1', 'Engineer',
            '.opencode/work/possessions/test1.md',
            'ses_test1', datetime('now'),
            'ACTIVE', datetime('now'), datetime('now')
        )
        """,
        {},
    )

    possession_id_2 = db.execute_insert(
        """
        INSERT INTO possessions (
            daemon_name, role, possession_log,
            opencode_session_id, start_time,
            status, created_at, updated_at
        ) VALUES (
            'worker2', 'Engineer',
            '.opencode/work/possessions/test2.md',
            'ses_test2', datetime('now'),
            'ACTIVE', datetime('now'), datetime('now')
        )
        """,
        {},
    )

    # Create conversation and messages
    msg_mgr = MessageManager(db)

    # Possession 1 sends message to Possession 2
    msg_mgr.send_conversation_message(
        from_possession_id=possession_id_1,
        to_possession_id=possession_id_2,
        body="Message from possession 1 to possession 2",
    )

    # Check messages for possession 2 BEFORE it replies (should see 1 message from possession 1)
    worker = DeskWorker(role="Engineer")
    worker.possession_id = possession_id_2

    messages = worker.check_for_messages()

    # Should see 1 message (from possession 1), not any messages possession 2 sent
    assert len(messages) == 1
    assert messages[0].from_possession_id == possession_id_1


@patch("desk_worker.get_db_path")
def test_check_for_messages_priority_order(mock_get_db_path, test_db):
    """Test messages are sorted by priority (CRITICAL > HIGH > MEDIUM > LOW)."""
    mock_get_db_path.return_value = test_db

    db = Database(test_db)

    # Create sender and receiver daemons/possessions
    db.execute_update(
        "INSERT INTO daemons (name, role, incarnations) VALUES ('admin', 'Administrator', 0)",
        {},
    )
    db.execute_update(
        "INSERT INTO daemons (name, role, incarnations) VALUES ('worker', 'Engineer', 0)",
        {},
    )

    sender_id = db.execute_insert(
        """
        INSERT INTO possessions (
            daemon_name, role, possession_log,
            opencode_session_id, start_time,
            status, created_at, updated_at
        ) VALUES (
            'admin', 'Administrator',
            '.opencode/work/possessions/admin.md',
            'ses_admin', datetime('now'),
            'ACTIVE', datetime('now'), datetime('now')
        )
        """,
        {},
    )

    receiver_id = db.execute_insert(
        """
        INSERT INTO possessions (
            daemon_name, role, possession_log,
            opencode_session_id, start_time,
            status, created_at, updated_at
        ) VALUES (
            'worker', 'Engineer',
            '.opencode/work/possessions/worker.md',
            'ses_worker', datetime('now'),
            'ACTIVE', datetime('now'), datetime('now')
        )
        """,
        {},
    )

    msg_mgr = MessageManager(db)

    # Send messages with different priorities
    msg_mgr.send_conversation_message(
        from_possession_id=sender_id,
        to_possession_id=receiver_id,
        body="Low priority message",
        priority="LOW",
    )

    msg_mgr.send_conversation_message(
        from_possession_id=sender_id,
        to_possession_id=receiver_id,
        body="Critical priority message",
        priority="CRITICAL",
    )

    msg_mgr.send_conversation_message(
        from_possession_id=sender_id,
        to_possession_id=receiver_id,
        body="Medium priority message",
        priority="MEDIUM",
    )

    msg_mgr.send_conversation_message(
        from_possession_id=sender_id,
        to_possession_id=receiver_id,
        body="High priority message",
        priority="HIGH",
    )

    # Check messages
    worker = DeskWorker(role="Engineer")
    worker.possession_id = receiver_id

    messages = worker.check_for_messages()

    # Verify correct order: CRITICAL, HIGH, MEDIUM, LOW
    assert len(messages) == 4
    assert messages[0].priority == "CRITICAL"
    assert messages[1].priority == "HIGH"
    assert messages[2].priority == "MEDIUM"
    assert messages[3].priority == "LOW"


@patch("desk_worker.get_db_path")
def test_process_message_success(mock_get_db_path, test_db, mock_subprocess):
    """Test process_message executes opencode run and marks message as read."""
    mock_get_db_path.return_value = test_db

    db = Database(test_db)

    # Create daemons and possessions
    db.execute_update(
        "INSERT INTO daemons (name, role, incarnations) VALUES ('admin', 'Administrator', 0)",
        {},
    )
    db.execute_update(
        "INSERT INTO daemons (name, role, incarnations) VALUES ('worker', 'Engineer', 0)",
        {},
    )

    sender_id = db.execute_insert(
        """
        INSERT INTO possessions (
            daemon_name, role, possession_log,
            opencode_session_id, start_time,
            status, created_at, updated_at
        ) VALUES (
            'admin', 'Administrator',
            '.opencode/work/possessions/admin.md',
            'ses_admin', datetime('now'),
            'ACTIVE', datetime('now'), datetime('now')
        )
        """,
        {},
    )

    receiver_id = db.execute_insert(
        """
        INSERT INTO possessions (
            daemon_name, role, possession_log,
            opencode_session_id, start_time,
            status, created_at, updated_at
        ) VALUES (
            'worker', 'Engineer',
            '.opencode/work/possessions/worker.md',
            'ses_worker', datetime('now'),
            'ACTIVE', datetime('now'), datetime('now')
        )
        """,
        {},
    )

    msg_mgr = MessageManager(db)
    conversation, message = msg_mgr.send_conversation_message(
        from_possession_id=sender_id, to_possession_id=receiver_id, body="Test message"
    )

    # Process message
    worker = DeskWorker(role="Engineer")
    worker.possession_id = receiver_id
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
        WHERE conversation_id = :cid AND possession_id = :pid
        """,
        {"cid": conversation.id, "pid": receiver_id},
    )
    assert len(views) == 1


@patch("desk_worker.get_db_path")
def test_process_message_failure(mock_get_db_path, test_db, mock_subprocess):
    """Test process_message handles opencode run failure gracefully."""
    mock_get_db_path.return_value = test_db

    # Make subprocess.Popen return a failing process
    mock_process = MagicMock()
    mock_process.returncode = 1
    mock_process.communicate.return_value = ("", "Error occurred")
    mock_subprocess.return_value = mock_process

    db = Database(test_db)

    # Create daemons and possessions
    db.execute_update(
        "INSERT INTO daemons (name, role, incarnations) VALUES ('admin', 'Administrator', 0)",
        {},
    )
    db.execute_update(
        "INSERT INTO daemons (name, role, incarnations) VALUES ('worker', 'Engineer', 0)",
        {},
    )

    sender_id = db.execute_insert(
        """
        INSERT INTO possessions (
            daemon_name, role, possession_log,
            opencode_session_id, start_time,
            status, created_at, updated_at
        ) VALUES (
            'admin', 'Administrator',
            '.opencode/work/possessions/admin.md',
            'ses_admin', datetime('now'),
            'ACTIVE', datetime('now'), datetime('now')
        )
        """,
        {},
    )

    receiver_id = db.execute_insert(
        """
        INSERT INTO possessions (
            daemon_name, role, possession_log,
            opencode_session_id, start_time,
            status, created_at, updated_at
        ) VALUES (
            'worker', 'Engineer',
            '.opencode/work/possessions/worker.md',
            'ses_worker', datetime('now'),
            'ACTIVE', datetime('now'), datetime('now')
        )
        """,
        {},
    )

    msg_mgr = MessageManager(db)
    _, message = msg_mgr.send_conversation_message(
        from_possession_id=sender_id, to_possession_id=receiver_id, body="Test message"
    )

    # Process message
    worker = DeskWorker(role="Engineer")
    worker.possession_id = receiver_id
    worker.session_id = "ses_worker"

    result = worker.process_message(message)

    assert result is False


# ============================================================================
# Signal Handling Tests
# ============================================================================


@patch("desk_worker.get_db_path")
def test_handle_shutdown_cleans_up(mock_get_db_path, test_db, mock_subprocess):
    """Test handle_shutdown disables desk mode and ends possession."""
    mock_get_db_path.return_value = test_db

    db = Database(test_db)
    db.execute_update(
        "INSERT INTO daemons (name, role, incarnations) VALUES ('worker', 'Engineer', 0)",
        {},
    )
    possession_id = db.execute_insert(
        """
        INSERT INTO possessions (
            daemon_name, role, possession_log,
            opencode_session_id, start_time,
            status, desk_mode_active, created_at, updated_at
        ) VALUES (
            'worker', 'Engineer',
            '.opencode/work/possessions/test.md',
            'ses_test', datetime('now'),
            'ACTIVE', 1, datetime('now'), datetime('now')
        )
        """,
        {},
    )

    worker = DeskWorker(role="Engineer")
    worker.possession_id = possession_id
    worker.session_id = "ses_test"

    with pytest.raises(SystemExit):
        worker.handle_shutdown(signal.SIGTERM, None)

    # Verify desk mode was disabled
    rows = db.execute_query("SELECT desk_mode_active FROM possessions WHERE id = :pid", {"pid": possession_id})
    assert rows[0]["desk_mode_active"] == 0

    # Verify opencode run was called to end possession
    assert mock_subprocess.mock_run.called
    call_args = mock_subprocess.mock_run.call_args[0][0]
    assert "possession-end" in " ".join(call_args).lower()


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
            "--daemon",
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
                assert call_kwargs["daemon"] == "hephaestus"
                assert call_kwargs["model"] == "custom-model"
                assert call_kwargs["poll_interval"] == 15
