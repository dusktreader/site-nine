#!/usr/bin/env python3
"""
mission_init tool - Initialize a new site-nine mission for the current session.

This tool:
1. Receives context.sessionID from OpenCode
2. Checks for double-binding (session already has a mission)
3. Creates mission record with ROLE_PENDING status
4. Generates codename
5. Returns mission_id and codename
"""

import sys
import json
from loguru import logger

import pendulum

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.core.utils import utc_now
from site_nine.missions.manager import generate_mission_codename
from site_nine.missions.types import MissionStatus


def main():
    try:
        # Read context from stdin
        context = json.loads(sys.stdin.read())
        session_id = context["session_id"]

        logger.debug("mission_init_called", session_id=session_id)

        # Connect to database
        db_path = get_db_path()
        db = Database(db_path)

        # Check for existing mission bound to this session
        existing = db.execute_query(
            """
            SELECT id, codename, status
            FROM missions
            WHERE opencode_session_id = :session_id
            AND status IN ('ROLE_PENDING', 'PERSONA_PENDING', 'ACTIVE', 'SUSPENDED')
            """,
            {"session_id": session_id},
        )

        if existing:
            mission = existing[0]
            logger.warning(
                "session_already_bound_to_mission",
                session_id=session_id,
                mission_id=mission["id"],
                codename=mission["codename"],
                status=mission["status"],
            )
            return json.dumps(
                {
                    "error": "double_binding",
                    "message": f"Session already bound to mission {mission['codename']} (ID: {mission['id']}, status: {mission['status']})",
                    "mission_id": mission["id"],
                    "codename": mission["codename"],
                }
            )

        # Create new mission with ROLE_PENDING status
        now = pendulum.now("UTC")
        now_str = utc_now()
        result = db.execute_query(
            """
            INSERT INTO missions (
                start_date, start_time,
                status, opencode_session_id, last_active_at,
                created_at, updated_at
            )
            VALUES (
                :start_date, :start_time,
                :status, :session_id, :now,
                :now, :now
            )
            RETURNING id
            """,
            {
                "start_date": now.format("YYYY-MM-DD"),
                "start_time": now.format("HH:mm:ss"),
                "status": MissionStatus.ROLE_PENDING.value,
                "session_id": session_id,
                "now": now_str,
            },
        )

        if not result:
            logger.error("mission_creation_failed", session_id=session_id)
            return json.dumps({"error": "creation_failed", "message": "Failed to create mission record"})

        mission_id = result[0]["id"]

        # Generate codename
        codename = generate_mission_codename(mission_id)

        # Update mission with codename
        db.execute_query(
            "UPDATE missions SET codename = :codename WHERE id = :id RETURNING *",
            {"codename": codename, "id": mission_id},
        )

        logger.info(
            "mission_initialized",
            mission_id=mission_id,
            codename=codename,
            session_id=session_id,
        )

        return json.dumps(
            {
                "mission_id": mission_id,
                "codename": codename,
            }
        )

    except Exception as e:
        logger.exception("mission_init_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
