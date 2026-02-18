"""Path utilities for project and package paths"""

from importlib.resources import files
from pathlib import Path

from site_nine.core.exceptions import PathTraversalError


def get_package_data_dir() -> Path:
    """Get path to site_nine/data/ directory containing schema.sql, seed.sql, etc."""
    return Path(str(files("site_nine").joinpath("data")))


def find_opencode_dir(start_path: Path | None = None) -> Path | None:
    """
    Find .opencode directory by walking up from start_path.

    Similar to how git finds .git directory, this function searches
    for .opencode starting from the given path and walking up the
    directory tree until found or reaching filesystem root.

    Args:
        start_path: Starting directory (defaults to current working directory)

    Returns:
        Path to .opencode directory if found, None otherwise

    Example:
        >>> opencode_dir = find_opencode_dir()
        >>> if opencode_dir:
        ...     db_path = opencode_dir / "data" / "project.db"
    """
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()

    while True:
        opencode_dir = current / ".opencode"
        if opencode_dir.exists() and opencode_dir.is_dir():
            return opencode_dir

        parent = current.parent
        if parent == current:
            return None

        current = parent


def get_opencode_dir() -> Path:
    """
    Get .opencode directory or raise error if not found.

    This is a convenience wrapper around find_opencode_dir() that
    raises a clear error message instead of returning None.

    Returns:
        Path to .opencode directory

    Raises:
        FileNotFoundError: If .opencode directory not found

    Example:
        >>> opencode_dir = get_opencode_dir()
        >>> db_path = opencode_dir / "data" / "project.db"
    """
    opencode_dir = find_opencode_dir()
    if opencode_dir is None:
        msg = ".opencode directory not found. Run 's9 init' in your project root to create it."
        raise FileNotFoundError(msg)
    return opencode_dir


def get_db_path() -> Path:
    """
    Get path to the project database file.

    Returns:
        Path to the project.db file

    Raises:
        FileNotFoundError: If .opencode directory or project.db not found
    """
    opencode_dir = get_opencode_dir()
    db_path = opencode_dir / "data" / "project.db"
    if not db_path.exists():
        raise FileNotFoundError("project.db not found. Run 's9 init' first.")
    return db_path


def resolve_opencode_path(relative_path: str) -> Path:
    """
    Resolve a path relative to .opencode (e.g. ".opencode/docs/adrs/foo.md") to an absolute path.

    Raises:
        FileNotFoundError: If .opencode directory not found
    """
    opencode_dir = get_opencode_dir()
    return opencode_dir / Path(relative_path).relative_to(".opencode")


def get_project_root() -> Path:
    """
    Get project root directory (parent of .opencode).

    Returns:
        Path to project root directory

    Raises:
        FileNotFoundError: If .opencode directory not found

    Example:
        >>> project_root = get_project_root()
        >>> pyproject_path = project_root / "pyproject.toml"
    """
    return get_opencode_dir().parent


def validate_path_within_project(path: Path | str, *, allow_relative: bool = True) -> Path:
    """
    Validate that a path is within the project boundaries.

    This helper prevents directory traversal attacks by ensuring that
    resolved paths don't escape the project root directory.

    Args:
        path: Path to validate (can be relative or absolute)
        allow_relative: If False, only accept paths that already resolve within project

    Returns:
        Resolved Path object within project boundaries

    Raises:
        PathTraversalError: If path is outside project root
        FileNotFoundError: If .opencode directory not found

    Example:
        >>> # Safe path within project
        >>> validate_path_within_project(".opencode/work/sessions/foo.md")
        PosixPath('/project/root/.opencode/work/sessions/foo.md')

        >>> # Path outside project
        >>> validate_path_within_project("../../etc/passwd")
        Traceback (most recent call last):
        PathTraversalError: Path is outside project directory

        >>> # Absolute path outside project
        >>> validate_path_within_project("/etc/passwd")
        Traceback (most recent call last):
        PathTraversalError: Path is outside project directory
    """
    project_root = get_project_root()

    if isinstance(path, str):
        path = Path(path)

    if not path.is_absolute():
        if allow_relative:
            resolved_path = (project_root / path).resolve()
        else:
            resolved_path = path.resolve()
    else:
        resolved_path = path.resolve()

    try:
        resolved_path.relative_to(project_root)
    except ValueError:
        msg = f"Path is outside project directory: {resolved_path} is not within {project_root}"
        raise PathTraversalError(msg) from None

    return resolved_path
