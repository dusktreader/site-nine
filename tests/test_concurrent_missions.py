"""Test concurrent mission starts with atomic persona claiming"""

import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed
from site_nine.missions.manager import MissionManager
from site_nine.personas.manager import PersonaManager


def test_concurrent_mission_start_no_race(test_db):
    """Test that concurrent mission starts don't assign the same persona"""
    mission_manager = MissionManager(test_db)
    persona_manager = PersonaManager(test_db)

    # Clear existing personas and add 3 fresh test personas for Engineer role
    test_db.execute_update("DELETE FROM personas WHERE role = 'Engineer'")
    persona_manager.add_persona("test-eng-1", "Engineer", "Test", "Test persona 1")
    persona_manager.add_persona("test-eng-2", "Engineer", "Test", "Test persona 2")
    persona_manager.add_persona("test-eng-3", "Engineer", "Test", "Test persona 3")

    # Start 3 missions concurrently without specifying persona names
    def start_mission(i):
        return mission_manager.start_mission(
            role="Engineer",
            objective=f"Test mission {i}",
            persona_name=None,  # Auto-claim
        )

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(start_mission, i) for i in range(3)]
        mission_ids = [future.result() for future in as_completed(futures)]

    # Verify all missions were created
    assert len(mission_ids) == 3
    assert len(set(mission_ids)) == 3  # All unique

    # Verify each mission has a different persona
    personas_used = []
    for mission_id in mission_ids:
        mission = mission_manager.get_mission(mission_id)
        assert mission is not None
        personas_used.append(mission.persona_name)

    # All personas should be different (no race condition)
    assert len(set(personas_used)) == 3, f"Race condition detected! Personas used: {personas_used}"

    # Verify all test personas were used
    assert set(personas_used) == {"test-eng-1", "test-eng-2", "test-eng-3"}


def test_auto_claim_uses_least_used_persona(test_db):
    """Test that auto-claim selects the least-used persona"""
    mission_manager = MissionManager(test_db)
    persona_manager = PersonaManager(test_db)

    # Clear existing personas and add 3 test personas for Engineer role
    test_db.execute_update("DELETE FROM personas WHERE role = 'Engineer'")
    persona_manager.add_persona("eng-a", "Engineer", "Test", "Persona A")
    persona_manager.add_persona("eng-b", "Engineer", "Test", "Persona B")
    persona_manager.add_persona("eng-c", "Engineer", "Test", "Persona C")

    # Start first mission - should get eng-a (all have 0 usage, alphabetically first)
    mission1_id = mission_manager.start_mission(role="Engineer", objective="Test 1", persona_name=None)
    mission1 = mission_manager.get_mission(mission1_id)
    assert mission1.persona_name == "eng-a"

    # Start second mission - should get eng-b
    mission2_id = mission_manager.start_mission(role="Engineer", objective="Test 2", persona_name=None)
    mission2 = mission_manager.get_mission(mission2_id)
    assert mission2.persona_name == "eng-b"

    # End first mission
    mission_manager.end_mission(mission1_id)

    # Start third mission - should get eng-c (not eng-a, even though a is ended)
    # because eng-c has 0 usage
    mission3_id = mission_manager.start_mission(role="Engineer", objective="Test 3", persona_name=None)
    mission3 = mission_manager.get_mission(mission3_id)
    assert mission3.persona_name == "eng-c"

    # Start fourth mission - should cycle back to eng-a (LRU with count=1)
    mission4_id = mission_manager.start_mission(role="Engineer", objective="Test 4", persona_name=None)
    mission4 = mission_manager.get_mission(mission4_id)
    assert mission4.persona_name == "eng-a"


def test_manual_persona_selection_still_works(test_db):
    """Test that manual persona selection still works alongside auto-claim"""
    mission_manager = MissionManager(test_db)
    persona_manager = PersonaManager(test_db)

    # Add test persona
    persona_manager.add_persona("specific-eng", "Engineer", "Test", "Specific Engineer")

    # Start mission with explicit persona
    mission_id = mission_manager.start_mission(role="Engineer", objective="Test mission", persona_name="specific-eng")

    mission = mission_manager.get_mission(mission_id)
    assert mission.persona_name == "specific-eng"
