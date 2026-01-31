"""Agent session management"""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from s9.core.database import Database
from s9.core.paths import validate_path_within_project


@dataclass
class AgentSession:
    """Agent session data"""

    id: int | None
    name: str
    base_name: str
    suffix: str | None
    role: str
    session_file: str
    session_date: str
    start_time: str
    end_time: str | None
    status: str
    task_summary: str
    created_at: str
    updated_at: str


class AgentSessionManager:
    """Manages agent sessions"""

    def __init__(self, db: Database) -> None:
        self.db = db

    def start_session(self, name: str, role: str, task_summary: str, session_file: str | None = None) -> int:
        """Start a new agent session"""

        # Parse name for suffix
        if "-" in name:
            parts = name.rsplit("-", 1)
            base_name = parts[0]
            suffix = parts[1] if len(parts) > 1 else None
        else:
            base_name = name
            suffix = None

        # Generate session file name if not provided
        if not session_file:
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")
            session_file = f".opencode/work/sessions/{date_str}.{time_str}.{role.lower()}.{name}.md"

        # Insert into database
        result = self.db.execute_query(
            """
            INSERT INTO agents (
                name, base_name, suffix, role, session_file,
                session_date, start_time, status, task_summary,
                created_at, updated_at
            )
            VALUES (
                :name, :base_name, :suffix, :role, :session_file,
                date('now'), time('now'), 'in-progress', :task_summary,
                datetime('now'), datetime('now')
            )
            RETURNING id
            """,
            {
                "name": name,
                "base_name": base_name,
                "suffix": suffix,
                "role": role,
                "session_file": session_file,
                "task_summary": task_summary,
            },
        )

        session_id = result[0]["id"]

        # Update daemon name usage
        self.db.execute_update(
            """
            UPDATE daemon_names
            SET usage_count = usage_count + 1,
                last_used_at = datetime('now')
            WHERE name = :base_name
            """,
            {"base_name": base_name},
        )

        return session_id

    def end_session(self, session_id: int, status: str = "completed") -> None:
        """End an agent session and update both database and session file"""
        # Get session info first
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Get current time for end_time
        end_time = datetime.now().strftime("%H:%M:%S")

        # Update database
        self.db.execute_update(
            """
            UPDATE agents
            SET end_time = :end_time,
                status = :status,
                updated_at = datetime('now')
            WHERE id = :session_id
            """,
            {"session_id": session_id, "status": status, "end_time": end_time},
        )

        # Update session file if it exists
        if session.session_file:
            # Validate path to prevent directory traversal
            session_path = validate_path_within_project(session.session_file)
            if session_path.exists():
                self._update_session_file_frontmatter(session_path, end_time, status)

    def _update_session_file_frontmatter(self, session_path: Path, end_time: str, status: str) -> None:
        """Update YAML frontmatter in session file"""
        content = session_path.read_text()

        # Match YAML frontmatter block
        frontmatter_pattern = r"^---\n(.*?)\n---\n"
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if not match:
            # No frontmatter found, skip update
            return

        frontmatter_text = match.group(1)

        # Update the frontmatter text directly with regex to avoid YAML parsing issues
        # (YAML interprets HH:MM:SS as sexagesimal numbers)
        frontmatter_text = re.sub(r"(end_time:\s*).*", f"end_time: {end_time}", frontmatter_text)
        frontmatter_text = re.sub(r"(status:\s*).*", f"status: {status}", frontmatter_text)

        # Reconstruct file with updated frontmatter
        new_content = f"---\n{frontmatter_text}\n---\n" + content[match.end() :]

        # Write back to file
        session_path.write_text(new_content)

    def list_sessions(self, active_only: bool = False, role: str | None = None) -> list[AgentSession]:
        """List agent sessions"""
        query = "SELECT * FROM agents WHERE 1=1"
        params = {}

        if active_only:
            query += " AND status = 'in-progress'"

        if role:
            query += " AND role = :role"
            params["role"] = role

        query += " ORDER BY created_at DESC"

        rows = self.db.execute_query(query, params)
        return [AgentSession(**row) for row in rows]

    def get_session(self, session_id: int) -> AgentSession | None:
        """Get session by ID"""
        rows = self.db.execute_query("SELECT * FROM agents WHERE id = :id", {"id": session_id})
        return AgentSession(**rows[0]) if rows else None

    def pause_session(self, session_id: int) -> None:
        """Pause an active agent session"""
        self.db.execute_update(
            """
            UPDATE agents
            SET status = 'paused',
                updated_at = datetime('now')
            WHERE id = :session_id
            """,
            {"session_id": session_id},
        )

    def resume_session(self, session_id: int) -> None:
        """Resume a paused agent session"""
        self.db.execute_update(
            """
            UPDATE agents
            SET status = 'in-progress',
                updated_at = datetime('now')
            WHERE id = :session_id
            """,
            {"session_id": session_id},
        )

    def update_session(self, session_id: int, task_summary: str | None = None, role: str | None = None) -> None:
        """Update agent session metadata"""
        update_fields = ["updated_at = datetime('now')"]
        params = {"session_id": session_id}

        if task_summary is not None:
            update_fields.append("task_summary = :task_summary")
            params["task_summary"] = task_summary

        if role is not None:
            update_fields.append("role = :role")
            params["role"] = role

        query = f"UPDATE agents SET {', '.join(update_fields)} WHERE id = :session_id"
        self.db.execute_update(query, params)
