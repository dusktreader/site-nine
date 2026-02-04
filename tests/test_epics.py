"""Tests for epic management"""

import pytest
from site_nine.core.database import Database
from site_nine.epics.epic_ids import format_epic_id, get_next_epic_number, parse_epic_id, validate_epic_id
from site_nine.epics.manager import EpicManager
from site_nine.epics.models import Epic
from site_nine.tasks.manager import TaskManager


class TestEpicIDs:
    """Test epic ID generation and validation"""

    def test_format_epic_id(self):
        """Test formatting epic IDs"""
        assert format_epic_id("HIGH", 1) == "EPC-H-0001"
        assert format_epic_id("CRITICAL", 2) == "EPC-C-0002"
        assert format_epic_id("MEDIUM", 3) == "EPC-M-0003"
        assert format_epic_id("LOW", 999) == "EPC-L-0999"

    def test_format_epic_id_invalid_priority(self):
        """Test formatting with invalid priority"""
        with pytest.raises(ValueError):
            format_epic_id("INVALID", 1)

    def test_parse_epic_id(self):
        """Test parsing epic IDs"""
        assert parse_epic_id("EPC-H-0001") == ("HIGH", 1)
        assert parse_epic_id("EPC-C-0002") == ("CRITICAL", 2)
        assert parse_epic_id("EPC-M-0003") == ("MEDIUM", 3)
        assert parse_epic_id("EPC-L-0999") == ("LOW", 999)

    def test_parse_epic_id_invalid(self):
        """Test parsing invalid epic IDs"""
        assert parse_epic_id("INVALID") is None
        assert parse_epic_id("EPC-X-0001") is None
        assert parse_epic_id("EPC-H-001") is None
        assert parse_epic_id("TSK-H-0001") is None

    def test_validate_epic_id(self):
        """Test validating epic IDs"""
        is_valid, error = validate_epic_id("EPC-H-0001")
        assert is_valid
        assert error is None

        is_valid, error = validate_epic_id("EPC-C-0002")
        assert is_valid
        assert error is None

    def test_validate_epic_id_invalid(self):
        """Test validating invalid epic IDs"""
        is_valid, error = validate_epic_id("")
        assert not is_valid
        assert "cannot be empty" in error

        is_valid, error = validate_epic_id("INVALID")
        assert not is_valid
        assert "must match format" in error

        is_valid, error = validate_epic_id("EPC-X-0001")
        assert not is_valid
        assert "must match format" in error  # Pattern doesn't match invalid priority code

    def test_get_next_epic_number(self, test_db: Database):
        """Test getting next epic number"""
        manager = EpicManager(test_db)

        # Should start at 1
        assert get_next_epic_number(test_db) == 1

        # Create some epics
        manager.create_epic("Test Epic 1", "HIGH")
        assert get_next_epic_number(test_db) == 2

        manager.create_epic("Test Epic 2", "MEDIUM")
        assert get_next_epic_number(test_db) == 3

        manager.create_epic("Test Epic 3", "CRITICAL")
        assert get_next_epic_number(test_db) == 4


class TestEpicManager:
    """Test epic manager operations"""

    def test_create_epic(self, test_db: Database):
        """Test creating an epic"""
        manager = EpicManager(test_db)
        epic = manager.create_epic("Test Epic", "HIGH", "Test description")

        assert epic.id == "EPC-H-0001"
        assert epic.title == "Test Epic"
        assert epic.description == "Test description"
        assert epic.priority == "HIGH"
        assert epic.status == "TODO"
        assert epic.file_path == ".opencode/work/epics/EPC-H-0001.md"
        assert epic.subtask_count == 0
        assert epic.completed_count == 0

    def test_create_epic_with_custom_id(self, test_db: Database):
        """Test creating epic with custom ID"""
        manager = EpicManager(test_db)
        epic = manager.create_epic("Test Epic", "CRITICAL", epic_id="EPC-C-0099")

        assert epic.id == "EPC-C-0099"
        assert epic.priority == "CRITICAL"

    def test_create_epic_invalid_id(self, test_db: Database):
        """Test creating epic with invalid ID"""
        manager = EpicManager(test_db)

        with pytest.raises(ValueError, match="Invalid epic ID"):
            manager.create_epic("Test", "HIGH", epic_id="INVALID")

    def test_create_epic_mismatched_priority(self, test_db: Database):
        """Test creating epic with ID/priority mismatch"""
        manager = EpicManager(test_db)

        with pytest.raises(ValueError, match="does not match"):
            manager.create_epic("Test", "HIGH", epic_id="EPC-C-0001")

    def test_get_epic(self, test_db: Database):
        """Test getting epic by ID"""
        manager = EpicManager(test_db)
        created = manager.create_epic("Test Epic", "HIGH")

        retrieved = manager.get_epic(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == created.title

    def test_get_epic_not_found(self, test_db: Database):
        """Test getting non-existent epic"""
        manager = EpicManager(test_db)
        assert manager.get_epic("EPC-H-9999") is None

    def test_list_epics(self, test_db: Database):
        """Test listing epics"""
        manager = EpicManager(test_db)

        # Create multiple epics
        manager.create_epic("Epic 1", "HIGH")
        manager.create_epic("Epic 2", "MEDIUM")
        manager.create_epic("Epic 3", "CRITICAL")

        epics = manager.list_epics()
        assert len(epics) == 3

    def test_list_epics_by_status(self, test_db: Database):
        """Test listing epics by status"""
        manager = EpicManager(test_db)
        task_manager = TaskManager(test_db)

        # Create epics
        epic1 = manager.create_epic("Epic 1", "HIGH")
        epic2 = manager.create_epic("Epic 2", "MEDIUM")

        # Create task for epic1 to make it UNDERWAY
        task_id = task_manager.generate_task_id("Builder", "HIGH")
        task_manager.create_task(task_id, "Test Task", "Builder", "HIGH")
        manager.link_task(task_id, epic1.id)
        task_manager.update_status(task_id, "UNDERWAY")

        # List by status
        todo_epics = manager.list_epics(status="TODO")
        assert len(todo_epics) == 1
        assert todo_epics[0].id == epic2.id

        underway_epics = manager.list_epics(status="UNDERWAY")
        assert len(underway_epics) == 1
        assert underway_epics[0].id == epic1.id

    def test_list_epics_by_priority(self, test_db: Database):
        """Test listing epics by priority"""
        manager = EpicManager(test_db)

        manager.create_epic("Epic 1", "HIGH")
        manager.create_epic("Epic 2", "MEDIUM")
        manager.create_epic("Epic 3", "HIGH")

        high_epics = manager.list_epics(priority="HIGH")
        assert len(high_epics) == 2

        medium_epics = manager.list_epics(priority="MEDIUM")
        assert len(medium_epics) == 1

    def test_update_epic(self, test_db: Database):
        """Test updating epic fields"""
        manager = EpicManager(test_db)
        epic = manager.create_epic("Original Title", "HIGH", "Original description")

        # Update title
        updated = manager.update_epic(epic.id, title="New Title")
        assert updated.title == "New Title"
        assert updated.description == "Original description"

        # Update description
        updated = manager.update_epic(epic.id, description="New description")
        assert updated.description == "New description"

    def test_update_epic_invalid_field(self, test_db: Database):
        """Test updating with invalid field"""
        manager = EpicManager(test_db)
        epic = manager.create_epic("Test", "HIGH")

        with pytest.raises(ValueError, match="Cannot update field"):
            manager.update_epic(epic.id, status="COMPLETE")

    def test_abort_epic(self, test_db: Database):
        """Test aborting epic and subtasks"""
        manager = EpicManager(test_db)
        task_manager = TaskManager(test_db)

        # Create epic with tasks
        epic = manager.create_epic("Test Epic", "HIGH")

        task1_id = task_manager.generate_task_id("Builder", "HIGH")
        task_manager.create_task(task1_id, "Task 1", "Builder", "HIGH")
        manager.link_task(task1_id, epic.id)

        task2_id = task_manager.generate_task_id("Builder", "MEDIUM")
        task_manager.create_task(task2_id, "Task 2", "Builder", "MEDIUM")
        manager.link_task(task2_id, epic.id)

        # Abort epic
        manager.abort_epic(epic.id, "Test abort reason")

        # Verify epic aborted
        aborted_epic = manager.get_epic(epic.id)
        assert aborted_epic.status == "ABORTED"
        assert aborted_epic.aborted_reason == "Test abort reason"
        assert aborted_epic.aborted_at is not None

        # Verify all tasks aborted
        subtasks = manager.get_subtasks(epic.id)
        assert all(task.status == "ABORTED" for task in subtasks)

    def test_get_subtasks(self, test_db: Database):
        """Test getting epic subtasks"""
        manager = EpicManager(test_db)
        task_manager = TaskManager(test_db)

        epic = manager.create_epic("Test Epic", "HIGH")

        # Create tasks
        task1_id = task_manager.generate_task_id("Builder", "HIGH")
        task_manager.create_task(task1_id, "Task 1", "Builder", "HIGH")
        manager.link_task(task1_id, epic.id)

        task2_id = task_manager.generate_task_id("Tester", "MEDIUM")
        task_manager.create_task(task2_id, "Task 2", "Tester", "MEDIUM")
        manager.link_task(task2_id, epic.id)

        # Get subtasks
        subtasks = manager.get_subtasks(epic.id)
        assert len(subtasks) == 2
        assert all(task.epic_id == epic.id for task in subtasks)

    def test_link_task(self, test_db: Database):
        """Test linking task to epic"""
        manager = EpicManager(test_db)
        task_manager = TaskManager(test_db)

        epic = manager.create_epic("Test Epic", "HIGH")
        task_id = task_manager.generate_task_id("Builder", "HIGH")
        task_manager.create_task(task_id, "Test Task", "Builder", "HIGH")

        # Link task
        manager.link_task(task_id, epic.id)

        # Verify link
        task = task_manager.get_task(task_id)
        assert task.epic_id == epic.id

    def test_link_task_invalid_epic(self, test_db: Database):
        """Test linking task to non-existent epic"""
        manager = EpicManager(test_db)
        task_manager = TaskManager(test_db)

        task_id = task_manager.generate_task_id("Builder", "HIGH")
        task_manager.create_task(task_id, "Test Task", "Builder", "HIGH")

        with pytest.raises(ValueError, match="not found"):
            manager.link_task(task_id, "EPC-H-9999")

    def test_unlink_task(self, test_db: Database):
        """Test unlinking task from epic"""
        manager = EpicManager(test_db)
        task_manager = TaskManager(test_db)

        epic = manager.create_epic("Test Epic", "HIGH")
        task_id = task_manager.generate_task_id("Builder", "HIGH")
        task_manager.create_task(task_id, "Test Task", "Builder", "HIGH")

        # Link then unlink
        manager.link_task(task_id, epic.id)
        manager.unlink_task(task_id)

        # Verify unlinked
        task = task_manager.get_task(task_id)
        assert task.epic_id is None


class TestEpicStatusTriggers:
    """Test epic status auto-update triggers"""

    def test_epic_status_becomes_underway(self, test_db: Database):
        """Test epic status changes to UNDERWAY when task starts"""
        manager = EpicManager(test_db)
        task_manager = TaskManager(test_db)

        epic = manager.create_epic("Test Epic", "HIGH")
        task_id = task_manager.generate_task_id("Builder", "HIGH")
        task_manager.create_task(task_id, "Test Task", "Builder", "HIGH")
        manager.link_task(task_id, epic.id)

        # Update task to UNDERWAY
        task_manager.update_status(task_id, "UNDERWAY")

        # Epic should now be UNDERWAY
        updated_epic = manager.get_epic(epic.id)
        assert updated_epic.status == "UNDERWAY"

    def test_epic_status_becomes_complete(self, test_db: Database):
        """Test epic status changes to COMPLETE when all tasks complete"""
        manager = EpicManager(test_db)
        task_manager = TaskManager(test_db)

        epic = manager.create_epic("Test Epic", "HIGH")

        # Create two tasks
        task1_id = task_manager.generate_task_id("Builder", "HIGH")
        task_manager.create_task(task1_id, "Task 1", "Builder", "HIGH")
        manager.link_task(task1_id, epic.id)

        task2_id = task_manager.generate_task_id("Tester", "MEDIUM")
        task_manager.create_task(task2_id, "Task 2", "Tester", "MEDIUM")
        manager.link_task(task2_id, epic.id)

        # Complete first task
        task_manager.update_status(task1_id, "UNDERWAY")
        task_manager.update_status(task1_id, "COMPLETE")

        # Epic should still be UNDERWAY
        epic_check1 = manager.get_epic(epic.id)
        assert epic_check1.status == "TODO"  # Task 2 is still TODO

        # Complete second task
        task_manager.update_status(task2_id, "UNDERWAY")
        task_manager.update_status(task2_id, "COMPLETE")

        # Epic should now be COMPLETE
        epic_check2 = manager.get_epic(epic.id)
        assert epic_check2.status == "COMPLETE"
        assert epic_check2.completed_at is not None

    def test_epic_status_remains_todo(self, test_db: Database):
        """Test epic status stays TODO when all tasks are TODO"""
        manager = EpicManager(test_db)
        task_manager = TaskManager(test_db)

        epic = manager.create_epic("Test Epic", "HIGH")

        task_id = task_manager.generate_task_id("Builder", "HIGH")
        task_manager.create_task(task_id, "Test Task", "Builder", "HIGH")
        manager.link_task(task_id, epic.id)

        # Epic should remain TODO
        updated_epic = manager.get_epic(epic.id)
        assert updated_epic.status == "TODO"

    def test_aborted_epic_not_auto_updated(self, test_db: Database):
        """Test aborted epic status is not auto-updated by triggers"""
        manager = EpicManager(test_db)
        task_manager = TaskManager(test_db)

        epic = manager.create_epic("Test Epic", "HIGH")
        task_id = task_manager.generate_task_id("Builder", "HIGH")
        task_manager.create_task(task_id, "Test Task", "Builder", "HIGH")
        manager.link_task(task_id, epic.id)

        # Abort epic
        manager.abort_epic(epic.id, "Testing")

        # Try to update task (should not change epic status)
        task_manager.update_status(task_id, "COMPLETE")

        # Epic should still be ABORTED
        epic_check = manager.get_epic(epic.id)
        assert epic_check.status == "ABORTED"


class TestEpicModel:
    """Test Epic model properties"""

    def test_progress_percent(self):
        """Test progress percentage calculation"""
        epic = Epic(
            id="EPC-H-0001",
            title="Test",
            description=None,
            status="UNDERWAY",
            priority="HIGH",
            aborted_reason=None,
            created_at="2026-02-03",
            updated_at="2026-02-03",
            completed_at=None,
            aborted_at=None,
            file_path=".opencode/work/epics/EPC-H-0001.md",
            subtask_count=4,
            completed_count=2,
        )

        assert epic.progress_percent == 50

    def test_progress_percent_zero_tasks(self):
        """Test progress with zero tasks"""
        epic = Epic(
            id="EPC-H-0001",
            title="Test",
            description=None,
            status="TODO",
            priority="HIGH",
            aborted_reason=None,
            created_at="2026-02-03",
            updated_at="2026-02-03",
            completed_at=None,
            aborted_at=None,
            file_path=".opencode/work/epics/EPC-H-0001.md",
            subtask_count=0,
            completed_count=0,
        )

        assert epic.progress_percent == 0

    def test_is_active(self):
        """Test is_active property"""
        epic_todo = Epic(
            id="EPC-H-0001",
            title="Test",
            description=None,
            status="TODO",
            priority="HIGH",
            aborted_reason=None,
            created_at="2026-02-03",
            updated_at="2026-02-03",
            completed_at=None,
            aborted_at=None,
            file_path=".opencode/work/epics/EPC-H-0001.md",
        )
        assert epic_todo.is_active

        epic_underway = Epic(
            id="EPC-H-0002",
            title="Test",
            description=None,
            status="UNDERWAY",
            priority="HIGH",
            aborted_reason=None,
            created_at="2026-02-03",
            updated_at="2026-02-03",
            completed_at=None,
            aborted_at=None,
            file_path=".opencode/work/epics/EPC-H-0002.md",
        )
        assert epic_underway.is_active

    def test_is_closed(self):
        """Test is_closed property"""
        epic_complete = Epic(
            id="EPC-H-0001",
            title="Test",
            description=None,
            status="COMPLETE",
            priority="HIGH",
            aborted_reason=None,
            created_at="2026-02-03",
            updated_at="2026-02-03",
            completed_at="2026-02-03",
            aborted_at=None,
            file_path=".opencode/work/epics/EPC-H-0001.md",
        )
        assert epic_complete.is_closed

        epic_aborted = Epic(
            id="EPC-H-0002",
            title="Test",
            description=None,
            status="ABORTED",
            priority="HIGH",
            aborted_reason="Test",
            created_at="2026-02-03",
            updated_at="2026-02-03",
            completed_at=None,
            aborted_at="2026-02-03",
            file_path=".opencode/work/epics/EPC-H-0002.md",
        )
        assert epic_aborted.is_closed
