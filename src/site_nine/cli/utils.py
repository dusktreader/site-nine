from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import NoReturn

import typer
from snick import conjoin
from typerdrive import terminal_message

from site_nine.core.paths import get_db_path, get_opencode_dir


def abort(message: str, subject: str = "Error") -> NoReturn:
    terminal_message(message, subject=subject, subject_color="red", error=True)
    raise typer.Exit(1)


def abort_unless(condition: object, message: str, subject: str = "Error") -> None:
    if not condition:
        abort(message, subject=subject)


def require_opencode_dir() -> Path:
    """Get the .opencode directory, or exit with a user-friendly error."""
    try:
        return get_opencode_dir()
    except FileNotFoundError:
        abort(".opencode directory not found. Run 's9 init' first.")


def require_db_path() -> Path:
    """Get the project database path, or exit with a user-friendly error."""
    try:
        return get_db_path()
    except FileNotFoundError as e:
        abort(str(e))


def open_in_editor(filename: str, file_path: Path) -> None:
    """Open a file in the system editor with standard pre/post messages."""
    abort_unless(
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
        abort(f"Failed to open editor: {e}")
    except FileNotFoundError:
        abort(
            conjoin(
                f"Editor '{editor}' not found.",
                "Set the EDITOR or VISUAL environment variable to your preferred editor.",
            ),
        )

    terminal_message(f"Done editing {filename}", subject="Done", subject_color="green")
