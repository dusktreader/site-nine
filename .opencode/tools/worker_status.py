#!/usr/bin/env python3
"""
worker_status tool - Return active worker possessions for a given role.

This tool:
1. Receives an optional role filter
2. Queries active possessions (end_time IS NULL) filtered by role if provided
3. Returns possession list with id, daemon_name, role, status, and last_active_at
"""

import sys
import json
from tool_logging import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.possessions import PossessionManager


def possession_to_dict(possession) -> dict:
    return {
        "id": possession.id,
        "daemon_name": possession.daemon_name,
        "role": possession.role,
        "status": possession.status.value if hasattr(possession.status, "value") else str(possession.status),
        "desk_mode_active": possession.desk_mode_active,
        "last_active_at": possession.last_heartbeat_at.isoformat() if possession.last_heartbeat_at else None,
        "start_time": possession.start_time,
    }


def main():
    try:
        args = json.loads(sys.stdin.read())
        role = args.get("role")

        logger.debug("worker_status_called", role=role)

        db = Database(get_db_path())
        manager = PossessionManager(db)

        possessions = manager.list_possessions(active_only=True, role=role)

        logger.info("worker_status_returned", role=role, count=len(possessions))

        return json.dumps(
            {
                "possessions": [possession_to_dict(p) for p in possessions],
                "count": len(possessions),
                "role_filter": role,
            }
        )

    except Exception as e:
        logger.exception("worker_status_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
