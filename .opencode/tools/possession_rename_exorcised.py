#!/usr/bin/env python3
"""
possession_rename_exorcised tool - Append '[EXORCISED]' to the OpenCode session title when a possession ends.

This tool:
1. Receives context.sessionID from OpenCode
2. Looks up the current session title
3. Appends '[EXORCISED]' suffix if not already present
4. Updates the OpenCode session title via OpenCodeSessionManager
5. Returns the new title and old title
"""

import sys
import json
from tool_logging import logger

from site_nine.core.paths import get_project_root
from site_nine.opencode.manager import OpenCodeSessionManager


EXORCISED_SUFFIX = "[EXORCISED]"


def main():
    try:
        context = json.loads(sys.stdin.read())
        session_id = context["session_id"]

        logger.debug("possession_rename_exorcised called", session_id=session_id)

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
        if current_title.endswith(EXORCISED_SUFFIX):
            return json.dumps(
                {
                    "session_id": session_id,
                    "old_title": current_title,
                    "new_title": current_title,
                    "note": "Session already marked as exorcised.",
                }
            )

        new_title = f"{current_title} {EXORCISED_SUFFIX}"

        result = session_manager.update_session_title(session_id, new_title)

        logger.info(
            "session_renamed_exorcised",
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
        logger.exception("possession_rename_exorcised_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
