#!/usr/bin/env python3
"""
plugin_activity_update.py - Update last_heartbeat_at for a possession bound to a session.

Called by the site-nine OpenCode plugin on session.updated events to track agent
activity without manual heartbeats (ADR-013).

Input (stdin, JSON):
    session_id: str  - OpenCode session ID

Output (stdout, JSON):
    On success:
        {"status": "updated", "possession_id": <int>, "daemon_name": <str>}
    On no possession found:
        {"status": "no_possession", "session_id": <str>}
    On error:
        {"status": "error", "message": <str>}
"""

import sys
import json
from tool_logging import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.core.utils import utc_now


def main() -> str:
    try:
        data = json.loads(sys.stdin.read())
        session_id = data["session_id"]

        logger.debug("plugin_activity_update_called", session_id=session_id)

        db_path = get_db_path()
        db = Database(db_path)

        # Find possession bound to this session that is in an active-ish state
        rows = db.execute_query(
            """
            SELECT id, daemon_name, status
            FROM possessions
            WHERE opencode_session_id = :session_id
              AND status IN ('ROLE_PENDING', 'DAEMON_PENDING', 'ACTIVE')
            LIMIT 1
            """,
            {"session_id": session_id},
        )

        if not rows:
            logger.debug("plugin_activity_update_no_possession", session_id=session_id)
            return json.dumps({"status": "no_possession", "session_id": session_id})

        possession = rows[0]
        possession_id = possession["id"]
        daemon_name = possession["daemon_name"]
        now_str = utc_now()

        db.execute_update(
            """
            UPDATE possessions
            SET last_heartbeat_at = :now, updated_at = :now
            WHERE id = :possession_id
            """,
            {"possession_id": possession_id, "now": now_str},
        )

        logger.info(
            "plugin_activity_updated",
            possession_id=possession_id,
            daemon_name=daemon_name,
            session_id=session_id,
            timestamp=now_str,
        )

        return json.dumps({"status": "updated", "possession_id": possession_id, "daemon_name": daemon_name})

    except Exception as e:
        logger.exception("plugin_activity_update_error", error=str(e))
        return json.dumps({"status": "error", "message": str(e)})


if __name__ == "__main__":
    print(main())
