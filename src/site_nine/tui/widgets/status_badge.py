"""StatusBadge — coloured inline status/priority badge component.

Full implementation is part of Phase 2 / Phase 4.
"""

from __future__ import annotations

from textual.widget import Widget


class StatusBadge(Widget):
    """Coloured status badge for priority and task/mission status display."""

    def __init__(self, text: str, css_class: str = "") -> None:
        super().__init__()
        self._text = text
        self._css_class = css_class
