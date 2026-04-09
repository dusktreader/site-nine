#!/usr/bin/env python3
"""
Minion Mode Worker Polling Script

Manages minion agent lifecycle outside agent context. Polls for unread messages,
invokes 'opencode run' for each message, and preserves session context across
invocations.

Usage:
    minion-worker.py <role> [--daemon NAME] [--model MODEL] [--poll-interval SECONDS]

Example:
    minion-worker.py engineer --daemon halphas
    minion-worker.py architect --poll-interval 15
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# Imports from site_nine package
# (No path manipulation needed - this module is now properly in src/site_nine/)
from site_nine.core.database import Database
from site_nine.core.paths import get_db_path, get_project_root
from site_nine.messaging.manager import MessageManager
from site_nine.possessions.manager import PossessionManager
from site_nine.workers.journal import DeskWorkerJournal


class MinionWorker:
    """External polling loop for minion mode workers."""

    # Default model to use for opencode run
    DEFAULT_MODEL = "github-copilot/claude-sonnet-4.6"

    # Default polling interval (seconds)
    DEFAULT_POLL_INTERVAL = 30

    # Idle heartbeat interval (seconds).  When no messages are processed for
    # this long, the worker touches possessions.last_heartbeat_at so that the
    # Inquisitor's tightened 15-minute staleness threshold does not incorrectly
    # exorcise a healthy idle worker.
    HEARTBEAT_INTERVAL = 300  # 5 minutes

    # Priority ordering for message processing
    PRIORITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

    def __init__(
        self,
        role: str,
        daemon: Optional[str] = None,
        model: Optional[str] = None,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
    ):
        """
        Initialize minion worker.

        Args:
            role: Worker role (e.g., 'Engineer', 'Architect', 'Tester')
            daemon: Optional specific daemon name (if None, auto-selected)
            model: OpenCode model to use (defaults to claude-sonnet-4.6)
            poll_interval: Seconds between message checks (default: 30)
        """
        self.role = role
        self.daemon = daemon
        self.model = model or self.DEFAULT_MODEL
        self.poll_interval = poll_interval
        self.session_id: Optional[str] = None
        self.possession_id: Optional[int] = None
        self.running = True

        # Open a pending journal immediately so pre-init output is captured.
        # The journal is renamed to its final possession-scoped path after
        # initialize() completes and we know the possession ID and daemon.
        possessions_dir = self._get_possessions_dir()
        self.journal: DeskWorkerJournal = DeskWorkerJournal.open_pending(possessions_dir, role)

    @staticmethod
    def _get_possessions_dir() -> Path:
        """Return the .opencode/work/possessions directory, creating it if needed."""
        try:
            project_root = get_project_root()
        except FileNotFoundError:
            # Fall back to cwd if project root not discoverable
            project_root = Path.cwd()
        possessions_dir = project_root / ".opencode" / "work" / "possessions"
        possessions_dir.mkdir(parents=True, exist_ok=True)
        return possessions_dir

    def initialize(self) -> None:
        """
        Initialize worker possession via opencode run.

        Launches initial session, waits for possession creation, and retrieves
        session ID from database.

        Raises:
            RuntimeError: If possession initialization fails
        """
        self.journal.write_entry(f"Worker process started (PID: {os.getpid()})")

        # Build initialization message
        init_parts = [f"Your role is {self.role}."]

        if self.daemon:
            init_parts.append(f"Your daemon is {self.daemon}.")

        init_parts.append(
            "Initialize your possession with the possession-start skill. Mode: minion. "
            "DO NOT claim any tasks. DO NOT do any work yet. "
            "After your possession is initialized and you have a possession ID, stop immediately. "
            "The minion-worker wrapper handles message polling and will send you work assignments. "
            "IMPORTANT: When you receive a work assignment message, you MUST use the worker_message "
            "tool to send status updates back to the sender (use their possession ID as to_possession_id). "
            "Send a message when you: (1) start a task, (2) complete a task, (3) hit a blocker, "
            "(4) make significant progress. Never work silently — always report back. "
            "ALSO: Use the push_status tool to send short toast notifications to the director "
            "whenever your status changes (task started, task complete, blocked, going idle). "
            "Keep push_status messages under 120 characters."
        )

        init_message = " ".join(init_parts)

        # Launch initial session with JSON format to extract session ID
        cmd = ["opencode", "run", "--format", "json", "--model", self.model, init_message]

        try:
            # Use Popen for non-blocking execution
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Wait for process with a 10-minute timeout for initialization
            try:
                stdout, stderr = process.communicate(timeout=600)

                # Extract session ID from JSON output lines
                session_id = None
                for line in stdout.splitlines():
                    if line.strip():
                        try:
                            event = json.loads(line)
                            if "sessionID" in event:
                                session_id = event["sessionID"]
                                break
                        except json.JSONDecodeError:
                            continue

                if not session_id:
                    raise RuntimeError(
                        f"Failed to extract session ID from opencode run output.\n"
                        f"Exit code: {process.returncode}\n"
                        f"Stderr: {stderr[:1000] if stderr else '(empty)'}\n"
                        f"Stdout (last 500 chars): {stdout[-500:] if stdout else '(empty)'}"
                    )

                self.session_id = session_id
                self.journal.write_entry(f"OpenCode session initialized (session: {session_id})")

                if process.returncode != 0:
                    # Non-zero exit is a warning, not fatal — the agent may have exited
                    # after completing init. As long as we got a session ID and the possession
                    # was created in the DB, we can continue.
                    self.journal.write_entry(
                        f"Warning: opencode run exited with code {process.returncode} (may be normal after init)"
                    )

            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                raise RuntimeError("Possession initialization timed out after 10 minutes")

        except FileNotFoundError:
            raise RuntimeError("opencode command not found. Is OpenCode installed and in PATH?")

        # Wait for possession to be created in database
        self.journal.write_entry("Waiting for possession to be created in database...")
        time.sleep(5)

        # Find possession ID from database.
        # Possession goes through ROLE_PENDING -> DAEMON_PENDING -> ACTIVE via OpenCode tools.
        # Poll until ACTIVE status appears, first by session ID then by role.
        db = Database(get_db_path())
        possession_row: dict | None = None

        # Phase 1: look up by session ID (preferred — agent bound the session via possession_init)
        for _ in range(30):  # up to 30s
            rows = db.execute_query(
                """
                SELECT id, daemon_name, created_at FROM possessions
                WHERE opencode_session_id = :session_id
                  AND status = 'ACTIVE'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                {"session_id": self.session_id},
            )
            if rows:
                possession_row = rows[0]
                break
            time.sleep(1)

        # Phase 2: fall back to role-based lookup (session may not have been bound)
        if possession_row is None:
            self.journal.write_entry("Possession not found by session ID, searching by role...")
            for _ in range(15):  # up to 15s
                rows = db.execute_query(
                    """
                    SELECT id, daemon_name, created_at FROM possessions
                    WHERE role = :role
                      AND opencode_session_id IS NULL
                      AND status = 'ACTIVE'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    {"role": self.role},
                )
                if rows:
                    possession_row = rows[0]
                    break
                time.sleep(1)

        if possession_row is None:
            raise RuntimeError(
                f"Failed to find initialized possession for role {self.role}. "
                "Check that possession-start completed successfully."
            )

        self.possession_id = possession_row["id"]
        daemon_used = possession_row["daemon_name"]

        # If found by role (no session binding), bind now
        if not db.execute_query(
            "SELECT id FROM possessions WHERE id = :id AND opencode_session_id IS NOT NULL",
            {"id": self.possession_id},
        ):
            self.journal.write_entry(f"Binding session {self.session_id} to possession #{self.possession_id}...")
            db.execute_update(
                """
                UPDATE possessions
                SET opencode_session_id = :session_id
                WHERE id = :possession_id
                """,
                {"session_id": self.session_id, "possession_id": self.possession_id},
            )

        if not self.session_id:
            raise RuntimeError(f"Possession #{self.possession_id} has no OpenCode session ID. Session binding failed.")

        self.journal.write_entry(f"Possession ACTIVE (id: {self.possession_id})")

        # Rename journal from pending to final possession-scoped path
        raw_created_at = possession_row["created_at"]
        if isinstance(raw_created_at, str):
            # SQLite may return a string; parse it
            try:
                created_at = datetime.fromisoformat(raw_created_at)
            except ValueError:
                created_at = datetime.now()
        else:
            created_at = raw_created_at if raw_created_at is not None else datetime.now()

        final_path = DeskWorkerJournal.make_final_path(
            possessions_dir=self._get_possessions_dir(),
            created_at=created_at,
            role=self.role,
            daemon=daemon_used,
            possession_id=self.possession_id,
        )
        self.journal.rename(final_path)

        # Now write the front-matter header (after rename so it lands in the right file)
        self.journal.write_header(
            possession_id=self.possession_id,
            daemon=daemon_used,
            role=self.role,
            start_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        # Re-record the key init events in structured form after the header
        self.journal.write_entry(f"Minion mode enabled. Polling every {self.poll_interval}s.")

    def enable_minion_mode(self) -> None:
        """
        Enable minion mode in database and register the worker PID.

        Sets minion_mode_active=1 and records os.getpid() in worker_pid for
        this worker's possession. The Inquisitor uses worker_pid to detect
        crashes via os.kill(pid, 0) without waiting for heartbeat staleness.

        Raises:
            RuntimeError: If possession_id is not set
        """
        if self.possession_id is None:
            raise RuntimeError("Cannot enable minion mode: possession_id is not set")

        db = Database(get_db_path())
        mgr = PossessionManager(db)
        mgr.set_minion_mode(self.possession_id, active=True)

        # Register worker PID for Inquisitor crash detection (ADR-016, Fix 4)
        db.execute_update(
            "UPDATE possessions SET worker_pid = :pid WHERE id = :id",
            {"pid": os.getpid(), "id": self.possession_id},
        )
        self.journal.write_entry(f"Worker PID registered: {os.getpid()}")

    def _emit_heartbeat(self) -> None:
        """Touch possessions.last_heartbeat_at so the Inquisitor knows this worker is alive.

        Called from the polling loop when no messages have been processed for
        HEARTBEAT_INTERVAL seconds.  Non-fatal: any exception is logged and
        swallowed so a transient DB error cannot kill the polling loop.
        """
        self.journal.write_entry("Heartbeat — idle, polling for messages")
        try:
            db = Database(get_db_path())
            mgr = PossessionManager(db)
            mgr.heartbeat(self.possession_id)
        except Exception as exc:
            self.journal.write_entry(f"Warning: heartbeat failed: {exc}")

    def check_for_messages(self) -> list:
        """
        Check for unread messages addressed to this worker.

        Returns:
            List of unread messages, sorted by priority (highest first)

        Raises:
            RuntimeError: If possession_id is not set
        """
        if self.possession_id is None:
            raise RuntimeError("Cannot check messages: possession_id not set")

        db = Database(get_db_path())
        msg_mgr = MessageManager(db)

        # Get unread conversations
        conversations = msg_mgr.get_unread_conversations(self.possession_id)

        # Collect unread messages from others
        messages = []
        for conv in conversations:
            unread = msg_mgr.get_unread_messages(conv.id, self.possession_id)
            for msg in unread:
                # Exclude own messages (only process messages from others)
                if msg.from_possession_id != self.possession_id:
                    messages.append(msg)

        # Sort by priority (CRITICAL > HIGH > MEDIUM > LOW)
        messages.sort(key=lambda m: self.PRIORITY_ORDER.get(m.priority, 99))

        return messages

    def process_message(self, message) -> bool:
        """
        Process a single message via opencode run.

        Args:
            message: Message object to process

        Returns:
            True if processing succeeded, False otherwise
        """
        # Resume session with message as prompt
        cmd = [
            "opencode",
            "run",
            "--session",
            self.session_id,
            "--model",
            self.model,
            message.body,
        ]

        ts = datetime.now().strftime("%H:%M:%S")
        body_preview = (message.body[:120] + "...") if len(message.body) > 120 else message.body
        self.journal.write_message_section(
            timestamp=ts,
            message_id=str(message.id),
            from_possession_id=message.from_possession_id,
            priority=message.priority,
            body_preview=body_preview,
        )
        self.journal.write_entry("Processing started")

        try:
            # Use Popen for non-blocking execution
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Wait for process with 20-minute timeout
            try:
                stdout, stderr = process.communicate(timeout=1200)

                # Mark conversation as viewed (read)
                db = Database(get_db_path())
                msg_mgr = MessageManager(db)
                if self.possession_id is not None:
                    msg_mgr.update_conversation_view(message.conversation_id, self.possession_id)

                if process.returncode == 0:
                    self.journal.write_entry(f"Processing complete (exit code 0)")
                    return True
                else:
                    self.journal.write_entry(f"Processing failed (exit code {process.returncode})")
                    return False

            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                self.journal.write_entry("Processing timed out after 20 minutes")
                return False

        except Exception as e:
            self.journal.write_entry(f"Processing error: {e}")
            return False

    def handle_shutdown(self, signum: int, frame) -> None:
        """
        Gracefully shutdown on SIGTERM/SIGINT.

        Disables minion mode, ends possession, and exits.

        Args:
            signum: Signal number
            frame: Current stack frame (unused)
        """
        signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
        self.journal.write_section("Shutdown")
        self.journal.write_entry(f"{signal_name} received. Disabling minion mode.")
        self.running = False

        # Disable minion mode and clear worker PID
        try:
            db = Database(get_db_path())
            mgr = PossessionManager(db)
            if self.possession_id is not None:
                mgr.set_minion_mode(self.possession_id, active=False)
                # Clear worker_pid on clean shutdown so Inquisitor knows this was not a crash
                db.execute_update(
                    "UPDATE possessions SET worker_pid = NULL WHERE id = :id",
                    {"id": self.possession_id},
                )
                self.journal.write_entry("Worker PID cleared (clean shutdown)")
        except Exception as e:
            self.journal.write_entry(f"Warning: Failed to disable minion mode: {e}")

        # End possession via opencode run
        try:
            self.journal.write_entry("Ending possession via opencode run.")
            cmd = [
                "opencode",
                "run",
                "--session",
                self.session_id,
                "--model",
                self.model,
                "You are being dismissed. End your possession using the possession-end skill.",
            ]
            subprocess.run(cmd, check=False, timeout=600)  # 10 minute timeout for shutdown
        except Exception as e:
            self.journal.write_entry(f"Warning: Failed to end possession cleanly: {e}")

        self.journal.write_entry("Shutdown complete.")
        self.journal.write_shutdown()
        raise SystemExit(0)

    def run(self) -> None:
        """
        Main polling loop.

        Sets up signal handlers, initializes worker, enables minion mode,
        and polls for messages at configured interval.
        """
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)

        try:
            # Initialize worker
            self.initialize()
            self.enable_minion_mode()

            self.journal.write_section("Message Log")

            # Track idle heartbeat timing (ADR-016, Fix 3)
            last_heartbeat_at = time.time()

            # Main polling loop
            while self.running:
                time.sleep(self.poll_interval)

                # Check if possession has been exorcised (e.g., by the OpenCode session
                # processing an exorcism signal and calling possession-end)
                db = Database(get_db_path())
                status_rows = db.execute_query(
                    "SELECT status FROM possessions WHERE id = :id",
                    {"id": self.possession_id},
                )
                if status_rows and status_rows[0]["status"] == "EXORCISED":
                    self.journal.write_entry("Possession has been exorcised. Shutting down polling loop.")
                    self.running = False
                    break

                try:
                    messages = self.check_for_messages()

                    if messages:
                        self.journal.write_entry(f"Found {len(messages)} new message(s)")
                        # Reset heartbeat timer — we were active this cycle
                        last_heartbeat_at = time.time()

                        for msg in messages:
                            success = self.process_message(msg)

                            if not success:
                                self.journal.write_entry("Message processing failed. Continuing to next message.")

                    else:
                        self.journal.write_entry("Poll cycle — no new messages")
                        # Emit idle heartbeat if enough time has passed since last one
                        if time.time() - last_heartbeat_at >= self.HEARTBEAT_INTERVAL:
                            self._emit_heartbeat()
                            last_heartbeat_at = time.time()

                except KeyboardInterrupt:
                    # Let signal handler take care of it
                    raise
                except Exception as e:
                    self.journal.write_entry(f"Error during polling cycle: {e}")
                    # Continue polling despite errors
                    continue

        except KeyboardInterrupt:
            # Signal handler will take care of shutdown
            pass
        except Exception as e:
            self.journal.write_entry(f"Fatal error: {e}")
            self.journal.write_shutdown()

            # Try to clean up
            if self.possession_id:
                try:
                    db = Database(get_db_path())
                    mgr = PossessionManager(db)
                    mgr.set_minion_mode(self.possession_id, active=False)
                except Exception:
                    pass

            raise SystemExit(1)


def main() -> None:
    """Parse arguments and start minion worker."""
    parser = argparse.ArgumentParser(
        description="Minion mode worker for site-nine agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start engineer worker with auto-selected daemon
  minion-worker.py Engineer

  # Start architect worker with specific daemon
  minion-worker.py Architect --daemon andromalius

  # Use custom polling interval
  minion-worker.py Tester --poll-interval 15

  # Use different model
  minion-worker.py Operator --model github-copilot/claude-opus-4
        """,
    )

    parser.add_argument(
        "role",
        help="Worker role (e.g., Engineer, Architect, Tester, Operator)",
    )

    parser.add_argument(
        "--daemon",
        help="Specific daemon name (if not provided, auto-selected by possession-start)",
    )

    parser.add_argument(
        "--model",
        default=MinionWorker.DEFAULT_MODEL,
        help=f"OpenCode model to use (default: {MinionWorker.DEFAULT_MODEL})",
    )

    parser.add_argument(
        "--poll-interval",
        type=int,
        default=MinionWorker.DEFAULT_POLL_INTERVAL,
        help=f"Seconds between message checks (default: {MinionWorker.DEFAULT_POLL_INTERVAL})",
    )

    args = parser.parse_args()

    # Validate role capitalization
    valid_roles = [
        "Administrator",
        "Architect",
        "Engineer",
        "Tester",
        "Documentarian",
        "Designer",
        "Inspector",
        "Operator",
        "Historian",
    ]

    # Auto-capitalize first letter if user provided lowercase
    role = args.role.capitalize()

    if role not in valid_roles:
        print(
            f"Error: Invalid role '{args.role}'. Valid roles are:\n  {', '.join(valid_roles)}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    # Start worker
    worker = MinionWorker(
        role=role,
        daemon=args.daemon,
        model=args.model,
        poll_interval=args.poll_interval,
    )

    worker.run()


if __name__ == "__main__":
    main()
