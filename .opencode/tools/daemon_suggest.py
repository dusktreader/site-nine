#!/usr/bin/env python3
"""
daemon_suggest tool - Suggest unused or least-used daemon names for a given role.

This tool:
1. Receives role and optional count from OpenCode
2. Queries the daemons table ordered by incarnations ASC (least-used first)
3. Returns the top N suggestions with name, daemonology, and usage info
"""

import sys
import json
from tool_logging import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.daemons.manager import DaemonManager


def daemon_to_dict(daemon) -> dict:
    """Serialize a Daemon to a JSON-safe dict."""
    return {
        "name": daemon.name,
        "role": daemon.role,
        "daemonology": daemon.daemonology,
        "incarnations": daemon.incarnations,
        "last_possession": daemon.last_possession,
        "is_unused": daemon.incarnations == 0,
    }


def main():
    try:
        args = json.loads(sys.stdin.read())

        role = args.get("role")
        count = args.get("count", 3)

        if not role:
            return json.dumps({"error": "missing_role", "message": "role is required."})

        logger.debug("daemon_suggest called", role=role, count=count)

        db_path = get_db_path()
        db = Database(db_path)
        manager = DaemonManager(db)

        suggestions = manager.suggest_for_role(role, count=count)

        logger.info("daemon_suggestions_returned", role=role, count=len(suggestions))

        return json.dumps(
            {
                "data": [daemon_to_dict(p) for p in suggestions],
                "count": len(suggestions),
                "role": role,
            }
        )

    except Exception as e:
        logger.exception("daemon_suggest_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
