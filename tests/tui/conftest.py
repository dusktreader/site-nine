"""Conftest for TUI tests.

Provides a fixture that yields a fully-initialised Database with a small
but realistic set of missions, tasks, epics and messages — enough for
every TUI screen to render a non-empty list.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Generator

import pytest

from site_nine.core.database import Database


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_tui_data(db: Database) -> None:
    """Insert minimal realistic rows so every TUI screen has something to show."""

    # Personas (foreign-key requirement for missions)
    db.execute_update("""
        INSERT OR IGNORE INTO personas (name, role, mythology, description)
        VALUES
            ('athena',  'Tester',   'Greek', 'Goddess of wisdom'),
            ('ares',    'Engineer', 'Greek', 'God of war'),
            ('hermes',  'Operator', 'Greek', 'Messenger god')
    """)

    # Missions
    db.execute_update("""
        INSERT OR IGNORE INTO missions
            (id, persona_name, role, codename, mission_file,
             start_date, start_time, objective, created_at, updated_at)
        VALUES
            (1001, 'athena',  'Tester',   'red-falcon',  '.opencode/work/missions/m1001.md',
             date('now'), time('now'), 'Run the test suite', datetime('now'), datetime('now')),
            (1002, 'ares',    'Engineer', 'blue-storm',  '.opencode/work/missions/m1002.md',
             date('now'), time('now'), 'Build the thing',    datetime('now'), datetime('now')),
            (1003, 'hermes',  'Operator', 'green-arrow', '.opencode/work/missions/m1003.md',
             date('now'), time('now'), 'Route the messages', datetime('now'), datetime('now'))
    """)

    # Tasks
    db.execute_update("""
        INSERT OR IGNORE INTO tasks
            (id, title, description, status, priority, role, file_path, created_at, updated_at)
        VALUES
            ('TST-T-0001', 'Alpha task',   'Description of alpha',  'TODO',     'HIGH',   'Tester',   '.opencode/work/tasks/TST-T-0001.md', datetime('now'), datetime('now')),
            ('TST-T-0002', 'Beta task',    'Description of beta',   'UNDERWAY', 'MEDIUM', 'Engineer', '.opencode/work/tasks/TST-T-0002.md', datetime('now'), datetime('now')),
            ('TST-T-0003', 'Gamma task',   'Description of gamma',  'COMPLETE', 'LOW',    'Operator', '.opencode/work/tasks/TST-T-0003.md', datetime('now'), datetime('now')),
            ('TST-T-0004', 'Delta task',   'Description of delta',  'TODO',     'CRITICAL','Tester',  '.opencode/work/tasks/TST-T-0004.md', datetime('now'), datetime('now')),
            ('TST-T-0005', 'Epsilon task', 'Description of epsilon','TODO',     'HIGH',   'Tester',   '.opencode/work/tasks/TST-T-0005.md', datetime('now'), datetime('now'))
    """)

    # Claim one task to a mission so the mission-column is non-trivial
    # (must also set status=UNDERWAY to satisfy the DB CHECK constraint)
    db.execute_update("""
        UPDATE tasks
        SET current_mission_id = 1001,
            claimed_at = datetime('now'),
            status = 'UNDERWAY'
        WHERE id = 'TST-T-0001'
    """)

    # Epics
    db.execute_update("""
        INSERT OR IGNORE INTO epics
            (id, title, description, status, priority, file_path, created_at, updated_at)
        VALUES
            ('EPC-T-0001', 'Epic Alpha', 'The first epic',  'UNDERWAY', 'HIGH',   '.opencode/work/epics/EPC-T-0001.md', datetime('now'), datetime('now')),
            ('EPC-T-0002', 'Epic Beta',  'The second epic', 'TODO',     'MEDIUM', '.opencode/work/epics/EPC-T-0002.md', datetime('now'), datetime('now'))
    """)

    # Messaging conversations
    db.execute_update("""
        INSERT OR IGNORE INTO conversations
            (id, subject, type, status, created_at, updated_at)
        VALUES
            ('CONV-T-0001', 'Test subject 1', 'conversation', 'open',   datetime('now'), datetime('now')),
            ('CONV-T-0002', 'Test subject 2', 'discussion',   'closed', datetime('now'), datetime('now'))
    """)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def tui_db_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """
    Session-scoped: build a single seeded DB once and reuse its path.

    Returns the path so tests can open their own Database handles
    (Textual screens manage their own connections).
    """
    base = tmp_path_factory.mktemp("tui_db")
    db_path = base / "tui_test.db"
    with Database(db_path) as db:
        db.initialize_schema()
        db.seed_data()
        _seed_tui_data(db)
    return db_path


@pytest.fixture()
def tui_db(tui_db_path: Path) -> Generator[Database, None, None]:
    """Per-test Database handle (read-heavy tests; writes isolated via session DB)."""
    with Database(tui_db_path) as db:
        yield db


@pytest.fixture()
def initialized_tui_project(
    tui_db_path: Path,
    tmp_path: Path,
) -> Generator[Path, None, None]:
    """
    Provide an on-disk project directory whose DB is the pre-seeded tui_db_path.

    Patches get_db_path() so SiteNineApp automatically picks up the test DB.
    """
    project = tmp_path / "tui-test-project"
    project.mkdir()
    opencode = project / ".opencode" / "data"
    opencode.mkdir(parents=True)
    # Symlink the session-scoped DB in so the app finds it via get_db_path()
    db_link = opencode / "project.db"
    shutil.copy2(tui_db_path, db_link)

    original_cwd = os.getcwd()
    try:
        os.chdir(str(project))
        yield project
    finally:
        os.chdir(original_cwd)
