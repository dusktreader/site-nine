#!/usr/bin/env python3
"""
mission_rename_session tool - Rename the OpenCode session title to match the active mission.

This tool:
1. Receives context.sessionID from OpenCode
2. Looks up the active mission bound to this session
3. Builds the title: "Operation <codename>: <Persona> - <Role>"
4. Updates the OpenCode session title via OpenCodeSessionManager
5. Returns the new title and old title
"""

import sys
import json
from loguru import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path, get_project_root
from site_nine.missions.types import MissionStatus
from site_nine.opencode.manager import OpenCodeSessionManager


ACTIVE_STATUSES = (
    MissionStatus.ROLE_PENDING.value,
    MissionStatus.PERSONA_PENDING.value,
    MissionStatus.ACTIVE.value,
    MissionStatus.SUSPENDED.value,
)


def main():
    try:
        context = json.loads(sys.stdin.read())
        session_id = context["session_id"]

        logger.debug("mission_rename_session called", session_id=session_id)

        db_path = get_db_path()
        db = Database(db_path)

        # Look up the mission bound to this session
        rows = db.execute_query(
            """
            SELECT id, codename, persona_name, role, status
            FROM missions
            WHERE opencode_session_id = :session_id
            AND status IN ('ROLE_PENDING', 'PERSONA_PENDING', 'ACTIVE', 'SUSPENDED')
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

        mission = rows[0]
        codename = mission["codename"] or "unknown"
        persona = mission["persona_name"] or "unknown"
        role = mission["role"] or "unknown"

        # Build title: "Operation <codename>: <Persona> - <Role>"
        persona_display = persona.capitalize() if persona != "unknown" else "Unknown"
        new_title = f"Operation {codename}: {persona_display} - {role}"

        # Rename the OpenCode session
        project_root = get_project_root()
        session_manager = OpenCodeSessionManager(project_root)
        result = session_manager.update_session_title(session_id, new_title)

        logger.info(
            "session_renamed",
            session_id=session_id,
            old_title=result.old_title,
            new_title=result.new_title,
            mission_id=mission["id"],
        )

        response = {
            "session_id": session_id,
            "mission_id": mission["id"],
            "old_title": result.old_title,
            "new_title": result.new_title,
        }
        if result.warning:
            response["warning"] = result.warning

        return json.dumps(response)

    except Exception as e:
        logger.exception("mission_rename_session_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
