"""Integration tests for role CLI command"""

from pathlib import Path
from unittest.mock import patch

from site_nine.__main__ import app
from typer.testing import CliRunner

runner = CliRunner()


def _get_called_file(mock_run):
    """Helper to get the file path that was passed to subprocess.run"""
    call_args = mock_run.call_args[0][0]
    return call_args[1] if len(call_args) > 1 else None


def _create_role_files(project: Path) -> Path:
    """Helper to create minimal role files for testing."""
    roles_dir = project / ".opencode" / "docs" / "roles"
    roles_dir.mkdir(parents=True, exist_ok=True)
    for name in ["engineer", "architect", "tester", "operator"]:
        (roles_dir / f"{name}.md").write_text(f"# {name.title()}\n")
    return roles_dir


# --- list command ---


def test_role_list_shows_available(initialized_project: Path):
    """Test listing available roles"""
    _create_role_files(initialized_project)

    result = runner.invoke(app, ["role", "list"])

    assert result.exit_code == 0, f"Command failed: {result.output}"
    output = " ".join(result.output.split())
    assert "Available Roles" in output
    assert "engineer" in output
    assert "architect" in output


def test_role_list_fails_without_init(in_temp_dir: Path):
    """Test that role list fails if project not initialized"""
    result = runner.invoke(app, ["role", "list"])

    assert result.exit_code != 0
    assert ".opencode" in result.output or "init" in result.output.lower()


def test_role_list_fails_when_roles_dir_missing(initialized_project: Path):
    """Test that role list fails when the roles directory doesn't exist"""
    import shutil

    roles_dir = initialized_project / ".opencode" / "docs" / "roles"
    if roles_dir.exists():
        shutil.rmtree(roles_dir)

    result = runner.invoke(app, ["role", "list"])

    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert "No role definitions found" in output


# --- edit command: happy path ---


def test_role_edit_opens_file(initialized_project: Path):
    """Test editing a role definition by name"""
    _create_role_files(initialized_project)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = None

        result = runner.invoke(app, ["role", "edit", "engineer"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Opening engineer.md" in result.output
        assert "Done editing" in result.output

        mock_run.assert_called_once()
        called_file = _get_called_file(mock_run)
        assert called_file and "engineer.md" in called_file


def test_role_edit_opens_another_role(initialized_project: Path):
    """Test editing a different role"""
    _create_role_files(initialized_project)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = None

        result = runner.invoke(app, ["role", "edit", "architect"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Opening architect.md" in result.output


# --- edit command: error paths ---


def test_role_edit_fails_without_init(in_temp_dir: Path):
    """Test that role edit fails if project not initialized"""
    result = runner.invoke(app, ["role", "edit", "engineer"])

    assert result.exit_code != 0
    assert ".opencode" in result.output or "init" in result.output.lower()


def test_role_edit_fails_when_not_found(initialized_project: Path):
    """Test that role edit fails when role doesn't exist"""
    _create_role_files(initialized_project)

    result = runner.invoke(app, ["role", "edit", "nonexistent"])

    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert "not found" in output.lower()
    assert "Available roles:" in output


def test_role_edit_shows_available_on_not_found(initialized_project: Path):
    """Test that the error message includes available role names"""
    _create_role_files(initialized_project)

    result = runner.invoke(app, ["role", "edit", "nonexistent"])

    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert "engineer" in output
    assert "architect" in output


def test_role_edit_fails_when_roles_dir_missing(initialized_project: Path):
    """Test that role edit fails when the roles directory doesn't exist"""
    import shutil

    roles_dir = initialized_project / ".opencode" / "docs" / "roles"
    if roles_dir.exists():
        shutil.rmtree(roles_dir)

    result = runner.invoke(app, ["role", "edit", "engineer"])

    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert "not found" in output.lower()


# --- help ---


def test_role_help_shows_subcommands():
    """Test that role --help shows available subcommands"""
    result = runner.invoke(app, ["role", "--help"])

    assert result.exit_code == 0
    assert "list" in result.stdout
    assert "edit" in result.stdout
