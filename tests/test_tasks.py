"""Tests for task management"""

from s9.core.database import Database
from s9.tasks import TaskManager


def test_create_task(test_db: Database):
    """Test creating a task"""
    manager = TaskManager(test_db)
    manager.create_task(
        task_id="BLD-H-0001",
        title="Test task",
        role="Builder",
        priority="HIGH",
        category="Testing",
        description="Test description",
    )

    task = manager.get_task("BLD-H-0001")
    assert task is not None
    assert task.id == "BLD-H-0001"
    assert task.title == "Test task"
    assert task.status == "TODO"
    assert task.priority == "HIGH"
    assert task.role == "Builder"


def test_claim_task(test_db: Database):
    """Test claiming a task"""
    manager = TaskManager(test_db)
    manager.create_task(
        task_id="BLD-M-0001",
        title="Claimable task",
        role="Builder",
        priority="MEDIUM",
    )

    manager.claim_task("BLD-M-0001", agent_name="test-agent")

    task = manager.get_task("BLD-M-0001")
    assert task.agent_name == "test-agent"
    assert task.status == "UNDERWAY"
    assert task.claimed_at is not None


def test_update_status(test_db: Database):
    """Test updating task status"""
    manager = TaskManager(test_db)
    manager.create_task(
        task_id="TST-M-0001",
        title="Status test",
        role="Tester",
        priority="MEDIUM",
    )

    manager.claim_task("TST-M-0001", "test-agent")
    manager.update_status("TST-M-0001", "REVIEW", notes="Ready for review")

    task = manager.get_task("TST-M-0001")
    assert task.status == "REVIEW"
    assert task.notes == "Ready for review"


def test_close_task(test_db: Database):
    """Test closing a task"""
    manager = TaskManager(test_db)
    manager.create_task(
        task_id="BLD-M-0002",
        title="Close test",
        role="Builder",
        priority="MEDIUM",
    )

    manager.claim_task("BLD-M-0002", "test-agent")
    manager.update_status("BLD-M-0002", "COMPLETE", notes="Task done")

    task = manager.get_task("BLD-M-0002")
    assert task.status == "COMPLETE"
    assert task.closed_at is not None


def test_list_tasks(test_db: Database):
    """Test listing tasks with filters"""
    manager = TaskManager(test_db)

    # Create multiple tasks
    manager.create_task("BLD-H-0002", "Task 5", "Builder", priority="HIGH")
    manager.create_task("TST-L-0001", "Task 6", "Tester", priority="LOW")
    manager.create_task("BLD-M-0003", "Task 7", "Builder", priority="MEDIUM")

    # Claim one task
    manager.claim_task("BLD-H-0002", "agent1")

    # List all tasks
    all_tasks = manager.list_tasks()
    assert len(all_tasks) == 3

    # Filter by status
    todo_tasks = manager.list_tasks(status="TODO")
    assert len(todo_tasks) == 2

    underway_tasks = manager.list_tasks(status="UNDERWAY")
    assert len(underway_tasks) == 1
    assert underway_tasks[0].id == "BLD-H-0002"

    # Filter by role
    builder_tasks = manager.list_tasks(role="Builder")
    assert len(builder_tasks) == 2

    # Filter by agent
    agent_tasks = manager.list_tasks(agent_name="agent1")
    assert len(agent_tasks) == 1
    assert agent_tasks[0].id == "BLD-H-0002"


def test_task_ordering(test_db: Database):
    """Test that tasks are returned in a consistent order"""
    manager = TaskManager(test_db)

    manager.create_task("BLD-L-0001", "Low priority", "Builder", priority="LOW")
    manager.create_task("BLD-H-0003", "High priority", "Builder", priority="HIGH")
    manager.create_task("BLD-M-0004", "Medium priority", "Builder", priority="MEDIUM")
    manager.create_task("BLD-C-0001", "Critical priority", "Builder", priority="CRITICAL")

    tasks = manager.list_tasks()

    # Verify all tasks are returned
    assert len(tasks) == 4
    task_ids = {t.id for t in tasks}
    assert task_ids == {"BLD-L-0001", "BLD-H-0003", "BLD-M-0004", "BLD-C-0001"}
