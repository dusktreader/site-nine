#!/usr/bin/env python3
"""
mission_end tool - End the site-nine mission bound to the current OpenCode session.

This tool:
1. Receives context.sessionID from OpenCode (and optional mission_id override)
2. Looks up the active mission bound to this session (or uses mission_id directly)
3. Validates the mission is in an endable state
4. Calls MissionManager.end_mission to transition to ENDED status
5. Returns the ended mission info
"""

import sys
import json
from loguru import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.missions.manager import MissionManager
from site_nine.missions.types import MissionStatus


ENDABLE_STATUSES = (
    MissionStatus.ROLE_PENDING.value,
    MissionStatus.PERSONA_PENDING.value,
    MissionStatus.ACTIVE.value,
    MissionStatus.IDLE.value,
    MissionStatus.SUSPENDED.value,
)


def main():
    try:
        context = json.loads(sys.stdin.read())
        session_id = context.get("session_id")
        mission_id_override = context.get("mission_id")

        logger.debug("mission_end called", session_id=session_id, mission_id_override=mission_id_override)

        db_path = get_db_path()
        db = Database(db_path)
        manager = MissionManager(db)

        if mission_id_override is not None:
            # Direct mission_id override — look up by ID
            mission = manager.get_mission(int(mission_id_override))
            if not mission:
                return json.dumps(
                    {
                        "error": "mission_not_found",
                        "message": f"Mission {mission_id_override} not found",
                    }
                )
        else:
            # Look up mission bound to this session
            if not session_id:
                return json.dumps(
                    {
                        "error": "no_session_id",
                        "message": "No session_id provided and no mission_id override",
                    }
                )

            rows = db.execute_query(
                """
                SELECT id, codename, persona_name, role, status
                FROM missions
                WHERE opencode_session_id = :session_id
                AND status IN ('ROLE_PENDING', 'PERSONA_PENDING', 'ACTIVE', 'IDLE', 'SUSPENDED')
                ORDER BY created_at DESC
                LIMIT 1
                """,
                {"session_id": session_id},
            )

            if not rows:
                return json.dumps(
                    {
                        "error": "no_active_mission",
                        "message": f"No active mission found for session {session_id}",
                    }
                )

            row = rows[0]
            mission = manager.get_mission(row["id"])
            if not mission:
                return json.dumps(
                    {
                        "error": "mission_not_found",
                        "message": f"Mission {row['id']} not found",
                    }
                )

        if mission.status.value not in ENDABLE_STATUSES:
            return json.dumps(
                {
                    "error": "invalid_status",
                    "message": f"Mission {mission.id} is in status '{mission.status.value}' and cannot be ended",
                    "current_status": mission.status.value,
                }
            )

        # End the mission
        manager.end_mission(mission.id)

        logger.info(
            "mission_ended",
            mission_id=mission.id,
            codename=mission.codename,
            persona=mission.persona_name,
            role=mission.role,
        )

        return json.dumps(
            {
                "mission_id": mission.id,
                "codename": mission.codename,
                "persona": mission.persona_name,
                "role": mission.role,
                "status": MissionStatus.ENDED.value,
            }
        )

    except Exception as e:
        logger.exception("mission_end_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
