#!/usr/bin/env python3
"""
task_release tool - Release a task back to TODO status.

This tool:
1. Receives task_id
2. Validates the task exists
3. Calls TaskManager.release_task to clear mission ownership and reset to TODO
4. Returns the released task info
"""

import sys
import json
from loguru import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.tasks import TaskManager
from site_nine.tasks.exceptions import TaskError


def main():
    try:
        args = json.loads(sys.stdin.read())
        task_id = args["task_id"]

        logger.debug("task_release called", task_id=task_id)

        db_path = get_db_path()
        db = Database(db_path)
        manager = TaskManager(db)

        task = manager.get_task(task_id)
        if not task:
            return json.dumps({"error": "task_not_found", "message": f"Task '{task_id}' not found"})

        try:
            manager.release_task(task_id)
        except TaskError as e:
            return json.dumps({"error": "release_failed", "message": str(e)})

        logger.info("task_released", task_id=task_id)
        return json.dumps(
            {
                "task_id": task_id,
                "title": task.title,
                "status": "TODO",
                "role": task.role,
                "priority": task.priority,
                "message": f"Task {task_id} released back to TODO.",
            }
        )

    except Exception as e:
        logger.exception("task_release_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
