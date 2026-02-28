"""Epic status computation - status is fully derived from subtasks"""

from site_nine.core.database import Database
from site_nine.epics.types import EpicStatus


def compute_epic_status(db: Database, epic_id: str) -> str:
    """
    Compute epic status from its subtasks.

    Rules:
    - ABORTED: The epic itself has been explicitly aborted (aborted_at IS NOT NULL)
    - COMPLETE: All tasks are terminal (COMPLETE or ABORTED)
    - UNDERWAY: At least one task is UNDERWAY or COMPLETE (but not all terminal)
    - TODO: All tasks are TODO (or no tasks)

    Note: Individual aborted tasks do not abort the epic. An epic is only ABORTED
    when explicitly aborted via the abort command (sets aborted_at on the epic itself).

    Args:
        db: Database connection
        epic_id: Epic ID

    Returns:
        Computed status: TODO, UNDERWAY, COMPLETE, or ABORTED
    """
    # Check if epic itself was explicitly aborted
    epic_result = db.execute_query(
        "SELECT aborted_at FROM epics WHERE id = :epic_id",
        {"epic_id": epic_id},
    )
    if epic_result and epic_result[0]["aborted_at"] is not None:
        return EpicStatus.ABORTED.value

    result = db.execute_query(
        """
        SELECT 
            COUNT(*) as total_tasks,
            SUM(CASE WHEN status = 'TODO' THEN 1 ELSE 0 END) as todo_count,
            SUM(CASE WHEN status = 'UNDERWAY' THEN 1 ELSE 0 END) as underway_count,
            SUM(CASE WHEN status = 'COMPLETE' THEN 1 ELSE 0 END) as complete_count,
            SUM(CASE WHEN status = 'ABORTED' THEN 1 ELSE 0 END) as aborted_count
        FROM tasks
        WHERE epic_id = :epic_id
        """,
        {"epic_id": epic_id},
    )

    if not result:
        return EpicStatus.TODO.value

    row = result[0]
    total = row["total_tasks"]
    underway = row["underway_count"]
    complete = row["complete_count"]
    aborted = row["aborted_count"]

    # No tasks → TODO
    if total == 0:
        return EpicStatus.TODO.value

    # All tasks terminal (complete or aborted) → COMPLETE
    if complete + aborted == total:
        return EpicStatus.COMPLETE.value

    # At least one task started (underway or complete) → UNDERWAY
    if underway > 0 or complete > 0:
        return EpicStatus.UNDERWAY.value

    # All tasks TODO → TODO
    return EpicStatus.TODO.value


def get_all_epic_statuses(db: Database) -> dict[str, str]:
    """
    Get computed status for all epics efficiently.

    Returns:
        Dictionary mapping epic_id → computed status
    """
    # Get all epics (including aborted_at for explicit abort detection)
    epics = db.execute_query("SELECT id, aborted_at FROM epics")

    if not epics:
        return {}

    # Get task counts grouped by epic
    result = db.execute_query(
        """
        SELECT 
            epic_id,
            COUNT(*) as total_tasks,
            SUM(CASE WHEN status = 'TODO' THEN 1 ELSE 0 END) as todo_count,
            SUM(CASE WHEN status = 'UNDERWAY' THEN 1 ELSE 0 END) as underway_count,
            SUM(CASE WHEN status = 'COMPLETE' THEN 1 ELSE 0 END) as complete_count,
            SUM(CASE WHEN status = 'ABORTED' THEN 1 ELSE 0 END) as aborted_count
        FROM tasks
        WHERE epic_id IS NOT NULL
        GROUP BY epic_id
        """
    )

    # Build status map
    status_map = {}
    task_counts = {row["epic_id"]: row for row in result}

    for epic in epics:
        epic_id = epic["id"]

        # Epic explicitly aborted → ABORTED
        if epic["aborted_at"] is not None:
            status_map[epic_id] = EpicStatus.ABORTED.value
            continue

        # Epic has no tasks → TODO
        if epic_id not in task_counts:
            status_map[epic_id] = EpicStatus.TODO.value
            continue

        counts = task_counts[epic_id]
        total = counts["total_tasks"]
        underway = counts["underway_count"]
        complete = counts["complete_count"]
        aborted = counts["aborted_count"]

        # All tasks terminal (complete or aborted) → COMPLETE
        if complete + aborted == total:
            status_map[epic_id] = EpicStatus.COMPLETE.value
        # At least one started → UNDERWAY
        elif underway > 0 or complete > 0:
            status_map[epic_id] = EpicStatus.UNDERWAY.value
        # All TODO → TODO
        else:
            status_map[epic_id] = EpicStatus.TODO.value

    return status_map
