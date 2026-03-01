"""MarkdownPreviewPane — scrollable markdown renderer that reacts to list selection.

Full implementation is part of Phase 2 (ENG-H-0241).
This stub establishes the module location and class interface.
"""

from __future__ import annotations

from textual.reactive import reactive
from textual.widget import Widget


class MarkdownPreviewPane(Widget):
    """
    Scrollable markdown renderer reacting to SelectableListPane.ItemSelected.

    Reactive attributes:
        content: str  — raw markdown content to display
        title:   str  — displayed in pane header

    Uses Textual's built-in Markdown widget for rendering.
    Loads file content asynchronously to avoid blocking the event loop.

    Full implementation in Phase 2 (ENG-H-0241).
    """

    content: reactive[str] = reactive("")
    title: reactive[str] = reactive("")
