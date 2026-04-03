#!/usr/bin/env python3
"""
Desk Mode Worker Polling Script

Manages desk agent lifecycle outside agent context. Polls for unread messages,
invokes 'opencode run' for each message, and preserves session context across
invocations.

Usage:
    desk-worker.py <role> [--daemon NAME] [--model MODEL] [--poll-interval SECONDS]

Example:
    desk-worker.py engineer --daemon halphas
    desk-worker.py architect --poll-interval 15
"""

import argparse
import json
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

# Imports from site_nine package
# (No path manipulation needed - this module is now properly in src/site_nine/)
from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.messaging.manager import MessageManager
from site_nine.possessions.manager import PossessionManager


class DeskWorker:
    """External polling loop for desk mode workers."""

    # Default model to use for opencode run
    DEFAULT_MODEL = "github-copilot/claude-sonnet-4.6"

    # Default polling interval (seconds)
    DEFAULT_POLL_INTERVAL = 30

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
        Initialize desk worker.

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

    def initialize(self) -> None:
        """
        Initialize worker possession via opencode run.

        Launches initial session, waits for possession creation, and retrieves
        session ID from database.

        Raises:
            RuntimeError: If possession initialization fails
        """
        print(f"Initializing {self.role} worker...", flush=True)

        # Build initialization message
        init_parts = [f"Your role is {self.role}."]

        if self.daemon:
            init_parts.append(f"Your daemon is {self.daemon}.")

        init_parts.append(
            "Initialize your possession with the possession-start skill. Mode: desk. "
            "DO NOT claim any tasks. DO NOT do any work yet. "
            "After your possession is initialized and you have a possession ID, stop immediately. "
            "The desk-worker wrapper handles message polling and will send you work assignments. "
            "IMPORTANT: When you receive a work assignment message, you MUST use the worker_message "
            "tool to send status updates back to the sender (use their possession ID as to_possession_id). "
            "Send a message when you: (1) start a task, (2) complete a task, (3) hit a blocker, "
            "(4) make significant progress. Never work silently — always report back."
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
                print(f"Extracted session ID: {session_id}", flush=True)

                if process.returncode != 0:
                    # Non-zero exit is a warning, not fatal — the agent may have exited
                    # after completing init. As long as we got a session ID and the possession
                    # was created in the DB, we can continue.
                    print(
                        f"Warning: opencode run exited with code {process.returncode} (may be normal after init)",
                        file=sys.stderr,
                        flush=True,
                    )
                    if stderr:
                        print(f"Stderr: {stderr[:500]}", file=sys.stderr, flush=True)

            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                raise RuntimeError("Possession initialization timed out after 10 minutes")

        except FileNotFoundError:
            raise RuntimeError("opencode command not found. Is OpenCode installed and in PATH?")

        # Wait for possession to be created in database
        print("Waiting for possession to be created...", flush=True)
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
                SELECT id, daemon_name FROM possessions
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
            print("Possession not found by session ID, searching by role...", flush=True)
            for _ in range(15):  # up to 15s
                rows = db.execute_query(
                    """
                    SELECT id, daemon_name FROM possessions
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
            print(f"Binding session {self.session_id} to possession #{self.possession_id}...", flush=True)
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

        print(
            f"Possession initialized successfully:\n"
            f"  Possession ID: {self.possession_id}\n"
            f"  Session ID: {self.session_id}\n"
            f"  Daemon: {daemon_used}",
            flush=True,
        )

    def enable_desk_mode(self) -> None:
        """
        Enable desk mode in database.

        Sets desk_mode_active=1 for this worker's possession.

        Raises:
            RuntimeError: If possession_id is not set
        """
        if self.possession_id is None:
            raise RuntimeError("Cannot enable desk mode: possession_id is not set")

        db = Database(get_db_path())
        mgr = PossessionManager(db)
        mgr.set_desk_mode(self.possession_id, active=True)
        print(f"Desk mode enabled for possession #{self.possession_id}", flush=True)

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

        print(f"\nProcessing message {message.id} ({message.priority})...", flush=True)
        print(f"  Subject: {message.subject}", flush=True)
        print(f"  From: Possession #{message.from_possession_id}", flush=True)

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
                    print(f"  ✓ Processed {message.id} successfully", flush=True)
                    return True
                else:
                    print(
                        f"  ✗ Processing failed with exit code {process.returncode}",
                        file=sys.stderr,
                        flush=True,
                    )
                    if stderr:
                        print(f"  Error: {stderr}", file=sys.stderr, flush=True)
                    return False

            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                print(
                    f"  ✗ Processing timed out after 20 minutes",
                    file=sys.stderr,
                    flush=True,
                )
                return False

        except Exception as e:
            print(f"  ✗ Processing failed: {e}", file=sys.stderr, flush=True)
            return False

    def handle_shutdown(self, signum: int, frame) -> None:
        """
        Gracefully shutdown on SIGTERM/SIGINT.

        Disables desk mode, ends possession, and exits.

        Args:
            signum: Signal number
            frame: Current stack frame (unused)
        """
        signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
        print(f"\n\nReceived {signal_name}, shutting down gracefully...", flush=True)
        self.running = False

        # Disable desk mode
        try:
            db = Database(get_db_path())
            mgr = PossessionManager(db)
            if self.possession_id is not None:
                mgr.set_desk_mode(self.possession_id, active=False)
            print("Desk mode disabled", flush=True)
        except Exception as e:
            print(f"Warning: Failed to disable desk mode: {e}", file=sys.stderr)

        # End possession via opencode run
        try:
            print("Ending possession...", flush=True)
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
            print("Possession ended successfully", flush=True)
        except Exception as e:
            print(
                f"Warning: Failed to end possession cleanly: {e}",
                file=sys.stderr,
                flush=True,
            )

        print("Shutdown complete", flush=True)
        raise SystemExit(0)

    def run(self) -> None:
        """
        Main polling loop.

        Sets up signal handlers, initializes worker, enables desk mode,
        and polls for messages at configured interval.
        """
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)

        try:
            # Initialize worker
            self.initialize()
            self.enable_desk_mode()

            print(
                f"\nDesk worker started successfully!\n"
                f"  Role: {self.role}\n"
                f"  Possession: #{self.possession_id}\n"
                f"  Session: {self.session_id}\n"
                f"  Poll interval: {self.poll_interval}s\n",
                flush=True,
            )
            print("Polling for messages...\n", flush=True)

            # Main polling loop
            while self.running:
                time.sleep(self.poll_interval)

                try:
                    messages = self.check_for_messages()

                    if messages:
                        print(
                            f"\n{'=' * 60}\nFound {len(messages)} new message(s)!\n{'=' * 60}",
                            flush=True,
                        )

                        for msg in messages:
                            success = self.process_message(msg)

                            if not success:
                                # Continue processing other messages even if one fails
                                print(
                                    f"  Continuing despite failure...",
                                    file=sys.stderr,
                                    flush=True,
                                )

                        print(f"{'=' * 60}\n", flush=True)
                    else:
                        print(
                            f"[{time.strftime('%H:%M:%S')}] Checking comms... No new messages. (0 unread)",
                            flush=True,
                        )

                except KeyboardInterrupt:
                    # Let signal handler take care of it
                    raise
                except Exception as e:
                    print(
                        f"Error during polling cycle: {e}",
                        file=sys.stderr,
                        flush=True,
                    )
                    # Continue polling despite errors
                    continue

        except KeyboardInterrupt:
            # Signal handler will take care of shutdown
            pass
        except Exception as e:
            print(f"\nFatal error: {e}", file=sys.stderr, flush=True)

            # Try to clean up
            if self.possession_id:
                try:
                    db = Database(get_db_path())
                    mgr = PossessionManager(db)
                    mgr.set_desk_mode(self.possession_id, active=False)
                except Exception:
                    pass

            raise SystemExit(1)


def main() -> None:
    """Parse arguments and start desk worker."""
    parser = argparse.ArgumentParser(
        description="Desk mode worker for site-nine agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start engineer worker with auto-selected daemon
  desk-worker.py Engineer

  # Start architect worker with specific daemon
  desk-worker.py Architect --daemon andromalius

  # Use custom polling interval
  desk-worker.py Tester --poll-interval 15

  # Use different model
  desk-worker.py Operator --model github-copilot/claude-opus-4
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
        default=DeskWorker.DEFAULT_MODEL,
        help=f"OpenCode model to use (default: {DeskWorker.DEFAULT_MODEL})",
    )

    parser.add_argument(
        "--poll-interval",
        type=int,
        default=DeskWorker.DEFAULT_POLL_INTERVAL,
        help=f"Seconds between message checks (default: {DeskWorker.DEFAULT_POLL_INTERVAL})",
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
    worker = DeskWorker(
        role=role,
        daemon=args.daemon,
        model=args.model,
        poll_interval=args.poll_interval,
    )

    worker.run()


if __name__ == "__main__":
    main()
