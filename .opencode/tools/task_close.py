#!/usr/bin/env python3
"""
task_close tool - Close a task as COMPLETE or ABORTED.

This tool:
1. Receives task_id, status (COMPLETE or ABORTED), and optional notes
2. Validates the task exists and status is a terminal value
3. Calls TaskManager.update_status to set final status and closed_at
4. Returns the closed task info
"""

import sys
import json
from loguru import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.tasks import TaskManager
from site_nine.tasks.exceptions import TaskError


TERMINAL_STATUSES = {"COMPLETE", "ABORTED"}


def main():
    try:
        args = json.loads(sys.stdin.read())
        task_id = args["task_id"]
        status = args["status"]
        notes = args.get("notes")

        logger.debug("task_close called", task_id=task_id, status=status)

        status_upper = status.upper()
        if status_upper not in TERMINAL_STATUSES:
            return json.dumps(
                {
                    "error": "invalid_status",
                    "message": f"Invalid close status '{status}'. Must be COMPLETE or ABORTED.",
                }
            )

        db_path = get_db_path()
        db = Database(db_path)
        manager = TaskManager(db)

        task = manager.get_task(task_id)
        if not task:
            return json.dumps({"error": "task_not_found", "message": f"Task '{task_id}' not found"})

        try:
            manager.update_status(task_id, status_upper, notes=notes)
        except TaskError as e:
            return json.dumps({"error": "close_failed", "message": str(e)})

        logger.info("task_closed", task_id=task_id, status=status_upper)
        return json.dumps(
            {
                "task_id": task_id,
                "title": task.title,
                "status": status_upper,
                "role": task.role,
                "priority": task.priority,
            }
        )

    except Exception as e:
        logger.exception("task_close_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
