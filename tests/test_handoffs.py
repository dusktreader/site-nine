"""Tests for handoffs manager"""

import json

import pytest

from site_nine.handoffs.exceptions import HandoffError
from site_nine.handoffs.manager import HandoffManager
from site_nine.handoffs.models import Handoff


def test_handoff_manager_create_handoff_basic(test_db_with_data):
    """Test creating a basic handoff"""
    manager = HandoffManager(test_db_with_data)

    handoff_id = manager.create_handoff(
        task_id="ENG-M-0001", from_mission_id=1, to_role="Tester", summary="Ready for testing"
    )

    assert handoff_id > 0

    # Verify handoff was created
    result = test_db_with_data.execute_query("SELECT * FROM handoffs WHERE id = :id", {"id": handoff_id})
    assert len(result) == 1
    handoff = result[0]
    assert handoff["task_id"] == "ENG-M-0001"
    assert handoff["from_mission_id"] == 1
    assert handoff["to_role"] == "Tester"
    assert handoff["summary"] == "Ready for testing"


def test_handoff_manager_create_handoff_with_files(test_db_with_data):
    """Test creating handoff with file list"""
    manager = HandoffManager(test_db_with_data)

    files = ["src/main.py", "tests/test_main.py"]
    handoff_id = manager.create_handoff(
        task_id="ENG-M-0001", from_mission_id=1, to_role="Tester", summary="Ready for testing", files=files
    )

    handoff = manager.get_handoff(handoff_id)
    assert handoff is not None
    assert json.loads(handoff.files) == files


def test_handoff_manager_create_handoff_with_criteria(test_db_with_data):
    """Test creating handoff with acceptance criteria"""
    manager = HandoffManager(test_db_with_data)

    criteria = "All tests passing, no regressions"
    handoff_id = manager.create_handoff(
        task_id="ENG-M-0001",
        from_mission_id=1,
        to_role="Tester",
        summary="Ready for testing",
        acceptance_criteria=criteria,
    )

    handoff = manager.get_handoff(handoff_id)
    assert handoff.acceptance_criteria == criteria


def test_handoff_manager_create_handoff_with_notes(test_db_with_data):
    """Test creating handoff with additional notes"""
    manager = HandoffManager(test_db_with_data)

    notes = "Watch out for edge case with empty input"
    handoff_id = manager.create_handoff(
        task_id="ENG-M-0001", from_mission_id=1, to_role="Tester", summary="Ready for testing", notes=notes
    )

    handoff = manager.get_handoff(handoff_id)
    assert handoff.notes == notes


def test_handoff_manager_get_handoff(test_db_with_data):
    """Test retrieving a handoff by ID"""
    manager = HandoffManager(test_db_with_data)

    handoff_id = manager.create_handoff(
        task_id="ENG-M-0001", from_mission_id=1, to_role="Tester", summary="Ready for testing"
    )

    handoff = manager.get_handoff(handoff_id)

    assert handoff is not None
    assert handoff.id == handoff_id
    assert handoff.task_id == "ENG-M-0001"
    assert handoff.to_role == "Tester"


def test_handoff_manager_get_handoff_not_found(test_db_with_data):
    """Test getting non-existent handoff returns None"""
    manager = HandoffManager(test_db_with_data)

    handoff = manager.get_handoff(999)

    assert handoff is None


def test_handoff_manager_list_handoffs_empty(test_db_with_data):
    """Test listing handoffs when none exist"""
    manager = HandoffManager(test_db_with_data)

    handoffs = manager.list_handoffs()

    assert handoffs == []


def test_handoff_manager_list_handoffs(test_db_with_data):
    """Test listing all handoffs"""
    manager = HandoffManager(test_db_with_data)

    id1 = manager.create_handoff("ENG-M-0001", 1, "Tester", "Test 1")
    id2 = manager.create_handoff("ENG-M-0002", 1, "Tester", "Test 2")

    handoffs = manager.list_handoffs()

    assert len(handoffs) == 2
    # Verify both handoffs are present (order may vary with same timestamp)
    handoff_ids = {h.id for h in handoffs}
    assert handoff_ids == {id1, id2}


def test_handoff_manager_list_handoffs_by_role(test_db_with_data):
    """Test filtering handoffs by target role"""
    manager = HandoffManager(test_db_with_data)

    manager.create_handoff("ENG-M-0001", 1, "Tester", "For testing")
    manager.create_handoff("ENG-M-0002", 1, "Inspector", "For review")
    manager.create_handoff("ENG-M-0003", 1, "Tester", "More testing")

    tester_handoffs = manager.list_handoffs(to_role="Tester")

    assert len(tester_handoffs) == 2
    assert all(h.to_role == "Tester" for h in tester_handoffs)


def test_handoff_manager_list_handoffs_by_mission(test_db_with_data):
    """Test filtering handoffs by source mission"""
    manager = HandoffManager(test_db_with_data)

    manager.create_handoff("ENG-M-0001", 1, "Tester", "From mission 1")
    manager.create_handoff("ENG-M-0002", 2, "Tester", "From mission 2")
    manager.create_handoff("ENG-M-0003", 1, "Tester", "Also from mission 1")

    mission1_handoffs = manager.list_handoffs(from_mission_id=1)

    assert len(mission1_handoffs) == 2
    assert all(h.from_mission_id == 1 for h in mission1_handoffs)


def test_handoff_manager_delete_handoff(test_db_with_data):
    """Test soft-deleting a handoff"""
    manager = HandoffManager(test_db_with_data)

    handoff_id = manager.create_handoff("ENG-M-0001", 1, "Tester", "Test")

    manager.delete_handoff(handoff_id)

    # Should not appear in default list
    handoffs = manager.list_handoffs()
    assert len(handoffs) == 0

    # But should appear when including deleted
    all_handoffs = manager.list_handoffs(include_deleted=True)
    assert len(all_handoffs) == 1
    assert all_handoffs[0].deleted_at is not None


def test_handoff_manager_delete_handoff_idempotent(test_db_with_data):
    """Test deleting already deleted handoff is safe"""
    manager = HandoffManager(test_db_with_data)

    handoff_id = manager.create_handoff("ENG-M-0001", 1, "Tester", "Test")

    manager.delete_handoff(handoff_id)
    manager.delete_handoff(handoff_id)  # Should not error

    all_handoffs = manager.list_handoffs(include_deleted=True)
    assert len(all_handoffs) == 1


def test_handoff_manager_get_pending_handoffs_for_role(test_db_with_data):
    """Test getting pending handoffs for a specific role"""
    manager = HandoffManager(test_db_with_data)

    id1 = manager.create_handoff("ENG-M-0001", 1, "Tester", "Test 1")
    manager.create_handoff("ENG-M-0002", 1, "Inspector", "Review")
    id3 = manager.create_handoff("ENG-M-0003", 1, "Tester", "Test 2")

    # Delete one tester handoff
    manager.delete_handoff(id1)

    pending = manager.get_pending_handoffs_for_role("Tester")

    assert len(pending) == 1
    assert pending[0].id == id3


def test_handoff_manager_list_excludes_deleted_by_default(test_db_with_data):
    """Test that deleted handoffs are excluded by default"""
    manager = HandoffManager(test_db_with_data)

    id1 = manager.create_handoff("ENG-M-0001", 1, "Tester", "Test 1")
    manager.create_handoff("ENG-M-0002", 1, "Tester", "Test 2")

    manager.delete_handoff(id1)

    # Default should exclude deleted
    handoffs = manager.list_handoffs()
    assert len(handoffs) == 1
    assert handoffs[0].id != id1


def test_handoff_manager_combined_filters(test_db_with_data):
    """Test using multiple filters together"""
    manager = HandoffManager(test_db_with_data)

    manager.create_handoff("ENG-M-0001", 1, "Tester", "Mission 1 to tester")
    manager.create_handoff("ENG-M-0002", 1, "Inspector", "Mission 1 to inspector")
    manager.create_handoff("ENG-M-0003", 2, "Tester", "Mission 2 to tester")

    # Filter by both mission and role
    handoffs = manager.list_handoffs(to_role="Tester", from_mission_id=1)

    assert len(handoffs) == 1
    assert handoffs[0].task_id == "ENG-M-0001"
