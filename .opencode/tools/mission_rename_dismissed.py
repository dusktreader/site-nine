#!/usr/bin/env python3
"""
mission_rename_dismissed tool - Append '[DISMISSED]' to the OpenCode session title when a mission ends.

This tool:
1. Receives context.sessionID from OpenCode
2. Looks up the current session title
3. Appends '[DISMISSED]' suffix if not already present
4. Updates the OpenCode session title via OpenCodeSessionManager
5. Returns the new title and old title
"""

import sys
import json
from loguru import logger

from site_nine.core.paths import get_project_root
from site_nine.opencode.manager import OpenCodeSessionManager


DISMISSED_SUFFIX = "[DISMISSED]"


def main():
    try:
        context = json.loads(sys.stdin.read())
        session_id = context["session_id"]

        logger.debug("mission_rename_dismissed called", session_id=session_id)

        project_root = get_project_root()
        session_manager = OpenCodeSessionManager(project_root)

        # Get the current session title from the OpenCode DB
        db_path = session_manager.find_db()
        if not db_path:
            return json.dumps(
                {
                    "error": "no_opencode_db",
                    "message": "OpenCode database not found. Cannot rename session.",
                }
            )

        import sqlite3

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT title FROM session WHERE id = ?",
                (session_id,),
            ).fetchone()
        finally:
            conn.close()

        if not row:
            return json.dumps(
                {
                    "error": "session_not_found",
                    "message": f"Session {session_id} not found in OpenCode database.",
                }
            )

        current_title = row["title"] or "Untitled"

        # Don't double-append the suffix
        if current_title.endswith(DISMISSED_SUFFIX):
            return json.dumps(
                {
                    "session_id": session_id,
                    "old_title": current_title,
                    "new_title": current_title,
                    "note": "Session already marked as dismissed.",
                }
            )

        new_title = f"{current_title} {DISMISSED_SUFFIX}"

        result = session_manager.update_session_title(session_id, new_title)

        logger.info(
            "session_renamed_dismissed",
            session_id=session_id,
            old_title=result.old_title,
            new_title=result.new_title,
        )

        response = {
            "session_id": session_id,
            "old_title": result.old_title,
            "new_title": result.new_title,
        }
        if result.warning:
            response["warning"] = result.warning

        return json.dumps(response)

    except Exception as e:
        logger.exception("mission_rename_dismissed_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
