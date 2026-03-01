"""MessagesScreen — Conversations and Discussions viewer for the Site-Nine TUI.

Layout:
  - Two sub-views toggled by Tab: Conversations and Discussions
  - List pane: subject, participants/scope, last-update time, unread badge
  - Preview pane: last few messages in thread with sender and timestamp
  - Full-page view: full conversation thread scrollable, newest at bottom
  - Unread items highlighted
  - Keybindings: j/k or up/down, Tab to switch sub-view, Enter for full page, Escape to close
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pendulum
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Label, Static

from site_nine.core.database import Database
from site_nine.messaging.manager import MessageManager
from site_nine.messaging.models import Conversation, Message

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PRIORITY_COLOURS: dict[str, str] = {
    "CRITICAL": "red",
    "HIGH": "yellow",
    "MEDIUM": "white",
    "LOW": "dim",
}

_SUBVIEW_LABELS = ("Conversations", "Discussions")


def _age(dt: pendulum.DateTime) -> str:
    """Human-readable age string (e.g. '5m ago', '2h ago')."""
    now = pendulum.now("UTC")
    diff = now.diff(dt)
    if diff.in_seconds() < 60:
        return "just now"
    if diff.in_minutes() < 60:
        return f"{diff.in_minutes()}m ago"
    if diff.in_hours() < 24:
        return f"{diff.in_hours()}h ago"
    return f"{diff.in_days()}d ago"


def _truncate(text: str, width: int) -> str:
    """Truncate string to *width* characters, appending '…' if needed."""
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"


# ---------------------------------------------------------------------------
# Full-page view (pushed screen)
# ---------------------------------------------------------------------------


class ConversationFullPage(Screen):
    """Full scrollable view of a conversation thread."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("j", "scroll_down", "Scroll down", show=False),
        Binding("k", "scroll_up", "Scroll up", show=False),
        Binding("d", "scroll_page_down", "Page down", show=False),
        Binding("u", "scroll_page_up", "Page up", show=False),
        Binding("g", "scroll_home", "Top", show=False),
        Binding("G", "scroll_end", "Bottom", show=False),
    ]

    def __init__(self, conversation: Conversation, messages: list[Message], db: Database) -> None:
        super().__init__()
        self._conversation = conversation
        self._messages = messages
        self._db = db

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        conv = self._conversation
        if conv.type == "conversation":
            title = f"[ESC] Conversation {conv.id}: {conv.subject}"
        else:
            scope = conv.scope_role or conv.scope_epic_id or conv.scope_type or "all"
            title = f"[ESC] Discussion {conv.id} [{scope}]: {conv.subject}"
        yield Header(show_clock=False)
        yield Static(title, id="fullpage-title", classes="fullpage-title")
        with ScrollableContainer(id="fullpage-scroll"):
            yield Static(self._render_thread(), id="fullpage-body", markup=True)
        yield Footer()

    def _render_thread(self) -> str:
        """Render all messages as a text block (oldest first)."""
        if not self._messages:
            return "[dim]No messages in this conversation.[/dim]"

        lines: list[str] = []
        for msg in self._messages:
            priority_colour = _PRIORITY_COLOURS.get(msg.priority, "white")
            age = _age(msg.created_at)
            indent = "    " if msg.parent_message_id else ""
            header = (
                f"{indent}[bold]Mission #{msg.from_mission_id}[/bold]  "
                f"[{priority_colour}]{msg.priority}[/{priority_colour}]  "
                f"[dim]{age}[/dim]"
            )
            lines.append(header)
            for line in msg.body.splitlines():
                lines.append(f"{indent}  {line}")
            lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_scroll_down(self) -> None:
        self.query_one("#fullpage-scroll", ScrollableContainer).scroll_down()

    def action_scroll_up(self) -> None:
        self.query_one("#fullpage-scroll", ScrollableContainer).scroll_up()

    def action_scroll_page_down(self) -> None:
        scroll = self.query_one("#fullpage-scroll", ScrollableContainer)
        scroll.scroll_relative(y=scroll.size.height // 2)

    def action_scroll_page_up(self) -> None:
        scroll = self.query_one("#fullpage-scroll", ScrollableContainer)
        scroll.scroll_relative(y=-(scroll.size.height // 2))

    def action_scroll_home(self) -> None:
        self.query_one("#fullpage-scroll", ScrollableContainer).scroll_home()

    def action_scroll_end(self) -> None:
        self.query_one("#fullpage-scroll", ScrollableContainer).scroll_end()


# ---------------------------------------------------------------------------
# Messages screen
# ---------------------------------------------------------------------------


class MessagesScreen(Screen):
    """
    Messages screen — conversations and discussions viewer.

    Sub-views (toggled with Tab):
        Conversations — 1-on-1 conversations between missions
        Discussions   — scoped group discussions (role / epic / all)

    Keybindings:
        j / down    Move selection down
        k / up      Move selection up
        Tab         Toggle sub-view (Conversations ↔ Discussions)
        Enter       Open full-page view
        Escape      Pop this screen
        /           (reserved — filter bar not yet implemented)
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("up", "cursor_up", "Up", show=False),
        Binding("tab", "toggle_subview", "Toggle view"),
        Binding("enter", "open_fullpage", "Open"),
        Binding("escape", "app.pop_screen", "Back"),
        Binding("4", "app.switch_screen('messages')", "Messages", show=False),
    ]

    # Which sub-view is active: 0 = Conversations, 1 = Discussions
    active_subview: reactive[int] = reactive(0)

    def __init__(self, db: Database) -> None:
        super().__init__()
        self._db = db
        self._manager = MessageManager(db)
        self._conversations: list[Conversation] = []
        self._discussions: list[Conversation] = []

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="messages-body"):
            with Vertical(id="sidebar", classes="sidebar"):
                yield Static("4 Messages", classes="sidebar-active")
            with Vertical(id="content-area"):
                yield Static(self._subview_label(), id="subview-label", classes="subview-label")
                yield DataTable(id="messages-table", show_cursor=True, zebra_stripes=True)
                with ScrollableContainer(id="preview-pane", classes="preview-pane"):
                    yield Static("", id="preview-text", markup=True)
        yield Footer()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        self._load_data()
        self._populate_table()

    def _load_data(self) -> None:
        """Load conversations and discussions from the database."""
        try:
            all_convs = self._manager.list_conversations()
            self._conversations = [c for c in all_convs if c.type == "conversation"]
            self._discussions = [c for c in all_convs if c.type == "discussion"]
        except Exception as exc:  # noqa: BLE001
            self._conversations = []
            self._discussions = []
            self._set_preview(f"[red]Error loading messages: {exc}[/red]")

    def _populate_table(self) -> None:
        """Populate the DataTable with the active sub-view data."""
        table = self.query_one("#messages-table", DataTable)
        table.clear(columns=True)

        if self.active_subview == 0:
            # Conversations
            table.add_columns("ID", "Subject", "Participants", "Status", "Updated")
            for conv in self._conversations:
                p1 = str(conv.participant_1_id) if conv.participant_1_id else "-"
                p2 = str(conv.participant_2_id) if conv.participant_2_id else "-"
                participants = f"#{p1} ↔ #{p2}"
                status_style = "green" if conv.status == "open" else "dim"
                table.add_row(
                    conv.id,
                    _truncate(conv.subject, 40),
                    participants,
                    f"[{status_style}]{conv.status}[/{status_style}]",
                    _age(conv.updated_at),
                    key=conv.id,
                )
            if not self._conversations:
                self._set_preview("[dim]No conversations found.[/dim]")
        else:
            # Discussions
            table.add_columns("ID", "Subject", "Scope", "Status", "Updated")
            for disc in self._discussions:
                if disc.scope_type == "role":
                    scope = f"role:{disc.scope_role}"
                elif disc.scope_type == "epic":
                    scope = f"epic:{disc.scope_epic_id}"
                else:
                    scope = disc.scope_type or "all"
                status_style = "green" if disc.status == "open" else "dim"
                table.add_row(
                    disc.id,
                    _truncate(disc.subject, 40),
                    scope,
                    f"[{status_style}]{disc.status}[/{status_style}]",
                    _age(disc.updated_at),
                    key=disc.id,
                )
            if not self._discussions:
                self._set_preview("[dim]No discussions found.[/dim]")

        if table.row_count > 0:
            table.move_cursor(row=0)
            self._refresh_preview()

    # ------------------------------------------------------------------
    # Reactive watchers
    # ------------------------------------------------------------------

    def watch_active_subview(self, _: int) -> None:
        label = self.query_one("#subview-label", Static)
        label.update(self._subview_label())
        self._populate_table()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def on_data_table_cursor_moved(self, event: DataTable.CursorMoved) -> None:  # noqa: ARG002
        self._refresh_preview()

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def _refresh_preview(self) -> None:
        """Update preview pane with messages from selected conversation."""
        table = self.query_one("#messages-table", DataTable)
        if table.row_count == 0:
            return
        try:
            row_key = table.get_row_at(table.cursor_row)[0]  # ID is first column
            conv_id = str(row_key)
        except Exception:  # noqa: BLE001
            return
        self._show_preview_for(conv_id)

    def _show_preview_for(self, conv_id: str) -> None:
        """Render the last few messages of a conversation into the preview pane."""
        try:
            messages = self._manager.list_messages(conversation_id=conv_id)
            recent = messages[-5:]  # last 5 messages
            if not recent:
                self._set_preview(f"[dim]{conv_id}: No messages yet.[/dim]")
                return
            lines: list[str] = [f"[bold]{conv_id}[/bold] — last {len(recent)} message(s)\n"]
            for msg in recent:
                priority_colour = _PRIORITY_COLOURS.get(msg.priority, "white")
                age = _age(msg.created_at)
                lines.append(
                    f"[bold]#{msg.from_mission_id}[/bold]  "
                    f"[{priority_colour}]{msg.priority}[/{priority_colour}]  "
                    f"[dim]{age}[/dim]"
                )
                # Show first two lines of body
                body_preview = "\n".join(msg.body.splitlines()[:2])
                lines.append(f"  {_truncate(body_preview, 120)}")
                lines.append("")
            self._set_preview("\n".join(lines))
        except Exception as exc:  # noqa: BLE001
            self._set_preview(f"[red]Preview error: {exc}[/red]")

    def _set_preview(self, markup: str) -> None:
        self.query_one("#preview-text", Static).update(markup)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_cursor_down(self) -> None:
        self.query_one("#messages-table", DataTable).action_scroll_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#messages-table", DataTable).action_scroll_cursor_up()

    def action_toggle_subview(self) -> None:
        self.active_subview = 1 - self.active_subview

    def action_open_fullpage(self) -> None:
        """Push the full-page conversation view."""
        table = self.query_one("#messages-table", DataTable)
        if table.row_count == 0:
            return
        try:
            conv_id = str(table.get_row_at(table.cursor_row)[0])
        except Exception:  # noqa: BLE001
            return

        items = self._conversations if self.active_subview == 0 else self._discussions
        conv = next((c for c in items if c.id == conv_id), None)
        if conv is None:
            return

        try:
            messages = self._manager.list_messages(conversation_id=conv_id)
        except Exception:  # noqa: BLE001
            messages = []

        self.app.push_screen(ConversationFullPage(conv, messages, self._db))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _subview_label(self) -> str:
        tabs = []
        for i, label in enumerate(_SUBVIEW_LABELS):
            if i == self.active_subview:
                tabs.append(f"[bold underline]{label}[/bold underline]")
            else:
                tabs.append(f"[dim]{label}[/dim]")
        return "  ".join(tabs) + "  [dim](Tab to switch)[/dim]"
