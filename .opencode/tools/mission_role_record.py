#!/usr/bin/env python3
"""
mission_role_record tool - Record role selection for a pending mission.

This tool:
1. Receives mission_id and role
2. Validates mission exists and is in ROLE_PENDING status
3. Validates role is a valid value
4. Updates mission role field
5. Transitions status from ROLE_PENDING to PERSONA_PENDING
6. Returns updated mission info
"""

import sys
import json
from loguru import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.core.utils import utc_now
from site_nine.missions.types import MissionStatus

VALID_ROLES = (
    "Administrator",
    "Architect",
    "Engineer",
    "Tester",
    "Documentarian",
    "Designer",
    "Inspector",
    "Operator",
    "Historian",
)


def main():
    try:
        # Read context from stdin
        context = json.loads(sys.stdin.read())
        mission_id = context["mission_id"]
        role = context["role"]

        logger.debug("mission_role_record called", mission_id=mission_id, role=role)

        # Validate role
        if role not in VALID_ROLES:
            return json.dumps(
                {
                    "error": "invalid_role",
                    "message": f"Invalid role '{role}'. Must be one of: {', '.join(VALID_ROLES)}",
                }
            )

        # Connect to database
        db_path = get_db_path()
        db = Database(db_path)

        # Fetch mission
        rows = db.execute_query(
            "SELECT id, codename, status FROM missions WHERE id = :mission_id",
            {"mission_id": mission_id},
        )

        if not rows:
            return json.dumps(
                {
                    "error": "mission_not_found",
                    "message": f"Mission {mission_id} not found",
                }
            )

        mission = rows[0]

        if mission["status"] != MissionStatus.ROLE_PENDING.value:
            return json.dumps(
                {
                    "error": "invalid_status",
                    "message": f"Mission {mission_id} is in status '{mission['status']}', expected '{MissionStatus.ROLE_PENDING.value}'",
                    "current_status": mission["status"],
                }
            )

        # Update role and transition to PERSONA_PENDING
        now_str = utc_now()
        db.execute_update(
            """
            UPDATE missions
            SET role = :role,
                status = :new_status,
                updated_at = :now
            WHERE id = :mission_id
            """,
            {
                "role": role,
                "new_status": MissionStatus.PERSONA_PENDING.value,
                "now": now_str,
                "mission_id": mission_id,
            },
        )

        logger.info(
            "mission_role_recorded",
            mission_id=mission_id,
            codename=mission["codename"],
            role=role,
            new_status=MissionStatus.PERSONA_PENDING.value,
        )

        return json.dumps(
            {
                "mission_id": mission_id,
                "codename": mission["codename"],
                "role": role,
                "status": MissionStatus.PERSONA_PENDING.value,
            }
        )

    except Exception as e:
        logger.exception("mission_role_record_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
