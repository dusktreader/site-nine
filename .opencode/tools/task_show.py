#!/usr/bin/env python3
"""
task_show tool - Query site-nine tasks with rich filtering.

Modes (selected by args):
  1. Single task  — task_id provided: return full task details
  2. List         — role/status/possession_id filters: return matching tasks
  3. Mine         — possession_id alone: return tasks owned by that possession
  4. Report       — report=true: return summary report (optionally active_only)
"""

import sys
import json
from tool_logging import logger

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.tasks.manager import TaskManager


def task_to_dict(task) -> dict:
    """Serialize a Task dataclass to a JSON-safe dict."""
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status.value if hasattr(task.status, "value") else str(task.status),
        "priority": task.priority,
        "role": task.role,
        "category": task.category,
        "description": task.description,
        "notes": task.notes,
        "current_mission_id": task.current_possession_id,
        "claimed_at": task.claimed_at.isoformat() if task.claimed_at else None,
        "closed_at": task.closed_at.isoformat() if task.closed_at else None,
        "actual_hours": task.actual_hours,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "file_path": task.file_path,
        "epic_id": task.epic_id,
    }


def main():
    try:
        args = json.loads(sys.stdin.read())

        task_id = args.get("task_id")
        role = args.get("role")
        status = args.get("status")
        mission_id = args.get("possession_id") or args.get("mission_id")  # accept both for backward compat
        report = args.get("report", False)
        active_only = args.get("active_only", False)

        logger.debug(
            "task_show called",
            task_id=task_id,
            role=role,
            status=status,
            mission_id=mission_id,
            report=report,
            active_only=active_only,
        )

        db_path = get_db_path()
        db = Database(db_path)
        manager = TaskManager(db)

        # ── Mode 1: single task by ID ──────────────────────────────────────
        if task_id:
            task = manager.get_task(task_id)
            if not task:
                return json.dumps(
                    {
                        "error": "task_not_found",
                        "message": f"Task {task_id} not found.",
                    }
                )
            logger.info("task_shown", task_id=task_id)
            return json.dumps({"data": task_to_dict(task)})

        # ── Mode 4: summary report ─────────────────────────────────────────
        if report:
            tasks = manager.list_tasks(role=role)
            if active_only:
                tasks = [t for t in tasks if t.status.value not in ("COMPLETE", "ABORTED")]

            status_counts: dict[str, int] = {}
            role_counts: dict[str, int] = {}
            priority_counts: dict[str, int] = {}

            for t in tasks:
                s = t.status.value if hasattr(t.status, "value") else str(t.status)
                status_counts[s] = status_counts.get(s, 0) + 1
                role_counts[t.role] = role_counts.get(t.role, 0) + 1
                priority_counts[t.priority] = priority_counts.get(t.priority, 0) + 1

            logger.info("task_report_generated", total=len(tasks))
            return json.dumps(
                {
                    "data": {
                        "total": len(tasks),
                        "by_status": status_counts,
                        "by_role": role_counts,
                        "by_priority": priority_counts,
                        "tasks": [task_to_dict(t) for t in tasks],
                    }
                }
            )

        # ── Mode 3: tasks owned by a possession (possession_id alone) ─────────
        # Mode 3 and Mode 2 both use list_tasks — the distinction is
        # cosmetic (mine vs list), so we just filter by possession_id.

        # ── Mode 2 / 3: list with filters ─────────────────────────────────
        tasks = manager.list_tasks(
            status=status.upper() if status else None,
            role=role,
            possession_id=mission_id,
        )

        logger.info("tasks_listed", count=len(tasks), role=role, status=status, possession_id=mission_id)
        return json.dumps(
            {
                "data": [task_to_dict(t) for t in tasks],
                "count": len(tasks),
            }
        )

    except Exception as e:
        logger.exception("task_show_error", error=str(e))
        return json.dumps({"error": "unexpected_error", "message": str(e)})


if __name__ == "__main__":
    print(main())
