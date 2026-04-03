#!/usr/bin/env python3
"""
daemon_set_bio tool - Set or update the whimsical bio for a daemon.

This tool:
1. Receives daemon name and bio text from OpenCode
2. Updates the daemonology field in the database
3. Returns the updated daemon details
"""

import sys
import json
from tool_logging import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.daemons.manager import DaemonManager
from site_nine.daemons.exceptions import DaemonError


def main():
    try:
        args = json.loads(sys.stdin.read())
        name = args.get("name")
        bio = args.get("bio")

        if not name:
            return json.dumps({"error": "missing_name", "message": "name is required."})
        if not bio:
            return json.dumps({"error": "missing_bio", "message": "bio is required."})

        logger.debug("daemon_set_bio_called", name=name, bio_length=len(bio))

        db_path = get_db_path()
        db = Database(db_path)
        manager = DaemonManager(db)

        try:
            updated = manager.set_daemonology(name.lower(), bio)
        except DaemonError as e:
            logger.warning("daemon_set_bio_failed", name=name, error=str(e))
            return json.dumps({"error": "update_failed", "message": str(e)})

        logger.info("daemon_bio_set", name=updated.name)

        return json.dumps(
            {
                "name": updated.name,
                "role": updated.role,
                "daemonology": updated.daemonology,
            }
        )

    except Exception as e:
        logger.exception("daemon_set_bio_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
