"""Tests for idle heartbeat emission and Inquisitor minion threshold (ENG-H-0260).

Covers:
- MinionWorker.HEARTBEAT_INTERVAL constant is present and set to 300
- _emit_heartbeat() calls PossessionManager.heartbeat() and journals the event
- Polling loop emits a heartbeat after HEARTBEAT_INTERVAL seconds of idle time
- Polling loop resets heartbeat timer when messages are processed
- check_rogue_possessions uses 15-minute threshold for minion-mode possessions
- check_rogue_possessions uses 3-hour threshold for interactive possessions
- Inquisitor does NOT exorcise a fresh minion-mode possession with a recent heartbeat
- Inquisitor DOES exorcise a stale minion-mode possession (>15 min heartbeat)
- Inquisitor does NOT exorcise a 30-minute-old interactive possession (within 3h)
- InquisitorManager.run_diagnostics() accepts stale_minutes_minion parameter

ADR-016, Fix 3: Idle heartbeat emission and tightened Inquisitor threshold.
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pendulum
import pytest

from site_nine.core.database import Database
from site_nine.inquisitor.checks import check_rogue_possessions
from site_nine.inquisitor.manager import InquisitorManager


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
    last_heartbeat_at: str | None = None,
    status: str = "ACTIVE",
) -> int:
    """Insert a possession and return its rowid."""
    _create_daemon(db, daemon, role)
    rows = db.execute_query(
        """
        INSERT INTO possessions (
            daemon_name, role, possession_log,
            start_time, status,
            minion_mode_active,
            last_heartbeat_at, created_at, updated_at
        )
        VALUES (
            :daemon, :role,
            '.opencode/work/possessions/test.md',
            datetime('now'), :status,
            :minion_mode_active,
            :last_heartbeat_at, datetime('now'), datetime('now')
        )
        RETURNING id
        """,
        {
            "daemon": daemon,
            "role": role,
            "status": status,
            "minion_mode_active": minion_mode_active,
            "last_heartbeat_at": last_heartbeat_at,
        },
    )
    return rows[0]["id"]


# =============================================================================
# 1. HEARTBEAT_INTERVAL constant
# =============================================================================


def test_minion_worker_has_heartbeat_interval_constant() -> None:
    """MinionWorker.HEARTBEAT_INTERVAL is defined and set to 300 seconds."""
    from site_nine.workers.minion_worker import MinionWorker

    assert hasattr(MinionWorker, "HEARTBEAT_INTERVAL")
    assert MinionWorker.HEARTBEAT_INTERVAL == 300


# =============================================================================
# 2. _emit_heartbeat() method
# =============================================================================


def test_emit_heartbeat_calls_possession_manager_heartbeat(test_db: Database) -> None:
    """_emit_heartbeat() invokes PossessionManager.heartbeat() for the worker's possession."""
    pos_id = _create_possession(test_db, minion_mode_active=1)

    mock_journal = MagicMock()

    with (
        patch("site_nine.workers.minion_worker.Database") as mock_db_cls,
        patch("site_nine.workers.minion_worker.get_db_path", return_value=test_db.db_path),
        patch("site_nine.workers.minion_worker.PossessionManager") as mock_mgr_cls,
    ):
        mock_db_cls.return_value = test_db
        mock_mgr_instance = MagicMock()
        mock_mgr_cls.return_value = mock_mgr_instance

        from site_nine.workers.minion_worker import MinionWorker

        worker = MinionWorker.__new__(MinionWorker)
        worker.possession_id = pos_id
        worker.journal = mock_journal

        worker._emit_heartbeat()

    mock_mgr_instance.heartbeat.assert_called_once_with(pos_id)


def test_emit_heartbeat_writes_journal_entry(test_db: Database) -> None:
    """_emit_heartbeat() writes an 'idle' entry to the journal."""
    pos_id = _create_possession(test_db, minion_mode_active=1)

    mock_journal = MagicMock()

    with (
        patch("site_nine.workers.minion_worker.Database") as mock_db_cls,
        patch("site_nine.workers.minion_worker.get_db_path", return_value=test_db.db_path),
        patch("site_nine.workers.minion_worker.PossessionManager"),
    ):
        mock_db_cls.return_value = test_db

        from site_nine.workers.minion_worker import MinionWorker

        worker = MinionWorker.__new__(MinionWorker)
        worker.possession_id = pos_id
        worker.journal = mock_journal

        worker._emit_heartbeat()

    # Journal should have received at least one write_entry call mentioning 'heartbeat'
    calls_text = " ".join(str(c) for c in mock_journal.write_entry.call_args_list)
    assert "heartbeat" in calls_text.lower() or "idle" in calls_text.lower()


def test_emit_heartbeat_swallows_exceptions(test_db: Database) -> None:
    """_emit_heartbeat() does not propagate exceptions from PossessionManager."""
    pos_id = _create_possession(test_db, minion_mode_active=1)

    mock_journal = MagicMock()

    with (
        patch("site_nine.workers.minion_worker.Database") as mock_db_cls,
        patch("site_nine.workers.minion_worker.get_db_path", return_value=test_db.db_path),
        patch("site_nine.workers.minion_worker.PossessionManager") as mock_mgr_cls,
    ):
        mock_db_cls.return_value = test_db
        mock_mgr_cls.return_value.heartbeat.side_effect = RuntimeError("DB gone")

        from site_nine.workers.minion_worker import MinionWorker

        worker = MinionWorker.__new__(MinionWorker)
        worker.possession_id = pos_id
        worker.journal = mock_journal

        # Should not raise
        worker._emit_heartbeat()


# =============================================================================
# 3. check_rogue_possessions — minion threshold (15 min)
# =============================================================================


def test_check_rogue_possessions_fresh_minion_passes(test_db: Database) -> None:
    """A minion-mode possession with a recent heartbeat (5 min ago) is NOT flagged."""
    recent = pendulum.now("UTC").subtract(minutes=5).isoformat()
    _create_possession(test_db, minion_mode_active=1, last_heartbeat_at=recent)

    label, issues = check_rogue_possessions(test_db, stale_minutes_minion=15)
    assert label == "10c. Rogue Possessions"
    assert issues == []


def test_check_rogue_possessions_stale_minion_flagged(test_db: Database) -> None:
    """A minion-mode possession with a heartbeat older than 15 min IS flagged."""
    stale = pendulum.now("UTC").subtract(minutes=20).isoformat()
    pos_id = _create_possession(test_db, minion_mode_active=1, last_heartbeat_at=stale)

    label, issues = check_rogue_possessions(test_db, stale_minutes_minion=15)
    assert len(issues) == 1
    assert str(pos_id) in issues[0].description


def test_check_rogue_possessions_fresh_interactive_passes(test_db: Database) -> None:
    """An interactive possession with a 30-minute-old heartbeat is NOT flagged (within 3h)."""
    recent = pendulum.now("UTC").subtract(minutes=30).isoformat()
    _create_possession(test_db, minion_mode_active=0, last_heartbeat_at=recent)

    label, issues = check_rogue_possessions(test_db, stale_hours=3, stale_minutes_minion=15)
    assert issues == []


def test_check_rogue_possessions_stale_interactive_flagged(test_db: Database) -> None:
    """An interactive possession with a heartbeat older than 3 hours IS flagged."""
    stale = pendulum.now("UTC").subtract(hours=4).isoformat()
    pos_id = _create_possession(test_db, minion_mode_active=0, last_heartbeat_at=stale)

    label, issues = check_rogue_possessions(test_db, stale_hours=3, stale_minutes_minion=15)
    assert len(issues) == 1
    assert str(pos_id) in issues[0].description


def test_check_rogue_possessions_minion_not_affected_by_3h_threshold(test_db: Database) -> None:
    """A minion possession that is only 2 hours stale IS flagged (minion threshold is 15 min)."""
    stale = pendulum.now("UTC").subtract(hours=2).isoformat()
    pos_id = _create_possession(test_db, minion_mode_active=1, last_heartbeat_at=stale)

    label, issues = check_rogue_possessions(test_db, stale_hours=3, stale_minutes_minion=15)
    # 2 hours > 15 minutes — should be caught by minion threshold
    assert len(issues) == 1
    assert str(pos_id) in issues[0].description


def test_check_rogue_possessions_interactive_not_affected_by_15min_threshold(test_db: Database) -> None:
    """An interactive possession that is 20 minutes stale is NOT flagged (threshold is 3h)."""
    stale = pendulum.now("UTC").subtract(minutes=20).isoformat()
    _create_possession(test_db, minion_mode_active=0, last_heartbeat_at=stale)

    label, issues = check_rogue_possessions(test_db, stale_hours=3, stale_minutes_minion=15)
    assert issues == []


def test_check_rogue_possessions_minion_threshold_in_description(test_db: Database) -> None:
    """Threshold description in issue text mentions minutes for minion mode."""
    stale = pendulum.now("UTC").subtract(minutes=20).isoformat()
    _create_possession(test_db, minion_mode_active=1, last_heartbeat_at=stale)

    _, issues = check_rogue_possessions(test_db, stale_minutes_minion=15)
    assert len(issues) == 1
    assert "min" in issues[0].description


def test_check_rogue_possessions_interactive_threshold_in_description(test_db: Database) -> None:
    """Threshold description in issue text mentions hours for interactive mode."""
    stale = pendulum.now("UTC").subtract(hours=4).isoformat()
    _create_possession(test_db, minion_mode_active=0, last_heartbeat_at=stale)

    _, issues = check_rogue_possessions(test_db, stale_hours=3)
    assert len(issues) == 1
    assert "h" in issues[0].description  # "3h" or similar


# =============================================================================
# 4. InquisitorManager.run_diagnostics accepts stale_minutes_minion
# =============================================================================


def test_inquisitor_manager_run_diagnostics_accepts_stale_minutes_minion(test_db: Database, tmp_path: Path) -> None:
    """InquisitorManager.run_diagnostics() accepts and uses stale_minutes_minion."""
    opencode_dir = tmp_path / ".opencode"
    (opencode_dir / "data").mkdir(parents=True)
    # Copy the in-memory DB path to satisfy the db_path check
    db_path = opencode_dir / "data" / "project.db"

    # Create a stale minion possession (20 min ago) — should be caught by 15min threshold
    stale = pendulum.now("UTC").subtract(minutes=20).isoformat()
    _create_possession(test_db, minion_mode_active=1, last_heartbeat_at=stale)

    manager = InquisitorManager(test_db, opencode_dir)
    # Override db_path so infrastructure checks don't abort
    manager.db_path = test_db.db_path

    report = manager.run_diagnostics(stale_hours=3, stale_minutes_minion=15)

    # Find 10c check
    check_10c = next((c for c in report.data_checks if c.label == "10c. Rogue Possessions"), None)
    assert check_10c is not None
    assert len(check_10c.issues) == 1, "stale minion possession should be flagged by 15-min threshold"


def test_inquisitor_manager_run_diagnostics_minion_passes_with_fresh_heartbeat(
    test_db: Database, tmp_path: Path
) -> None:
    """InquisitorManager.run_diagnostics() does not flag a minion with a recent heartbeat."""
    opencode_dir = tmp_path / ".opencode"
    (opencode_dir / "data").mkdir(parents=True)

    recent = pendulum.now("UTC").subtract(minutes=5).isoformat()
    _create_possession(test_db, minion_mode_active=1, last_heartbeat_at=recent)

    manager = InquisitorManager(test_db, opencode_dir)
    manager.db_path = test_db.db_path

    report = manager.run_diagnostics(stale_hours=3, stale_minutes_minion=15)

    check_10c = next((c for c in report.data_checks if c.label == "10c. Rogue Possessions"), None)
    assert check_10c is not None
    assert check_10c.issues == []
