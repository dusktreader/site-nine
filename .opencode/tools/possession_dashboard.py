#!/usr/bin/env python3
"""
possession_dashboard tool - Show role-filtered task dashboard.

This tool:
1. Receives a role from OpenCode
2. Queries available (TODO and UNDERWAY) tasks for that role
3. Returns structured task list for the agent to present to the Director
"""

import sys
import json
from tool_logging import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.core.roles import Role
from site_nine.tasks import TaskManager


def task_to_dict(task) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status.value if hasattr(task.status, "value") else str(task.status),
        "priority": task.priority,
        "role": task.role,
        "current_possession_id": task.current_possession_id,
        "epic_id": task.epic_id,
    }


def main():
    try:
        args = json.loads(sys.stdin.read())
        role_raw = args.get("role")

        if not role_raw:
            return json.dumps({"error": "missing_role", "message": "role is required."})

        logger.debug("possession_dashboard_called", role=role_raw)

        # Validate role
        try:
            role_enum = Role.from_string(role_raw)
        except ValueError:
            logger.warning("possession_dashboard_invalid_role", role=role_raw)
            return json.dumps(
                {
                    "error": "invalid_role",
                    "message": f"Unknown role '{role_raw}'. Valid roles: Engineer, Operator, Architect, Tester, Designer, Documentarian, Administrator",
                }
            )

        db_path = get_db_path()
        db = Database(db_path)
        manager = TaskManager(db)

        all_tasks = manager.list_tasks(role=role_enum.title_case)
        available = [
            t
            for t in all_tasks
            if (t.status.value if hasattr(t.status, "value") else str(t.status)) in ("TODO", "UNDERWAY")
        ]

        logger.info("possession_dashboard_returned", role=role_enum.title_case, task_count=len(available))

        return json.dumps(
            {
                "role": role_enum.title_case,
                "available_tasks": [task_to_dict(t) for t in available],
                "task_count": len(available),
            }
        )

    except Exception as e:
        logger.exception("possession_dashboard_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
