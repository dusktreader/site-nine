"""SelectableListPane — generic list widget with cursor tracking and vim navigation.

Full implementation is part of Phase 2 (ENG-H-0241).
This stub establishes the module location and class interface.
"""

from __future__ import annotations

from textual.message import Message
from textual.widget import Widget


class SelectableListPane(Widget):
    """
    Generic list widget with cursor tracking.

    Reactive attributes:
        items:        list[Any]  — data items to render
        cursor_index: int        — currently highlighted row
        filter_text:  str        — active filter string

    Messages emitted:
        ItemSelected(item)   — cursor moved to item
        ItemActivated(item)  — Enter/Space pressed on item

    Full implementation in Phase 2 (ENG-H-0241).
    """

    class ItemSelected(Message):
        """Emitted when the cursor moves to a new item."""

        def __init__(self, item: object) -> None:
            super().__init__()
            self.item = item

    class ItemActivated(Message):
        """Emitted when Enter or Space is pressed on the selected item."""

        def __init__(self, item: object) -> None:
            super().__init__()
            self.item = item
