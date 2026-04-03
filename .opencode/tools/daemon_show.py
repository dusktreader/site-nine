#!/usr/bin/env python3
"""
daemon_show tool - Show daemon details including mythology, description, and whimsical bio.

This tool:
1. Receives daemon name from OpenCode
2. Fetches daemon record from database
3. Returns all daemon fields including bio (null if not yet generated)
"""

import sys
import json
from tool_logging import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.daemons.manager import DaemonManager


def daemon_to_dict(daemon) -> dict:
    return {
        "name": daemon.name,
        "role": daemon.role,
        "daemonology": daemon.daemonology,
        "personality": daemon.personality,
        "incarnations": daemon.incarnations,
        "last_possession": str(daemon.last_possession) if daemon.last_possession else None,
        "created_at": str(daemon.created_at) if daemon.created_at else None,
    }


def main():
    try:
        args = json.loads(sys.stdin.read())
        name = args.get("name")

        if not name:
            return json.dumps({"error": "missing_name", "message": "name is required."})

        logger.debug("daemon_show_called", name=name)

        db_path = get_db_path()
        db = Database(db_path)
        manager = DaemonManager(db)

        daemon = manager.get_daemon(name.lower())

        if not daemon:
            logger.warning("daemon_not_found", name=name)
            return json.dumps(
                {
                    "error": "daemon_not_found",
                    "message": f"Daemon '{name}' not found.",
                }
            )

        logger.info("daemon_shown", name=daemon.name, has_daemonology=bool(daemon.daemonology))

        return json.dumps({"daemon": daemon_to_dict(daemon)})

    except Exception as e:
        logger.exception("daemon_show_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
