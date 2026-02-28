#!/usr/bin/env python3
"""
worker_status tool - Return active worker missions for a given role.

This tool:
1. Receives an optional role filter
2. Queries active missions (end_time IS NULL) filtered by role if provided
3. Returns mission list with id, persona_name, role, codename, status, and last_active_at
"""

import sys
import json
from loguru import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.missions import MissionManager


def mission_to_dict(mission) -> dict:
    return {
        "id": mission.id,
        "persona_name": mission.persona_name,
        "role": mission.role,
        "codename": mission.codename,
        "status": mission.status.value if hasattr(mission.status, "value") else str(mission.status),
        "objective": mission.objective,
        "desk_mode_active": mission.desk_mode_active,
        "last_active_at": mission.last_active_at.isoformat() if mission.last_active_at else None,
        "start_date": mission.start_date,
        "start_time": mission.start_time,
    }


def main():
    try:
        args = json.loads(sys.stdin.read())
        role = args.get("role")

        logger.debug("worker_status_called", role=role)

        db = Database(get_db_path())
        manager = MissionManager(db)

        missions = manager.list_missions(active_only=True, role=role)

        logger.info("worker_status_returned", role=role, count=len(missions))

        return json.dumps(
            {
                "missions": [mission_to_dict(m) for m in missions],
                "count": len(missions),
                "role_filter": role,
            }
        )

    except Exception as e:
        logger.exception("worker_status_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
