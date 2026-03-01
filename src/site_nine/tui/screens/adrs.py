"""ADRsScreen — Architecture Decision Records viewer for the Site-Nine TUI.

Layout:
  - List pane: table of ADRs (id, title, status, file_path)
  - Preview pane: first ~30 lines of the ADR markdown file rendered
  - Full-page view: full ADR file content, scrollable
  - Color-coded by status: ACCEPTED=green, PROPOSED=yellow, DEPRECATED=dim,
    SUPERSEDED=strikethrough (dim), REJECTED=red
  - Keybindings: j/k or up/down, Enter for full page, Escape to close,
    / to filter by title
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, Static

from site_nine.adrs.manager import ADRManager
from site_nine.adrs.models import ArchitectureDoc
from site_nine.core.database import Database

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STATUS_COLOURS: dict[str, str] = {
    "PROPOSED": "yellow",
    "ACCEPTED": "green",
    "REJECTED": "red",
    "SUPERSEDED": "dim",
    "DEPRECATED": "dim",
}

_STATUS_SYMBOLS: dict[str, str] = {
    "PROPOSED": "?",
    "ACCEPTED": "✓",
    "REJECTED": "✗",
    "SUPERSEDED": "↩",
    "DEPRECATED": "↩",
}


def _truncate(text: str, width: int) -> str:
    """Truncate string to *width* characters, appending '…' if needed."""
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"


def _status_markup(status: str) -> str:
    """Return Rich markup for an ADR status string."""
    col = _STATUS_COLOURS.get(status, "white")
    sym = _STATUS_SYMBOLS.get(status, " ")
    if status in ("SUPERSEDED", "DEPRECATED"):
        return f"[{col}]{sym} {status}[/{col}]"
    return f"[{col}]{sym} {status}[/{col}]"


def _read_file_safe(file_path: str, max_lines: int | None = None) -> str:
    """Read a file safely, returning an error message if unavailable."""
    path = Path(file_path)
    if not path.exists():
        return f"[dim](File not found: {file_path})[/dim]"
    try:
        content = path.read_text(encoding="utf-8")
        if max_lines is not None:
            lines = content.splitlines()
            if len(lines) > max_lines:
                content = "\n".join(lines[:max_lines]) + f"\n[dim]... ({len(lines) - max_lines} more lines)[/dim]"
        return content
    except OSError as exc:
        return f"[red]Error reading file: {exc}[/red]"


# ---------------------------------------------------------------------------
# Full-page view (pushed screen)
# ---------------------------------------------------------------------------


class ADRFullPage(Screen):
    """Full scrollable view of an ADR file."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("j", "scroll_down", "Scroll down", show=False),
        Binding("k", "scroll_up", "Scroll up", show=False),
        Binding("d", "scroll_page_down", "Page down", show=False),
        Binding("u", "scroll_page_up", "Page up", show=False),
        Binding("g", "scroll_home", "Top", show=False),
        Binding("G", "scroll_end", "Bottom", show=False),
    ]

    def __init__(self, adr: ArchitectureDoc, db: Database) -> None:
        super().__init__()
        self._adr = adr
        self._db = db

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        adr = self._adr
        status_col = _STATUS_COLOURS.get(adr.status.value, "white")
        title = f"[ESC]  {adr.id}: {_truncate(adr.title, 55)}  [{status_col}]{adr.status.value}[/{status_col}]"
        yield Static(title, id="fullpage-title", classes="fullpage-title", markup=True)
        with ScrollableContainer(id="fullpage-scroll"):
            yield Static(self._build_content(), id="fullpage-body", markup=True)
        yield Footer()

    def _build_content(self) -> str:
        """Read and render the full ADR file content."""
        raw = _read_file_safe(self._adr.file_path)
        # Escape Rich markup characters from file content to avoid injection
        return raw.replace("[", "\\[")

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
# ADRs screen
# ---------------------------------------------------------------------------


class ADRsScreen(Screen):
    """
    ADRs screen — Architecture Decision Records list with preview and full-page view.

    List view columns: ID, Title, Status, File
    Preview pane: first ~30 lines of the ADR markdown file
    Full-page view: full ADR file content scrollable

    Status colours:
        ACCEPTED    → green
        PROPOSED    → yellow
        REJECTED    → red
        SUPERSEDED  → dim
        DEPRECATED  → dim

    Keybindings:
        j / down    Move selection down
        k / up      Move selection up
        Enter       Open full-page view
        Escape      Pop this screen
        /           Focus title-filter input
        r           Reset filter
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("up", "cursor_up", "Up", show=False),
        Binding("enter", "open_fullpage", "Open"),
        Binding("escape", "app.pop_screen", "Back"),
        Binding("/", "focus_filter", "Filter", show=True),
        Binding("r", "reset_filter", "Reset", show=False),
        Binding("5", "app.switch_screen('adrs')", "ADRs", show=False),
    ]

    def __init__(self, db: Database) -> None:
        super().__init__()
        self._db = db
        self._manager = ADRManager(db)
        self._all_adrs: list[ArchitectureDoc] = []
        self._filtered_adrs: list[ArchitectureDoc] = []
        self._filter_text: str = ""

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="adrs-body"):
            with Vertical(id="sidebar", classes="sidebar"):
                yield Static("5 ADRs", classes="sidebar-active")
            with Vertical(id="content-area"):
                yield Static(self._filter_label(), id="filter-label", classes="subview-label", markup=True)
                yield Input(
                    placeholder="Filter by title (Enter to apply, Esc to cancel)",
                    id="title-filter-input",
                    classes="filter-input",
                )
                yield DataTable(id="adrs-table", show_cursor=True, zebra_stripes=True)
                with ScrollableContainer(id="preview-pane", classes="preview-pane"):
                    yield Static("", id="preview-text", markup=True)
        yield Footer()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        self.query_one("#title-filter-input", Input).display = False
        self._load_data()
        self._populate_table()

    def _load_data(self) -> None:
        """Load all ADRs from the database."""
        try:
            self._all_adrs = self._manager.list_adrs()
        except Exception as exc:  # noqa: BLE001
            self._all_adrs = []
            self._set_preview(f"[red]Error loading ADRs: {exc}[/red]")

    def _apply_filter(self) -> list[ArchitectureDoc]:
        """Return ADRs matching the current title filter."""
        if not self._filter_text:
            return list(self._all_adrs)
        needle = self._filter_text.lower()
        return [a for a in self._all_adrs if needle in a.title.lower() or needle in a.id.lower()]

    def _populate_table(self) -> None:
        """Populate the DataTable with (filtered) ADR data."""
        self._filtered_adrs = self._apply_filter()
        table = self.query_one("#adrs-table", DataTable)
        table.clear(columns=True)
        table.add_columns("ID", "Title", "Status", "File")

        for adr in self._filtered_adrs:
            status_val = adr.status.value
            status_col = _STATUS_COLOURS.get(status_val, "white")
            sym = _STATUS_SYMBOLS.get(status_val, " ")

            table.add_row(
                adr.id,
                _truncate(adr.title, 45),
                f"[{status_col}]{sym} {status_val}[/{status_col}]",
                _truncate(adr.file_path, 40),
                key=adr.id,
            )

        self.query_one("#filter-label", Static).update(self._filter_label())

        if not self._filtered_adrs:
            self._set_preview("[dim]No ADRs match the current filter.[/dim]")
        else:
            table.move_cursor(row=0)
            self._refresh_preview()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:  # noqa: ARG002
        self._refresh_preview()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Apply title filter when Enter is pressed."""
        self._filter_text = event.value.strip()
        input_widget = self.query_one("#title-filter-input", Input)
        input_widget.display = False
        self.query_one("#adrs-table", DataTable).focus()
        self._populate_table()

    def on_input_key(self, event) -> None:  # type: ignore[override]
        """Hide filter input on Escape."""
        if hasattr(event, "key") and event.key == "escape":
            input_widget = self.query_one("#title-filter-input", Input)
            if input_widget.display:
                input_widget.display = False
                self.query_one("#adrs-table", DataTable).focus()

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def _refresh_preview(self) -> None:
        """Update preview pane with first ~30 lines of the selected ADR file."""
        table = self.query_one("#adrs-table", DataTable)
        if table.row_count == 0:
            return
        try:
            adr_id = str(table.get_row_at(table.cursor_row)[0])
        except Exception:  # noqa: BLE001
            return
        self._show_preview_for(adr_id)

    def _show_preview_for(self, adr_id: str) -> None:
        """Render preview of the selected ADR."""
        adr = next((a for a in self._filtered_adrs if a.id == adr_id), None)
        if adr is None:
            self._set_preview(f"[dim]{adr_id} not found.[/dim]")
            return

        status_val = adr.status.value
        status_col = _STATUS_COLOURS.get(status_val, "white")
        sym = _STATUS_SYMBOLS.get(status_val, " ")

        lines: list[str] = [
            f"[bold]{adr.id}[/bold]  [{status_col}]{sym} {status_val}[/{status_col}]",
            f"[bold]{adr.title}[/bold]",
            f"[dim]{adr.file_path}[/dim]",
            "",
        ]

        # Read first 30 lines of the file
        raw = _read_file_safe(adr.file_path, max_lines=30)
        # Escape Rich markup to prevent injection
        for line in raw.splitlines():
            lines.append(line.replace("[", "\\["))

        self._set_preview("\n".join(lines))

    def _set_preview(self, markup: str) -> None:
        self.query_one("#preview-text", Static).update(markup)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_cursor_down(self) -> None:
        self.query_one("#adrs-table", DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#adrs-table", DataTable).action_cursor_up()

    def action_open_fullpage(self) -> None:
        """Push the full-page ADR view."""
        table = self.query_one("#adrs-table", DataTable)
        if table.row_count == 0:
            return
        try:
            adr_id = str(table.get_row_at(table.cursor_row)[0])
        except Exception:  # noqa: BLE001
            return

        adr = next((a for a in self._filtered_adrs if a.id == adr_id), None)
        if adr is None:
            return
        self.app.push_screen(ADRFullPage(adr, self._db))

    def action_focus_filter(self) -> None:
        """Show and focus the title filter input."""
        input_widget = self.query_one("#title-filter-input", Input)
        input_widget.display = True
        input_widget.focus()

    def action_reset_filter(self) -> None:
        """Clear the title filter."""
        self._filter_text = ""
        self.query_one("#title-filter-input", Input).value = ""
        self._populate_table()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _filter_label(self) -> str:
        count = len(self._filtered_adrs)
        total = len(self._all_adrs)
        if self._filter_text:
            filter_str = f"filter:[bold]{self._filter_text}[/bold]"
            count_str = f"[dim]({count}/{total})[/dim]"
        else:
            filter_str = "[dim]filter:none[/dim]"
            count_str = f"[dim]({total})[/dim]"
        return f"{filter_str}  {count_str}  [dim]/=filter  r=reset[/dim]"
