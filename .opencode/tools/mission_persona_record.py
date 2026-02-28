#!/usr/bin/env python3
"""
mission_persona_record tool - Record persona selection for a pending mission.

This tool:
1. Receives mission_id and optional persona name
2. If persona is not provided, atomically claims the least-used persona for the mission's role
3. Validates mission exists and is in PERSONA_PENDING status
4. Validates persona exists in the personas table (if provided)
5. Updates mission: persona_name, mission_file, start_date, start_time
6. Creates the mission markdown file
7. Updates persona mission_count / last_mission_at (if manual selection)
8. Transitions status from PERSONA_PENDING to ACTIVE
9. Returns updated mission info
"""

import sys
import json
import pendulum
from loguru import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.core.utils import utc_now
from site_nine.missions.manager import MissionManager
from site_nine.missions.types import MissionStatus
from site_nine.personas.manager import PersonaManager


def main():
    try:
        # Read context from stdin
        context = json.loads(sys.stdin.read())
        mission_id = context["mission_id"]
        persona_input = context.get("persona")  # Optional now

        # Normalize persona if provided
        persona = persona_input.lower().strip() if persona_input else None

        logger.debug(
            "mission_persona_record called",
            mission_id=mission_id,
            persona=persona,
            auto_claim=persona is None,
        )

        # Connect to database
        db_path = get_db_path()
        db = Database(db_path)

        # Fetch mission
        rows = db.execute_query(
            "SELECT id, codename, role, status FROM missions WHERE id = :mission_id",
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

        if mission["status"] != MissionStatus.PERSONA_PENDING.value:
            return json.dumps(
                {
                    "error": "invalid_status",
                    "message": f"Mission {mission_id} is in status '{mission['status']}', expected '{MissionStatus.PERSONA_PENDING.value}'",
                    "current_status": mission["status"],
                }
            )

        if not mission["role"]:
            return json.dumps(
                {
                    "error": "role_not_set",
                    "message": f"Mission {mission_id} has no role set — run mission_role_record first",
                }
            )

        role = mission["role"]
        persona_manager = PersonaManager(db)

        # Handle persona selection: auto-claim or validate manual selection
        if persona is None:
            # Auto-claim: atomically select and claim least-used persona
            claimed_persona = persona_manager.claim_persona(role)
            persona = claimed_persona.name
            logger.info(
                "persona_auto_claimed",
                mission_id=mission_id,
                role=role,
                persona=persona,
            )
        else:
            # Manual selection: validate persona exists
            persona_rows = db.execute_query(
                "SELECT name, mythology, description FROM personas WHERE name = :name",
                {"name": persona},
            )

            if not persona_rows:
                return json.dumps(
                    {
                        "error": "persona_not_found",
                        "message": f"Persona '{persona}' not found in personas table",
                    }
                )

            # Update persona usage stats (manual selection only - auto-claim already did this)
            now_str = utc_now()
            db.execute_update(
                """
                UPDATE personas
                SET mission_count = mission_count + 1,
                    last_mission_at = :now
                WHERE name = :persona
                """,
                {"now": now_str, "persona": persona},
            )

        # Compute mission file path and timestamps
        now = pendulum.now("UTC")
        date_str = now.format("YYYY-MM-DD")
        time_str = now.format("HH:mm:ss")
        codename = mission["codename"]
        mission_file = f".opencode/work/missions/{date_str}.{time_str}.{role.lower()}.{persona}.md"

        now_str = utc_now()

        # Update mission record
        db.execute_update(
            """
            UPDATE missions
            SET persona_name = :persona,
                mission_file = :mission_file,
                start_date = :start_date,
                start_time = :start_time,
                status = :new_status,
                last_active_at = :now,
                updated_at = :now
            WHERE id = :mission_id
            """,
            {
                "persona": persona,
                "mission_file": mission_file,
                "start_date": date_str,
                "start_time": time_str,
                "new_status": MissionStatus.ACTIVE.value,
                "now": now_str,
                "mission_id": mission_id,
            },
        )

        # Create mission markdown file via MissionManager helper
        manager = MissionManager(db)
        manager._create_mission_file(
            mission_file=mission_file,
            persona_name=persona,
            role=role,
            codename=codename,
            objective="",
        )

        logger.info(
            "mission_persona_recorded",
            mission_id=mission_id,
            codename=codename,
            persona=persona,
            role=role,
            mission_file=mission_file,
        )

        return json.dumps(
            {
                "mission_id": mission_id,
                "codename": codename,
                "persona": persona,
                "role": role,
                "status": MissionStatus.ACTIVE.value,
                "mission_file": mission_file,
            }
        )

    except Exception as e:
        logger.exception("mission_persona_record_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
