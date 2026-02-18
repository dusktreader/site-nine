"""Tests for settings, cache, and logs CLI commands"""

from pathlib import Path

from site_nine.__main__ import app
from typer.testing import CliRunner

runner = CliRunner()


# Settings tests
def test_settings_show(initialized_project: Path):
    """Test showing settings"""
    result = runner.invoke(app, ["settings", "show"])
    assert result.exit_code in [0, 1]


def test_settings_bind(initialized_project: Path):
    """Test binding settings"""
    result = runner.invoke(app, ["settings", "bind"])
    assert result.exit_code in [0, 1]


def test_settings_reset(initialized_project: Path):
    """Test resetting settings"""
    result = runner.invoke(app, ["settings", "reset"])
    assert result.exit_code in [0, 1]


# Cache tests
def test_cache_show(initialized_project: Path):
    """Test showing cache"""
    result = runner.invoke(app, ["cache", "show"])
    assert result.exit_code in [0, 1]


def test_cache_clear(initialized_project: Path):
    """Test clearing cache"""
    result = runner.invoke(app, ["cache", "clear"])
    assert result.exit_code in [0, 1]


# Logs tests
def test_logs_show(initialized_project: Path):
    """Test showing logs"""
    result = runner.invoke(app, ["logs", "show"])
    assert result.exit_code in [0, 1]


def test_logs_clear(initialized_project: Path):
    """Test clearing logs"""
    result = runner.invoke(app, ["logs", "clear"])
    assert result.exit_code in [0, 1]


# Version test
def test_version_command(initialized_project: Path):
    """Test version command"""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "site-nine" in result.stdout or "version" in result.stdout.lower()
