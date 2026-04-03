"""DashboardScreen — main overview screen for the Site-Nine TUI.

Shows:
  - Active missions count and list
  - Task stats (TODO / UNDERWAY / COMPLETE / total)
  - Unread message count
  - Open epics with progress
  - Recent activity

This is the default screen on launch and auto-refreshes every 30 seconds.
"""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import Footer, Header, Static

from site_nine.core.database import Database
from site_nine.tui.app import SCREEN_ORDER
from site_nine.tui.screens.base import PRIORITY_COLOURS, STATUS_COLOURS, STATUS_SYMBOLS, truncate

_REFRESH_INTERVAL = 30  # seconds


class DashboardScreen(Screen):
    """
    Dashboard — default start screen with live project overview.

    Auto-refreshes every 30 seconds.
    Keybindings: r = manual refresh, 1-7 switch screens, q quit.
    """

    SCREEN_NAME = "dashboard"

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("r", "refresh", "Refresh"),
        Binding("1", "app.switch_screen('dashboard')", "Dashboard", show=False),
        Binding("2", "app.switch_screen('missions')", "Missions", show=False),
        Binding("3", "app.switch_screen('tasks')", "Tasks", show=False),
        Binding("4", "app.switch_screen('messages')", "Messages", show=False),
        Binding("5", "app.switch_screen('adrs')", "ADRs", show=False),
        Binding("6", "app.switch_screen('histories')", "Histories", show=False),
        Binding("7", "app.switch_screen('epics')", "Epics", show=False),
    ]

    def __init__(self, db: Database | None) -> None:
        super().__init__()
        self._db = db
        self._refresh_timer: Timer | None = None

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="content-body"):
            with Vertical(id="sidebar", classes="sidebar"):
                for _num, name, label in SCREEN_ORDER:
                    css_class = "sidebar-active" if name == self.SCREEN_NAME else "sidebar-item"
                    yield Static(f"{_num} {label}", classes=css_class)
            with ScrollableContainer(id="dashboard-scroll"):
                yield Static("", id="dashboard-content", markup=True)
        yield Footer()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        self._load_and_render()
        self._refresh_timer = self.set_interval(_REFRESH_INTERVAL, self._load_and_render)

    def on_unmount(self) -> None:
        if self._refresh_timer is not None:
            self._refresh_timer.stop()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _load_and_render(self) -> None:
        """Load data and update the dashboard content."""
        content = self._build_content()
        try:
            self.query_one("#dashboard-content", Static).update(content)
        except Exception:  # noqa: BLE001
            pass

    def _build_content(self) -> str:  # noqa: PLR0912
        if self._db is None:
            return (
                "[red bold]Database unavailable.[/red bold]\n\n"
                "[dim]Run [bold]s9 init[/bold] to initialise the project database.[/dim]"
            )

        lines: list[str] = []

        # ---- Active possessions ------------------------------------------
        try:
            from site_nine.possessions.manager import PossessionManager

            mm = PossessionManager(self._db)
            active = mm.list_possessions(active_only=True)

            lines.append("[bold underline]Active Possessions[/bold underline]")
            if active:
                lines.append(f"  [green]{len(active)} possession(s) running[/green]\n")
                for m in active[:10]:
                    status_col = STATUS_COLOURS.get(
                        m.status.value if hasattr(m.status, "value") else str(m.status), "white"
                    )
                    sym = STATUS_SYMBOLS.get(m.status.value if hasattr(m.status, "value") else str(m.status), "●")
                    lines.append(
                        f"  [{status_col}]{sym}[/{status_col}] [bold]#{m.id}[/bold] {m.daemon_name} ({m.role})"
                    )
                if len(active) > 10:
                    lines.append(f"  [dim]...and {len(active) - 10} more[/dim]")
            else:
                lines.append("  [dim]No active possessions.[/dim]")
        except Exception as exc:  # noqa: BLE001
            lines.append(f"  [red]Error loading possessions: {exc}[/red]")

        lines.append("")

        # ---- Task stats -----------------------------------------------
        try:
            from site_nine.tasks.manager import TaskManager

            tm = TaskManager(self._db)
            all_tasks = tm.list_tasks()
            todo = sum(1 for t in all_tasks if t.status == "TODO")
            underway = sum(1 for t in all_tasks if t.status == "UNDERWAY")
            complete = sum(1 for t in all_tasks if t.status == "COMPLETE")
            blocked = sum(1 for t in all_tasks if t.status == "BLOCKED")
            total = len(all_tasks)

            lines.append("[bold underline]Task Queue[/bold underline]")
            lines.append(f"  Total: [bold]{total}[/bold]")
            lines.append(f"  [white]○ TODO:[/white]     {todo}")
            lines.append(f"  [yellow]● UNDERWAY:[/yellow] {underway}")
            lines.append(f"  [green]✓ COMPLETE:[/green] {complete}")
            if blocked:
                lines.append(f"  [red]⊘ BLOCKED:[/red]  {blocked}")

            # Priority breakdown for TODO/UNDERWAY
            active_tasks = [t for t in all_tasks if t.status in ("TODO", "UNDERWAY")]
            critical = sum(1 for t in active_tasks if t.priority == "CRITICAL")
            high = sum(1 for t in active_tasks if t.priority == "HIGH")
            if critical or high:
                lines.append("")
                lines.append("  [bold]Needs attention:[/bold]")
                if critical:
                    lines.append(f"    [red]CRITICAL: {critical}[/red]")
                if high:
                    lines.append(f"    [yellow]HIGH: {high}[/yellow]")
        except Exception as exc:  # noqa: BLE001
            lines.append(f"  [red]Error loading tasks: {exc}[/red]")

        lines.append("")

        # ---- Unread messages -----------------------------------------
        try:
            from site_nine.messaging.manager import MessageManager

            msgm = MessageManager(self._db)
            all_convs = msgm.list_conversations()
            open_convs = [c for c in all_convs if c.status == "open"]
            conversations = [c for c in open_convs if c.type == "conversation"]
            discussions = [c for c in open_convs if c.type == "discussion"]

            lines.append("[bold underline]Messages[/bold underline]")
            lines.append(f"  Open conversations: [bold]{len(conversations)}[/bold]")
            lines.append(f"  Open discussions:   [bold]{len(discussions)}[/bold]")
        except Exception as exc:  # noqa: BLE001
            lines.append(f"  [red]Error loading messages: {exc}[/red]")

        lines.append("")

        # ---- Open epics ----------------------------------------------
        try:
            from site_nine.epics.manager import EpicManager

            em = EpicManager(self._db)
            todo_epics = em.list_epics(status="TODO")
            underway_epics = em.list_epics(status="UNDERWAY")
            open_epics = todo_epics + underway_epics

            lines.append("[bold underline]Open Epics[/bold underline]")
            if open_epics:
                for epic in open_epics[:5]:
                    status_col = STATUS_COLOURS.get(epic.status or "TODO", "white")
                    progress = ""
                    if epic.subtask_count:
                        pct = epic.progress_percent
                        filled = int(20 * pct / 100)
                        bar = "█" * filled + "░" * (20 - filled)
                        progress = f"  [{bar}] {pct}%"
                    lines.append(f"  [{status_col}]{epic.id}[/{status_col}] {truncate(epic.title, 45)}{progress}")
                if len(open_epics) > 5:
                    lines.append(f"  [dim]...and {len(open_epics) - 5} more[/dim]")
            else:
                lines.append("  [dim]No open epics.[/dim]")
        except Exception as exc:  # noqa: BLE001
            lines.append(f"  [red]Error loading epics: {exc}[/red]")

        lines.append("")

        # ---- Recent activity -----------------------------------------
        try:
            from site_nine.tasks.manager import TaskManager

            tm2 = TaskManager(self._db)
            # Get recently-updated tasks (status changes, new claims, completions)
            all_tasks2 = tm2.list_tasks()
            # Sort by updated_at descending; fall back gracefully if field missing
            recent_tasks = sorted(
                all_tasks2,
                key=lambda t: getattr(t, "updated_at", "") or "",
                reverse=True,
            )[:5]

            lines.append("[bold underline]Recent Activity[/bold underline]")
            if recent_tasks:
                for t in recent_tasks:
                    status_col = STATUS_COLOURS.get(
                        t.status.value if hasattr(t.status, "value") else str(t.status), "white"
                    )
                    sym = STATUS_SYMBOLS.get(t.status.value if hasattr(t.status, "value") else str(t.status), "●")
                    lines.append(
                        f"  [{status_col}]{sym}[/{status_col}] [bold]{t.id}[/bold] {truncate(t.title or '', 55)}"
                    )
            else:
                lines.append("  [dim]No recent task activity.[/dim]")
        except Exception as exc:  # noqa: BLE001
            lines.append(f"  [red]Error loading activity: {exc}[/red]")

        lines.append("")
        lines.append("[dim]Auto-refreshes every 30s — press [bold]r[/bold] to refresh now.[/dim]")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_refresh(self) -> None:
        self._load_and_render()
