"""Pytest configuration and fixtures"""

import os
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
def test_db(temp_dir: Path) -> Database:
    """Create a test database with schema initialized"""
    db_path = temp_dir / "test.db"
    db = Database(db_path)
    db.initialize_schema()
    return db


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


@pytest.fixture
def initialized_project(temp_dir: Path) -> Generator[Path, None, None]:
    """Create an initialized project for testing CLI commands"""
    from site_nine.cli.main import app
    from typer.testing import CliRunner

    project = temp_dir / "test-project"
    project.mkdir()
    original_cwd = os.getcwd()

    try:
        os.chdir(str(project))

        # Initialize the project
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["init"],
            input="\n".join(
                [
                    "test-project",
                    "python",
                    "",
                    "y",  # PM system
                    "y",  # session tracking
                    "y",  # commit guidelines
                    "y",  # default roles
                ]
            ),
        )

        if result.exit_code != 0:
            raise RuntimeError(f"Failed to initialize project: {result.stdout}")

        yield project
    finally:
        os.chdir(original_cwd)
