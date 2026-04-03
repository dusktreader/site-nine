"""Tests for DaemonManager — summon_daemon LRU logic, invent_required signal, and add_daemon."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pendulum
import pytest

from site_nine.core.database import Database
from site_nine.daemons.manager import DaemonManager
from site_nine.daemons.exceptions import DaemonError


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Isolated DB with schema only — seed daemons removed so tests start clean."""
    db_path = tmp_path / "test_daemon_manager.db"
    database = Database(db_path)
    database.initialize_schema()
    # Remove the 9 canonical seed daemons so each test controls its own state.
    database.execute_update("DELETE FROM daemons")
    return database


@pytest.fixture
def manager(db: Database) -> DaemonManager:
    return DaemonManager(db)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _add(manager: DaemonManager, name: str, role: str = "Engineer") -> None:
    manager.add_daemon(name, role)


def _stamp_recent(db: Database, name: str, days_ago: float = 0.5) -> None:
    """Mark a daemon as last summoned `days_ago` days in the past."""
    ts = pendulum.now("UTC").subtract(days=days_ago).to_iso8601_string()
    db.execute_update(
        "UPDATE daemons SET last_possession = :ts, incarnations = incarnations + 1 WHERE lower(name) = :name",
        {"ts": ts, "name": name.lower()},
    )


def _stamp_old(db: Database, name: str, days_ago: float = 4) -> None:
    """Mark a daemon as last summoned `days_ago` days in the past (older than threshold)."""
    ts = pendulum.now("UTC").subtract(days=days_ago).to_iso8601_string()
    db.execute_update(
        "UPDATE daemons SET last_possession = :ts, incarnations = incarnations + 1 WHERE lower(name) = :name",
        {"ts": ts, "name": name.lower()},
    )


# ---------------------------------------------------------------------------
# summon_daemon — normal cases
# ---------------------------------------------------------------------------


class TestSummonDaemonNormal:
    def test_summons_only_daemon(self, manager: DaemonManager, db: Database) -> None:
        """A fresh daemon with no last_possession should be returned."""
        _add(manager, "azazel")
        result = manager.summon_daemon("engineer")
        assert result is not None
        assert result.name == "azazel"

    def test_summon_increments_incarnations(self, manager: DaemonManager, db: Database) -> None:
        _add(manager, "azazel")
        result = manager.summon_daemon("engineer")
        assert result is not None
        assert result.incarnations == 1

    def test_summon_sets_last_possession(self, manager: DaemonManager, db: Database) -> None:
        _add(manager, "azazel")
        result = manager.summon_daemon("engineer")
        assert result is not None
        assert result.last_possession is not None

    def test_lru_prefers_unused_daemon(self, manager: DaemonManager, db: Database) -> None:
        """With two daemons, one recently used and one fresh, the fresh one is chosen."""
        _add(manager, "azazel")
        _add(manager, "furcas")
        _stamp_recent(db, "azazel")  # used 0.5 days ago — within 3-day window
        # furcas has no last_possession → should be preferred
        result = manager.summon_daemon("engineer")
        assert result is not None
        assert result.name == "furcas"

    def test_lru_prefers_oldest_when_both_stale(self, manager: DaemonManager, db: Database) -> None:
        """Both daemons older than threshold — oldest last_possession wins."""
        _add(manager, "azazel")
        _add(manager, "furcas")
        _stamp_old(db, "azazel", days_ago=10)
        _stamp_old(db, "furcas", days_ago=4)
        # azazel has older last_possession → should be chosen
        result = manager.summon_daemon("engineer")
        assert result is not None
        assert result.name == "azazel"

    def test_lru_alphabetical_tiebreak(self, manager: DaemonManager, db: Database) -> None:
        """Both daemons untouched — alphabetical tiebreak applies."""
        _add(manager, "zzz-daemon")
        _add(manager, "aaa-daemon")
        result = manager.summon_daemon("engineer")
        assert result is not None
        assert result.name == "aaa-daemon"


# ---------------------------------------------------------------------------
# summon_daemon — returns None (invent_required trigger)
# ---------------------------------------------------------------------------


class TestSummonDaemonNone:
    def test_returns_none_when_no_daemons_exist(self, manager: DaemonManager) -> None:
        """No daemons for the role → None."""
        result = manager.summon_daemon("engineer")
        assert result is None

    def test_returns_none_when_single_daemon_recently_used(self, manager: DaemonManager, db: Database) -> None:
        """The only daemon was used within 3 days → None (invention required)."""
        _add(manager, "azazel")
        _stamp_recent(db, "azazel", days_ago=1)
        result = manager.summon_daemon("engineer")
        assert result is None

    def test_returns_none_when_all_daemons_recently_used(self, manager: DaemonManager, db: Database) -> None:
        """Two daemons, both used within 3 days → None."""
        _add(manager, "azazel")
        _add(manager, "furcas")
        _stamp_recent(db, "azazel", days_ago=0.5)
        _stamp_recent(db, "furcas", days_ago=1.5)
        result = manager.summon_daemon("engineer")
        assert result is None

    def test_not_none_when_one_daemon_outside_threshold(self, manager: DaemonManager, db: Database) -> None:
        """Two daemons: one recent, one stale — should succeed (not None)."""
        _add(manager, "azazel")
        _add(manager, "furcas")
        _stamp_recent(db, "azazel", days_ago=0.5)
        _stamp_old(db, "furcas", days_ago=4)
        result = manager.summon_daemon("engineer")
        assert result is not None
        assert result.name == "furcas"

    def test_threshold_boundary_exactly_3_days_is_recent(self, manager: DaemonManager, db: Database) -> None:
        """A daemon used exactly at the threshold boundary (< 3 days) is still recent."""
        _add(manager, "azazel")
        # 2 days, 23 hours, 59 minutes ago — still within 3 days
        ts = pendulum.now("UTC").subtract(days=2, hours=23, minutes=59).to_iso8601_string()
        db.execute_update(
            "UPDATE daemons SET last_possession = :ts, incarnations = 1 WHERE lower(name) = 'azazel'",
            {"ts": ts},
        )
        result = manager.summon_daemon("engineer")
        assert result is None

    def test_daemon_just_outside_threshold_is_eligible(self, manager: DaemonManager, db: Database) -> None:
        """A daemon last used just over 3 days ago should be eligible."""
        _add(manager, "azazel")
        _stamp_old(db, "azazel", days_ago=3.01)
        result = manager.summon_daemon("engineer")
        assert result is not None
        assert result.name == "azazel"


# ---------------------------------------------------------------------------
# invent → add_daemon → re-summon cycle
# ---------------------------------------------------------------------------


class TestInventCycle:
    def test_add_and_resommon_after_invent(self, manager: DaemonManager, db: Database) -> None:
        """After invention: add_daemon inserts the new daemon; summon_daemon returns it."""
        _add(manager, "azazel")
        _stamp_recent(db, "azazel", days_ago=1)

        # Invention required
        assert manager.summon_daemon("engineer") is None

        # Invent and add
        invented = manager.add_daemon("nachtherex", "engineer", personality="precise, cold")
        assert invented.name == "nachtherex"
        assert invented.role == "Engineer"

        # Now summon should pick the new (unused) daemon
        result = manager.summon_daemon("engineer")
        assert result is not None
        assert result.name == "nachtherex"

    def test_add_daemon_with_full_fields(self, manager: DaemonManager) -> None:
        bio = "I am the forge-daemon. I have watched engineers toil since Babylon fell."
        persona = "methodical, blunt, relentless"
        d = manager.add_daemon("nachtherex", "engineer", daemonology=bio, personality=persona)
        assert d.daemonology == bio
        assert d.personality == persona

    def test_add_daemon_duplicate_raises(self, manager: DaemonManager) -> None:
        manager.add_daemon("nachtherex", "engineer")
        with pytest.raises(DaemonError, match="already exists"):
            manager.add_daemon("nachtherex", "engineer")


# ---------------------------------------------------------------------------
# Role isolation
# ---------------------------------------------------------------------------


class TestRoleIsolation:
    def test_summon_only_picks_from_correct_role(self, manager: DaemonManager, db: Database) -> None:
        """Daemons for other roles are invisible to Engineer summon."""
        _add(manager, "lilith-t", "tester")
        result = manager.summon_daemon("engineer")
        assert result is None

    def test_roles_are_independent(self, manager: DaemonManager, db: Database) -> None:
        _add(manager, "azazel")  # engineer
        _add(manager, "lilith-t", "tester")
        r_eng = manager.summon_daemon("engineer")
        r_tst = manager.summon_daemon("tester")
        assert r_eng is not None and r_eng.name == "azazel"
        assert r_tst is not None and r_tst.name == "lilith-t"
