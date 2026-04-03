#!/usr/bin/env python3
"""
possession_role_record tool - Record role selection for a pending possession.

This tool:
1. Receives possession_id and role
2. Validates possession exists and is in ROLE_PENDING status
3. Validates role is a valid value
4. Updates possession role field
5. Transitions status from ROLE_PENDING to DAEMON_PENDING
6. Returns updated possession info
"""

import sys
import json
from tool_logging import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.core.utils import utc_now
from site_nine.possessions.types import PossessionStatus

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
        possession_id = context["possession_id"]
        role = context["role"]

        logger.debug("possession_role_record called", possession_id=possession_id, role=role)

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

        # Fetch possession
        rows = db.execute_query(
            "SELECT id, status FROM possessions WHERE id = :possession_id",
            {"possession_id": possession_id},
        )

        if not rows:
            return json.dumps(
                {
                    "error": "possession_not_found",
                    "message": f"Possession {possession_id} not found",
                }
            )

        possession = rows[0]

        if possession["status"] != PossessionStatus.ROLE_PENDING.value:
            return json.dumps(
                {
                    "error": "invalid_status",
                    "message": f"Possession {possession_id} is in status '{possession['status']}', expected '{PossessionStatus.ROLE_PENDING.value}'",
                    "current_status": possession["status"],
                }
            )

        # Update role and transition to DAEMON_PENDING
        now_str = utc_now()
        db.execute_update(
            """
            UPDATE possessions
            SET role = :role,
                status = :new_status,
                updated_at = :now
            WHERE id = :possession_id
            """,
            {
                "role": role,
                "new_status": PossessionStatus.DAEMON_PENDING.value,
                "now": now_str,
                "possession_id": possession_id,
            },
        )

        logger.info(
            "possession_role_recorded",
            possession_id=possession_id,
            role=role,
            new_status=PossessionStatus.DAEMON_PENDING.value,
        )

        return json.dumps(
            {
                "possession_id": possession_id,
                "role": role,
                "status": PossessionStatus.DAEMON_PENDING.value,
            }
        )

    except Exception as e:
        logger.exception("possession_role_record_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
