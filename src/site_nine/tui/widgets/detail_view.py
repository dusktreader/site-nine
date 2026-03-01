"""DetailScreen — full-page detail overlay pushed onto the Textual screen stack.

Full implementation is part of Phase 2 (ENG-H-0241).
This stub establishes the module location and class interface.
"""

from __future__ import annotations

from pathlib import Path

from textual.screen import Screen


class DetailScreen(Screen):
    """
    Full-page detail overlay pushed onto the Textual screen stack.

    Parameters:
        title:     str           — header title
        content:   str           — markdown content
        file_path: Path | None   — optional file to open in $EDITOR

    Pops itself on Esc/q. Calls app.suspend() around $EDITOR invocations.

    Full implementation in Phase 2 (ENG-H-0241).
    """

    def __init__(self, title: str, content: str, file_path: Path | None = None) -> None:
        super().__init__()
        self._title = title
        self._content = content
        self._file_path = file_path
