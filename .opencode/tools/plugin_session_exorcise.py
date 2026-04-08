#!/usr/bin/env python3
"""
plugin_session_exorcise.py - Exorcise the possession bound to a given session.

Called by the site-nine OpenCode plugin on session.deleted events to auto-exorcise
active possessions when their session closes (ENG-H-0245).

This replaces the previous suspend-on-close behavior. When a session ends:
  1. Find the possession bound to the session ID
  2. Exorcise (end) the possession via PossessionManager
  3. Release any UNDERWAY tasks back to TODO

Input (stdin, JSON):
    session_id: str     - OpenCode session ID

Output (stdout, JSON):
    On success:
        {"status": "exorcised", "possession_id": <int>, "tasks_released": [<str>, ...]}
    On no active possession found:
        {"status": "no_possession", "session_id": <str>}
    On possession already exorcised (skip silently):
        {"status": "skipped", "reason": "already_exorcised", "possession_id": <int>}
    On error:
        {"status": "error", "message": <str>}
"""

import json
import sys

from tool_logging import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.possessions.manager import PossessionManager
from site_nine.possessions.types import PossessionStatus
from site_nine.tasks.manager import TaskManager


def main() -> str:
    try:
        data = json.loads(sys.stdin.read())
        session_id = data["session_id"]

        logger.debug("plugin_session_exorcise_called", session_id=session_id)

        db_path = get_db_path()
        db = Database(db_path)

        # Find possession bound to this session that hasn't already been exorcised
        rows = db.execute_query(
            """
            SELECT id, status
            FROM possessions
            WHERE opencode_session_id = :session_id
              AND status != 'EXORCISED'
            LIMIT 1
            """,
            {"session_id": session_id},
        )

        if not rows:
            logger.debug("plugin_session_exorcise_no_possession", session_id=session_id)
            return json.dumps({"status": "no_possession", "session_id": session_id})

        possession = rows[0]
        possession_id = possession["id"]
        current_status = possession["status"]

        # Skip if already exorcised (defensive — query already filters this)
        if current_status == PossessionStatus.EXORCISED.value:
            logger.debug(
                "plugin_session_exorcise_skipped",
                possession_id=possession_id,
            )
            return json.dumps({"status": "skipped", "reason": "already_exorcised", "possession_id": possession_id})

        # Release any UNDERWAY tasks owned by this possession back to TODO
        task_manager = TaskManager(db)
        underway_tasks = db.execute_query(
            """
            SELECT id FROM tasks
            WHERE current_possession_id = :possession_id
              AND status = 'UNDERWAY'
            """,
            {"possession_id": possession_id},
        )

        tasks_released = []
        for task_row in underway_tasks:
            task_id = task_row["id"]
            try:
                task_manager.release_task(task_id)
                tasks_released.append(task_id)
                logger.info(
                    "plugin_session_exorcise_task_released",
                    task_id=task_id,
                    possession_id=possession_id,
                )
            except Exception as e:
                logger.warning(
                    "plugin_session_exorcise_task_release_failed",
                    task_id=task_id,
                    error=str(e),
                )

        # Exorcise the possession
        manager = PossessionManager(db)
        manager.exorcise(possession_id)

        logger.info(
            "plugin_session_exorcised",
            possession_id=possession_id,
            session_id=session_id,
            previous_status=current_status,
            tasks_released=tasks_released,
        )

        return json.dumps(
            {
                "status": "exorcised",
                "possession_id": possession_id,
                "tasks_released": tasks_released,
            }
        )

    except Exception as e:
        logger.exception("plugin_session_exorcise_error", error=str(e))
        return json.dumps({"status": "error", "message": str(e)})


if __name__ == "__main__":
    print(main())
