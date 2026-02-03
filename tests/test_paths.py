"""Tests for path utilities"""

import pytest
from s9.core.paths import (
    PathTraversalError,
    find_opencode_dir,
    get_opencode_dir,
    get_project_root,
    validate_path_within_project,
)


def test_find_opencode_dir_in_current_directory(tmp_path):
    """Test finding .opencode in current directory"""
    # Create .opencode directory
    opencode_dir = tmp_path / ".opencode"
    opencode_dir.mkdir()

    # Should find it
    result = find_opencode_dir(tmp_path)
    assert result == opencode_dir


def test_find_opencode_dir_in_parent_directory(tmp_path):
    """Test finding .opencode in parent directory"""
    # Create .opencode in parent
    opencode_dir = tmp_path / ".opencode"
    opencode_dir.mkdir()

    # Create subdirectory
    subdir = tmp_path / "src" / "myproject"
    subdir.mkdir(parents=True)

    # Should find it by walking up
    result = find_opencode_dir(subdir)
    assert result == opencode_dir


def test_find_opencode_dir_multiple_levels_up(tmp_path):
    """Test finding .opencode several directories up"""
    # Create .opencode at root
    opencode_dir = tmp_path / ".opencode"
    opencode_dir.mkdir()

    # Create deeply nested directory
    deep_dir = tmp_path / "a" / "b" / "c" / "d" / "e"
    deep_dir.mkdir(parents=True)

    # Should find it even from deep nesting
    result = find_opencode_dir(deep_dir)
    assert result == opencode_dir


def test_find_opencode_dir_not_found(tmp_path):
    """Test when .opencode doesn't exist"""
    result = find_opencode_dir(tmp_path)
    assert result is None


def test_find_opencode_dir_prefers_closest(tmp_path):
    """Test that closest .opencode is found (not parent's)"""
    # Create .opencode in parent
    parent_opencode = tmp_path / ".opencode"
    parent_opencode.mkdir()

    # Create nested project with its own .opencode
    nested_project = tmp_path / "nested"
    nested_project.mkdir()
    nested_opencode = nested_project / ".opencode"
    nested_opencode.mkdir()

    # From nested project, should find nested .opencode
    result = find_opencode_dir(nested_project)
    assert result == nested_opencode

    # From parent, should find parent .opencode
    result = find_opencode_dir(tmp_path)
    assert result == parent_opencode


def test_find_opencode_dir_ignores_files(tmp_path):
    """Test that .opencode file (not directory) is ignored"""
    # Create .opencode as a file (not directory)
    opencode_file = tmp_path / ".opencode"
    opencode_file.touch()

    # Should not find it (must be directory)
    result = find_opencode_dir(tmp_path)
    assert result is None


def test_get_opencode_dir_success(tmp_path):
    """Test get_opencode_dir when directory exists"""
    opencode_dir = tmp_path / ".opencode"
    opencode_dir.mkdir()

    _result = get_opencode_dir()
    # Can't easily test this without changing cwd, but we can at least verify it doesn't raise


def test_get_opencode_dir_not_found(tmp_path, monkeypatch):
    """Test get_opencode_dir raises error when not found"""
    # Change to directory without .opencode
    monkeypatch.chdir(tmp_path)

    with pytest.raises(FileNotFoundError, match=".opencode directory not found"):
        get_opencode_dir()


def test_get_project_root(tmp_path, monkeypatch):
    """Test getting project root"""
    # Create .opencode
    opencode_dir = tmp_path / ".opencode"
    opencode_dir.mkdir()

    # Create subdirectory and change to it
    subdir = tmp_path / "src"
    subdir.mkdir()
    monkeypatch.chdir(subdir)

    # Should get project root (parent of .opencode)
    result = get_project_root()
    assert result == tmp_path


def test_find_opencode_dir_defaults_to_cwd(tmp_path, monkeypatch):
    """Test that find_opencode_dir defaults to current working directory"""
    opencode_dir = tmp_path / ".opencode"
    opencode_dir.mkdir()

    monkeypatch.chdir(tmp_path)

    # Should find it from cwd when no path specified
    result = find_opencode_dir()
    assert result == opencode_dir


def test_validate_path_within_project_safe_relative(tmp_path, monkeypatch):
    """Test validation of safe relative path within project"""
    opencode_dir = tmp_path / ".opencode"
    opencode_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    # Safe relative path
    result = validate_path_within_project(".opencode/work/sessions/foo.md")
    assert result == tmp_path / ".opencode" / "work" / "sessions" / "foo.md"


def test_validate_path_within_project_safe_absolute(tmp_path, monkeypatch):
    """Test validation of safe absolute path within project"""
    opencode_dir = tmp_path / ".opencode"
    opencode_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    # Safe absolute path
    safe_path = tmp_path / ".opencode" / "data" / "project.db"
    result = validate_path_within_project(safe_path)
    assert result == safe_path


def test_validate_path_within_project_traversal_relative(tmp_path, monkeypatch):
    """Test validation rejects relative path traversal"""
    opencode_dir = tmp_path / ".opencode"
    opencode_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    # Attempt to traverse outside project
    with pytest.raises(PathTraversalError, match="Path traversal detected"):
        validate_path_within_project("../../etc/passwd")


def test_validate_path_within_project_traversal_absolute(tmp_path, monkeypatch):
    """Test validation rejects absolute path outside project"""
    opencode_dir = tmp_path / ".opencode"
    opencode_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    # Absolute path outside project
    with pytest.raises(PathTraversalError, match="Path traversal detected"):
        validate_path_within_project("/etc/passwd")


def test_validate_path_within_project_symlink_escape(tmp_path, monkeypatch):
    """Test validation handles symlinks that escape project"""
    opencode_dir = tmp_path / ".opencode"
    opencode_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    # Create a symlink that points outside project
    external_dir = tmp_path.parent / "external"
    external_dir.mkdir(exist_ok=True)
    symlink = tmp_path / "evil_link"
    symlink.symlink_to(external_dir)

    # Should detect that symlink resolves outside project
    with pytest.raises(PathTraversalError, match="Path traversal detected"):
        validate_path_within_project("evil_link")


def test_validate_path_within_project_accepts_string(tmp_path, monkeypatch):
    """Test validation accepts string paths"""
    opencode_dir = tmp_path / ".opencode"
    opencode_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    # String path should work
    result = validate_path_within_project(".opencode/data")
    assert result == tmp_path / ".opencode" / "data"
