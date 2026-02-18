"""Tests for epics.computed_status module"""

from site_nine.epics.computed_status import compute_epic_status, get_all_epic_statuses


def _create_epic(db, epic_id, priority="HIGH"):
    """Helper to create an epic"""
    db.execute_update(
        """
        INSERT INTO epics (id, title, description, priority, file_path, created_at, updated_at)
        VALUES (:id, :title, :desc, :priority, :file_path, datetime('now'), datetime('now'))
        """,
        {
            "id": epic_id,
            "title": f"Epic {epic_id}",
            "desc": "Test description",
            "priority": priority,
            "file_path": f".opencode/work/epics/{epic_id}.md",
        },
    )


def _create_task_for_epic(db, task_id, epic_id, status="TODO"):
    """Helper to create a task for an epic"""
    db.execute_update(
        """
        INSERT INTO tasks (id, title, description, status, priority, role, epic_id, file_path, created_at, updated_at)
        VALUES (:id, :title, :desc, :status, 'MEDIUM', 'Engineer', :epic_id, :file_path, datetime('now'), datetime('now'))
        """,
        {
            "id": task_id,
            "title": f"Task {task_id}",
            "desc": "Test",
            "status": status,
            "epic_id": epic_id,
            "file_path": f".opencode/work/tasks/{task_id}.md",
        },
    )


def test_compute_epic_status_no_tasks(test_db):
    """Test epic with no tasks returns TODO"""
    _create_epic(test_db, "EPC-H-0001")

    status = compute_epic_status(test_db, "EPC-H-0001")
    assert status == "TODO"


def test_compute_epic_status_all_todo(test_db):
    """Test epic with all TODO tasks returns TODO"""
    _create_epic(test_db, "EPC-H-0001")
    _create_task_for_epic(test_db, "ENG-M-0001", "EPC-H-0001", status="TODO")
    _create_task_for_epic(test_db, "ENG-M-0002", "EPC-H-0001", status="TODO")

    status = compute_epic_status(test_db, "EPC-H-0001")
    assert status == "TODO"


def test_compute_epic_status_all_complete(test_db):
    """Test epic with all COMPLETE tasks returns COMPLETE"""
    _create_epic(test_db, "EPC-H-0001")
    _create_task_for_epic(test_db, "ENG-M-0001", "EPC-H-0001", status="COMPLETE")
    _create_task_for_epic(test_db, "ENG-M-0002", "EPC-H-0001", status="COMPLETE")

    status = compute_epic_status(test_db, "EPC-H-0001")
    assert status == "COMPLETE"


def test_compute_epic_status_some_underway(test_db):
    """Test epic with some UNDERWAY tasks returns UNDERWAY"""
    _create_epic(test_db, "EPC-H-0001")
    _create_task_for_epic(test_db, "ENG-M-0001", "EPC-H-0001", status="TODO")
    _create_task_for_epic(test_db, "ENG-M-0002", "EPC-H-0001", status="UNDERWAY")

    status = compute_epic_status(test_db, "EPC-H-0001")
    assert status == "UNDERWAY"


def test_compute_epic_status_some_complete_not_all(test_db):
    """Test epic with some COMPLETE but not all returns UNDERWAY"""
    _create_epic(test_db, "EPC-H-0001")
    _create_task_for_epic(test_db, "ENG-M-0001", "EPC-H-0001", status="COMPLETE")
    _create_task_for_epic(test_db, "ENG-M-0002", "EPC-H-0001", status="TODO")

    status = compute_epic_status(test_db, "EPC-H-0001")
    assert status == "UNDERWAY"


def test_compute_epic_status_all_terminal_with_aborted(test_db):
    """Test epic with all terminal tasks (complete+aborted) and at least one aborted returns ABORTED"""
    _create_epic(test_db, "EPC-H-0001")
    _create_task_for_epic(test_db, "ENG-M-0001", "EPC-H-0001", status="COMPLETE")
    _create_task_for_epic(test_db, "ENG-M-0002", "EPC-H-0001", status="ABORTED")

    status = compute_epic_status(test_db, "EPC-H-0001")
    assert status == "ABORTED"


def test_compute_epic_status_all_aborted(test_db):
    """Test epic with all ABORTED tasks returns ABORTED"""
    _create_epic(test_db, "EPC-H-0001")
    _create_task_for_epic(test_db, "ENG-M-0001", "EPC-H-0001", status="ABORTED")
    _create_task_for_epic(test_db, "ENG-M-0002", "EPC-H-0001", status="ABORTED")

    status = compute_epic_status(test_db, "EPC-H-0001")
    assert status == "ABORTED"


def test_compute_epic_status_mixed_with_aborted_not_terminal(test_db):
    """Test epic with aborted but not all terminal returns TODO (aborted alone doesn't count as progress)"""
    _create_epic(test_db, "EPC-H-0001")
    _create_task_for_epic(test_db, "ENG-M-0001", "EPC-H-0001", status="ABORTED")
    _create_task_for_epic(test_db, "ENG-M-0002", "EPC-H-0001", status="TODO")

    status = compute_epic_status(test_db, "EPC-H-0001")
    # ABORTED alone doesn't count as progress (only UNDERWAY/COMPLETE do)
    # Since no tasks are UNDERWAY or COMPLETE, returns TODO
    assert status == "TODO"


def test_get_all_epic_statuses_empty(test_db):
    """Test getting statuses when no epics exist"""
    result = get_all_epic_statuses(test_db)
    assert result == {}


def test_get_all_epic_statuses_single_epic(test_db):
    """Test getting statuses for single epic with multiple tasks"""
    _create_epic(test_db, "EPC-H-0001")
    _create_task_for_epic(test_db, "ENG-M-0001", "EPC-H-0001", status="COMPLETE")
    _create_task_for_epic(test_db, "ENG-M-0002", "EPC-H-0001", status="TODO")

    result = get_all_epic_statuses(test_db)
    assert len(result) == 1
    assert result["EPC-H-0001"] == "UNDERWAY"  # One complete but not all


def test_get_all_epic_statuses_multiple_epics(test_db):
    """Test getting statuses for multiple epics"""
    # Epic 1: All complete
    _create_epic(test_db, "EPC-H-0001")
    _create_task_for_epic(test_db, "ENG-M-0001", "EPC-H-0001", status="COMPLETE")
    _create_task_for_epic(test_db, "ENG-M-0002", "EPC-H-0001", status="COMPLETE")

    # Epic 2: All TODO
    _create_epic(test_db, "EPC-H-0002")
    _create_task_for_epic(test_db, "ENG-M-0003", "EPC-H-0002", status="TODO")

    # Epic 3: No tasks
    _create_epic(test_db, "EPC-H-0003")

    # Epic 4: Some underway
    _create_epic(test_db, "EPC-H-0004")
    _create_task_for_epic(test_db, "ENG-M-0004", "EPC-H-0004", status="UNDERWAY")

    # Epic 5: Terminal with aborted
    _create_epic(test_db, "EPC-H-0005")
    _create_task_for_epic(test_db, "ENG-M-0005", "EPC-H-0005", status="COMPLETE")
    _create_task_for_epic(test_db, "ENG-M-0006", "EPC-H-0005", status="ABORTED")

    result = get_all_epic_statuses(test_db)

    assert len(result) == 5
    assert result["EPC-H-0001"] == "COMPLETE"
    assert result["EPC-H-0002"] == "TODO"
    assert result["EPC-H-0003"] == "TODO"
    assert result["EPC-H-0004"] == "UNDERWAY"
    assert result["EPC-H-0005"] == "ABORTED"


def test_get_all_epic_statuses_epic_without_tasks(test_db):
    """Test that epics without tasks are correctly handled"""
    _create_epic(test_db, "EPC-H-0001")
    _create_epic(test_db, "EPC-H-0002")

    # Add multiple tasks to first epic (one complete, one todo)
    _create_task_for_epic(test_db, "ENG-M-0001", "EPC-H-0001", status="COMPLETE")
    _create_task_for_epic(test_db, "ENG-M-0002", "EPC-H-0001", status="TODO")

    result = get_all_epic_statuses(test_db)

    assert len(result) == 2
    assert result["EPC-H-0001"] == "UNDERWAY"  # Has tasks with some complete
    assert result["EPC-H-0002"] == "TODO"  # No tasks
