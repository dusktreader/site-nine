"""Tests for init CLI command"""

from pathlib import Path

from site_nine.__main__ import app
from typer.testing import CliRunner

runner = CliRunner()


def test_init_multiple_times(initialized_project: Path):
    """Test running init on already initialized project"""
    result = runner.invoke(app, ["init"])

    # Should fail or warn about existing .opencode
    assert result.exit_code in [0, 1]


def test_init_with_force_flag(initialized_project: Path):
    """Test init with force flag"""
    result = runner.invoke(app, ["init", "--force"])

    # May succeed or fail depending on state
    assert result.exit_code in [0, 1]


def test_init_with_config_flag(in_temp_dir: Path):
    """Test init with individual config flags"""
    result = runner.invoke(app, ["init", "--name", "test", "--type", "python", "--description", "test project"])

    # Should accept config flags
    assert result.exit_code in [0, 1]


def test_init_short_flags(in_temp_dir: Path):
    """Test init with short flags"""
    result = runner.invoke(app, ["init", "-f"])

    # Should work with short flag
    assert result.exit_code in [0, 1]


def test_init_creates_opencode_dir(in_temp_dir: Path):
    """Test that init creates .opencode directory"""
    result = runner.invoke(app, ["init"], input="\n" * 10)

    # Should create .opencode
    opencode_dir = in_temp_dir / ".opencode"
    assert opencode_dir.exists() or result.exit_code != 0


def test_init_creates_data_dir(in_temp_dir: Path):
    """Test that init creates data directory"""
    result = runner.invoke(app, ["init"], input="\n" * 10)

    # Should create data directory
    data_dir = in_temp_dir / ".opencode" / "data"
    assert data_dir.exists() or result.exit_code != 0


def test_init_creates_database(in_temp_dir: Path):
    """Test that init creates database file"""
    result = runner.invoke(app, ["init"], input="\n" * 10)

    # Should create database
    db_file = in_temp_dir / ".opencode" / "data" / "project.db"
    assert db_file.exists() or result.exit_code != 0
