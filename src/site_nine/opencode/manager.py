from __future__ import annotations

import json
import sqlite3
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from loguru import logger

from site_nine.opencode.exceptions import OpenCodeError
from site_nine.opencode.models import SessionDetectionResult, SessionInfo, SessionUpdateResult


class OpenCodeSessionManager:
    """Manages OpenCode TUI session detection and manipulation.

    This manager handles finding, identifying, and renaming OpenCode sessions
    by querying OpenCode's SQLite database (~/.local/share/opencode/opencode.db)
    with fallback to file-based storage (~/.local/share/opencode/storage/).

    OpenCode stores real-time session data in its SQLite database. The file-based
    storage under storage/ is a secondary representation that may not be flushed
    in real-time (particularly for part/tool-output data). For reliable detection,
    the DB should always be preferred.
    """

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()

    def find_db(self) -> Path | None:
        """Find the OpenCode SQLite database.

        Returns:
            Path to opencode.db, or None if not found.
        """
        db_path = Path.home() / ".local" / "share" / "opencode" / "opencode.db"
        if db_path.exists():
            return db_path
        return None

    def find_storage(self) -> tuple[Path, Path, Path]:
        """Find and validate OpenCode storage directories.

        Returns:
            Tuple of (session_diff_storage, session_storage, part_storage) paths.

        Raises:
            OpenCodeError: If OpenCode storage directory is not found.
        """
        opencode_storage = Path.home() / ".local" / "share" / "opencode" / "storage"
        OpenCodeError.require_condition(
            opencode_storage.exists(),
            "OpenCode storage directory not found. Expected: ~/.local/share/opencode/storage",
        )

        session_diff_storage = opencode_storage / "session_diff"
        session_storage = opencode_storage / "session"
        part_storage = opencode_storage / "part"
        return session_diff_storage, session_storage, part_storage

    def generate_session_uuid(self) -> str:
        """Generate a unique session UUID marker for reliable session detection.

        Returns:
            Session UUID marker string (e.g., "session-marker-abc123def456").
        """
        session_uuid = f"session-marker-{uuid.uuid4().hex[:16]}"
        logger.debug("session_uuid_generated")
        return session_uuid

    def detect_session(
        self,
        uuid_marker: str | None = None,
    ) -> SessionDetectionResult:
        """Detect the current OpenCode session using a cascade of methods.

        Detection order:
        1. UUID marker search in DB (if provided, most reliable)
        2. UUID marker search in filesystem (fallback if DB unavailable)
        3. DB recency (most recently updated session for this project)
        4. Content correlation (git changes vs session diffs)
        5. Diff file recency
        6. Session file recency

        Args:
            uuid_marker: UUID marker to search for in session data.

        Returns:
            SessionDetectionResult with the detected session_id (or None).
        """
        # Try DB-based detection first (most reliable)
        db_path = self.find_db()

        warning = None
        if uuid_marker:
            # Try DB first
            if db_path:
                detected = self._detect_via_db_uuid_marker(db_path, uuid_marker)
                if detected:
                    return SessionDetectionResult(session_id=detected, method="db_uuid_marker")

            # Fall back to filesystem
            try:
                session_diff_storage, session_storage, part_storage = self.find_storage()
                detected = self._detect_via_uuid_marker(
                    uuid_marker, session_diff_storage, session_storage, part_storage
                )
                if detected:
                    return SessionDetectionResult(session_id=detected, method="uuid_marker")
            except OpenCodeError:
                pass  # Storage not found, continue to other methods

            warning = f"UUID marker '{uuid_marker}' not found in any recent sessions. Falling back to other detection methods..."

        # Try DB recency (reliable when DB available)
        if db_path:
            detected = self._detect_via_db_recency(db_path)
            if detected:
                result = SessionDetectionResult(session_id=detected, method="db_recency")
                result.warning = warning
                return result

        # Fall back to filesystem-based detection
        try:
            session_diff_storage, session_storage, part_storage = self.find_storage()
        except OpenCodeError:
            raise OpenCodeError(
                "Neither OpenCode database nor storage directory found. "
                "Is OpenCode installed and has it been used in this project?"
            )

        # Try content correlation
        detected = self._detect_via_diff_content(session_diff_storage, session_storage)
        if detected:
            result = SessionDetectionResult(session_id=detected, method="diff_content")
            result.warning = warning
            return result

        logger.debug("content_correlation_failed_fallback_to_timestamp")

        # Check for multiple active sessions
        multiple_active = self._check_multiple_active(session_diff_storage)

        # Try diff file recency
        detected = self._detect_via_diff_recency(session_diff_storage, session_storage)
        if detected:
            result = SessionDetectionResult(
                session_id=detected,
                method="diff_recency",
                warning=warning,
                multiple_active=multiple_active,
            )
            return result

        logger.debug("diff_recency_failed_fallback_to_session_recency")

        # Final fallback: session file recency
        project_sessions = self.find_project_sessions(session_storage)
        detected, recency_warning = self._detect_via_recency(project_sessions)
        result = SessionDetectionResult(
            session_id=detected,
            method="session_recency",
            warning=warning or recency_warning,
            multiple_active=multiple_active,
        )
        return result

    def find_project_sessions(self, session_storage: Path) -> list[tuple[Path, float]]:
        """Find all OpenCode sessions for the current project.

        Args:
            session_storage: Path to OpenCode session storage directory.

        Returns:
            List of (session_file_path, modification_time) tuples.
        """
        project_sessions = []
        for project_dir in session_storage.iterdir():
            if not project_dir.is_dir() or project_dir.name == "global":
                continue

            for session_file in project_dir.glob("ses_*.json"):
                try:
                    with open(session_file) as f:
                        session_data = json.load(f)

                    session_dir = session_data.get("directory", "")
                    if session_dir and Path(session_dir).resolve() == self.project_root:
                        mtime = session_file.stat().st_mtime
                        project_sessions.append((session_file, mtime))
                except (json.JSONDecodeError, FileNotFoundError, PermissionError):
                    continue

        return project_sessions

    def list_project_sessions(self) -> list[SessionInfo]:
        """List all OpenCode sessions for the current project.

        Prefers the SQLite database for accurate, real-time data.
        Falls back to filesystem if DB is unavailable.

        Returns:
            List of SessionInfo objects sorted by recency.

        Raises:
            OpenCodeError: If neither DB nor storage directory is found.
        """
        db_path = self.find_db()
        if db_path:
            return self._list_sessions_from_db(db_path)
        return self._list_sessions_from_filesystem()

    def update_session_title(self, session_id: str, new_title: str) -> SessionUpdateResult:
        """Update the title of an OpenCode session.

        Writes to the SQLite database (primary) and filesystem (if file exists).
        The DB write is what the TUI actually reads; the filesystem write is for
        compatibility with older detection methods.

        Args:
            session_id: OpenCode session ID (e.g., "ses_xxx").
            new_title: New title to set.

        Returns:
            SessionUpdateResult with old and new titles.

        Raises:
            OpenCodeError: If session cannot be found or updated.
        """
        db_path = self.find_db()
        old_title = "Untitled"
        warning = None

        # Update in DB (primary)
        if db_path:
            try:
                conn = sqlite3.connect(str(db_path))
                conn.row_factory = sqlite3.Row
                try:
                    row = conn.execute(
                        "SELECT title, directory FROM session WHERE id = ?",
                        (session_id,),
                    ).fetchone()

                    if row:
                        old_title = row["title"]
                        session_dir = row["directory"]

                        if session_dir:
                            try:
                                if not Path(session_dir).samefile(self.project_root):
                                    warning = (
                                        f"Session is for different project:\n"
                                        f"  Session: {session_dir}\n"
                                        f"  Current: {self.project_root}\n"
                                        f"Renaming anyway."
                                    )
                            except (FileNotFoundError, OSError):
                                pass

                        conn.execute(
                            "UPDATE session SET title = ? WHERE id = ?",
                            (new_title, session_id),
                        )
                        conn.commit()

                        logger.info(
                            "opencode_session_renamed",
                            session_id=session_id,
                            old_title=old_title,
                            new_title=new_title,
                        )
                    else:
                        raise OpenCodeError(f"Session {session_id} not found in database")
                finally:
                    conn.close()
            except sqlite3.Error as e:
                raise OpenCodeError(f"Failed to update session in database: {e}")
        else:
            raise OpenCodeError("OpenCode database not found. Cannot update session title.")

        # Also update filesystem if the file exists (best-effort)
        self._update_session_file(session_id, new_title)

        return SessionUpdateResult(
            session_id=session_id,
            old_title=old_title,
            new_title=new_title,
            warning=warning,
        )

    def _is_session_for_project(self, session_file: Path) -> bool:
        """Check if a session file belongs to the current project."""
        try:
            with open(session_file) as f:
                session_data = json.load(f)
            session_dir = session_data.get("directory", "")
            return bool(session_dir and Path(session_dir).resolve() == self.project_root)
        except (json.JSONDecodeError, FileNotFoundError, PermissionError):
            return False

    def _find_session_file_in_storage(self, session_id: str, session_storage: Path) -> Path | None:
        """Find a session file across all project directories in storage."""
        for project_dir in session_storage.iterdir():
            if not project_dir.is_dir():
                continue
            candidate = project_dir / f"{session_id}.json"
            if candidate.exists():
                return candidate
        return None

    def _detect_via_uuid_marker(
        self,
        uuid_marker: str,
        session_diff_storage: Path,
        session_storage: Path,
        part_storage: Path,
    ) -> str | None:
        """Detect session by searching for UUID marker in message parts."""
        current_time = time.time()
        recent_threshold = 600

        part_files = []
        for msg_dir in part_storage.iterdir():
            if not msg_dir.is_dir() or not msg_dir.name.startswith("msg_"):
                continue
            for part_file in msg_dir.glob("prt_*.json"):
                try:
                    mtime = part_file.stat().st_mtime
                    if current_time - mtime <= recent_threshold:
                        part_files.append((part_file, mtime))
                except (FileNotFoundError, PermissionError):
                    continue

        part_files.sort(key=lambda x: x[1], reverse=True)

        verified_sessions: dict[str, bool] = {}

        for part_file, mtime in part_files:
            try:
                with open(part_file) as f:
                    part_data = json.load(f)

                if part_data.get("type") != "tool":
                    continue

                sid = part_data.get("sessionID")
                if not sid:
                    continue

                if sid not in verified_sessions:
                    session_file = self._find_session_file_in_storage(sid, session_storage)
                    if not session_file:
                        verified_sessions[sid] = False
                        continue
                    verified_sessions[sid] = self._is_session_for_project(session_file)

                if not verified_sessions[sid]:
                    continue

                state = part_data.get("state", {})
                output = state.get("output", "")
                if isinstance(output, str) and uuid_marker in output:
                    age_seconds = current_time - mtime
                    logger.debug(
                        "session_detected_via_uuid_marker",
                        session_id=sid,
                        uuid_marker=uuid_marker,
                        age_seconds=int(age_seconds),
                    )
                    return sid

            except (json.JSONDecodeError, FileNotFoundError, PermissionError):
                continue

        logger.debug("uuid_marker_not_found", uuid_marker=uuid_marker)
        return None

    def _detect_via_diff_content(
        self,
        session_diff_storage: Path,
        session_storage: Path,
    ) -> str | None:
        """Detect session by correlating recent git changes with diff content."""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=2,
            )
            recent_files = set(result.stdout.strip().split("\n")) if result.stdout.strip() else set()

            result = subprocess.run(
                ["git", "diff", "--name-only", "--cached"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.stdout.strip():
                recent_files.update(result.stdout.strip().split("\n"))

            if not recent_files:
                logger.debug("no_git_changes_for_content_correlation")
                return None

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            logger.debug("git_command_failed_in_content_correlation")
            return None

        current_time = time.time()
        recent_threshold = 60

        diff_files = sorted(
            session_diff_storage.glob("ses_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        candidate_sessions = []

        for diff_file in diff_files:
            mtime = diff_file.stat().st_mtime
            age_seconds = current_time - mtime

            if age_seconds > recent_threshold:
                break

            sid = diff_file.stem
            session_file = self._find_session_file_in_storage(sid, session_storage)
            if not session_file:
                continue

            if not self._is_session_for_project(session_file):
                continue

            try:
                with open(diff_file) as f:
                    diff_data = json.load(f)

                if not (type(diff_data).__name__ == "list" and len(diff_data) > 0):
                    continue

                recent_diff_files = {entry.get("file", "") for entry in diff_data[-10:]}
                overlap = recent_files & recent_diff_files

                if overlap:
                    score = len(overlap)
                    candidate_sessions.append((sid, score, age_seconds))
                    logger.debug(
                        "session_content_match_found",
                        session_id=sid,
                        matched_files=[*overlap][:3],
                        score=score,
                    )

            except (json.JSONDecodeError, FileNotFoundError, PermissionError):
                continue

        if candidate_sessions:
            best_match = sorted(candidate_sessions, key=lambda x: (-x[1], x[2]))[0]
            sid, score, age_seconds = best_match
            logger.debug(
                "session_detected_via_content_correlation",
                session_id=sid,
                score=score,
                age_seconds=int(age_seconds),
            )
            return sid

        return None

    def _detect_via_diff_recency(
        self,
        session_diff_storage: Path,
        session_storage: Path,
    ) -> str | None:
        """Detect session by finding most recently modified diff file."""
        diff_files = sorted(
            session_diff_storage.glob("ses_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if not diff_files:
            return None

        current_time = time.time()
        recent_threshold = 10

        recent_project_sessions = []
        for diff_file in diff_files:
            mtime = diff_file.stat().st_mtime
            age_seconds = current_time - mtime

            if age_seconds > recent_threshold:
                break

            sid = diff_file.stem
            session_file = self._find_session_file_in_storage(sid, session_storage)
            if not session_file:
                continue

            if self._is_session_for_project(session_file):
                recent_project_sessions.append((sid, age_seconds))

        if recent_project_sessions:
            sid, age_seconds = min(recent_project_sessions, key=lambda x: x[1])

            if len(recent_project_sessions) > 1:
                logger.warning(
                    "multiple_active_sessions_detected",
                    count=len(recent_project_sessions),
                    selected=sid,
                    note="If wrong session renamed, use --uuid-marker flag",
                )

            logger.debug("session_detected_via_diff_recency", session_id=sid, age_seconds=int(age_seconds))
            return sid

        # Fallback: no recent sessions, use top 5
        for diff_file in diff_files[:5]:
            sid = diff_file.stem
            session_file = self._find_session_file_in_storage(sid, session_storage)
            if not session_file:
                continue

            if self._is_session_for_project(session_file):
                mtime = diff_file.stat().st_mtime
                age_seconds = current_time - mtime
                logger.debug(
                    "session_detected_via_diff_recency_fallback",
                    session_id=sid,
                    age_seconds=int(age_seconds),
                )
                return sid

        return None

    def _detect_via_recency(
        self,
        project_sessions: list[tuple[Path, float]],
    ) -> tuple[str | None, str | None]:
        """Detect session based on recent activity.

        Returns:
            Tuple of (session_id, warning_message). Raises OpenCodeError if
            multiple very recent sessions detected and user must choose.
        """
        if not project_sessions:
            raise OpenCodeError(f"No OpenCode sessions found for project {self.project_root.name}")

        very_recent = [(f, mt) for f, mt in project_sessions if time.time() - mt < 3]

        if len(very_recent) == 1:
            sid = very_recent[0][0].stem
            logger.debug("session_auto_detected_single_active", session_id=sid)
            return sid, None

        elif len(very_recent) > 1:
            lines = [
                "Multiple active OpenCode sessions detected for this project.",
                "Please specify which session to rename:",
                "",
            ]
            for session_file, mtime in sorted(very_recent, key=lambda x: x[1], reverse=True):
                try:
                    with open(session_file) as f:
                        session_data = json.load(f)
                    slug = session_data.get("slug", "")
                    age = int(time.time() - mtime)
                    lines.append(f"  {session_file.stem} ({slug}) - {age}s ago")
                except Exception:
                    pass

            lines.append("")
            lines.append("Use: s9 mission list-opencode-sessions (to see all sessions)")
            raise OpenCodeError("\n".join(lines))

        else:
            most_recent = max(project_sessions, key=lambda x: x[1])
            sid = most_recent[0].stem
            mtime = most_recent[1]
            age = int(time.time() - mtime)
            warning = (
                f"No session modified in last 3 seconds. Using most recent ({age}s ago).\n"
                f"Session: {sid}\n"
                f"If this is wrong, ensure --uuid-marker is passed."
            )
            logger.debug("session_auto_detected_fallback", session_id=sid, age_seconds=age)
            return sid, warning

    def _check_multiple_active(self, session_diff_storage: Path) -> bool:
        """Check if multiple sessions have been active recently."""
        current_time = time.time()
        recent_threshold = 10
        diff_files = sorted(
            session_diff_storage.glob("ses_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        recent_count = 0
        for diff_file in diff_files:
            if current_time - diff_file.stat().st_mtime > recent_threshold:
                break
            recent_count += 1
        return recent_count > 1

    # --- DB-backed detection methods ---

    def _detect_via_db_uuid_marker(self, db_path: Path, uuid_marker: str) -> str | None:
        """Detect session by searching for UUID marker in the DB part table.

        Queries the ``part`` table for rows whose ``data`` JSON contains the
        UUID marker string, then verifies the owning session belongs to the
        current project directory.

        Args:
            db_path: Path to the OpenCode SQLite database.
            uuid_marker: UUID marker string to search for.

        Returns:
            Session ID string, or None if not found.
        """
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    """
                    SELECT p.session_id
                    FROM part p
                    JOIN session s ON s.id = p.session_id
                    WHERE p.data LIKE ?
                      AND s.directory IS NOT NULL
                    ORDER BY p.time_created DESC
                    LIMIT 10
                    """,
                    (f"%{uuid_marker}%",),
                ).fetchall()

                for row in rows:
                    sid = row["session_id"]
                    # Verify this session is for our project
                    sess = conn.execute(
                        "SELECT directory FROM session WHERE id = ?",
                        (sid,),
                    ).fetchone()
                    if sess and sess["directory"]:
                        try:
                            if Path(sess["directory"]).resolve() == self.project_root:
                                logger.debug(
                                    "session_detected_via_db_uuid_marker",
                                    session_id=sid,
                                    uuid_marker=uuid_marker,
                                )
                                return sid
                        except (OSError, ValueError):
                            continue
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.debug("db_uuid_marker_query_failed", error=str(exc))

        return None

    def _detect_via_db_recency(self, db_path: Path) -> str | None:
        """Detect session by most recently updated session in the DB.

        Finds the session for the current project directory that was updated
        most recently (``time_updated`` is maintained in real-time by OpenCode).

        Args:
            db_path: Path to the OpenCode SQLite database.

        Returns:
            Session ID string, or None if not found.
        """
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    """
                    SELECT id, title, time_updated, directory
                    FROM session
                    WHERE directory IS NOT NULL
                    ORDER BY time_updated DESC
                    LIMIT 20
                    """,
                ).fetchall()

                for row in rows:
                    try:
                        if Path(row["directory"]).resolve() == self.project_root:
                            sid = row["id"]
                            age_ms = int(time.time() * 1000) - row["time_updated"]
                            logger.debug(
                                "session_detected_via_db_recency",
                                session_id=sid,
                                title=row["title"],
                                age_ms=age_ms,
                            )
                            return sid
                    except (OSError, ValueError):
                        continue
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.debug("db_recency_query_failed", error=str(exc))

        return None

    def _list_sessions_from_db(self, db_path: Path) -> list[SessionInfo]:
        """List all sessions for the current project from the DB.

        Args:
            db_path: Path to the OpenCode SQLite database.

        Returns:
            List of SessionInfo objects sorted by recency (most recent first).
        """
        sessions: list[SessionInfo] = []
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    """
                    SELECT id, title, slug, directory, time_updated
                    FROM session
                    WHERE directory IS NOT NULL
                    ORDER BY time_updated DESC
                    """,
                ).fetchall()

                now_ms = int(time.time() * 1000)
                for row in rows:
                    try:
                        if Path(row["directory"]).resolve() != self.project_root:
                            continue
                    except (OSError, ValueError):
                        continue

                    age_seconds = (now_ms - row["time_updated"]) / 1000.0
                    sessions.append(
                        SessionInfo(
                            session_id=row["id"],
                            title=row["title"] or "Untitled",
                            slug=row["slug"] or "",
                            directory=row["directory"],
                            age_seconds=age_seconds,
                        )
                    )
            finally:
                conn.close()
        except sqlite3.Error as exc:
            logger.warning("db_list_sessions_failed", error=str(exc))

        return sessions

    def _list_sessions_from_filesystem(self) -> list[SessionInfo]:
        """List all sessions for the current project from the filesystem.

        Fallback for when the SQLite database is unavailable.

        Returns:
            List of SessionInfo objects sorted by recency (most recent first).

        Raises:
            OpenCodeError: If storage directory is not found.
        """
        _, session_storage, _ = self.find_storage()
        project_sessions = self.find_project_sessions(session_storage)

        sessions: list[SessionInfo] = []
        current_time = time.time()
        for session_file, mtime in sorted(project_sessions, key=lambda x: x[1], reverse=True):
            try:
                with open(session_file) as f:
                    data = json.load(f)

                sessions.append(
                    SessionInfo(
                        session_id=session_file.stem,
                        title=data.get("title", "Untitled"),
                        slug=data.get("slug", ""),
                        directory=data.get("directory", ""),
                        age_seconds=current_time - mtime,
                        session_file=session_file,
                    )
                )
            except (json.JSONDecodeError, FileNotFoundError, PermissionError):
                continue

        return sessions

    def _update_session_file(self, session_id: str, new_title: str) -> None:
        """Best-effort update of the filesystem session JSON file.

        This is a secondary write for compatibility; the primary write is to
        the SQLite database in ``update_session_title()``.

        Args:
            session_id: OpenCode session ID (e.g., "ses_xxx").
            new_title: New title to write.
        """
        try:
            _, session_storage, _ = self.find_storage()
        except OpenCodeError:
            logger.debug("filesystem_storage_not_found_skipping_file_update")
            return

        session_file = self._find_session_file_in_storage(session_id, session_storage)
        if not session_file:
            logger.debug("session_file_not_found_skipping_file_update", session_id=session_id)
            return

        try:
            with open(session_file) as f:
                data = json.load(f)

            data["title"] = new_title

            # Write to temp file then rename for atomicity
            tmp = tempfile.NamedTemporaryFile(
                mode="w",
                dir=session_file.parent,
                suffix=".tmp",
                delete=False,
            )
            try:
                json.dump(data, tmp, indent=2)
                tmp.close()
                Path(tmp.name).replace(session_file)
                logger.debug("session_file_updated", session_file=str(session_file))
            except Exception:
                Path(tmp.name).unlink(missing_ok=True)
                raise
        except Exception as exc:
            logger.debug("session_file_update_failed", error=str(exc), session_id=session_id)
