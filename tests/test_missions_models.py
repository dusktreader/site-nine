"""Tests for missions.models module"""

import pendulum

from site_nine.missions.models import Mission
from site_nine.missions.types import MissionStatus


def test_mission_from_db_row():
    """Test creating Mission from database row"""
    row = {
        "id": 1,
        "persona_name": "atlas",
        "role": "Operator",
        "codename": "swift-falcon",
        "mission_file": ".opencode/work/missions/001-swift-falcon.md",
        "start_date": "2024-01-15",
        "start_time": "10:30:00",
        "end_time": "11:45:00",
        "objective": "Test mission",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T11:45:00Z",
    }

    mission = Mission.from_db_row(row)

    assert mission.id == 1
    assert mission.persona_name == "atlas"
    assert mission.role == "Operator"
    assert mission.codename == "swift-falcon"
    assert mission.mission_file == ".opencode/work/missions/001-swift-falcon.md"
    assert mission.start_date == "2024-01-15"
    assert mission.start_time == "10:30:00"
    assert mission.end_time == "11:45:00"
    assert mission.objective == "Test mission"
    assert isinstance(mission.created_at, pendulum.DateTime)
    assert isinstance(mission.updated_at, pendulum.DateTime)


def test_mission_from_db_row_no_end_time():
    """Test creating Mission from database row without end time"""
    row = {
        "id": 2,
        "persona_name": "kuk",
        "role": "Engineer",
        "codename": "bold-dragon",
        "mission_file": ".opencode/work/missions/002-bold-dragon.md",
        "start_date": "2024-01-16",
        "start_time": "09:00:00",
        "end_time": None,
        "objective": "Active mission",
        "created_at": "2024-01-16T09:00:00Z",
        "updated_at": "2024-01-16T09:00:00Z",
    }

    mission = Mission.from_db_row(row)

    assert mission.id == 2
    assert mission.end_time is None


def test_mission_dataclass_creation():
    """Test creating Mission directly"""
    created_at = pendulum.parse("2024-01-15T10:30:00Z")
    updated_at = pendulum.parse("2024-01-15T11:45:00Z")

    mission = Mission(
        id=1,
        persona_name="atlas",
        role="Operator",
        codename="swift-falcon",
        mission_file=".opencode/work/missions/001-swift-falcon.md",
        start_date="2024-01-15",
        start_time="10:30:00",
        end_time="11:45:00",
        objective="Test mission",
        status=MissionStatus.ENDED,
        last_active_at=updated_at,
        epic_id=None,
        desk_mode_active=False,
        created_at=created_at,
        updated_at=updated_at,
    )

    assert mission.id == 1
    assert mission.persona_name == "atlas"
    assert mission.role == "Operator"
    assert mission.status == MissionStatus.ENDED
    assert mission.last_active_at == updated_at


def test_mission_none_id():
    """Test creating Mission with None id"""
    created_at = pendulum.parse("2024-01-15T10:30:00Z")
    updated_at = pendulum.parse("2024-01-15T11:45:00Z")

    mission = Mission(
        id=None,
        persona_name="test",
        role="Tester",
        codename="test-mission",
        mission_file=".opencode/work/missions/test.md",
        start_date="2024-01-15",
        start_time="10:30:00",
        end_time=None,
        objective="Test",
        status=MissionStatus.ACTIVE,
        last_active_at=None,
        epic_id=None,
        desk_mode_active=False,
        created_at=created_at,
        updated_at=updated_at,
    )

    assert mission.id is None
    assert mission.status == MissionStatus.ACTIVE
    assert mission.last_active_at is None
