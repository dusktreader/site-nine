"""Path utilities for finding and resolving .opencode directory"""

from pathlib import Path


class PathTraversalError(ValueError):
    """Raised when a path attempts to escape the project boundary"""

    pass


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

    # Walk up directory tree
    while True:
        opencode_dir = current / ".opencode"
        if opencode_dir.exists() and opencode_dir.is_dir():
            return opencode_dir

        # Check if we've reached the filesystem root
        parent = current.parent
        if parent == current:
            # Reached root without finding .opencode
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
        PathTraversalError: If path attempts to escape project root
        FileNotFoundError: If .opencode directory not found

    Example:
        >>> # Safe path within project
        >>> validate_path_within_project(".opencode/work/sessions/foo.md")
        PosixPath('/project/root/.opencode/work/sessions/foo.md')

        >>> # Dangerous path attempting traversal
        >>> validate_path_within_project("../../etc/passwd")
        Traceback (most recent call last):
        PathTraversalError: Path traversal detected: path escapes project root

        >>> # Absolute path outside project
        >>> validate_path_within_project("/etc/passwd")
        Traceback (most recent call last):
        PathTraversalError: Path traversal detected: path escapes project root
    """
    project_root = get_project_root()

    # Convert to Path object if string
    if isinstance(path, str):
        path = Path(path)

    # Resolve the path to handle .. and symlinks
    # If path is relative, resolve it relative to project root
    if not path.is_absolute():
        if allow_relative:
            resolved_path = (project_root / path).resolve()
        else:
            resolved_path = path.resolve()
    else:
        resolved_path = path.resolve()

    # Check if resolved path is within project root
    try:
        resolved_path.relative_to(project_root)
    except ValueError:
        msg = f"Path traversal detected: path escapes project root ({resolved_path} not within {project_root})"
        raise PathTraversalError(msg) from None

    return resolved_path
