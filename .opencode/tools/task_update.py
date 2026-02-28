#!/usr/bin/env python3
"""
task_update tool - Update fields on an existing task.

This tool:
1. Receives task_id plus optional fields: title, description, priority, category, notes, status
2. Validates task exists
3. If status is provided, calls TaskManager.update_status
4. If other fields are provided, calls TaskManager.update_task
5. Returns updated task details
"""

import sys
import json
from loguru import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.tasks import TaskManager
from site_nine.tasks.exceptions import TaskError
from site_nine.tasks.types import TaskStatus


VALID_STATUSES = {s.value for s in TaskStatus}


def task_to_dict(task) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status.value if hasattr(task.status, "value") else str(task.status),
        "priority": task.priority,
        "role": task.role,
        "category": task.category,
        "description": task.description,
        "notes": task.notes,
        "current_mission_id": task.current_mission_id,
        "epic_id": task.epic_id,
    }


def main():
    try:
        args = json.loads(sys.stdin.read())
        task_id = args["task_id"]
        title = args.get("title")
        description = args.get("description")
        priority = args.get("priority")
        category = args.get("category")
        notes = args.get("notes")
        status = args.get("status")

        logger.debug(
            "task_update called",
            task_id=task_id,
            title=title,
            priority=priority,
            status=status,
        )

        db_path = get_db_path()
        db = Database(db_path)
        manager = TaskManager(db)

        # Validate task exists
        task = manager.get_task(task_id)
        if not task:
            return json.dumps({"error": "task_not_found", "message": f"Task '{task_id}' not found"})

        # Validate status if provided
        if status:
            status_upper = status.upper()
            if status_upper not in VALID_STATUSES:
                return json.dumps(
                    {
                        "error": "invalid_status",
                        "message": f"Invalid status '{status}'. Valid values: {', '.join(sorted(VALID_STATUSES))}",
                    }
                )
            try:
                manager.update_status(
                    task_id,
                    status_upper,
                    notes=notes if notes and not any([title, description, priority, category]) else None,
                )
                logger.info("task_status_updated", task_id=task_id, status=status_upper)
            except TaskError as e:
                return json.dumps({"error": "update_failed", "message": str(e)})

        # Update other fields if provided
        field_updates = {}
        if title is not None:
            field_updates["title"] = title
        if description is not None:
            field_updates["description"] = description
        if priority is not None:
            priority_upper = priority.upper()
            valid_priorities = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
            if priority_upper not in valid_priorities:
                return json.dumps(
                    {
                        "error": "invalid_priority",
                        "message": f"Invalid priority '{priority}'. Valid values: {', '.join(sorted(valid_priorities))}",
                    }
                )
            field_updates["priority"] = priority_upper
        if category is not None:
            field_updates["category"] = category
        if field_updates:
            try:
                manager.update_task(task_id, **field_updates)
                logger.info("task_fields_updated", task_id=task_id, fields=list(field_updates.keys()))
            except TaskError as e:
                return json.dumps({"error": "update_failed", "message": str(e)})

        # Update notes standalone (if provided and status wasn't already updated with notes)
        if notes is not None and not status:
            # Re-fetch current status to pass to update_status (which accepts notes kwarg)
            current_task = manager.get_task(task_id)
            assert current_task is not None
            current_status = (
                current_task.status.value if hasattr(current_task.status, "value") else str(current_task.status)
            )
            try:
                manager.update_status(task_id, current_status, notes=notes)
                logger.info("task_notes_updated", task_id=task_id)
            except TaskError as e:
                return json.dumps({"error": "update_failed", "message": str(e)})

        if not status and not field_updates and notes is None:
            return json.dumps({"error": "no_updates", "message": "No fields provided to update"})

        # Return updated task
        updated_task = manager.get_task(task_id)
        logger.info("task_updated", task_id=task_id)
        return json.dumps({"task": task_to_dict(updated_task)})

    except Exception as e:
        logger.exception("task_update_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
