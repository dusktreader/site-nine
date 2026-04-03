#!/usr/bin/env python3
"""
possession_rename_session tool - Rename the OpenCode session title to match the active possession.

This tool:
1. Receives context.sessionID from OpenCode
2. Looks up the active possession bound to this session
3. Builds the title: "Operation <Daemon> - <Role>"
4. Updates the OpenCode session title via OpenCodeSessionManager
5. Returns the new title and old title
"""

import sys
import json
from tool_logging import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path, get_project_root
from site_nine.possessions.types import PossessionStatus
from site_nine.opencode.manager import OpenCodeSessionManager


ACTIVE_STATUSES = (
    PossessionStatus.ROLE_PENDING.value,
    PossessionStatus.DAEMON_PENDING.value,
    PossessionStatus.ACTIVE.value,
    PossessionStatus.SUSPENDED.value,
)


def main():
    try:
        context = json.loads(sys.stdin.read())
        session_id = context["session_id"]

        logger.debug("possession_rename_session called", session_id=session_id)

        db_path = get_db_path()
        db = Database(db_path)

        # Look up the possession bound to this session
        rows = db.execute_query(
            """
            SELECT id, daemon_name, role, status
            FROM possessions
            WHERE opencode_session_id = :session_id
            AND status IN ('ROLE_PENDING', 'DAEMON_PENDING', 'ACTIVE', 'SUSPENDED')
            ORDER BY created_at DESC
            LIMIT 1
            """,
            {"session_id": session_id},
        )

        if not rows:
            return json.dumps(
                {
                    "error": "no_active_possession",
                    "message": f"No active possession found for session {session_id}",
                }
            )

        possession = rows[0]
        daemon = possession["daemon_name"] or "unknown"
        role = possession["role"] or "unknown"

        # Build title: "Operation <Daemon> - <Role>"
        daemon_display = daemon.capitalize() if daemon != "unknown" else "Unknown"
        new_title = f"Operation {daemon_display} - {role}"

        # Rename the OpenCode session
        project_root = get_project_root()
        session_manager = OpenCodeSessionManager(project_root)
        result = session_manager.update_session_title(session_id, new_title)

        logger.info(
            "session_renamed",
            session_id=session_id,
            old_title=result.old_title,
            new_title=result.new_title,
            possession_id=possession["id"],
        )

        response = {
            "session_id": session_id,
            "possession_id": possession["id"],
            "old_title": result.old_title,
            "new_title": result.new_title,
        }
        if result.warning:
            response["warning"] = result.warning

        return json.dumps(response)

    except Exception as e:
        logger.exception("possession_rename_session_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
