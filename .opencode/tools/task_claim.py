#!/usr/bin/env python3
"""
task_claim tool - Claim a task for the current possession.

This tool:
1. Receives task_id, possession_id, and role
2. Validates the task exists and role matches
3. Checks for unresolved external blockers
4. Checks for incomplete task dependencies
5. Calls TaskManager.claim_task to transition to UNDERWAY
6. Returns the claimed task info
"""

import sys
import json
from tool_logging import logger

from site_nine.blocks import BlockManager
from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.dependencies import DependencyManager
from site_nine.tasks import TaskManager
from site_nine.tasks.types import TaskStatus


def main():
    try:
        context = json.loads(sys.stdin.read())
        task_id = context["task_id"]
        possession_id = int(context.get("possession_id") or context.get("mission_id"))
        role = context["role"]

        logger.debug("task_claim called", task_id=task_id, possession_id=possession_id, role=role)

        db_path = get_db_path()
        db = Database(db_path)
        manager = TaskManager(db)

        # Validate task exists
        task = manager.get_task(task_id)
        if not task:
            return json.dumps(
                {
                    "error": "task_not_found",
                    "message": f"Task '{task_id}' not found",
                }
            )

        # Validate role match
        if task.role != role:
            return json.dumps(
                {
                    "error": "role_mismatch",
                    "message": f"Task role '{task.role}' does not match claiming role '{role}'",
                    "task_role": task.role,
                    "claiming_role": role,
                }
            )

        # Check for unresolved external blockers
        block_manager = BlockManager(db)
        unresolved_blocks = block_manager.get_unresolved_blocks(task_id)
        if unresolved_blocks:
            return json.dumps(
                {
                    "error": "task_blocked",
                    "message": f"Task {task_id} is blocked by {len(unresolved_blocks)} external blocker(s)",
                    "blockers": [
                        {"id": b.id, "type": b.block_type, "description": b.description} for b in unresolved_blocks
                    ],
                }
            )

        # Check for incomplete task dependencies
        dep_manager = DependencyManager(db)
        incomplete_deps = dep_manager.check_task_blocked_by_dependencies(task_id)
        if incomplete_deps:
            return json.dumps(
                {
                    "error": "dependencies_incomplete",
                    "message": f"Task {task_id} is blocked by {len(incomplete_deps)} incomplete dependency(ies)",
                    "incomplete_dependencies": incomplete_deps,
                }
            )

        # Claim the task
        manager.claim_task(task_id, possession_id, role)

        logger.info(
            "task_claimed",
            task_id=task_id,
            possession_id=possession_id,
            role=role,
            title=task.title,
        )

        return json.dumps(
            {
                "task_id": task_id,
                "title": task.title,
                "status": TaskStatus.UNDERWAY.value,
                "priority": task.priority,
                "role": task.role,
                "possession_id": possession_id,
            }
        )

    except Exception as e:
        logger.exception("task_claim_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
