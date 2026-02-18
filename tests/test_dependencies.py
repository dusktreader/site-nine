"""Tests for dependencies module"""

import pytest

from site_nine.dependencies.exceptions import DependencyError
from site_nine.dependencies.manager import DependencyManager
from site_nine.dependencies.models import TaskDependency


def _create_task(db, task_id, status="TODO", role="Engineer", priority="MEDIUM"):
    """Helper to create a task"""
    db.execute_update(
        """
        INSERT INTO tasks (id, title, description, status, priority, role, file_path, created_at, updated_at)
        VALUES (:id, :title, :desc, :status, :priority, :role, :file_path, datetime('now'), datetime('now'))
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


def test_add_dependency(test_db):
    """Test adding a dependency between tasks"""
    _create_task(test_db, "ENG-M-0001")
    _create_task(test_db, "ENG-M-0002")

    manager = DependencyManager(test_db)
    manager.add_dependency("ENG-M-0001", "ENG-M-0002")

    # Check dependency was created
    deps = manager.get_dependencies("ENG-M-0001")
    assert deps == ["ENG-M-0002"]


def test_add_dependency_duplicate(test_db):
    """Test adding duplicate dependency does not create duplicate entry"""
    _create_task(test_db, "ENG-M-0001")
    _create_task(test_db, "ENG-M-0002")

    manager = DependencyManager(test_db)
    manager.add_dependency("ENG-M-0001", "ENG-M-0002")
    manager.add_dependency("ENG-M-0001", "ENG-M-0002")  # Add again

    # Should still only have one dependency
    deps = manager.get_dependencies("ENG-M-0001")
    assert deps == ["ENG-M-0002"]


def test_add_multiple_dependencies(test_db):
    """Test adding multiple dependencies to one task"""
    _create_task(test_db, "ENG-M-0001")
    _create_task(test_db, "ENG-M-0002")
    _create_task(test_db, "ENG-M-0003")
    _create_task(test_db, "ENG-M-0004")

    manager = DependencyManager(test_db)
    manager.add_dependency("ENG-M-0001", "ENG-M-0002")
    manager.add_dependency("ENG-M-0001", "ENG-M-0003")
    manager.add_dependency("ENG-M-0001", "ENG-M-0004")

    # Should have all three dependencies, sorted
    deps = manager.get_dependencies("ENG-M-0001")
    assert deps == ["ENG-M-0002", "ENG-M-0003", "ENG-M-0004"]


def test_remove_dependency(test_db):
    """Test removing a dependency"""
    _create_task(test_db, "ENG-M-0001")
    _create_task(test_db, "ENG-M-0002")

    manager = DependencyManager(test_db)
    manager.add_dependency("ENG-M-0001", "ENG-M-0002")

    # Remove the dependency
    manager.remove_dependency("ENG-M-0001", "ENG-M-0002")

    # Should have no dependencies
    deps = manager.get_dependencies("ENG-M-0001")
    assert deps == []


def test_remove_dependency_nonexistent(test_db):
    """Test removing non-existent dependency does not error"""
    _create_task(test_db, "ENG-M-0001")
    _create_task(test_db, "ENG-M-0002")

    manager = DependencyManager(test_db)

    # Remove non-existent dependency (should not error)
    manager.remove_dependency("ENG-M-0001", "ENG-M-0002")

    # Should have no dependencies
    deps = manager.get_dependencies("ENG-M-0001")
    assert deps == []


def test_get_dependencies_empty(test_db):
    """Test getting dependencies for task with no dependencies"""
    _create_task(test_db, "ENG-M-0001")

    manager = DependencyManager(test_db)
    deps = manager.get_dependencies("ENG-M-0001")

    assert deps == []


def test_get_dependencies_nonexistent_task(test_db):
    """Test getting dependencies for non-existent task"""
    manager = DependencyManager(test_db)
    deps = manager.get_dependencies("NONEXISTENT")

    assert deps == []


def test_get_dependents(test_db):
    """Test getting tasks that depend on a given task"""
    _create_task(test_db, "ENG-M-0001")
    _create_task(test_db, "ENG-M-0002")
    _create_task(test_db, "ENG-M-0003")

    manager = DependencyManager(test_db)
    # Task 2 and 3 both depend on task 1
    manager.add_dependency("ENG-M-0002", "ENG-M-0001")
    manager.add_dependency("ENG-M-0003", "ENG-M-0001")

    # Get dependents of task 1
    dependents = manager.get_dependents("ENG-M-0001")
    assert dependents == ["ENG-M-0002", "ENG-M-0003"]


def test_get_dependents_empty(test_db):
    """Test getting dependents for task with no dependents"""
    _create_task(test_db, "ENG-M-0001")

    manager = DependencyManager(test_db)
    dependents = manager.get_dependents("ENG-M-0001")

    assert dependents == []


def test_check_task_blocked_by_dependencies_not_blocked(test_db):
    """Test checking if task is blocked when dependency is complete"""
    _create_task(test_db, "ENG-M-0001")
    _create_task(test_db, "ENG-M-0002", status="COMPLETE")

    manager = DependencyManager(test_db)
    manager.add_dependency("ENG-M-0001", "ENG-M-0002")

    # Task 1 depends on task 2, but task 2 is complete
    blocked = manager.check_task_blocked_by_dependencies("ENG-M-0001")
    assert blocked == []


def test_check_task_blocked_by_dependencies_blocked(test_db):
    """Test checking if task is blocked when dependency is incomplete"""
    _create_task(test_db, "ENG-M-0001")
    _create_task(test_db, "ENG-M-0002", status="TODO")

    manager = DependencyManager(test_db)
    manager.add_dependency("ENG-M-0001", "ENG-M-0002")

    # Task 1 depends on task 2, and task 2 is not complete
    blocked = manager.check_task_blocked_by_dependencies("ENG-M-0001")
    assert blocked == ["ENG-M-0002"]


def test_check_task_blocked_by_dependencies_multiple(test_db):
    """Test checking blocked status with multiple incomplete dependencies"""
    _create_task(test_db, "ENG-M-0001")
    _create_task(test_db, "ENG-M-0002", status="TODO")
    _create_task(test_db, "ENG-M-0003", status="UNDERWAY")
    _create_task(test_db, "ENG-M-0004", status="COMPLETE")

    manager = DependencyManager(test_db)
    manager.add_dependency("ENG-M-0001", "ENG-M-0002")
    manager.add_dependency("ENG-M-0001", "ENG-M-0003")
    manager.add_dependency("ENG-M-0001", "ENG-M-0004")

    # Task 1 is blocked by tasks 2 and 3 (not complete)
    blocked = manager.check_task_blocked_by_dependencies("ENG-M-0001")
    assert blocked == ["ENG-M-0002", "ENG-M-0003"]


def test_check_task_blocked_by_dependencies_no_dependencies(test_db):
    """Test checking blocked status for task with no dependencies"""
    _create_task(test_db, "ENG-M-0001")

    manager = DependencyManager(test_db)
    blocked = manager.check_task_blocked_by_dependencies("ENG-M-0001")

    assert blocked == []


def test_list_all_dependencies_empty(test_db):
    """Test listing all dependencies when none exist"""
    manager = DependencyManager(test_db)
    deps = manager.list_all_dependencies()

    assert deps == []


def test_list_all_dependencies(test_db):
    """Test listing all dependencies in the system"""
    _create_task(test_db, "ENG-M-0001")
    _create_task(test_db, "ENG-M-0002")
    _create_task(test_db, "ENG-M-0003")
    _create_task(test_db, "ENG-M-0004")

    manager = DependencyManager(test_db)
    manager.add_dependency("ENG-M-0001", "ENG-M-0002")
    manager.add_dependency("ENG-M-0001", "ENG-M-0003")
    manager.add_dependency("ENG-M-0004", "ENG-M-0002")

    # Get all dependencies
    deps = manager.list_all_dependencies()

    assert len(deps) == 3
    assert deps[0] == TaskDependency("ENG-M-0001", "ENG-M-0002")
    assert deps[1] == TaskDependency("ENG-M-0001", "ENG-M-0003")
    assert deps[2] == TaskDependency("ENG-M-0004", "ENG-M-0002")


def test_task_dependency_model():
    """Test TaskDependency model creation"""
    dep = TaskDependency("ENG-M-0001", "ENG-M-0002")

    assert dep.task_id == "ENG-M-0001"
    assert dep.depends_on_task_id == "ENG-M-0002"


def test_add_dependency_self_dependency(test_db):
    """Test that adding a self-dependency raises DependencyError"""
    _create_task(test_db, "ENG-M-0001")

    manager = DependencyManager(test_db)

    with pytest.raises(DependencyError, match="Task cannot depend on itself"):
        manager.add_dependency("ENG-M-0001", "ENG-M-0001")
