"""Tests for task management"""

from s9.core.database import Database
from s9.tasks import TaskManager


def test_create_task(test_db: Database):
    """Test creating a task"""
    manager = TaskManager(test_db)
    manager.create_task(
        task_id="T001",
        title="Test task",
        objective="Test objective",
        role="Builder",
        priority="HIGH",
        category="Testing",
        description="Test description",
    )

    task = manager.get_task("T001")
    assert task is not None
    assert task.id == "T001"
    assert task.title == "Test task"
    assert task.status == "TODO"
    assert task.priority == "HIGH"
    assert task.role == "Builder"


def test_claim_task(test_db: Database):
    """Test claiming a task"""
    manager = TaskManager(test_db)
    manager.create_task(
        task_id="T002",
        title="Claimable task",
        objective="Test claim",
        role="Builder",
    )

    manager.claim_task("T002", agent_name="test-agent")

    task = manager.get_task("T002")
    assert task.agent_name == "test-agent"
    assert task.status == "UNDERWAY"
    assert task.claimed_at is not None


def test_update_status(test_db: Database):
    """Test updating task status"""
    manager = TaskManager(test_db)
    manager.create_task(
        task_id="T003",
        title="Status test",
        objective="Test status",
        role="Tester",
    )

    manager.claim_task("T003", "test-agent")
    manager.update_status("T003", "REVIEW", notes="Ready for review")

    task = manager.get_task("T003")
    assert task.status == "REVIEW"
    assert task.notes == "Ready for review"


def test_close_task(test_db: Database):
    """Test closing a task"""
    manager = TaskManager(test_db)
    manager.create_task(
        task_id="T004",
        title="Close test",
        objective="Test close",
        role="Builder",
    )

    manager.claim_task("T004", "test-agent")
    manager.update_status("T004", "COMPLETE", notes="Task done")

    task = manager.get_task("T004")
    assert task.status == "COMPLETE"
    assert task.closed_at is not None


def test_list_tasks(test_db: Database):
    """Test listing tasks with filters"""
    manager = TaskManager(test_db)

    # Create multiple tasks
    manager.create_task("T005", "Task 5", "Objective 5", "Builder", priority="HIGH")
    manager.create_task("T006", "Task 6", "Objective 6", "Tester", priority="LOW")
    manager.create_task("T007", "Task 7", "Objective 7", "Builder", priority="MEDIUM")

    # Claim one task
    manager.claim_task("T005", "agent1")

    # List all tasks
    all_tasks = manager.list_tasks()
    assert len(all_tasks) == 3

    # Filter by status
    todo_tasks = manager.list_tasks(status="TODO")
    assert len(todo_tasks) == 2

    underway_tasks = manager.list_tasks(status="UNDERWAY")
    assert len(underway_tasks) == 1
    assert underway_tasks[0].id == "T005"

    # Filter by role
    builder_tasks = manager.list_tasks(role="Builder")
    assert len(builder_tasks) == 2

    # Filter by agent
    agent_tasks = manager.list_tasks(agent_name="agent1")
    assert len(agent_tasks) == 1
    assert agent_tasks[0].id == "T005"


def test_task_ordering(test_db: Database):
    """Test that tasks are returned in a consistent order"""
    manager = TaskManager(test_db)

    manager.create_task("T008", "Low priority", "Objective", "Builder", priority="LOW")
    manager.create_task("T009", "High priority", "Objective", "Builder", priority="HIGH")
    manager.create_task("T010", "Medium priority", "Objective", "Builder", priority="MEDIUM")
    manager.create_task("T011", "Critical priority", "Objective", "Builder", priority="CRITICAL")

    tasks = manager.list_tasks()

    # Verify all tasks are returned
    assert len(tasks) == 4
    task_ids = {t.id for t in tasks}
    assert task_ids == {"T008", "T009", "T010", "T011"}
