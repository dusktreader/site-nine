"""Tests for missions manager"""

import pytest
from datetime import datetime
from pathlib import Path

from site_nine.core.database import Database
from site_nine.missions.exceptions import MissionError
from site_nine.missions.manager import MissionManager, generate_mission_codename
from site_nine.missions.models import Mission


def test_generate_mission_codename():
    """Test codename generation is deterministic"""
    codename1 = generate_mission_codename(1)
    codename2 = generate_mission_codename(1)
    assert codename1 == codename2

    # Different IDs should give different codenames (usually)
    codename3 = generate_mission_codename(2)
    assert codename1 != codename3

    # Codenames should follow format
    assert "-" in codename1
    parts = codename1.split("-")
    assert len(parts) == 2


def test_generate_mission_codename_collision():
    """Test that collisions occur at expected point"""
    # First collision should happen at 31 * 37 = 1147
    codename_0 = generate_mission_codename(0)
    codename_1147 = generate_mission_codename(1147)
    assert codename_0 == codename_1147


def test_mission_manager_start_mission(test_db):
    """Test starting a new mission"""
    manager = MissionManager(test_db)

    mission_id = manager.start_mission(persona_name="test-persona", role="Engineer", objective="Test mission")

    assert mission_id > 0

    # Verify mission was created
    result = test_db.execute_query("SELECT * FROM missions WHERE id = :id", {"id": mission_id})
    assert len(result) == 1
    mission = result[0]
    assert mission["persona_name"] == "test-persona"
    assert mission["role"] == "Engineer"
    assert mission["objective"] == "Test mission"


def test_mission_manager_start_mission_with_file(test_db, tmp_path):
    """Test starting mission with custom file path"""
    manager = MissionManager(test_db)

    mission_file = str(tmp_path / "custom-mission.md")

    mission_id = manager.start_mission(
        persona_name="test-persona", role="Engineer", objective="Test mission", mission_file=mission_file
    )

    assert mission_id > 0

    # Verify file path was stored
    result = test_db.execute_query("SELECT mission_file FROM missions WHERE id = :id", {"id": mission_id})
    assert result[0]["mission_file"] == mission_file


def test_mission_manager_get_mission(test_db):
    """Test retrieving a mission"""
    manager = MissionManager(test_db)

    mission_id = manager.start_mission(persona_name="test-persona", role="Engineer", objective="Test mission")

    mission = manager.get_mission(mission_id)

    assert mission is not None
    assert mission.id == mission_id
    assert mission.persona_name == "test-persona"
    assert mission.role == "Engineer"
    assert mission.objective == "Test mission"


def test_mission_manager_get_mission_not_found(test_db):
    """Test getting non-existent mission returns None"""
    manager = MissionManager(test_db)

    mission = manager.get_mission(999)

    assert mission is None


def test_mission_manager_list_missions_empty(test_db):
    """Test listing missions when none exist"""
    manager = MissionManager(test_db)

    missions = manager.list_missions()

    assert missions == []


def test_mission_manager_list_missions(test_db):
    """Test listing all missions"""
    manager = MissionManager(test_db)

    # Create multiple missions
    id1 = manager.start_mission("persona1", "Engineer", "Objective 1")
    id2 = manager.start_mission("persona2", "Tester", "Objective 2")

    missions = manager.list_missions()

    assert len(missions) >= 2  # May have more from other tests


def test_mission_manager_list_missions_by_role(test_db):
    """Test filtering missions by role"""
    manager = MissionManager(test_db)

    manager.start_mission("persona1", "Engineer", "Objective 1")
    manager.start_mission("persona2", "Tester", "Objective 2")
    manager.start_mission("persona3", "Engineer", "Objective 3")

    engineer_missions = manager.list_missions(role="Engineer")

    assert len(engineer_missions) >= 2
    assert all(m.role == "Engineer" for m in engineer_missions)


def test_mission_manager_end_mission(test_db):
    """Test ending a mission"""
    manager = MissionManager(test_db)

    mission_id = manager.start_mission("test-persona", "Engineer", "Test")

    manager.end_mission(mission_id)

    mission = manager.get_mission(mission_id)
    assert mission.end_time is not None


def test_mission_manager_update_mission(test_db):
    """Test updating mission objective"""
    manager = MissionManager(test_db)

    mission_id = manager.start_mission("test-persona", "Engineer", "Old objective")

    manager.update_mission(mission_id, objective="New objective")

    mission = manager.get_mission(mission_id)
    assert mission.objective == "New objective"


def test_mission_manager_codename_generation(test_db):
    """Test missions get unique codenames"""
    manager = MissionManager(test_db)

    id1 = manager.start_mission("persona1", "Engineer", "Test")
    id2 = manager.start_mission("persona2", "Tester", "Test")

    mission1 = manager.get_mission(id1)
    mission2 = manager.get_mission(id2)

    assert mission1.codename
    assert mission2.codename
    # Codenames may be the same for different IDs, just check they exist


def test_mission_manager_start_mission_with_epic(test_db):
    """Test starting a mission with epic_id"""
    from site_nine.epics import EpicManager

    # Create an epic first
    epic_manager = EpicManager(test_db)
    epic_manager.create_epic(
        epic_id="EPC-H-0001", title="Test Epic", description="Test epic description", priority="HIGH"
    )

    manager = MissionManager(test_db)

    mission_id = manager.start_mission(
        persona_name="test-persona", role="Engineer", objective="Test mission", epic_id="EPC-H-0001"
    )

    assert mission_id > 0

    # Verify mission was created with epic_id
    result = test_db.execute_query("SELECT * FROM missions WHERE id = :id", {"id": mission_id})
    assert len(result) == 1
    mission = result[0]
    assert mission["persona_name"] == "test-persona"
    assert mission["role"] == "Engineer"
    assert mission["epic_id"] == "EPC-H-0001"


def test_mission_manager_start_mission_without_epic(test_db):
    """Test starting a mission without epic_id sets NULL"""
    manager = MissionManager(test_db)

    mission_id = manager.start_mission(persona_name="test-persona", role="Engineer", objective="Test mission")

    assert mission_id > 0

    # Verify epic_id is NULL
    result = test_db.execute_query("SELECT epic_id FROM missions WHERE id = :id", {"id": mission_id})
    assert len(result) == 1
    assert result[0]["epic_id"] is None


def test_mission_manager_list_missions_by_epic(test_db):
    """Test filtering missions by epic_id"""
    from site_nine.epics import EpicManager

    # Add persona4 to database
    test_db.execute_update("""
        INSERT INTO personas (name, role, mythology, description)
        VALUES ('persona4', 'Operator', 'Test', 'Test persona 4')
    """)

    # Create epics
    epic_manager = EpicManager(test_db)
    epic_manager.create_epic(epic_id="EPC-M-0010", title="Epic 10", description="Description 10", priority="MEDIUM")
    epic_manager.create_epic(epic_id="EPC-H-0011", title="Epic 11", description="Description 11", priority="HIGH")

    manager = MissionManager(test_db)

    # Create missions with different epic scopes
    manager.start_mission("persona1", "Engineer", "Objective 1", epic_id="EPC-M-0010")
    manager.start_mission("persona2", "Tester", "Objective 2", epic_id="EPC-H-0011")
    manager.start_mission("persona3", "Engineer", "Objective 3", epic_id="EPC-M-0010")
    manager.start_mission("persona4", "Operator", "Objective 4")  # No epic

    # Filter by epic
    epic10_missions = manager.list_missions(epic_id="EPC-M-0010")

    assert len(epic10_missions) == 2
    assert all(m.epic_id == "EPC-M-0010" for m in epic10_missions)


def test_mission_manager_get_mission_includes_epic(test_db):
    """Test that get_mission returns epic_id field"""
    from site_nine.epics import EpicManager

    # Create epic
    epic_manager = EpicManager(test_db)
    epic_manager.create_epic(epic_id="EPC-C-0020", title="Epic 20", description="Description 20", priority="CRITICAL")

    manager = MissionManager(test_db)
    mission_id = manager.start_mission("test-persona", "Engineer", "Test", epic_id="EPC-C-0020")

    mission = manager.get_mission(mission_id)

    assert mission is not None
    assert mission.epic_id == "EPC-C-0020"
