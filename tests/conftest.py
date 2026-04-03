"""Pytest configuration and fixtures"""

import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Generator

import pytest
from site_nine.core.database import Database


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing"""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_db(temp_dir: Path) -> Generator[Database, None, None]:
    """Create a test database with schema initialized"""
    db_path = temp_dir / "test.db"

    with Database(db_path) as db:
        db.initialize_schema()

        # Add test daemons (required for foreign keys)
        db.execute_update("""
            INSERT INTO daemons (name, role, incarnations)
            VALUES 
                ('test-persona', 'Engineer', 0),
                ('persona1', 'Engineer', 0),
                ('persona2', 'Tester', 0),
                ('persona3', 'Engineer', 0)
        """)

        yield db


@pytest.fixture
def test_db_with_data(test_db: Database) -> Generator[Database, None, None]:
    """Create a test database with tasks and possessions for handoff tests"""
    # Add test tasks for handoff tests
    test_db.execute_update("""
        INSERT INTO tasks (id, title, description, status, priority, role, file_path, created_at)
        VALUES 
            ('ENG-M-0001', 'Test task 1', 'Description 1', 'TODO', 'MEDIUM', 'Engineer', '.opencode/work/tasks/ENG-M-0001.md', datetime('now')),
            ('ENG-M-0002', 'Test task 2', 'Description 2', 'TODO', 'MEDIUM', 'Tester', '.opencode/work/tasks/ENG-M-0002.md', datetime('now')),
            ('ENG-M-0003', 'Test task 3', 'Description 3', 'TODO', 'MEDIUM', 'Tester', '.opencode/work/tasks/ENG-M-0003.md', datetime('now'))
    """)

    # Add test possessions for handoff tests
    test_db.execute_update("""
        INSERT INTO possessions (id, daemon_name, role, possession_log, start_time, created_at, updated_at)
        VALUES 
            (1, 'test-persona', 'Engineer', '.opencode/work/possessions/test.md', datetime('now'), datetime('now'), datetime('now')),
            (2, 'persona1', 'Tester', '.opencode/work/possessions/test2.md', datetime('now'), datetime('now'), datetime('now'))
    """)

    yield test_db

    # Cleanup is handled by test_db fixture


@pytest.fixture
def opencode_dir(temp_dir: Path) -> Path:
    """Create a mock .opencode directory structure"""
    opencode = temp_dir / ".opencode"
    opencode.mkdir()
    (opencode / "data").mkdir()
    (opencode / "sessions").mkdir()
    (opencode / "planning").mkdir()
    return opencode


@pytest.fixture
def in_temp_dir(temp_dir: Path) -> Generator[Path, None, None]:
    """Change to temp directory and back, yielding the path"""
    original_cwd = os.getcwd()
    try:
        os.chdir(str(temp_dir))
        yield temp_dir
    finally:
        os.chdir(original_cwd)


@pytest.fixture
def project_dir(temp_dir: Path) -> Generator[Path, None, None]:
    """Create a project directory and change to it"""
    project = temp_dir / "test-project"
    project.mkdir()
    original_cwd = os.getcwd()
    try:
        os.chdir(str(project))
        yield project
    finally:
        os.chdir(original_cwd)


def _build_initialized_project(target_dir: Path) -> None:
    """Build an initialized .opencode project structure directly via Python.

    Bypasses the CLI layer (no Typer runner, no Rich progress bars) for speed.
    Produces the same result as ``s9 init --name test-project --type python``.
    """
    from site_nine.core.models import ProjectConfig
    from site_nine.core.templates import TemplateRenderer, copy_static_scaffold, render_scaffold_templates

    opencode_dir = target_dir / ".opencode"
    opencode_dir.mkdir()

    db_path = opencode_dir / "data" / "project.db"
    db_path.parent.mkdir(parents=True)
    with Database(db_path) as db:
        db.initialize_schema()
        db.seed_data()

    renderer = TemplateRenderer()
    config = ProjectConfig(name="test-project", type="python")
    context = config.template_context()
    copy_static_scaffold(renderer.scaffold_static_dir(), opencode_dir)
    render_scaffold_templates(renderer, opencode_dir, context)

    for empty_dir in ["work/tasks", "work/epics", "work/possessions"]:
        (opencode_dir / empty_dir).mkdir(parents=True, exist_ok=True)


@pytest.fixture(scope="session")
def _golden_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build a single initialized project once per test session.

    This is an internal fixture — tests should use ``initialized_project``
    which copies this golden directory to get a fresh, isolated copy.
    """
    golden = tmp_path_factory.mktemp("golden") / "test-project"
    golden.mkdir()
    _build_initialized_project(golden)
    return golden


@pytest.fixture
def initialized_project(_golden_project: Path, tmp_path: Path) -> Generator[Path, None, None]:
    """Create an initialized project for testing CLI commands.

    Copies a pre-built golden project directory so each test gets a fresh,
    isolated copy without paying the cost of DB init + scaffold rendering.
    """
    project = tmp_path / "test-project"
    shutil.copytree(_golden_project, project)
    original_cwd = os.getcwd()

    try:
        os.chdir(str(project))
        yield project
    finally:
        os.chdir(original_cwd)
