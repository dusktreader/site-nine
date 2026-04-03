#!/usr/bin/env python3
"""
possession_end tool - End the site-nine possession bound to the current OpenCode session.

This tool:
1. Receives context.sessionID from OpenCode (and optional possession_id override)
2. Looks up the active possession bound to this session (or uses possession_id directly)
3. Validates the possession is in an endable state
4. Calls PossessionManager.exorcise to transition to EXORCISED status
5. Returns the ended possession info
"""

import sys
import json
from tool_logging import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.possessions.manager import PossessionManager
from site_nine.possessions.types import PossessionStatus


ENDABLE_STATUSES = (
    PossessionStatus.ROLE_PENDING.value,
    PossessionStatus.DAEMON_PENDING.value,
    PossessionStatus.ACTIVE.value,
    PossessionStatus.SUSPENDED.value,
)


def main():
    try:
        context = json.loads(sys.stdin.read())
        session_id = context.get("session_id")
        possession_id_override = context.get("possession_id")

        logger.debug("possession_end called", session_id=session_id, possession_id_override=possession_id_override)

        db_path = get_db_path()
        db = Database(db_path)
        manager = PossessionManager(db)

        if possession_id_override is not None:
            # Direct possession_id override — look up by ID
            possession = manager.get_possession(int(possession_id_override))
            if not possession:
                return json.dumps(
                    {
                        "error": "possession_not_found",
                        "message": f"Possession {possession_id_override} not found",
                    }
                )
        else:
            # Look up possession bound to this session
            if not session_id:
                return json.dumps(
                    {
                        "error": "no_session_id",
                        "message": "No session_id provided and no possession_id override",
                    }
                )

            rows = db.execute_query(
                """
                SELECT id, daemon_name, role, status
                FROM possessions
                WHERE opencode_session_id = :session_id
                AND status IN ('ROLE_PENDING', 'DAEMON_PENDING', 'ACTIVE', 'SUSPENDED')
                ORDER BY created_at DESC
                LIMIT 1
                """,
                {"session_id": session_id},
            )

            if not rows:
                return json.dumps(
                    {
                        "error": "no_active_possession",
                        "message": f"No active possession found for session {session_id}",
                    }
                )

            row = rows[0]
            possession = manager.get_possession(row["id"])
            if not possession:
                return json.dumps(
                    {
                        "error": "possession_not_found",
                        "message": f"Possession {row['id']} not found",
                    }
                )

        if possession.status.value not in ENDABLE_STATUSES:
            return json.dumps(
                {
                    "error": "invalid_status",
                    "message": f"Possession {possession.id} is in status '{possession.status.value}' and cannot be ended",
                    "current_status": possession.status.value,
                }
            )

        # End the possession
        if possession.id is None:
            return json.dumps({"error": "invalid_possession", "message": "Possession has no ID"})
        manager.exorcise(possession.id)

        logger.info(
            "possession_ended",
            possession_id=possession.id,
            daemon=possession.daemon_name,
            role=possession.role,
        )

        return json.dumps(
            {
                "possession_id": possession.id,
                "daemon_name": possession.daemon_name,
                "role": possession.role,
                "status": PossessionStatus.EXORCISED.value,
            }
        )

    except Exception as e:
        logger.exception("possession_end_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
