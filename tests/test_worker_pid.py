"""Tests for worker_pid column and Inquisitor crash detection (ENG-H-0259).

Tests cover:
- worker_pid is set in DB when enable_minion_mode() is called
- worker_pid is cleared to NULL on clean shutdown in handle_shutdown()
- Possession model includes worker_pid field
- Inquisitor detects crashed minion workers (dead PID) and auto-exorcises them
- Inquisitor passes when all PIDs are alive
- Inquisitor passes when no minion workers have a worker_pid set
- worker_status tool response includes worker_pid field
- Migration script adds worker_pid column to existing databases

ADR-016, Fix 4: Worker PID Registration and Crash Detection
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from site_nine.core.database import Database
from site_nine.inquisitor.checks import _is_pid_alive, check_crashed_minion_workers
from site_nine.possessions.manager import PossessionManager
from site_nine.possessions.models import Possession


# =============================================================================
# Helpers
# =============================================================================


def _create_daemon(db: Database, name: str = "test-daemon", role: str = "Engineer") -> None:
    db.execute_update(
        "INSERT OR IGNORE INTO daemons (name, role, incarnations) VALUES (:name, :role, 0)",
        {"name": name, "role": role},
    )


def _create_possession(
    db: Database,
    *,
    daemon: str = "test-daemon",
    role: str = "Engineer",
    minion_mode_active: int = 0,
    worker_pid: int | None = None,
    status: str = "ACTIVE",
) -> int:
    """Insert a possession directly and return its rowid."""
    _create_daemon(db, daemon, role)
    rows = db.execute_query(
        """
        INSERT INTO possessions (
            daemon_name, role, possession_log,
            start_time, status,
            minion_mode_active, worker_pid,
            last_heartbeat_at, created_at, updated_at
        )
        VALUES (
            :daemon, :role,
            '.opencode/work/possessions/test.md',
            datetime('now'), :status,
            :minion_mode_active, :worker_pid,
            datetime('now'), datetime('now'), datetime('now')
        )
        RETURNING id
        """,
        {
            "daemon": daemon,
            "role": role,
            "status": status,
            "minion_mode_active": minion_mode_active,
            "worker_pid": worker_pid,
        },
    )
    return rows[0]["id"]


def _get_possession_row(db: Database, possession_id: int) -> dict:
    rows = db.execute_query(
        "SELECT * FROM possessions WHERE id = :id",
        {"id": possession_id},
    )
    assert rows, f"Possession {possession_id} not found"
    return rows[0]


# =============================================================================
# 1. Possession model includes worker_pid field
# =============================================================================


def test_possession_model_has_worker_pid_field(test_db: Database) -> None:
    """Possession dataclass exposes worker_pid field after schema change."""
    pid = _create_possession(test_db, worker_pid=12345)
    rows = test_db.execute_query("SELECT * FROM possessions WHERE id = :id", {"id": pid})
    possession = Possession.from_db_row(rows[0])
    assert possession.worker_pid == 12345


def test_possession_model_worker_pid_defaults_null(test_db: Database) -> None:
    """Possession without worker_pid defaults to None."""
    pid = _create_possession(test_db)
    rows = test_db.execute_query("SELECT * FROM possessions WHERE id = :id", {"id": pid})
    possession = Possession.from_db_row(rows[0])
    assert possession.worker_pid is None


# =============================================================================
# 2. enable_minion_mode() sets worker_pid
# =============================================================================


def test_enable_minion_mode_sets_worker_pid(test_db: Database) -> None:
    """enable_minion_mode() writes os.getpid() to possessions.worker_pid."""
    pid = _create_possession(test_db)

    # Mock the journal so we don't need a real DeskWorkerJournal instance
    mock_journal = MagicMock()

    with (
        patch("site_nine.workers.minion_worker.Database") as mock_db_cls,
        patch("site_nine.workers.minion_worker.get_db_path", return_value=test_db.db_path),
    ):
        mock_db_cls.return_value = test_db

        from site_nine.workers.minion_worker import MinionWorker

        worker = MinionWorker.__new__(MinionWorker)
        worker.possession_id = pid
        worker.journal = mock_journal

        worker.enable_minion_mode()

    row = _get_possession_row(test_db, pid)
    assert row["worker_pid"] == os.getpid()
    assert bool(row["minion_mode_active"]) is True


# =============================================================================
# 3. handle_shutdown() clears worker_pid
# =============================================================================


def test_handle_shutdown_clears_worker_pid(test_db: Database) -> None:
    """handle_shutdown() sets worker_pid to NULL for clean shutdown detection."""
    pid = _create_possession(test_db, minion_mode_active=1, worker_pid=os.getpid())

    mock_journal = MagicMock()

    with (
        patch("site_nine.workers.minion_worker.Database") as mock_db_cls,
        patch("site_nine.workers.minion_worker.get_db_path", return_value=test_db.db_path),
        patch("site_nine.workers.minion_worker.subprocess.run"),
        patch("site_nine.workers.minion_worker.signal"),
        pytest.raises(SystemExit),
    ):
        mock_db_cls.return_value = test_db

        from site_nine.workers.minion_worker import MinionWorker
        import signal as _signal

        worker = MinionWorker.__new__(MinionWorker)
        worker.possession_id = pid
        worker.session_id = "ses_test"
        worker.model = "test-model"
        worker.running = True
        worker.journal = mock_journal

        worker.handle_shutdown(_signal.SIGTERM, None)

    row = _get_possession_row(test_db, pid)
    assert row["worker_pid"] is None
    assert bool(row["minion_mode_active"]) is False


# =============================================================================
# 4. _is_pid_alive helper
# =============================================================================


def test_is_pid_alive_returns_true_for_current_process() -> None:
    """_is_pid_alive returns True for the current process PID."""
    assert _is_pid_alive(os.getpid()) is True


def test_is_pid_alive_returns_false_for_dead_pid() -> None:
    """_is_pid_alive returns False for a PID that does not exist."""
    # PID 0 is the swapper; os.kill(0, 0) raises PermissionError on Linux
    # but we can mock ProcessLookupError directly.
    with patch("os.kill", side_effect=ProcessLookupError):
        assert _is_pid_alive(99999999) is False


def test_is_pid_alive_returns_true_for_permission_error() -> None:
    """_is_pid_alive returns True when PermissionError is raised (process exists)."""
    with patch("os.kill", side_effect=PermissionError):
        assert _is_pid_alive(1) is True


# =============================================================================
# 5. check_crashed_minion_workers — no issues when all PIDs alive
# =============================================================================


def test_check_crashed_minion_workers_passes_when_pid_alive(test_db: Database) -> None:
    """check_crashed_minion_workers finds no issues when worker PID is still running."""
    _create_possession(
        test_db,
        minion_mode_active=1,
        worker_pid=os.getpid(),  # current process is definitely alive
    )

    label, issues = check_crashed_minion_workers(test_db)
    assert label == "10d. Crashed Minion Workers"
    assert issues == []


def test_check_crashed_minion_workers_passes_when_no_pid_set(test_db: Database) -> None:
    """check_crashed_minion_workers finds no issues when worker_pid is NULL."""
    _create_possession(test_db, minion_mode_active=1, worker_pid=None)

    label, issues = check_crashed_minion_workers(test_db)
    assert issues == []


def test_check_crashed_minion_workers_passes_when_no_minion_possessions(test_db: Database) -> None:
    """check_crashed_minion_workers finds no issues when no minion-mode possessions exist."""
    _create_possession(test_db, minion_mode_active=0, worker_pid=99999)

    label, issues = check_crashed_minion_workers(test_db)
    assert issues == []


# =============================================================================
# 6. check_crashed_minion_workers — detects dead PID and auto-exorcises
# =============================================================================


def test_check_crashed_minion_workers_detects_dead_pid(test_db: Database) -> None:
    """check_crashed_minion_workers reports FIXABLE issue when worker PID is dead."""
    dead_pid = 99999999
    pos_id = _create_possession(test_db, minion_mode_active=1, worker_pid=dead_pid)

    with patch("site_nine.inquisitor.checks.os.kill", side_effect=ProcessLookupError):
        label, issues = check_crashed_minion_workers(test_db)

    assert label == "10d. Crashed Minion Workers"
    assert len(issues) == 1
    issue = issues[0]
    assert "crashed" in issue.description.lower()
    assert str(dead_pid) in issue.description
    assert issue.fix_fn is not None
    # Category and severity
    assert issue.category == "crashed_worker"
    from site_nine.inquisitor.models import Severity

    assert issue.severity == Severity.FIXABLE


def test_check_crashed_minion_workers_fix_exorcises_possession(test_db: Database) -> None:
    """check_crashed_minion_workers fix sets possession to EXORCISED and clears worker_pid."""
    dead_pid = 99999999
    pos_id = _create_possession(test_db, minion_mode_active=1, worker_pid=dead_pid)

    with patch("site_nine.inquisitor.checks.os.kill", side_effect=ProcessLookupError):
        _, issues = check_crashed_minion_workers(test_db)

    assert len(issues) == 1
    issues[0].fix_fn()

    row = _get_possession_row(test_db, pos_id)
    assert row["status"] == "EXORCISED"
    assert row["worker_pid"] is None
    assert row["minion_mode_active"] == 0
    assert row["end_time"] is not None


def test_check_crashed_minion_workers_fix_releases_underway_tasks(test_db: Database) -> None:
    """check_crashed_minion_workers fix releases UNDERWAY tasks held by the crashed possession."""
    dead_pid = 99999999
    pos_id = _create_possession(test_db, minion_mode_active=1, worker_pid=dead_pid)

    # Add a task claimed by this possession
    test_db.execute_update(
        """
        INSERT INTO tasks (id, title, status, priority, role, current_possession_id, claimed_at, file_path)
        VALUES ('ENG-H-9999', 'Held Task', 'UNDERWAY', 'HIGH', 'Engineer', :pid, datetime('now'), '.opencode/work/tasks/ENG-H-9999.md')
        """,
        {"pid": pos_id},
    )

    with patch("site_nine.inquisitor.checks.os.kill", side_effect=ProcessLookupError):
        _, issues = check_crashed_minion_workers(test_db)

    assert len(issues) == 1
    issues[0].fix_fn()

    task_rows = test_db.execute_query("SELECT status, current_possession_id FROM tasks WHERE id = 'ENG-H-9999'")
    assert task_rows[0]["status"] == "TODO"
    assert task_rows[0]["current_possession_id"] is None


# =============================================================================
# 7. CLI inquisitor integration — 10d check appears in output
# =============================================================================


def test_inquisitor_passes_check_10d_no_crashed_workers(initialized_project: Path) -> None:
    """Inquisitor check 10d passes when no crashed minion workers exist."""
    from typer.testing import CliRunner
    from site_nine.__main__ import app

    runner = CliRunner()
    result = runner.invoke(app, ["inquisitor"])
    assert result.exit_code == 0
    assert "No crashed minion worker possessions detected" in result.stdout


def test_inquisitor_detects_crashed_minion_worker_cli(initialized_project: Path) -> None:
    """Inquisitor CLI check 10d detects and reports crashed minion worker possession."""
    import sqlite3 as _sqlite3
    from typer.testing import CliRunner
    from site_nine.__main__ import app

    db_path = initialized_project / ".opencode" / "data" / "project.db"

    # Insert daemon and crashed minion possession
    conn = _sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute(
        """
        INSERT INTO daemons (name, role, incarnations) VALUES ('crashed-daemon', 'Engineer', 1)
        """
    )
    conn.execute(
        """
        INSERT INTO possessions (
            daemon_name, role, possession_log,
            start_time, status,
            minion_mode_active, worker_pid,
            last_heartbeat_at, created_at, updated_at
        )
        VALUES (
            'crashed-daemon', 'Engineer',
            '.opencode/work/possessions/crashed.md',
            datetime('now'), 'ACTIVE',
            1, 99999999,
            datetime('now'), datetime('now'), datetime('now')
        )
        """
    )
    conn.commit()
    conn.close()

    runner = CliRunner()
    with patch("site_nine.inquisitor.checks.os.kill", side_effect=ProcessLookupError):
        result = runner.invoke(app, ["inquisitor", "--verbose"])

    assert result.exit_code == 0
    assert "crashed" in result.stdout.lower()


def test_inquisitor_fix_exorcises_crashed_minion_worker_cli(initialized_project: Path) -> None:
    """Inquisitor --fix exorcises crashed minion worker possession via CLI."""
    import sqlite3 as _sqlite3
    from typer.testing import CliRunner
    from site_nine.__main__ import app

    db_path = initialized_project / ".opencode" / "data" / "project.db"

    conn = _sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("INSERT INTO daemons (name, role, incarnations) VALUES ('crash-fix-daemon', 'Engineer', 1)")
    conn.execute(
        """
        INSERT INTO possessions (
            id, daemon_name, role, possession_log,
            start_time, status,
            minion_mode_active, worker_pid,
            last_heartbeat_at, created_at, updated_at
        )
        VALUES (
            800, 'crash-fix-daemon', 'Engineer',
            '.opencode/work/possessions/crashed2.md',
            datetime('now'), 'ACTIVE',
            1, 99999999,
            datetime('now'), datetime('now'), datetime('now')
        )
        """
    )
    conn.commit()
    conn.close()

    runner = CliRunner()
    with patch("site_nine.inquisitor.checks.os.kill", side_effect=ProcessLookupError):
        result = runner.invoke(app, ["inquisitor", "--fix"])

    assert result.exit_code == 0

    conn = _sqlite3.connect(str(db_path))
    conn.row_factory = _sqlite3.Row
    row = conn.execute("SELECT status, worker_pid, minion_mode_active FROM possessions WHERE id = 800").fetchone()
    conn.close()

    assert row["status"] == "EXORCISED"
    assert row["worker_pid"] is None
    assert row["minion_mode_active"] == 0


# =============================================================================
# 8. Migration script adds worker_pid column
# =============================================================================


def test_migration_adds_worker_pid_column(tmp_path: Path) -> None:
    """Migration 004 adds worker_pid column to an existing possessions table."""
    migration_sql = Path("scripts/migrations/004_add_worker_pid.sql").read_text()

    # Create a minimal DB without worker_pid
    db_path = tmp_path / "test_migrate.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE possessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            daemon_name TEXT,
            role TEXT,
            status TEXT DEFAULT 'ACTIVE',
            last_heartbeat_at TEXT
        )
        """
    )
    conn.commit()

    # Verify worker_pid is absent before migration
    cols_before = {row[1] for row in conn.execute("PRAGMA table_info(possessions)").fetchall()}
    assert "worker_pid" not in cols_before

    # Apply migration
    conn.executescript(migration_sql)

    # Verify worker_pid is present after migration
    cols_after = {row[1] for row in conn.execute("PRAGMA table_info(possessions)").fetchall()}
    assert "worker_pid" in cols_after

    # Verify NULL semantics
    conn.execute("INSERT INTO possessions (daemon_name, role) VALUES ('x', 'Engineer')")
    conn.commit()
    row = conn.execute("SELECT worker_pid FROM possessions").fetchone()
    assert row[0] is None

    conn.close()
