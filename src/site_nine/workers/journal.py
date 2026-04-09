"""
Per-possession markdown journal for desk (minion) workers.

Implements the DeskWorkerJournal class as specified in ADR-016, Fix 1.
Each worker opens a temporary pending file before its possession is
initialized, then renames it to a final possession-scoped path once
initialization is complete and the possession ID and daemon name are known.

Journal filename conventions:

  Pending:  .opencode/work/possessions/minion-worker-{role}-{uuid8}.pending.md
  Final:    .opencode/work/possessions/YYYY-MM-DD.HH-MM-SS.{role}.{Daemon}.{possession_id}.journal.md

All writes are flushed immediately so the journal is readable throughout the
worker's lifetime, even if the process crashes before clean shutdown.
"""

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class DeskWorkerJournal:
    """
    Markdown journal for a single minion-mode worker possession.

    The journal is opened in two phases:

    1. **Pending** — opened immediately at worker startup with a UUID-based
       filename, before the possession ID and daemon name are known.
    2. **Final** — renamed after possession initialization completes, using
       the timestamp, role, daemon, and possession ID.

    All write methods flush immediately so entries are visible in real time.
    """

    def __init__(self, pending_path: Path) -> None:
        """
        Open the journal at a temporary pending path.

        Creates parent directories as needed. The file is opened in append
        mode so that any pre-existing content is preserved (e.g., if the
        worker restarts and the file already exists).

        Args:
            pending_path: Path to the temporary pending journal file.
        """
        self._path: Path = pending_path
        pending_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = open(pending_path, "a", encoding="utf-8")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def path(self) -> Path:
        """Current path of the journal file (pending or final)."""
        return self._path

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @classmethod
    def open_pending(cls, possessions_dir: Path, role: str) -> "DeskWorkerJournal":
        """
        Factory: open a new pending journal in the given directory.

        Generates a UUID-based filename so concurrent workers of the same
        role do not collide.

        Args:
            possessions_dir: Directory in which to create the pending file
                (typically ``.opencode/work/possessions/``).
            role: Worker role name (e.g., ``"engineer"``).

        Returns:
            A new DeskWorkerJournal ready for writing.
        """
        uid8 = uuid.uuid4().hex[:8]
        filename = f"minion-worker-{role.lower()}-{uid8}.pending.md"
        return cls(possessions_dir / filename)

    def rename(self, final_path: Path) -> None:
        """
        Rename the journal from its pending path to the final possession-scoped path.

        Flushes and closes the current file handle, performs the rename,
        then reopens the file for further appending at the new path.

        Args:
            final_path: Destination path following the convention
                ``YYYY-MM-DD.HH-MM-SS.<role>.<Daemon>.<possession_id>.journal.md``.
        """
        self._file.flush()
        self._file.close()
        os.rename(self._path, final_path)
        self._path = final_path
        self._file = open(final_path, "a", encoding="utf-8")

    @classmethod
    def make_final_path(
        cls,
        possessions_dir: Path,
        created_at: datetime,
        role: str,
        daemon: str,
        possession_id: int,
    ) -> Path:
        """
        Build the final journal path from possession metadata.

        Args:
            possessions_dir: Parent directory for possession files.
            created_at: Possession creation timestamp (from DB ``created_at``).
                Will be converted to local time for the filename.
            role: Worker role (e.g., ``"Engineer"``).
            daemon: Daemon name (e.g., ``"Halphas"``).
            possession_id: Numeric possession ID.

        Returns:
            A Path with the conventional final filename.
        """
        # Convert to local time for the filename (mirrors interactive possession convention)
        if created_at.tzinfo is not None:
            ts = created_at.astimezone().replace(tzinfo=None)
        else:
            ts = created_at
        date_str = ts.strftime("%Y-%m-%d.%H-%M-%S")
        filename = f"{date_str}.{role.lower()}.{daemon}.{possession_id}.journal.md"
        return possessions_dir / filename

    # ------------------------------------------------------------------
    # Write helpers
    # ------------------------------------------------------------------

    def write_header(
        self,
        possession_id: int,
        daemon: str,
        role: str,
        start_time: str,
    ) -> None:
        """
        Write the YAML front-matter and H1 heading to the journal.

        Should be called once, immediately after the journal is opened
        (before any entries are written).

        Args:
            possession_id: Numeric possession ID.
            daemon: Daemon name.
            role: Worker role.
            start_time: Human-readable start timestamp string.
        """
        header = (
            "---\n"
            f"possession_id: {possession_id}\n"
            f"daemon: {daemon}\n"
            f"role: {role}\n"
            f'start_time: "{start_time}"\n'
            "status: ACTIVE\n"
            "---\n"
            "\n"
            f"# Minion Worker Journal: {daemon} \u2014 {role}\n"
            "\n"
            "## Initialization\n"
            "\n"
        )
        self._file.write(header)
        self._file.flush()

    def write_entry(self, text: str) -> None:
        """
        Append a timestamped bullet entry to the journal.

        The entry is prefixed with the current local time in ``HH:MM:SS``
        format and flushed immediately.

        Args:
            text: Entry body text (single line or short phrase).
        """
        ts = datetime.now().strftime("%H:%M:%S")
        self._file.write(f"- **{ts}** {text}\n")
        self._file.flush()

    def write_section(self, heading: str) -> None:
        """
        Append a markdown H2 section heading.

        Args:
            heading: Section title text.
        """
        self._file.write(f"\n## {heading}\n\n")
        self._file.flush()

    def write_message_section(
        self,
        timestamp: str,
        message_id: str,
        from_possession_id: int,
        priority: str,
        body_preview: Optional[str] = None,
    ) -> None:
        """
        Append an H3 section for an incoming message.

        Args:
            timestamp: Formatted time string for the heading.
            message_id: Message identifier string.
            from_possession_id: Sender's possession ID.
            priority: Message priority (e.g., ``"HIGH"``).
            body_preview: Optional short preview of the message body.
        """
        self._file.write(f"\n### [{timestamp}] {message_id} from Possession #{from_possession_id} ({priority})\n")
        if body_preview:
            self._file.write(f"{body_preview}\n")
        self._file.flush()

    def write_shutdown(self) -> None:
        """
        Append the Shutdown section with a final timestamp.

        Should be called during clean shutdown before the process exits.
        If the process crashes, the journal simply ends at its last entry.
        """
        ts = datetime.now().strftime("%H:%M:%S")
        self._file.write(f"\n## Shutdown\n\n- **{ts}** Shutdown complete.\n")
        self._file.flush()
        self._file.close()
