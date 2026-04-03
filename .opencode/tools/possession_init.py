#!/usr/bin/env python3
"""
possession_init tool - Initialize a new site-nine possession for the current session.

This tool:
1. Receives context.sessionID from OpenCode
2. Checks for double-binding (session already has a possession)
3. Creates possession record with ROLE_PENDING status
4. Returns possession_id
"""

import sys
import json
from tool_logging import logger

import pendulum

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.core.utils import utc_now
from site_nine.possessions.types import PossessionStatus


def main():
    try:
        # Read context from stdin
        context = json.loads(sys.stdin.read())
        session_id = context["session_id"]

        logger.debug("possession_init_called", session_id=session_id)

        # Connect to database
        db_path = get_db_path()
        db = Database(db_path)

        # Check for existing possession bound to this session
        existing = db.execute_query(
            """
            SELECT id, status
            FROM possessions
            WHERE opencode_session_id = :session_id
            AND status IN ('ROLE_PENDING', 'DAEMON_PENDING', 'ACTIVE', 'SUSPENDED')
            """,
            {"session_id": session_id},
        )

        if existing:
            possession = existing[0]
            logger.warning(
                "session_already_bound_to_possession",
                session_id=session_id,
                possession_id=possession["id"],
                status=possession["status"],
            )
            return json.dumps(
                {
                    "error": "double_binding",
                    "message": f"Session already bound to possession ID: {possession['id']}, status: {possession['status']}",
                    "possession_id": possession["id"],
                }
            )

        # Create new possession with ROLE_PENDING status
        now = pendulum.now("UTC")
        now_str = utc_now()
        result = db.execute_query(
            """
            INSERT INTO possessions (
                start_time,
                status, opencode_session_id, last_heartbeat_at,
                created_at, updated_at
            )
            VALUES (
                :start_time,
                :status, :session_id, :now,
                :now, :now
            )
            RETURNING id
            """,
            {
                "start_time": now.format("HH:mm:ss"),
                "status": PossessionStatus.ROLE_PENDING.value,
                "session_id": session_id,
                "now": now_str,
            },
        )

        if not result:
            logger.error("possession_creation_failed", session_id=session_id)
            return json.dumps({"error": "creation_failed", "message": "Failed to create possession record"})

        possession_id = result[0]["id"]

        logger.info(
            "possession_initialized",
            possession_id=possession_id,
            session_id=session_id,
        )

        return json.dumps(
            {
                "possession_id": possession_id,
            }
        )

    except Exception as e:
        logger.exception("possession_init_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
