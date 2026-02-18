from __future__ import annotations

import os
import subprocess
from pathlib import Path

from snick import conjoin
from typerdrive import terminal_message

from site_nine.core.paths import get_db_path, get_opencode_dir
from site_nine.exceptions import SiteNineError


class CLIError(SiteNineError):
    """CLI-layer error for user-facing validation failures."""


def require_opencode_dir() -> Path:
    """Get the .opencode directory, or raise CLIError."""
    try:
        return get_opencode_dir()
    except FileNotFoundError:
        raise CLIError(".opencode directory not found. Run 's9 init' first.")


def require_db_path() -> Path:
    """Get the project database path, or raise CLIError."""
    try:
        return get_db_path()
    except FileNotFoundError as e:
        raise CLIError(str(e))


def open_in_editor(filename: str, file_path: Path) -> None:
    """Open a file in the system editor with standard pre/post messages."""
    CLIError.require_condition(
        file_path.exists(),
        conjoin(
            f"{filename} not found at {file_path}.",
            "This file should be created during 's9 init'.",
        ),
    )

    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vim"
    terminal_message(f"Opening {filename} in {editor}...", subject="Edit")

    try:
        subprocess.run([editor, str(file_path)], check=True)
    except subprocess.CalledProcessError as e:
        raise CLIError(f"Failed to open editor: {e}")
    except FileNotFoundError:
        raise CLIError(
            conjoin(
                f"Editor '{editor}' not found.",
                "Set the EDITOR or VISUAL environment variable to your preferred editor.",
            ),
        )

    terminal_message(f"Done editing {filename}", subject="Done", subject_color="green")
