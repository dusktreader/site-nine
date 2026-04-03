#!/usr/bin/env python3
"""
plugin_session_suspend.py - Suspend the mission bound to a given session.

Called by the site-nine OpenCode plugin on session.deleted events to auto-suspend
active missions when their session closes unexpectedly (ADR-013).

Input (stdin, JSON):
    session_id: str     - OpenCode session ID
    reason:     str     - Suspension reason (optional, defaults to "Session closed")

Output (stdout, JSON):
    On success:
        {"status": "suspended", "mission_id": <int>, "codename": <str>}
    On no active mission found:
        {"status": "no_mission", "session_id": <str>}
    On mission already ended (skip silently):
        {"status": "skipped", "reason": "already_ended", "mission_id": <int>}
    On error:
        {"status": "error", "message": <str>}
"""

import sys
import json
from tool_logging import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.core.utils import utc_now
from site_nine.possessions.manager import PossessionManager
from site_nine.possessions.types import PossessionStatus


def main() -> str:
    try:
        data = json.loads(sys.stdin.read())
        session_id = data["session_id"]
        reason = data.get("reason", "Session closed unexpectedly")

        logger.debug("plugin_session_suspend_called", session_id=session_id, reason=reason)

        db_path = get_db_path()
        db = Database(db_path)

        # Find possession bound to this session in a suspendable state
        rows = db.execute_query(
            """
            SELECT id, status
            FROM possessions
            WHERE opencode_session_id = :session_id
              AND status != 'EXORCISED'
              AND status != 'SUSPENDED'
            LIMIT 1
            """,
            {"session_id": session_id},
        )

        if not rows:
            logger.debug("plugin_session_suspend_no_mission", session_id=session_id)
            return json.dumps({"status": "no_mission", "session_id": session_id})

        mission = rows[0]
        mission_id = mission["id"]
        current_status = mission["status"]

        # Skip if already exorcised
        if current_status == PossessionStatus.EXORCISED.value:
            logger.info(
                "plugin_session_suspend_skipped_ended",
                mission_id=mission_id,
            )
            return json.dumps({"status": "skipped", "reason": "already_ended", "mission_id": mission_id})

        # Suspend the possession
        manager = PossessionManager(db)
        manager.suspend_possession(mission_id, reason=reason)

        logger.info(
            "plugin_session_suspended",
            mission_id=mission_id,
            session_id=session_id,
            reason=reason,
            previous_status=current_status,
        )

        return json.dumps({"status": "suspended", "mission_id": mission_id})

    except Exception as e:
        logger.exception("plugin_session_suspend_error", error=str(e))
        return json.dumps({"status": "error", "message": str(e)})


if __name__ == "__main__":
    print(main())
