"""Tests for tasks.manager module"""

import pytest

from site_nine.tasks.manager import TaskError, TaskManager
from site_nine.tasks.types import TaskStatus


def _create_task(db, task_id, role="Engineer", priority="MEDIUM", status="TODO"):
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


def test_list_tasks_empty(test_db):
    """Test listing tasks when none exist"""
    manager = TaskManager(test_db)
    tasks = manager.list_tasks()
    assert tasks == []


def test_list_tasks_all(test_db):
    """Test listing all tasks"""
    _create_task(test_db, "ENG-M-0001")
    _create_task(test_db, "ENG-H-0002", priority="HIGH")
    _create_task(test_db, "TST-L-0003", role="Tester", priority="LOW")

    manager = TaskManager(test_db)
    tasks = manager.list_tasks()

    assert len(tasks) == 3
    # Should be sorted by priority: HIGH > MEDIUM > LOW
    assert tasks[0].id == "ENG-H-0002"
    assert tasks[1].id == "ENG-M-0001"
    assert tasks[2].id == "TST-L-0003"


def test_list_tasks_filter_by_status(test_db):
    """Test filtering tasks by status"""
    _create_task(test_db, "ENG-M-0001", status="TODO")
    _create_task(test_db, "ENG-M-0002", status="COMPLETE")
    _create_task(test_db, "ENG-M-0003", status="TODO")

    manager = TaskManager(test_db)
    tasks = manager.list_tasks(status="TODO")

    assert len(tasks) == 2
    assert all(t.status == "TODO" for t in tasks)


def test_list_tasks_filter_by_role(test_db):
    """Test filtering tasks by role"""
    _create_task(test_db, "ENG-M-0001", role="Engineer")
    _create_task(test_db, "TST-M-0002", role="Tester")
    _create_task(test_db, "ENG-M-0003", role="Engineer")

    manager = TaskManager(test_db)
    tasks = manager.list_tasks(role="Engineer")

    assert len(tasks) == 2
    assert all(t.role == "Engineer" for t in tasks)


def test_list_tasks_filter_by_mission(test_db_with_data):
    """Test filtering tasks by possession ID"""
    # Update one task to have a possession
    test_db_with_data.execute_update("UPDATE tasks SET current_possession_id = 1 WHERE id = 'ENG-M-0001'")

    manager = TaskManager(test_db_with_data)
    tasks = manager.list_tasks(possession_id=1)

    assert len(tasks) == 1
    assert tasks[0].id == "ENG-M-0001"


def test_list_tasks_sorting_by_priority(test_db):
    """Test that tasks are sorted by priority correctly"""
    _create_task(test_db, "ENG-L-0001", priority="LOW")
    _create_task(test_db, "ENG-C-0002", priority="CRITICAL")
    _create_task(test_db, "ENG-M-0003", priority="MEDIUM")
    _create_task(test_db, "ENG-H-0004", priority="HIGH")

    manager = TaskManager(test_db)
    tasks = manager.list_tasks()

    # Should be: CRITICAL, HIGH, MEDIUM, LOW
    assert tasks[0].priority == "CRITICAL"
    assert tasks[1].priority == "HIGH"
    assert tasks[2].priority == "MEDIUM"
    assert tasks[3].priority == "LOW"


def test_get_task_exists(test_db):
    """Test getting an existing task"""
    _create_task(test_db, "ENG-M-0001")

    manager = TaskManager(test_db)
    task = manager.get_task("ENG-M-0001")

    assert task is not None
    assert task.id == "ENG-M-0001"
    assert task.title == "Task ENG-M-0001"


def test_get_task_not_found(test_db):
    """Test getting a non-existent task"""
    manager = TaskManager(test_db)
    task = manager.get_task("ENG-M-9999")
    assert task is None


def test_claim_task_basic(test_db_with_data):
    """Test claiming a task for a possession"""
    manager = TaskManager(test_db_with_data)

    # ENG-M-0001 exists in fixture with status TODO
    manager.claim_task("ENG-M-0001", possession_id=1, current_role="Engineer")

    task = manager.get_task("ENG-M-0001")
    assert task.current_possession_id == 1
    assert task.status == TaskStatus.UNDERWAY.value
    assert task.claimed_at is not None


def test_release_task(test_db_with_data):
    """Test releasing a claimed task back to TODO"""
    # First claim a task
    test_db_with_data.execute_update(
        """
        UPDATE tasks 
        SET current_possession_id = 1, claimed_at = datetime('now'), status = 'UNDERWAY'
        WHERE id = 'ENG-M-0001'
        """
    )

    manager = TaskManager(test_db_with_data)
    manager.release_task("ENG-M-0001")

    task = manager.get_task("ENG-M-0001")
    assert task.current_possession_id is None
    assert task.claimed_at is None
    assert task.status == "TODO"


def test_update_status_basic(test_db):
    """Test updating task status"""
    _create_task(test_db, "ENG-M-0001", status="TODO")

    manager = TaskManager(test_db)
    manager.update_status("ENG-M-0001", "UNDERWAY")

    task = manager.get_task("ENG-M-0001")
    assert task.status == "UNDERWAY"


def test_update_status_to_complete_sets_closed_at(test_db):
    """Test that COMPLETE status sets closed_at"""
    _create_task(test_db, "ENG-M-0001", status="UNDERWAY")

    manager = TaskManager(test_db)
    manager.update_status("ENG-M-0001", "COMPLETE")

    task = manager.get_task("ENG-M-0001")
    assert task.status == "COMPLETE"
    assert task.closed_at is not None


def test_update_status_to_aborted_sets_closed_at(test_db):
    """Test that ABORTED status sets closed_at"""
    _create_task(test_db, "ENG-M-0001", status="UNDERWAY")

    manager = TaskManager(test_db)
    manager.update_status("ENG-M-0001", "ABORTED")

    task = manager.get_task("ENG-M-0001")
    assert task.status == "ABORTED"
    assert task.closed_at is not None


def test_update_status_with_notes(test_db):
    """Test updating status with notes"""
    _create_task(test_db, "ENG-M-0001")

    manager = TaskManager(test_db)
    manager.update_status("ENG-M-0001", "COMPLETE", notes="Finished successfully")

    task = manager.get_task("ENG-M-0001")
    assert task.status == "COMPLETE"
    assert task.notes == "Finished successfully"


def test_update_task_title(test_db):
    """Test updating task title"""
    _create_task(test_db, "ENG-M-0001")

    manager = TaskManager(test_db)
    manager.update_task("ENG-M-0001", title="Updated Title")

    task = manager.get_task("ENG-M-0001")
    assert task.title == "Updated Title"


def test_update_task_multiple_fields(test_db):
    """Test updating multiple task fields"""
    _create_task(test_db, "ENG-M-0001")

    manager = TaskManager(test_db)
    manager.update_task(
        "ENG-M-0001",
        title="New Title",
        description="New Description",
        priority="HIGH",
        category="bug-fix",
    )

    task = manager.get_task("ENG-M-0001")
    assert task.title == "New Title"
    assert task.description == "New Description"
    assert task.priority == "HIGH"
    assert task.category == "bug-fix"


def test_update_task_invalid_field(test_db):
    """Test that updating invalid field raises error"""
    _create_task(test_db, "ENG-M-0001")

    manager = TaskManager(test_db)
    with pytest.raises(TaskError, match="Cannot update field 'status'"):
        manager.update_task("ENG-M-0001", status="COMPLETE")


def test_update_task_no_fields(test_db):
    """Test that updating with no fields raises error"""
    _create_task(test_db, "ENG-M-0001")

    manager = TaskManager(test_db)
    with pytest.raises(TaskError, match="No fields to update"):
        manager.update_task("ENG-M-0001")


def test_create_task_basic(test_db):
    """Test creating a basic task"""
    manager = TaskManager(test_db)
    manager.create_task(
        task_id="ENG-M-0001",
        title="New Task",
        role="Engineer",
        priority="MEDIUM",
    )

    task = manager.get_task("ENG-M-0001")
    assert task is not None
    assert task.title == "New Task"
    assert task.status == "TODO"
    assert task.role == "Engineer"
    assert task.priority == "MEDIUM"


def test_create_task_with_optional_fields(test_db):
    """Test creating task with optional fields"""
    manager = TaskManager(test_db)
    manager.create_task(
        task_id="ENG-H-0001",
        title="Bug Fix",
        role="Engineer",
        priority="HIGH",
        category="bug-fix",
        description="Fix critical bug",
        file_path=".custom/path/task.md",
    )

    task = manager.get_task("ENG-H-0001")
    assert task.category == "bug-fix"
    assert task.description == "Fix critical bug"
    assert task.file_path == ".custom/path/task.md"


def test_create_task_invalid_id_format(test_db):
    """Test creating task with invalid ID format"""
    manager = TaskManager(test_db)

    with pytest.raises(TaskError, match="Invalid task ID 'INVALID'"):
        manager.create_task(
            task_id="INVALID",
            title="Task",
            role="Engineer",
            priority="MEDIUM",
        )


def test_create_task_role_mismatch(test_db):
    """Test creating task where ID role doesn't match provided role"""
    manager = TaskManager(test_db)

    with pytest.raises(TaskError, match="Task ID role 'Engineer' does not match provided role 'Tester'"):
        manager.create_task(
            task_id="ENG-M-0001",
            title="Task",
            role="Tester",  # Mismatch
            priority="MEDIUM",
        )


def test_create_task_priority_mismatch(test_db):
    """Test creating task where ID priority doesn't match provided priority"""
    manager = TaskManager(test_db)

    with pytest.raises(TaskError, match="Task ID priority 'MEDIUM' does not match provided priority 'HIGH'"):
        manager.create_task(
            task_id="ENG-M-0001",
            title="Task",
            role="Engineer",
            priority="HIGH",  # Mismatch
        )


def test_generate_task_id(test_db):
    """Test generating task ID"""
    manager = TaskManager(test_db)
    task_id = manager.generate_task_id("Engineer", "HIGH")

    # Should generate ENG-H-0001 since no tasks exist
    assert task_id == "ENG-H-0001"


def test_generate_task_id_sequential(test_db):
    """Test generating sequential task IDs"""
    _create_task(test_db, "ENG-M-0001")
    _create_task(test_db, "TST-H-0002")

    manager = TaskManager(test_db)
    task_id = manager.generate_task_id("Engineer", "HIGH")

    # Should generate ENG-H-0003 (next after 0002)
    assert task_id == "ENG-H-0003"


def test_list_tasks_with_invalid_task_id_format(test_db):
    """Test that tasks with invalid ID format are sorted at the end"""
    # Manually insert task with non-standard ID to test fallback sorting
    test_db.execute_update(
        """
        INSERT INTO tasks (id, title, description, status, priority, role, file_path, created_at, updated_at)
        VALUES ('INVALID-ID', 'Invalid Task', 'Test', 'TODO', 'HIGH', 'Engineer', '.opencode/work/tasks/INVALID.md', datetime('now'), datetime('now'))
        """
    )
    _create_task(test_db, "ENG-H-0001", priority="HIGH")

    manager = TaskManager(test_db)
    tasks = manager.list_tasks()

    # Valid task should come first even though both are HIGH priority
    assert len(tasks) == 2
    assert tasks[0].id == "ENG-H-0001"
    assert tasks[1].id == "INVALID-ID"


def test_claim_task_with_epic_scoping_success(test_db_with_data):
    """Test claiming task succeeds when possession and task are in same epic"""
    # Create test epic
    test_db_with_data.execute_update(
        """
        INSERT INTO epics (id, title, description, priority, file_path, created_at, updated_at)
        VALUES ('EPC-H-0001', 'Test Epic', 'Description', 'HIGH', '.opencode/work/epics/EPC-H-0001.md', datetime('now'), datetime('now'))
        """
    )
    # Update possession 1 to be epic-scoped
    test_db_with_data.execute_update("UPDATE possessions SET epic_id = 'EPC-H-0001' WHERE id = 1")
    # Update task to belong to same epic
    test_db_with_data.execute_update("UPDATE tasks SET epic_id = 'EPC-H-0001' WHERE id = 'ENG-M-0001'")

    manager = TaskManager(test_db_with_data)
    manager.claim_task("ENG-M-0001", possession_id=1, current_role="Engineer")

    task = manager.get_task("ENG-M-0001")
    assert task.current_possession_id == 1
    assert task.status == TaskStatus.UNDERWAY.value


def test_claim_task_with_epic_scoping_mismatch(test_db_with_data):
    """Test claiming task fails when possession and task are in different epics"""
    # Create test epics
    test_db_with_data.execute_update(
        """
        INSERT INTO epics (id, title, description, priority, file_path, created_at, updated_at)
        VALUES 
            ('EPC-H-0001', 'Test Epic 1', 'Description', 'HIGH', '.opencode/work/epics/EPC-H-0001.md', datetime('now'), datetime('now')),
            ('EPC-H-0002', 'Test Epic 2', 'Description', 'HIGH', '.opencode/work/epics/EPC-H-0002.md', datetime('now'), datetime('now'))
        """
    )
    # Update possession 1 to be scoped to EPC-H-0001
    test_db_with_data.execute_update("UPDATE possessions SET epic_id = 'EPC-H-0001' WHERE id = 1")
    # Update task to belong to different epic
    test_db_with_data.execute_update("UPDATE tasks SET epic_id = 'EPC-H-0002' WHERE id = 'ENG-M-0001'")

    manager = TaskManager(test_db_with_data)
    with pytest.raises(
        TaskError,
        match="Cannot claim task ENG-M-0001 from epic EPC-H-0002 when possession is scoped to epic EPC-H-0001",
    ):
        manager.claim_task("ENG-M-0001", possession_id=1, current_role="Engineer")


def test_claim_task_without_epic_scoping(test_db_with_data):
    """Test claiming task succeeds when possession has no epic_id (general possession)"""
    # Possession 1 has no epic_id by default
    # Task also has no epic_id by default

    manager = TaskManager(test_db_with_data)
    manager.claim_task("ENG-M-0001", possession_id=1, current_role="Engineer")

    task = manager.get_task("ENG-M-0001")
    assert task.current_possession_id == 1
    assert task.status == TaskStatus.UNDERWAY.value


def test_claim_task_epic_scoped_mission_can_claim_task_in_epic(test_db_with_data):
    """Test epic-scoped possession can claim any task in that epic"""
    # Create test epic
    test_db_with_data.execute_update(
        """
        INSERT INTO epics (id, title, description, priority, file_path, created_at, updated_at)
        VALUES ('EPC-H-0001', 'Test Epic', 'Description', 'HIGH', '.opencode/work/epics/EPC-H-0001.md', datetime('now'), datetime('now'))
        """
    )
    # Update possession 1 to be epic-scoped
    test_db_with_data.execute_update("UPDATE possessions SET epic_id = 'EPC-H-0001' WHERE id = 1")
    # Update multiple tasks to belong to same epic
    test_db_with_data.execute_update("UPDATE tasks SET epic_id = 'EPC-H-0001' WHERE id IN ('ENG-M-0001', 'ENG-M-0002')")

    manager = TaskManager(test_db_with_data)

    # Claim first task
    manager.claim_task("ENG-M-0001", possession_id=1, current_role="Engineer")
    task1 = manager.get_task("ENG-M-0001")
    assert task1.current_possession_id == 1

    # Release and claim second task
    manager.release_task("ENG-M-0001")
    manager.claim_task("ENG-M-0002", possession_id=1, current_role="Tester")
    task2 = manager.get_task("ENG-M-0002")
    assert task2.current_possession_id == 1
