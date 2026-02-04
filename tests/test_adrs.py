"""Tests for ADR management"""

import pytest
from pathlib import Path
from site_nine.adrs.manager import ADRManager
from site_nine.adrs.models import ArchitectureDoc
from site_nine.core.database import Database
from site_nine.epics.manager import EpicManager
from site_nine.tasks.manager import TaskManager


class TestADRManager:
    """Test ADR manager operations"""

    def test_create_adr(self, test_db: Database):
        """Test creating an ADR"""
        manager = ADRManager(test_db)
        adr = manager.create_adr(
            adr_id="ADR-001", title="Test ADR", file_path=".opencode/docs/adrs/ADR-001-test-adr.md", status="PROPOSED"
        )

        assert adr.id == "ADR-001"
        assert adr.title == "Test ADR"
        assert adr.status == "PROPOSED"
        assert adr.file_path == ".opencode/docs/adrs/ADR-001-test-adr.md"
        assert adr.created_at is not None
        assert adr.updated_at is not None

    def test_create_adr_default_status(self, test_db: Database):
        """Test creating ADR with default status"""
        manager = ADRManager(test_db)
        adr = manager.create_adr(
            adr_id="ADR-001", title="Test ADR", file_path=".opencode/docs/adrs/ADR-001-test-adr.md"
        )

        assert adr.status == "PROPOSED"

    def test_get_adr(self, test_db: Database):
        """Test getting an ADR by ID"""
        manager = ADRManager(test_db)
        manager.create_adr(adr_id="ADR-001", title="Test ADR", file_path=".opencode/docs/adrs/ADR-001-test-adr.md")

        adr = manager.get_adr("ADR-001")
        assert adr is not None
        assert adr.id == "ADR-001"
        assert adr.title == "Test ADR"

    def test_get_nonexistent_adr(self, test_db: Database):
        """Test getting ADR that doesn't exist"""
        manager = ADRManager(test_db)
        adr = manager.get_adr("ADR-999")
        assert adr is None

    def test_list_adrs(self, test_db: Database):
        """Test listing all ADRs"""
        manager = ADRManager(test_db)

        manager.create_adr("ADR-001", "First ADR", ".opencode/docs/adrs/ADR-001.md", "PROPOSED")
        manager.create_adr("ADR-002", "Second ADR", ".opencode/docs/adrs/ADR-002.md", "ACCEPTED")
        manager.create_adr("ADR-003", "Third ADR", ".opencode/docs/adrs/ADR-003.md", "REJECTED")

        adrs = manager.list_adrs()
        assert len(adrs) == 3
        assert adrs[0].id == "ADR-001"
        assert adrs[1].id == "ADR-002"
        assert adrs[2].id == "ADR-003"

    def test_list_adrs_by_status(self, test_db: Database):
        """Test listing ADRs filtered by status"""
        manager = ADRManager(test_db)

        manager.create_adr("ADR-001", "First ADR", ".opencode/docs/adrs/ADR-001.md", "PROPOSED")
        manager.create_adr("ADR-002", "Second ADR", ".opencode/docs/adrs/ADR-002.md", "ACCEPTED")
        manager.create_adr("ADR-003", "Third ADR", ".opencode/docs/adrs/ADR-003.md", "ACCEPTED")

        accepted = manager.list_adrs(status="ACCEPTED")
        assert len(accepted) == 2
        assert all(adr.status == "ACCEPTED" for adr in accepted)

        proposed = manager.list_adrs(status="PROPOSED")
        assert len(proposed) == 1
        assert proposed[0].status == "PROPOSED"

    def test_update_adr_title(self, test_db: Database):
        """Test updating ADR title"""
        manager = ADRManager(test_db)
        manager.create_adr("ADR-001", "Original Title", ".opencode/docs/adrs/ADR-001.md")

        updated = manager.update_adr("ADR-001", title="Updated Title")
        assert updated.title == "Updated Title"

        retrieved = manager.get_adr("ADR-001")
        assert retrieved.title == "Updated Title"

    def test_update_adr_status(self, test_db: Database):
        """Test updating ADR status"""
        manager = ADRManager(test_db)
        manager.create_adr("ADR-001", "Test ADR", ".opencode/docs/adrs/ADR-001.md", "PROPOSED")

        updated = manager.update_adr("ADR-001", status="ACCEPTED")
        assert updated.status == "ACCEPTED"

        retrieved = manager.get_adr("ADR-001")
        assert retrieved.status == "ACCEPTED"

    def test_update_adr_multiple_fields(self, test_db: Database):
        """Test updating multiple ADR fields"""
        manager = ADRManager(test_db)
        manager.create_adr("ADR-001", "Original", ".opencode/docs/adrs/ADR-001.md", "PROPOSED")

        updated = manager.update_adr("ADR-001", title="New Title", status="ACCEPTED")
        assert updated.title == "New Title"
        assert updated.status == "ACCEPTED"

    def test_update_adr_no_fields_raises_error(self, test_db: Database):
        """Test that updating with no fields raises error"""
        manager = ADRManager(test_db)
        manager.create_adr("ADR-001", "Test", ".opencode/docs/adrs/ADR-001.md")

        with pytest.raises(ValueError, match="No fields to update"):
            manager.update_adr("ADR-001")

    def test_update_adr_invalid_field_raises_error(self, test_db: Database):
        """Test that updating invalid field raises error"""
        manager = ADRManager(test_db)
        manager.create_adr("ADR-001", "Test", ".opencode/docs/adrs/ADR-001.md")

        with pytest.raises(ValueError, match="Cannot update field"):
            manager.update_adr("ADR-001", invalid_field="value")


class TestADREpicLinking:
    """Test ADR to Epic linking functionality"""

    def test_link_adr_to_epic(self, test_db: Database):
        """Test linking an ADR to an epic"""
        adr_manager = ADRManager(test_db)
        epic_manager = EpicManager(test_db)

        # Create ADR and epic
        adr_manager.create_adr("ADR-001", "Test ADR", ".opencode/docs/adrs/ADR-001.md")
        epic_manager.create_epic("Test Epic", "HIGH")

        # Link them
        adr_manager.link_to_epic("ADR-001", "EPC-H-0001")

        # Verify link
        epic_adrs = adr_manager.get_epic_adrs("EPC-H-0001")
        assert len(epic_adrs) == 1
        assert epic_adrs[0].id == "ADR-001"

    def test_link_multiple_adrs_to_epic(self, test_db: Database):
        """Test linking multiple ADRs to one epic"""
        adr_manager = ADRManager(test_db)
        epic_manager = EpicManager(test_db)

        adr_manager.create_adr("ADR-001", "First ADR", ".opencode/docs/adrs/ADR-001.md")
        adr_manager.create_adr("ADR-002", "Second ADR", ".opencode/docs/adrs/ADR-002.md")
        epic_manager.create_epic("Test Epic", "HIGH")

        adr_manager.link_to_epic("ADR-001", "EPC-H-0001")
        adr_manager.link_to_epic("ADR-002", "EPC-H-0001")

        epic_adrs = adr_manager.get_epic_adrs("EPC-H-0001")
        assert len(epic_adrs) == 2
        assert {adr.id for adr in epic_adrs} == {"ADR-001", "ADR-002"}

    def test_link_adr_to_nonexistent_epic_raises_error(self, test_db: Database):
        """Test linking ADR to non-existent epic"""
        adr_manager = ADRManager(test_db)
        adr_manager.create_adr("ADR-001", "Test ADR", ".opencode/docs/adrs/ADR-001.md")

        # Should not raise error (foreign key constraint handled by database)
        # But we can verify the ADR exists
        with pytest.raises(ValueError, match="ADR ADR-999 not found"):
            adr_manager.link_to_epic("ADR-999", "EPC-H-0001")

    def test_link_duplicate_ignores(self, test_db: Database):
        """Test that linking same ADR to epic twice is idempotent"""
        adr_manager = ADRManager(test_db)
        epic_manager = EpicManager(test_db)

        adr_manager.create_adr("ADR-001", "Test ADR", ".opencode/docs/adrs/ADR-001.md")
        epic_manager.create_epic("Test Epic", "HIGH")

        # Link twice
        adr_manager.link_to_epic("ADR-001", "EPC-H-0001")
        adr_manager.link_to_epic("ADR-001", "EPC-H-0001")

        # Should still have only one link
        epic_adrs = adr_manager.get_epic_adrs("EPC-H-0001")
        assert len(epic_adrs) == 1

    def test_unlink_adr_from_epic(self, test_db: Database):
        """Test unlinking an ADR from an epic"""
        adr_manager = ADRManager(test_db)
        epic_manager = EpicManager(test_db)

        adr_manager.create_adr("ADR-001", "Test ADR", ".opencode/docs/adrs/ADR-001.md")
        epic_manager.create_epic("Test Epic", "HIGH")

        adr_manager.link_to_epic("ADR-001", "EPC-H-0001")
        adr_manager.unlink_from_epic("ADR-001", "EPC-H-0001")

        epic_adrs = adr_manager.get_epic_adrs("EPC-H-0001")
        assert len(epic_adrs) == 0

    def test_get_adr_epics(self, test_db: Database):
        """Test getting all epics linked to an ADR"""
        adr_manager = ADRManager(test_db)
        epic_manager = EpicManager(test_db)

        adr_manager.create_adr("ADR-001", "Test ADR", ".opencode/docs/adrs/ADR-001.md")
        epic_manager.create_epic("Epic 1", "HIGH")
        epic_manager.create_epic("Epic 2", "MEDIUM")

        adr_manager.link_to_epic("ADR-001", "EPC-H-0001")
        adr_manager.link_to_epic("ADR-001", "EPC-M-0002")

        epic_ids = adr_manager.get_adr_epics("ADR-001")
        assert len(epic_ids) == 2
        assert set(epic_ids) == {"EPC-H-0001", "EPC-M-0002"}


class TestADRTaskLinking:
    """Test ADR to Task linking functionality"""

    def test_link_adr_to_task(self, test_db: Database):
        """Test linking an ADR to a task"""
        adr_manager = ADRManager(test_db)
        task_manager = TaskManager(test_db)

        adr_manager.create_adr("ADR-001", "Test ADR", ".opencode/docs/adrs/ADR-001.md")
        task_manager.create_task("OPR-H-0001", "Test Task", "Operator", "HIGH", description="Test objective")

        adr_manager.link_to_task("ADR-001", "OPR-H-0001")

        task_adrs = adr_manager.get_task_adrs("OPR-H-0001")
        assert len(task_adrs) == 1
        assert task_adrs[0].id == "ADR-001"

    def test_link_multiple_adrs_to_task(self, test_db: Database):
        """Test linking multiple ADRs to one task"""
        adr_manager = ADRManager(test_db)
        task_manager = TaskManager(test_db)

        adr_manager.create_adr("ADR-001", "First ADR", ".opencode/docs/adrs/ADR-001.md")
        adr_manager.create_adr("ADR-002", "Second ADR", ".opencode/docs/adrs/ADR-002.md")
        task_manager.create_task("OPR-H-0001", "Test Task", "Operator", "HIGH", description="Test objective")

        adr_manager.link_to_task("ADR-001", "OPR-H-0001")
        adr_manager.link_to_task("ADR-002", "OPR-H-0001")

        task_adrs = adr_manager.get_task_adrs("OPR-H-0001")
        assert len(task_adrs) == 2
        assert {adr.id for adr in task_adrs} == {"ADR-001", "ADR-002"}

    def test_link_adr_to_nonexistent_task(self, test_db: Database):
        """Test linking ADR to non-existent task"""
        adr_manager = ADRManager(test_db)
        adr_manager.create_adr("ADR-001", "Test ADR", ".opencode/docs/adrs/ADR-001.md")

        with pytest.raises(ValueError, match="ADR ADR-999 not found"):
            adr_manager.link_to_task("ADR-999", "OPR-H-0001")

    def test_unlink_adr_from_task(self, test_db: Database):
        """Test unlinking an ADR from a task"""
        adr_manager = ADRManager(test_db)
        task_manager = TaskManager(test_db)

        adr_manager.create_adr("ADR-001", "Test ADR", ".opencode/docs/adrs/ADR-001.md")
        task_manager.create_task("OPR-H-0001", "Test Task", "Operator", "HIGH", description="Test objective")

        adr_manager.link_to_task("ADR-001", "OPR-H-0001")
        adr_manager.unlink_from_task("ADR-001", "OPR-H-0001")

        task_adrs = adr_manager.get_task_adrs("OPR-H-0001")
        assert len(task_adrs) == 0

    def test_get_adr_tasks(self, test_db: Database):
        """Test getting all tasks linked to an ADR"""
        adr_manager = ADRManager(test_db)
        task_manager = TaskManager(test_db)

        adr_manager.create_adr("ADR-001", "Test ADR", ".opencode/docs/adrs/ADR-001.md")
        task_manager.create_task("OPR-H-0001", "Task 1", "Operator", "HIGH", description="Objective 1")
        task_manager.create_task("OPR-M-0002", "Task 2", "Operator", "MEDIUM", description="Objective 2")

        adr_manager.link_to_task("ADR-001", "OPR-H-0001")
        adr_manager.link_to_task("ADR-001", "OPR-M-0002")

        task_ids = adr_manager.get_adr_tasks("ADR-001")
        assert len(task_ids) == 2
        assert set(task_ids) == {"OPR-H-0001", "OPR-M-0002"}


class TestADRModel:
    """Test ADR model properties"""

    def test_adr_model_creation(self):
        """Test creating an ADR model instance"""
        adr = ArchitectureDoc(
            id="ADR-001",
            title="Test ADR",
            status="PROPOSED",
            file_path=".opencode/docs/adrs/ADR-001.md",
            created_at="2026-02-04 10:00:00",
            updated_at="2026-02-04 10:00:00",
        )

        assert adr.id == "ADR-001"
        assert adr.title == "Test ADR"
        assert adr.status == "PROPOSED"
        assert adr.file_path == ".opencode/docs/adrs/ADR-001.md"
        assert adr.created_at == "2026-02-04 10:00:00"
        assert adr.updated_at == "2026-02-04 10:00:00"


class TestADRCascadeDelete:
    """Test cascade deletion behavior"""

    def test_delete_epic_removes_adr_links(self, test_db: Database):
        """Test that deleting an epic removes its ADR links"""
        adr_manager = ADRManager(test_db)
        epic_manager = EpicManager(test_db)

        adr_manager.create_adr("ADR-001", "Test ADR", ".opencode/docs/adrs/ADR-001.md")
        epic_manager.create_epic("Test Epic", "HIGH")
        adr_manager.link_to_epic("ADR-001", "EPC-H-0001")

        # Delete epic
        test_db.execute_update("DELETE FROM epics WHERE id = 'EPC-H-0001'")

        # ADR should still exist
        adr = adr_manager.get_adr("ADR-001")
        assert adr is not None

        # But link should be gone
        epic_ids = adr_manager.get_adr_epics("ADR-001")
        assert len(epic_ids) == 0

    def test_delete_task_removes_adr_links(self, test_db: Database):
        """Test that deleting a task removes its ADR links"""
        adr_manager = ADRManager(test_db)
        task_manager = TaskManager(test_db)

        adr_manager.create_adr("ADR-001", "Test ADR", ".opencode/docs/adrs/ADR-001.md")
        task_manager.create_task("OPR-H-0001", "Test Task", "Operator", "HIGH", description="Objective")
        adr_manager.link_to_task("ADR-001", "OPR-H-0001")

        # Delete task
        test_db.execute_update("DELETE FROM tasks WHERE id = 'OPR-H-0001'")

        # ADR should still exist
        adr = adr_manager.get_adr("ADR-001")
        assert adr is not None

        # But link should be gone
        task_ids = adr_manager.get_adr_tasks("ADR-001")
        assert len(task_ids) == 0

    def test_delete_adr_removes_all_links(self, test_db: Database):
        """Test that deleting an ADR removes all its links"""
        adr_manager = ADRManager(test_db)
        epic_manager = EpicManager(test_db)
        task_manager = TaskManager(test_db)

        adr_manager.create_adr("ADR-001", "Test ADR", ".opencode/docs/adrs/ADR-001.md")
        epic_manager.create_epic("Test Epic", "HIGH")
        task_manager.create_task("OPR-H-0001", "Test Task", "Operator", "HIGH", description="Objective")

        adr_manager.link_to_epic("ADR-001", "EPC-H-0001")
        adr_manager.link_to_task("ADR-001", "OPR-H-0001")

        # Delete ADR
        test_db.execute_update("DELETE FROM architecture_docs WHERE id = 'ADR-001'")

        # Epic and task should still exist
        epic = epic_manager.get_epic("EPC-H-0001")
        task = task_manager.get_task("OPR-H-0001")
        assert epic is not None
        assert task is not None

        # But links should be gone
        epic_adrs = adr_manager.get_epic_adrs("EPC-H-0001")
        task_adrs = adr_manager.get_task_adrs("OPR-H-0001")
        assert len(epic_adrs) == 0
        assert len(task_adrs) == 0
