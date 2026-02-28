#!/usr/bin/env python3
"""
task_create tool - Create a new task in the site-nine task database.

This tool:
1. Receives title, role, priority, category, description, and optional epic_id
2. Validates and normalises the role and priority values
3. Generates the next available task ID
4. Inserts the task record with TODO status
5. Optionally links the task to an epic
6. Returns the created task details
"""

import sys
import json
from loguru import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.core.roles import Role
from site_nine.core.types import Priority
from site_nine.epics import EpicManager
from site_nine.tasks import TaskManager
from site_nine.tasks.exceptions import TaskError


def main():
    try:
        context = json.loads(sys.stdin.read())
        title = context["title"]
        role_raw = context["role"]
        priority_raw = context.get("priority") or "MEDIUM"
        category = context.get("category")
        description = context.get("description")
        epic_id = context.get("epic_id")

        logger.debug(
            "task_create_called",
            title=title,
            role=role_raw,
            priority=priority_raw,
            epic_id=epic_id,
        )

        # Validate and normalise role
        try:
            role_enum = Role.from_string(role_raw)
        except ValueError:
            logger.warning("task_create_invalid_role", role=role_raw)
            return json.dumps(
                {
                    "error": "invalid_role",
                    "message": f"Unknown role '{role_raw}'. Valid roles: Engineer, Operator, Architect, Tester, Designer, Documentarian, Administrator",
                }
            )

        # Validate and normalise priority
        try:
            priority_enum = Priority.from_string(priority_raw)
        except ValueError:
            logger.warning("task_create_invalid_priority", priority=priority_raw)
            return json.dumps(
                {
                    "error": "invalid_priority",
                    "message": f"Unknown priority '{priority_raw}'. Valid values: CRITICAL, HIGH, MEDIUM, LOW",
                }
            )

        db_path = get_db_path()
        db = Database(db_path)
        manager = TaskManager(db)

        # Generate the next available task ID
        task_id = manager.generate_task_id(role_enum.title_case, priority_enum.value)

        # Create the task record
        try:
            task = manager.create_task(
                task_id=task_id,
                title=title,
                role=role_enum.title_case,
                priority=priority_enum.value,
                category=category,
                description=description,
            )
        except TaskError as e:
            logger.error("task_create_failed", task_id=task_id, error=str(e))
            return json.dumps({"error": "creation_failed", "message": str(e)})

        # Optionally link to epic
        epic_warning = None
        if epic_id:
            try:
                epic_manager = EpicManager(db)
                epic_manager.link_task(task_id, epic_id)
                logger.info("task_linked_to_epic", task_id=task_id, epic_id=epic_id)
            except Exception as e:
                epic_warning = f"Task created but failed to link to epic {epic_id}: {e}"
                logger.warning("task_epic_link_failed", task_id=task_id, epic_id=epic_id, error=str(e))

        logger.info(
            "task_created",
            task_id=task.id,
            title=task.title,
            role=task.role,
            priority=task.priority,
            epic_id=epic_id,
        )

        result = {
            "task_id": task.id,
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
            "role": task.role,
            "category": task.category,
            "epic_id": epic_id if not epic_warning else None,
        }
        if epic_warning:
            result["warning"] = epic_warning

        return json.dumps(result)

    except Exception as e:
        logger.exception("task_create_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
