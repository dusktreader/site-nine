#!/usr/bin/env python3
"""
mission_summary tool - Generate a summary of files, commits, and tasks for the current mission.

This tool:
1. Receives context.sessionID and optional mission_id override
2. Looks up the mission (by session or direct ID)
3. Calls MissionManager.generate_summary to collect git file changes, commits, and tasks
4. Returns structured summary JSON
"""

import sys
import json
from loguru import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.missions.manager import MissionManager


def main():
    try:
        context = json.loads(sys.stdin.read())
        session_id = context.get("session_id")
        mission_id_override = context.get("mission_id")

        logger.debug("mission_summary called", session_id=session_id, mission_id_override=mission_id_override)

        db_path = get_db_path()
        db = Database(db_path)
        manager = MissionManager(db)

        # Resolve mission_id
        if mission_id_override is not None:
            mission_id = int(mission_id_override)
            mission = manager.get_mission(mission_id)
            if not mission:
                return json.dumps(
                    {
                        "error": "mission_not_found",
                        "message": f"Mission {mission_id} not found",
                    }
                )
        else:
            if not session_id:
                return json.dumps(
                    {
                        "error": "no_session_id",
                        "message": "No session_id provided and no mission_id override",
                    }
                )

            rows = db.execute_query(
                """
                SELECT id FROM missions
                WHERE opencode_session_id = :session_id
                ORDER BY created_at DESC
                LIMIT 1
                """,
                {"session_id": session_id},
            )

            if not rows:
                return json.dumps(
                    {
                        "error": "no_mission",
                        "message": f"No mission found for session {session_id}",
                    }
                )

            mission_id = rows[0]["id"]
            mission = manager.get_mission(mission_id)
            if not mission:
                return json.dumps(
                    {
                        "error": "mission_not_found",
                        "message": f"Mission {mission_id} not found",
                    }
                )

        # Generate summary
        summary = manager.generate_summary(mission_id)

        logger.info(
            "mission_summary_generated",
            mission_id=mission_id,
            codename=mission.codename,
            files_changed=len(summary.files_changed),
            commits=len(summary.commits),
            tasks=len(summary.tasks),
        )

        return json.dumps(
            {
                "mission_id": mission.id,
                "codename": mission.codename,
                "persona": mission.persona_name,
                "role": mission.role,
                "status": mission.status.value,
                "start_date": mission.start_date,
                "start_time": mission.start_time,
                "files_changed": [{"status": fc.status, "file": fc.file} for fc in summary.files_changed],
                "commits": summary.commits,
                "tasks": [{"id": t.id, "title": t.title, "status": t.status.value} for t in summary.tasks],
                "warnings": summary.warnings,
            }
        )

    except Exception as e:
        logger.exception("mission_summary_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
