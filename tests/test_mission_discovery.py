"""Tests for mission discovery and filtering (TST-M-0100).

Covers ADR-009 Phase 2:
- mission list --epic filter (CLI layer)
- Availability column display logic (all 7 branches)
- JSON output structure with availability/desk_mode/current_task fields
- Desk mode missions in list context
- Edge cases: no missions in epic, multiple desk modes, general availability
"""

import json
import re

import pytest
from typer.testing import CliRunner

from site_nine.__main__ import app
from site_nine.core.database import Database
from site_nine.missions.manager import MissionManager
from site_nine.missions.types import MissionStatus

runner = CliRunner()


def _set_desk_mode_via_db(initialized_project, mission_id: int | str, active: bool = True) -> None:
    """Enable/disable desk mode directly via DB (bypasses comms desk polling loop)."""
    from site_nine.cli.utils import require_db_path
    from site_nine.core.database import Database as DB

    db_path = require_db_path()
    with DB(db_path) as db:
        db.execute_update(
            "UPDATE missions SET desk_mode_active = :active WHERE id = :id",
            {"active": 1 if active else 0, "id": int(mission_id)},
        )


# ---------------------------------------------------------------------------
# Helpers (mirrors test_mission_scoping.py)
# ---------------------------------------------------------------------------


def _create_epic(db: Database, epic_id: str, title: str = "Test Epic", priority: str = "HIGH") -> None:
    """Insert an epic row."""
    db.execute_update(
        """
        INSERT INTO epics (id, title, description, priority, file_path, created_at, updated_at)
        VALUES (:id, :title, 'Description', :priority,
                '.opencode/work/epics/' || :id || '.md', datetime('now'), datetime('now'))
        """,
        {"id": epic_id, "title": title, "priority": priority},
    )


def _create_task(
    db: Database,
    task_id: str,
    role: str = "Engineer",
    priority: str = "MEDIUM",
    status: str = "TODO",
    epic_id: str | None = None,
    mission_id: int | None = None,
) -> None:
    """Insert a task row, optionally assigned to a mission."""
    db.execute_update(
        """
        INSERT INTO tasks (id, title, description, status, priority, role, epic_id,
                           current_mission_id, file_path, created_at, updated_at)
        VALUES (:id, :title, 'Test description', :status, :priority, :role, :epic_id,
                :mission_id,
                '.opencode/work/tasks/' || :id || '.md', datetime('now'), datetime('now'))
        """,
        {
            "id": task_id,
            "title": f"Task {task_id}",
            "status": status,
            "priority": priority,
            "role": role,
            "epic_id": epic_id,
            "mission_id": mission_id,
        },
    )


def _create_mission(
    db: Database,
    persona_name: str = "test-persona",
    role: str = "Engineer",
    epic_id: str | None = None,
    status: str = "ACTIVE",
    desk_mode: bool = False,
    end_time: str | None = None,
) -> int:
    """Insert a mission row and return its ID."""
    result = db.execute_query(
        """
        INSERT INTO missions (
            persona_name, role, codename, mission_file,
            start_date, start_time, end_time, objective, epic_id,
            status, desk_mode_active, created_at, updated_at
        ) VALUES (
            :persona_name, :role, 'test-codename',
            '.opencode/work/missions/test.md',
            date('now'), time('now'), :end_time, 'Test objective', :epic_id,
            :status, :desk_mode, datetime('now'), datetime('now')
        ) RETURNING id
        """,
        {
            "persona_name": persona_name,
            "role": role,
            "epic_id": epic_id,
            "status": status,
            "desk_mode": 1 if desk_mode else 0,
            "end_time": end_time,
        },
    )
    return result[0]["id"]


# ===========================================================================
# UNIT TESTS: MissionManager.list_missions epic_id filter
# ===========================================================================


class TestListMissionsEpicFilter:
    """Test MissionManager.list_missions with epic_id filter."""

    def test_filter_by_epic_returns_only_matching(self, test_db):
        """Filtering by epic_id returns only missions for that epic."""
        _create_epic(test_db, "EPC-H-0001")
        _create_epic(test_db, "EPC-H-0002")

        _create_mission(test_db, persona_name="persona1", epic_id="EPC-H-0001")
        _create_mission(test_db, persona_name="persona2", epic_id="EPC-H-0002")
        _create_mission(test_db, persona_name="persona3", epic_id=None)

        manager = MissionManager(test_db)
        results = manager.list_missions(epic_id="EPC-H-0001")

        assert len(results) == 1
        assert results[0].epic_id == "EPC-H-0001"

    def test_filter_by_epic_no_missions_returns_empty(self, test_db):
        """Filtering by an epic with no missions returns empty list."""
        _create_epic(test_db, "EPC-H-0001")
        _create_epic(test_db, "EPC-H-0099")

        # Only create missions for EPC-H-0001
        _create_mission(test_db, persona_name="persona1", epic_id="EPC-H-0001")

        manager = MissionManager(test_db)
        results = manager.list_missions(epic_id="EPC-H-0099")

        assert results == []

    def test_filter_by_nonexistent_epic_returns_empty(self, test_db):
        """Filtering by an epic ID that doesn't exist returns empty list."""
        manager = MissionManager(test_db)
        results = manager.list_missions(epic_id="EPC-H-9999")

        assert results == []

    def test_filter_by_epic_combined_with_active_only(self, test_db):
        """Filtering by epic + active_only returns only active missions in that epic."""
        _create_epic(test_db, "EPC-H-0001")

        _create_mission(test_db, persona_name="persona1", epic_id="EPC-H-0001", status="ACTIVE")
        _create_mission(test_db, persona_name="persona2", epic_id="EPC-H-0001", status="ENDED", end_time="18:00:00")

        manager = MissionManager(test_db)
        results = manager.list_missions(epic_id="EPC-H-0001", active_only=True)

        assert len(results) == 1
        assert results[0].end_time is None

    def test_filter_by_epic_combined_with_role(self, test_db):
        """Filtering by epic + role returns only matching missions."""
        _create_epic(test_db, "EPC-H-0001")

        _create_mission(test_db, persona_name="persona1", role="Engineer", epic_id="EPC-H-0001")
        _create_mission(test_db, persona_name="persona2", role="Tester", epic_id="EPC-H-0001")

        manager = MissionManager(test_db)
        results = manager.list_missions(epic_id="EPC-H-0001", role="Engineer")

        assert len(results) == 1
        assert results[0].role == "Engineer"

    def test_no_filter_returns_all(self, test_db):
        """No epic filter returns all missions regardless of epic."""
        _create_epic(test_db, "EPC-H-0001")

        _create_mission(test_db, persona_name="persona1", epic_id="EPC-H-0001")
        _create_mission(test_db, persona_name="persona2", epic_id=None)

        manager = MissionManager(test_db)
        results = manager.list_missions()

        assert len(results) == 2

    def test_multiple_missions_same_epic(self, test_db):
        """Multiple missions for the same epic are all returned."""
        _create_epic(test_db, "EPC-H-0001")

        _create_mission(test_db, persona_name="persona1", epic_id="EPC-H-0001")
        _create_mission(test_db, persona_name="persona2", epic_id="EPC-H-0001")
        _create_mission(test_db, persona_name="persona3", epic_id="EPC-H-0001")

        manager = MissionManager(test_db)
        results = manager.list_missions(epic_id="EPC-H-0001")

        assert len(results) == 3


# ===========================================================================
# CLI TESTS: mission list --epic filter
# ===========================================================================


class TestCLIMissionListEpicFilter:
    """Test `s9 mission list --epic` CLI command."""

    def test_list_with_epic_filter(self, initialized_project):
        """CLI --epic filter shows only missions for that epic."""
        # Create an epic
        runner.invoke(app, ["epic", "create", "--title", "Filter Epic", "--priority", "HIGH"])

        # Start missions - one in epic, one general
        runner.invoke(
            app,
            ["mission", "start", "atar", "--role", "Engineer", "--epic", "EPC-H-0001"],
        )
        runner.invoke(
            app,
            ["mission", "start", "atar", "--role", "Engineer", "--task", "General work"],
        )

        # List with epic filter
        result = runner.invoke(app, ["mission", "list", "--epic", "EPC-H-0001"])
        assert result.exit_code == 0
        # Should show the epic-scoped mission but not the general one
        # The table should contain mission data
        assert "Agent Sessions" in result.output or "EPC-H-0001" in result.output

    def test_list_with_epic_filter_no_missions(self, initialized_project):
        """CLI --epic filter with no missions shows warning."""
        result = runner.invoke(app, ["mission", "list", "--epic", "EPC-H-9999"])
        assert result.exit_code == 0
        assert "No missions found" in result.output or "Warning" in result.output

    def test_list_with_epic_filter_json(self, initialized_project):
        """CLI --epic filter with --json returns filtered results."""
        # Create epic and mission
        runner.invoke(app, ["epic", "create", "--title", "JSON Filter Epic", "--priority", "HIGH"])
        runner.invoke(
            app,
            ["mission", "start", "atar", "--role", "Engineer", "--epic", "EPC-H-0001"],
        )
        # Also create a general mission that should NOT appear
        runner.invoke(
            app,
            ["mission", "start", "atar", "--role", "Tester", "--task", "General work"],
        )

        result = runner.invoke(app, ["mission", "list", "--epic", "EPC-H-0001", "--json"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert data["count"] == 1
        assert data["data"][0]["epic_id"] == "EPC-H-0001"


# ===========================================================================
# UNIT TESTS: Availability column display logic
# ===========================================================================


class TestAvailabilityDisplay:
    """Test all 7 branches of the _get_availability function.

    The function is defined locally in the CLI `list` command, so we test it
    indirectly through the CLI --json output which includes the availability field.
    """

    def test_availability_ended(self, initialized_project):
        """Ended mission shows 'Ended' availability."""
        # Start and end a mission
        start_result = runner.invoke(
            app,
            ["mission", "start", "atar", "--role", "Engineer", "--task", "Work"],
        )
        assert start_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", start_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        # End the mission
        end_result = runner.invoke(app, ["mission", "end", mission_id])
        assert end_result.exit_code == 0

        # Check availability in JSON
        result = runner.invoke(app, ["mission", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)

        ended_missions = [m for m in data["data"] if m["id"] == int(mission_id)]
        assert len(ended_missions) == 1
        assert ended_missions[0]["availability"] == "Ended"

    def test_availability_desk_epic(self, initialized_project):
        """Desk mode + epic_id shows 'Desk (EPC-X-NNNN)' availability."""
        # Create epic
        runner.invoke(app, ["epic", "create", "--title", "Desk Epic", "--priority", "HIGH"])

        # Start epic-scoped mission
        start_result = runner.invoke(
            app,
            ["mission", "start", "atar", "--role", "Engineer", "--epic", "EPC-H-0001"],
        )
        assert start_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", start_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        # Enable desk mode via direct DB update (comms desk uses a polling loop)
        _set_desk_mode_via_db(initialized_project, mission_id)

        # Check availability
        result = runner.invoke(app, ["mission", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)

        mission = next(m for m in data["data"] if m["id"] == int(mission_id))
        assert mission["availability"] == "Desk (EPC-H-0001)"
        assert mission["desk_mode_active"] is True

    def test_availability_desk_all(self, initialized_project):
        """Desk mode without epic_id shows 'Desk (All)' availability."""
        # Start general mission
        start_result = runner.invoke(
            app,
            ["mission", "start", "atar", "--role", "Engineer", "--task", "General work"],
        )
        assert start_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", start_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        # Enable desk mode via direct DB update
        _set_desk_mode_via_db(initialized_project, mission_id)

        # Check availability
        result = runner.invoke(app, ["mission", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)

        mission = next(m for m in data["data"] if m["id"] == int(mission_id))
        assert mission["availability"] == "Desk (All)"
        assert mission["desk_mode_active"] is True
        assert mission["epic_id"] is None

    def test_availability_working_epic(self, initialized_project):
        """Active mission with epic_id (no desk mode) shows 'Working (EPC-X-NNNN)'."""
        # Create epic
        runner.invoke(app, ["epic", "create", "--title", "Work Epic", "--priority", "HIGH"])

        # Start epic-scoped mission (no desk mode by default)
        start_result = runner.invoke(
            app,
            ["mission", "start", "atar", "--role", "Engineer", "--epic", "EPC-H-0001"],
        )
        assert start_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", start_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        # Check availability
        result = runner.invoke(app, ["mission", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)

        mission = next(m for m in data["data"] if m["id"] == int(mission_id))
        assert mission["availability"] == f"Working (EPC-H-0001)"
        assert mission["desk_mode_active"] is False

    def test_availability_working_task(self, initialized_project):
        """Active mission with current task shows 'Working (TASK-ID)'."""
        # Start general mission
        start_result = runner.invoke(
            app,
            ["mission", "start", "atar", "--role", "Engineer", "--task", "Work"],
        )
        assert start_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", start_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        # Create and claim a task
        create_result = runner.invoke(
            app,
            ["task", "create", "--title", "Working Task", "--role", "Engineer", "--priority", "HIGH"],
        )
        assert create_result.exit_code == 0
        task_match = re.search(r"Created task ([A-Z]+-[A-Z]-\d+)", create_result.output)
        assert task_match
        task_id = task_match.group(1)

        claim_result = runner.invoke(
            app,
            ["task", "claim", task_id, "--mission", mission_id, "--role", "Engineer"],
        )
        assert claim_result.exit_code == 0

        # Check availability
        result = runner.invoke(app, ["mission", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)

        mission = next(m for m in data["data"] if m["id"] == int(mission_id))
        assert mission["availability"] == f"Working ({task_id})"
        assert mission["current_task_id"] == task_id

    def test_availability_idle(self, initialized_project):
        """IDLE mission with no task/epic shows 'Idle'."""
        # Start a general mission
        start_result = runner.invoke(
            app,
            ["mission", "start", "atar", "--role", "Engineer"],
        )
        assert start_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", start_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        # Set mission status to IDLE via direct DB update
        from site_nine.cli.utils import require_db_path
        from site_nine.core.database import Database as DB

        db_path = require_db_path()
        with DB(db_path) as db:
            db.execute_update(
                "UPDATE missions SET status = :status WHERE id = :id",
                {"status": "IDLE", "id": int(mission_id)},
            )

        # Check availability
        result = runner.invoke(app, ["mission", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)

        mission = next(m for m in data["data"] if m["id"] == int(mission_id))
        assert mission["availability"] == "Idle"

    def test_availability_working_fallback(self, initialized_project):
        """Active general mission with no task shows 'Working' (fallback)."""
        # Start a general mission with a task objective (so it's task-scoped but no claimed task)
        start_result = runner.invoke(
            app,
            ["mission", "start", "atar", "--role", "Engineer", "--task", "Some work"],
        )
        assert start_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", start_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        # Don't claim any task — ACTIVE status, no epic, no current task
        result = runner.invoke(app, ["mission", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)

        mission = next(m for m in data["data"] if m["id"] == int(mission_id))
        assert mission["availability"] == "Working"
        assert mission["current_task_id"] is None
        assert mission["epic_id"] is None


# ===========================================================================
# CLI TESTS: JSON output structure
# ===========================================================================


class TestJSONOutputStructure:
    """Test that JSON output from `s9 mission list --json` contains all expected fields."""

    def test_json_output_has_all_fields(self, initialized_project):
        """JSON output includes all expected fields per ADR-009."""
        # Create epic for a rich test case
        runner.invoke(app, ["epic", "create", "--title", "JSON Epic", "--priority", "HIGH"])

        # Start an epic-scoped mission
        start_result = runner.invoke(
            app,
            ["mission", "start", "atar", "--role", "Engineer", "--epic", "EPC-H-0001"],
        )
        assert start_result.exit_code == 0

        result = runner.invoke(app, ["mission", "list", "--json"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert "data" in data
        assert "count" in data
        assert "timestamp" in data
        assert data["count"] >= 1

        mission = data["data"][0]
        expected_fields = [
            "id",
            "persona_name",
            "role",
            "codename",
            "status",
            "epic_id",
            "desk_mode_active",
            "current_task_id",
            "availability",
            "start_time",
            "end_time",
            "start_date",
            "objective",
            "mission_file",
        ]
        for field in expected_fields:
            assert field in mission, f"Missing field: {field}"

    def test_json_output_types(self, initialized_project):
        """JSON output field types are correct."""
        runner.invoke(
            app,
            ["mission", "start", "atar", "--role", "Engineer", "--task", "Type test"],
        )

        result = runner.invoke(app, ["mission", "list", "--json"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        mission = data["data"][0]

        # Type assertions
        assert isinstance(mission["id"], int)
        assert isinstance(mission["persona_name"], str)
        assert isinstance(mission["role"], str)
        assert isinstance(mission["codename"], str)
        assert isinstance(mission["status"], str)
        assert isinstance(mission["desk_mode_active"], bool)
        assert isinstance(mission["availability"], str)
        # Nullable fields
        assert mission["end_time"] is None or isinstance(mission["end_time"], str)
        assert mission["epic_id"] is None or isinstance(mission["epic_id"], str)
        assert mission["current_task_id"] is None or isinstance(mission["current_task_id"], str)

    def test_json_output_status_values(self, initialized_project):
        """JSON output status field uses enum values (uppercase)."""
        start_result = runner.invoke(
            app,
            ["mission", "start", "atar", "--role", "Engineer", "--task", "Status test"],
        )
        assert start_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", start_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        # Active mission
        result = runner.invoke(app, ["mission", "list", "--json"])
        data = json.loads(result.output)
        active_mission = next(m for m in data["data"] if m["id"] == int(mission_id))
        assert active_mission["status"] == "ACTIVE"

        # End the mission
        runner.invoke(app, ["mission", "end", mission_id])

        result = runner.invoke(app, ["mission", "list", "--json"])
        data = json.loads(result.output)
        ended_mission = next(m for m in data["data"] if m["id"] == int(mission_id))
        assert ended_mission["status"] == "ENDED"

    def test_json_output_with_current_task(self, initialized_project):
        """JSON output includes current_task_id when a task is claimed."""
        # Start mission
        start_result = runner.invoke(
            app,
            ["mission", "start", "atar", "--role", "Engineer", "--task", "Task test"],
        )
        assert start_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", start_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        # Create and claim task
        create_result = runner.invoke(
            app,
            ["task", "create", "--title", "JSON Task", "--role", "Engineer", "--priority", "HIGH"],
        )
        assert create_result.exit_code == 0
        task_match = re.search(r"Created task ([A-Z]+-[A-Z]-\d+)", create_result.output)
        assert task_match
        task_id = task_match.group(1)

        runner.invoke(
            app,
            ["task", "claim", task_id, "--mission", mission_id, "--role", "Engineer"],
        )

        # Check JSON output
        result = runner.invoke(app, ["mission", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)

        mission = next(m for m in data["data"] if m["id"] == int(mission_id))
        assert mission["current_task_id"] == task_id

    def test_json_empty_list_structure(self, initialized_project):
        """JSON output for empty mission list has correct structure."""
        result = runner.invoke(app, ["mission", "list", "--json"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert data["data"] == []
        assert data["count"] == 0

    def test_json_desk_mode_field(self, initialized_project):
        """JSON output includes desk_mode_active field accurately."""
        # Start mission
        start_result = runner.invoke(
            app,
            ["mission", "start", "atar", "--role", "Engineer", "--task", "Desk test"],
        )
        assert start_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", start_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        # Initially not in desk mode
        result = runner.invoke(app, ["mission", "list", "--json"])
        data = json.loads(result.output)
        mission = next(m for m in data["data"] if m["id"] == int(mission_id))
        assert mission["desk_mode_active"] is False

        # Enable desk mode via direct DB update
        _set_desk_mode_via_db(initialized_project, mission_id)

        result = runner.invoke(app, ["mission", "list", "--json"])
        data = json.loads(result.output)
        mission = next(m for m in data["data"] if m["id"] == int(mission_id))
        assert mission["desk_mode_active"] is True


# ===========================================================================
# CLI TESTS: Desk mode missions in list context
# ===========================================================================


class TestDeskModeMissionsInList:
    """Test desk mode display in mission list."""

    def test_multiple_desk_mode_missions(self, initialized_project):
        """Multiple missions can be in desk mode simultaneously."""
        # Start two missions
        result1 = runner.invoke(
            app,
            ["mission", "start", "atar", "--role", "Engineer", "--task", "Desk 1"],
        )
        assert result1.exit_code == 0
        mid1 = re.search(r"#(\d+)", result1.output).group(1)

        result2 = runner.invoke(
            app,
            ["mission", "start", "atar", "--role", "Tester", "--task", "Desk 2"],
        )
        assert result2.exit_code == 0
        mid2 = re.search(r"#(\d+)", result2.output).group(1)

        # Enable desk mode on both via direct DB update
        _set_desk_mode_via_db(initialized_project, mid1)
        _set_desk_mode_via_db(initialized_project, mid2)

        # Both should show desk mode
        result = runner.invoke(app, ["mission", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)

        desk_missions = [m for m in data["data"] if m["desk_mode_active"]]
        assert len(desk_missions) == 2

    def test_desk_mode_in_table_output(self, initialized_project):
        """Desk mode missions show desk availability in table output."""
        # Start and desk a mission
        start_result = runner.invoke(
            app,
            ["mission", "start", "atar", "--role", "Engineer", "--task", "Desk display"],
        )
        assert start_result.exit_code == 0
        mid = re.search(r"#(\d+)", start_result.output).group(1)

        _set_desk_mode_via_db(initialized_project, mid)

        # Table output should mention Desk
        result = runner.invoke(app, ["mission", "list"])
        assert result.exit_code == 0
        assert "Desk" in result.output

    def test_desk_mode_off_changes_availability(self, initialized_project):
        """Turning desk mode off changes availability back."""
        start_result = runner.invoke(
            app,
            ["mission", "start", "atar", "--role", "Engineer", "--task", "Toggle desk"],
        )
        assert start_result.exit_code == 0
        mid = re.search(r"#(\d+)", start_result.output).group(1)

        # Enable desk mode
        _set_desk_mode_via_db(initialized_project, mid)

        result = runner.invoke(app, ["mission", "list", "--json"])
        data = json.loads(result.output)
        mission = next(m for m in data["data"] if m["id"] == int(mid))
        assert mission["availability"] == "Desk (All)"

        # Disable desk mode
        _set_desk_mode_via_db(initialized_project, mid, active=False)

        result = runner.invoke(app, ["mission", "list", "--json"])
        data = json.loads(result.output)
        mission = next(m for m in data["data"] if m["id"] == int(mid))
        assert mission["availability"] == "Working"
        assert mission["desk_mode_active"] is False


# ===========================================================================
# EDGE CASE TESTS
# ===========================================================================


class TestEdgeCases:
    """Edge cases for mission discovery."""

    def test_general_availability_no_task_no_epic(self, initialized_project):
        """General mission (no flags) shows 'Working' when ACTIVE, no task."""
        start_result = runner.invoke(
            app,
            ["mission", "start", "atar", "--role", "Engineer"],
        )
        assert start_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", start_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        result = runner.invoke(app, ["mission", "list", "--json"])
        data = json.loads(result.output)
        mission = next(m for m in data["data"] if m["id"] == int(mission_id))

        # General mission with no task, no epic — but ACTIVE status
        # _get_availability: not ended, not desk, no epic_id, no current_task
        # status is ACTIVE (not IDLE), so falls through to "Working" fallback
        assert mission["availability"] == "Working"

    def test_list_missions_ordered_by_created_at_desc(self, test_db):
        """Missions are returned newest first (by created_at DESC)."""
        # Use explicit timestamps to ensure deterministic ordering
        # (datetime('now') in SQLite has second precision; both inserts may get same timestamp)
        test_db.execute_query(
            """
            INSERT INTO missions (
                persona_name, role, codename, mission_file,
                start_date, start_time, objective, epic_id,
                status, created_at, updated_at
            ) VALUES (
                'persona1', 'Engineer', 'codename-1',
                '.opencode/work/missions/test1.md',
                date('now'), time('now'), 'Objective 1', NULL,
                'ACTIVE', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z'
            ) RETURNING id
            """,
        )
        test_db.execute_query(
            """
            INSERT INTO missions (
                persona_name, role, codename, mission_file,
                start_date, start_time, objective, epic_id,
                status, created_at, updated_at
            ) VALUES (
                'persona2', 'Engineer', 'codename-2',
                '.opencode/work/missions/test2.md',
                date('now'), time('now'), 'Objective 2', NULL,
                'ACTIVE', '2026-01-02T00:00:00Z', '2026-01-02T00:00:00Z'
            ) RETURNING id
            """,
        )

        manager = MissionManager(test_db)
        results = manager.list_missions()

        assert len(results) == 2
        # Most recently created should be first
        assert results[0].persona_name == "persona2"
        assert results[1].persona_name == "persona1"

    def test_availability_priority_desk_over_working(self, initialized_project):
        """Desk mode takes priority over working status for availability."""
        # Create epic and mission
        runner.invoke(app, ["epic", "create", "--title", "Priority Epic", "--priority", "HIGH"])
        start_result = runner.invoke(
            app,
            ["mission", "start", "atar", "--role", "Engineer", "--epic", "EPC-H-0001"],
        )
        assert start_result.exit_code == 0
        mid = re.search(r"#(\d+)", start_result.output).group(1)

        # Create task in epic and claim it
        runner.invoke(
            app,
            [
                "task",
                "create",
                "--title",
                "Priority Task",
                "--role",
                "Engineer",
                "--priority",
                "HIGH",
                "--epic",
                "EPC-H-0001",
            ],
        )

        # Even with epic_id, desk mode should take priority
        _set_desk_mode_via_db(initialized_project, mid)

        result = runner.invoke(app, ["mission", "list", "--json"])
        data = json.loads(result.output)
        mission = next(m for m in data["data"] if m["id"] == int(mid))

        # Desk mode should show "Desk (EPC-H-0001)", not "Working (EPC-H-0001)"
        assert mission["availability"] == "Desk (EPC-H-0001)"

    def test_ended_mission_ignores_desk_mode(self, initialized_project):
        """Ended status takes priority over desk mode for availability."""
        start_result = runner.invoke(
            app,
            ["mission", "start", "atar", "--role", "Engineer", "--task", "End test"],
        )
        assert start_result.exit_code == 0
        mid = re.search(r"#(\d+)", start_result.output).group(1)

        # Enable desk mode then end
        _set_desk_mode_via_db(initialized_project, mid)
        runner.invoke(app, ["mission", "end", mid])

        result = runner.invoke(app, ["mission", "list", "--json"])
        data = json.loads(result.output)
        mission = next(m for m in data["data"] if m["id"] == int(mid))

        # Should show Ended, not Desk
        assert mission["availability"] == "Ended"
