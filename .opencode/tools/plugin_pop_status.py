#!/usr/bin/env python3
"""
plugin_pop_status - Pop pending status messages for the interactive session.

Called by the site-nine OpenCode plugin on session.updated events. Returns
queued status messages if the session belongs to a non-minion-mode possession (i.e.
the interactive director session). Deletes returned rows from the queue.

If the session has no bound possession (e.g. a fresh human session with no
possession yet), messages are still popped — the queue is global.

Input (stdin, JSON):
    session_id: str

Output (stdout, JSON):
    On messages available:
        {"status": "messages", "messages": [{"id": <int>, "possession_id": <int>, "daemon_name": <str|null>, "message": <str>}, ...]}
    On empty queue:
        {"status": "empty"}
    On minion-mode session (skip toasting):
        {"status": "minion_mode"}
    On error:
        {"status": "error", "message": <str>}
"""

import sys
import json
from tool_logging import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path


def main() -> str:
    try:
        data = json.loads(sys.stdin.read())
        session_id = data["session_id"]

        db_path = get_db_path()
        db = Database(db_path)

        # Check if this session belongs to a minion-mode possession.
        # Minion-mode sessions should not pop the queue — only the interactive
        # director session should surface toasts.
        possession_rows = db.execute_query(
            """
            SELECT id, minion_mode_active
            FROM possessions
            WHERE opencode_session_id = :session_id
              AND status IN ('ROLE_PENDING', 'DAEMON_PENDING', 'ACTIVE')
            LIMIT 1
            """,
            {"session_id": session_id},
        )

        if possession_rows:
            possession = possession_rows[0]
            if possession["minion_mode_active"]:
                return json.dumps({"status": "minion_mode"})

        # Pop all pending messages (ordered oldest-first)
        rows = db.execute_query(
            "SELECT sq.id, sq.possession_id, sq.message, p.daemon_name "
            "FROM status_queue sq "
            "LEFT JOIN possessions p ON p.id = sq.possession_id "
            "ORDER BY sq.created_at ASC",
            {},
        )

        if not rows:
            return json.dumps({"status": "empty"})

        # Delete the popped rows
        ids = [row["id"] for row in rows]
        placeholders = ",".join("?" * len(ids))
        import sqlite3

        raw_conn = sqlite3.connect(str(db_path))
        try:
            raw_conn.execute(f"DELETE FROM status_queue WHERE id IN ({placeholders})", ids)
            raw_conn.commit()
        finally:
            raw_conn.close()

        messages = [
            {
                "id": row["id"],
                "possession_id": row["possession_id"],
                "daemon_name": row["daemon_name"],
                "message": row["message"],
            }
            for row in rows
        ]

        logger.info("plugin_pop_status_ok", count=len(messages), session_id=session_id)
        return json.dumps({"status": "messages", "messages": messages})

    except Exception as e:
        logger.exception("plugin_pop_status_error", error=str(e))
        return json.dumps({"status": "error", "message": str(e)})


if __name__ == "__main__":
    print(main())
