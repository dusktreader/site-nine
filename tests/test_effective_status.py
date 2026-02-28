"""Tests for tasks.effective_status module - simplified version matching actual schema"""

import pytest

from site_nine.tasks import TaskManager
from site_nine.tasks.types import EffectiveStatus, TaskStatus


def _create_task(db, task_id, status="TODO", role="Engineer", priority="MEDIUM"):
    """Helper to create a task with correct schema"""
    db.execute_update(
        """
        INSERT INTO tasks (id, title, description, status, priority, role, file_path, created_at)
        VALUES (:id, :title, :desc, :status, :priority, :role, :file_path, datetime('now'))
        """,
        {
            "id": task_id,
            "title": f"Task {task_id}",
            "desc": "Test description",
            "status": status,
            "priority": priority,
            "role": role,
            "file_path": f".opencode/work/tasks/{task_id}.md",
        },
    )


def test_get_effective_status_task_not_found(test_db):
    """Test error when task does not exist"""
    manager = TaskManager(test_db)
    with pytest.raises(ValueError, match="Task ENG-M-0001 not found"):
        manager.get_effective_status("ENG-M-0001")


def test_get_effective_status_complete(test_db):
    """Test complete task returns COMPLETE status"""
    manager = TaskManager(test_db)
    _create_task(test_db, "ENG-M-0001", status=TaskStatus.COMPLETE.value)
    result = manager.get_effective_status("ENG-M-0001")
    assert result == TaskStatus.COMPLETE.value


def test_get_effective_status_aborted(test_db):
    """Test aborted task returns ABORTED status"""
    manager = TaskManager(test_db)
    _create_task(test_db, "ENG-M-0001", status=TaskStatus.ABORTED.value)
    result = manager.get_effective_status("ENG-M-0001")
    assert result == TaskStatus.ABORTED.value


def test_get_effective_status_blocked_external(test_db_with_data):
    """Test task with external block returns BLOCKED_EXTERNAL"""
    manager = TaskManager(test_db_with_data)
    # Create external block
    test_db_with_data.execute_update(
        """
        INSERT INTO blocks (task_id, block_type, description)
        VALUES (:task_id, :block_type, :description)
        """,
        {
            "task_id": "ENG-M-0001",
            "block_type": "external",
            "description": "Waiting on third-party API",
        },
    )

    result = manager.get_effective_status("ENG-M-0001")
    assert result == EffectiveStatus.BLOCKED_EXTERNAL.value


def test_get_effective_status_blocked_review(test_db_with_data):
    """Test task with review block returns BLOCKED_REVIEW"""
    manager = TaskManager(test_db_with_data)
    # Create review block
    test_db_with_data.execute_update(
        """
        INSERT INTO blocks (task_id, block_type, description)
        VALUES (:task_id, :block_type, :description)
        """,
        {
            "task_id": "ENG-M-0001",
            "block_type": "review",
            "description": "Awaiting code review approval",
        },
    )

    result = manager.get_effective_status("ENG-M-0001")
    assert result == EffectiveStatus.BLOCKED_REVIEW.value


def test_get_effective_status_underway(test_db):
    """Test UNDERWAY task with no blocks returns UNDERWAY"""
    manager = TaskManager(test_db)
    _create_task(test_db, "ENG-M-0001", status=TaskStatus.UNDERWAY.value)
    result = manager.get_effective_status("ENG-M-0001")
    assert result == TaskStatus.UNDERWAY.value


def test_get_all_effective_statuses_empty(test_db):
    """Test getting all effective statuses when no tasks exist"""
    manager = TaskManager(test_db)
    result = manager.get_all_effective_statuses()
    assert result == {}


def test_get_all_effective_statuses_multiple_tasks(test_db_with_data):
    """Test getting effective statuses for multiple tasks"""
    manager = TaskManager(test_db_with_data)
    result = manager.get_all_effective_statuses()
    # Should have 3 tasks from fixture
    assert len(result) == 3
    assert "ENG-M-0001" in result


def test_count_tasks_by_effective_status_no_role_filter(test_db_with_data):
    """Test counting tasks by effective status without role filter"""
    manager = TaskManager(test_db_with_data)
    result = manager.count_tasks_by_effective_status()
    # All statuses should be present
    assert EffectiveStatus.TODO.value in result
    # Should have 3 TODO tasks from fixture
    assert result[EffectiveStatus.TODO.value] >= 3


def test_get_effective_status_blocked_dependency(test_db):
    """Test task with incomplete dependency returns BLOCKED_DEPENDENCY"""
    manager = TaskManager(test_db)
    # Create two tasks
    _create_task(test_db, "ENG-M-0001", status="TODO")
    _create_task(test_db, "ENG-M-0002", status="TODO")

    # Make ENG-M-0001 depend on ENG-M-0002
    test_db.execute_update(
        """
        INSERT INTO task_dependencies (task_id, depends_on_task_id)
        VALUES (:task_id, :depends_on)
        """,
        {"task_id": "ENG-M-0001", "depends_on": "ENG-M-0002"},
    )

    # ENG-M-0001 should be blocked because ENG-M-0002 is not complete
    result = manager.get_effective_status("ENG-M-0001")
    assert result == EffectiveStatus.BLOCKED_DEPENDENCY.value

    # ENG-M-0002 should not be blocked
    result2 = manager.get_effective_status("ENG-M-0002")
    assert result2 == TaskStatus.TODO.value


def test_get_effective_status_dependency_complete(test_db):
    """Test task with complete dependency is not blocked"""
    manager = TaskManager(test_db)
    # Create two tasks
    _create_task(test_db, "ENG-M-0001", status="TODO")
    _create_task(test_db, "ENG-M-0002", status="COMPLETE")

    # Make ENG-M-0001 depend on ENG-M-0002
    test_db.execute_update(
        """
        INSERT INTO task_dependencies (task_id, depends_on_task_id)
        VALUES (:task_id, :depends_on)
        """,
        {"task_id": "ENG-M-0001", "depends_on": "ENG-M-0002"},
    )

    # ENG-M-0001 should NOT be blocked because ENG-M-0002 is complete
    result = manager.get_effective_status("ENG-M-0001")
    assert result == TaskStatus.TODO.value


def test_count_tasks_with_all_statuses(test_db):
    """Test counting tasks with terminal statuses"""
    manager = TaskManager(test_db)
    # Create tasks with different statuses
    _create_task(test_db, "ENG-M-0001", status="TODO")
    _create_task(test_db, "ENG-M-0002", status="UNDERWAY")
    _create_task(test_db, "ENG-M-0003", status="COMPLETE")
    _create_task(test_db, "ENG-M-0004", status="ABORTED")

    result = manager.count_tasks_by_effective_status()

    # Check that we have the expected statuses
    assert EffectiveStatus.TODO.value in result
    assert result[EffectiveStatus.TODO.value] == 1
    assert EffectiveStatus.UNDERWAY.value in result
    assert result[EffectiveStatus.UNDERWAY.value] == 1
    assert EffectiveStatus.COMPLETE.value in result
    assert result[EffectiveStatus.COMPLETE.value] == 1
    assert EffectiveStatus.ABORTED.value in result
    assert result[EffectiveStatus.ABORTED.value] == 1


def test_count_tasks_by_effective_status_with_role_filter(test_db):
    """Test counting tasks by effective status with role filter"""
    manager = TaskManager(test_db)
    # Create tasks with different roles
    _create_task(test_db, "ENG-M-0001", status="TODO", role="Engineer")
    _create_task(test_db, "ENG-M-0002", status="TODO", role="Engineer")
    _create_task(test_db, "TST-M-0001", status="TODO", role="Tester")
    _create_task(test_db, "ARC-M-0001", status="UNDERWAY", role="Architect")

    # Count only Engineer tasks
    result = manager.count_tasks_by_effective_status(role="Engineer")

    # Should only count Engineer tasks
    assert result[EffectiveStatus.TODO.value] == 2
    assert result[EffectiveStatus.UNDERWAY.value] == 0

    # Count only Tester tasks
    result = manager.count_tasks_by_effective_status(role="Tester")
    assert result[EffectiveStatus.TODO.value] == 1

    # Count only Architect tasks
    result = manager.count_tasks_by_effective_status(role="Architect")
    assert result[EffectiveStatus.UNDERWAY.value] == 1
