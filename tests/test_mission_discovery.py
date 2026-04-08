"""Tests for mission discovery and filtering (TST-M-0100).

Covers ADR-009 Phase 2:
- mission list --epic filter (CLI layer)
- Availability column display logic (all 7 branches)
- JSON output structure with availability/minion_mode/current_task fields
- Minion mode missions in list context
- Edge cases: no missions in epic, multiple minion modes, general availability
"""

import json
import re

import pytest
from typer.testing import CliRunner

from site_nine.__main__ import app
from site_nine.core.database import Database
from site_nine.possessions.manager import PossessionManager

runner = CliRunner()


def _set_minion_mode_via_db(initialized_project, mission_id: int | str, active: bool = True) -> None:
    """Enable/disable minion mode directly via DB (bypasses comms minion polling loop)."""
    from site_nine.cli.utils import require_db_path
    from site_nine.core.database import Database as DB

    db_path = require_db_path()
    with DB(db_path) as db:
        db.execute_update(
            "UPDATE possessions SET minion_mode_active = :active WHERE id = :id",
            {"active": 1 if active else 0, "id": int(mission_id)},
        )


# ---------------------------------------------------------------------------
# Helpers
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


def _create_daemon(db: Database, name: str = "test-daemon", role: str = "Engineer") -> None:
    """Insert a daemon row."""
    db.execute_update(
        """
        INSERT OR IGNORE INTO daemons (name, role, incarnations, created_at)
        VALUES (:name, :role, 0, datetime('now'))
        """,
        {"name": name, "role": role},
    )


def _create_task(
    db: Database,
    task_id: str,
    role: str = "Engineer",
    priority: str = "MEDIUM",
    status: str = "TODO",
    epic_id: str | None = None,
    possession_id: int | None = None,
) -> None:
    """Insert a task row, optionally assigned to a possession."""
    db.execute_update(
        """
        INSERT INTO tasks (id, title, description, status, priority, role, epic_id,
                           current_possession_id, file_path, created_at, updated_at)
        VALUES (:id, :title, 'Test description', :status, :priority, :role, :epic_id,
                :possession_id,
                '.opencode/work/tasks/' || :id || '.md', datetime('now'), datetime('now'))
        """,
        {
            "id": task_id,
            "title": f"Task {task_id}",
            "status": status,
            "priority": priority,
            "role": role,
            "epic_id": epic_id,
            "possession_id": possession_id,
        },
    )


def _create_possession(
    db: Database,
    daemon_name: str = "test-daemon",
    role: str = "Engineer",
    epic_id: str | None = None,
    status: str = "ACTIVE",
    minion_mode: bool = False,
    end_time: str | None = None,
) -> int:
    """Insert a possession row and return its ID."""
    _create_daemon(db, daemon_name, role)
    result = db.execute_query(
        """
        INSERT INTO possessions (
            daemon_name, role, possession_log,
            start_time, end_time, epic_id,
            status, minion_mode_active, created_at, updated_at
        ) VALUES (
            :daemon_name, :role,
            '.opencode/work/possessions/test.md',
            datetime('now'), :end_time, :epic_id,
            :status, :minion_mode, datetime('now'), datetime('now')
        ) RETURNING id
        """,
        {
            "daemon_name": daemon_name,
            "role": role,
            "epic_id": epic_id,
            "status": status,
            "minion_mode": 1 if minion_mode else 0,
            "end_time": end_time,
        },
    )
    return result[0]["id"]


# ===========================================================================
# UNIT TESTS: PossessionManager.list_possessions epic_id filter
# ===========================================================================


class TestListMissionsEpicFilter:
    """Test PossessionManager.list_possessions with epic_id filter."""

    def test_filter_by_epic_returns_only_matching(self, test_db):
        """Filtering by epic_id returns only possessions for that epic."""
        _create_epic(test_db, "EPC-H-0001")
        _create_epic(test_db, "EPC-H-0002")

        _create_possession(test_db, daemon_name="persona1", epic_id="EPC-H-0001")
        _create_possession(test_db, daemon_name="persona2", epic_id="EPC-H-0002")
        _create_possession(test_db, daemon_name="persona3", epic_id=None)

        manager = PossessionManager(test_db)
        results = manager.list_possessions(epic_id="EPC-H-0001")

        assert len(results) == 1
        assert results[0].epic_id == "EPC-H-0001"

    def test_filter_by_epic_no_missions_returns_empty(self, test_db):
        """Filtering by an epic with no possessions returns empty list."""
        _create_epic(test_db, "EPC-H-0001")
        _create_epic(test_db, "EPC-H-0099")

        _create_possession(test_db, daemon_name="persona1", epic_id="EPC-H-0001")

        manager = PossessionManager(test_db)
        results = manager.list_possessions(epic_id="EPC-H-0099")

        assert results == []

    def test_filter_by_nonexistent_epic_returns_empty(self, test_db):
        """Filtering by an epic ID that doesn't exist returns empty list."""
        manager = PossessionManager(test_db)
        results = manager.list_possessions(epic_id="EPC-H-9999")

        assert results == []

    def test_filter_by_epic_combined_with_active_only(self, test_db):
        """Filtering by epic + active_only returns only active possessions in that epic."""
        _create_epic(test_db, "EPC-H-0001")

        _create_possession(test_db, daemon_name="persona1", epic_id="EPC-H-0001", status="ACTIVE")
        _create_possession(
            test_db, daemon_name="persona2", epic_id="EPC-H-0001", status="EXORCISED", end_time="2026-01-01T18:00:00"
        )

        manager = PossessionManager(test_db)
        results = manager.list_possessions(epic_id="EPC-H-0001", active_only=True)

        assert len(results) == 1
        assert results[0].end_time is None

    def test_filter_by_epic_combined_with_role(self, test_db):
        """Filtering by epic + role returns only matching possessions."""
        _create_epic(test_db, "EPC-H-0001")

        _create_possession(test_db, daemon_name="persona1", role="Engineer", epic_id="EPC-H-0001")
        _create_possession(test_db, daemon_name="persona2", role="Tester", epic_id="EPC-H-0001")

        manager = PossessionManager(test_db)
        results = manager.list_possessions(epic_id="EPC-H-0001", role="Engineer")

        assert len(results) == 1
        assert results[0].role == "Engineer"

    def test_no_filter_returns_all(self, test_db):
        """No epic filter returns all possessions regardless of epic."""
        _create_epic(test_db, "EPC-H-0001")

        _create_possession(test_db, daemon_name="persona1", epic_id="EPC-H-0001")
        _create_possession(test_db, daemon_name="persona2", epic_id=None)

        manager = PossessionManager(test_db)
        results = manager.list_possessions()

        assert len(results) == 2

    def test_multiple_missions_same_epic(self, test_db):
        """Multiple possessions for the same epic are all returned."""
        _create_epic(test_db, "EPC-H-0001")

        _create_possession(test_db, daemon_name="persona1", epic_id="EPC-H-0001")
        _create_possession(test_db, daemon_name="persona2", epic_id="EPC-H-0001")
        _create_possession(test_db, daemon_name="persona3", epic_id="EPC-H-0001")

        manager = PossessionManager(test_db)
        results = manager.list_possessions(epic_id="EPC-H-0001")

        assert len(results) == 3


# ===========================================================================
# CLI TESTS: mission list --epic filter
# ===========================================================================


class TestCLIMissionListEpicFilter:
    """Test `s9 mission list --epic` CLI command."""

    def test_list_with_epic_filter(self, initialized_project):
        """CLI --epic filter shows only missions for that epic."""
        runner.invoke(app, ["persona", "add", "atar", "--role", "Engineer"])
        runner.invoke(app, ["epic", "create", "--title", "Filter Epic", "--priority", "HIGH"])

        runner.invoke(app, ["mission", "start", "--role", "Engineer", "--name", "atar", "--epic", "EPC-H-0001"])
        runner.invoke(app, ["mission", "start", "--role", "Engineer", "--name", "atar", "--task", "General work"])

        result = runner.invoke(app, ["mission", "list", "--epic", "EPC-H-0001"])
        assert result.exit_code == 0
        assert "Agent Sessions" in result.output or "EPC-H-0001" in result.output

    def test_list_with_epic_filter_no_missions(self, initialized_project):
        """CLI --epic filter with no missions shows warning."""
        result = runner.invoke(app, ["mission", "list", "--epic", "EPC-H-9999"])
        assert result.exit_code == 0
        assert "No missions found" in result.output or "Warning" in result.output

    def test_list_with_epic_filter_json(self, initialized_project):
        """CLI --epic filter with --json returns filtered results."""
        runner.invoke(app, ["persona", "add", "atar", "--role", "Engineer"])
        runner.invoke(app, ["epic", "create", "--title", "JSON Filter Epic", "--priority", "HIGH"])
        runner.invoke(app, ["mission", "start", "--role", "Engineer", "--name", "atar", "--epic", "EPC-H-0001"])
        runner.invoke(app, ["mission", "start", "--role", "Tester", "--name", "atar", "--task", "General work"])

        result = runner.invoke(app, ["mission", "list", "--epic", "EPC-H-0001", "--json"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert data["count"] == 1
        assert data["data"][0]["epic_id"] == "EPC-H-0001"


# ===========================================================================
# UNIT TESTS: Availability column display logic
# ===========================================================================


class TestAvailabilityDisplay:
    """Test all branches of the _get_availability function.

    The function is defined locally in the CLI `list` command, so we test it
    indirectly through the CLI --json output which includes the availability field.
    """

    def test_availability_ended(self, initialized_project):
        """Ended mission shows 'Ended' availability."""
        runner.invoke(app, ["persona", "add", "atar", "--role", "Engineer"])
        start_result = runner.invoke(
            app, ["mission", "start", "--role", "Engineer", "--name", "atar", "--task", "Work"]
        )
        assert start_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", start_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        end_result = runner.invoke(app, ["mission", "end", mission_id])
        assert end_result.exit_code == 0

        result = runner.invoke(app, ["mission", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)

        ended_missions = [m for m in data["data"] if m["id"] == int(mission_id)]
        assert len(ended_missions) == 1
        assert ended_missions[0]["availability"] == "Ended"

    def test_availability_minion_epic(self, initialized_project):
        """Minion mode + epic_id shows 'Minion (EPC-X-NNNN)' availability."""
        runner.invoke(app, ["persona", "add", "atar", "--role", "Engineer"])
        runner.invoke(app, ["epic", "create", "--title", "Minion Epic", "--priority", "HIGH"])

        start_result = runner.invoke(
            app,
            ["mission", "start", "--role", "Engineer", "--name", "atar", "--epic", "EPC-H-0001"],
        )
        assert start_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", start_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        _set_minion_mode_via_db(initialized_project, mission_id)

        result = runner.invoke(app, ["mission", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)

        mission = next(m for m in data["data"] if m["id"] == int(mission_id))
        assert mission["availability"] == "Minion (EPC-H-0001)"
        assert mission["minion_mode_active"] is True

    def test_availability_minion_all(self, initialized_project):
        """Minion mode without epic_id shows 'Minion (All)' availability."""
        runner.invoke(app, ["persona", "add", "atar", "--role", "Engineer"])
        start_result = runner.invoke(
            app,
            ["mission", "start", "--role", "Engineer", "--name", "atar", "--task", "General work"],
        )
        assert start_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", start_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        _set_minion_mode_via_db(initialized_project, mission_id)

        result = runner.invoke(app, ["mission", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)

        mission = next(m for m in data["data"] if m["id"] == int(mission_id))
        assert mission["availability"] == "Minion (All)"
        assert mission["minion_mode_active"] is True
        assert mission["epic_id"] is None
        """Active mission with epic_id (no minion mode) shows 'Working (EPC-X-NNNN)'."""
        runner.invoke(app, ["persona", "add", "atar", "--role", "Engineer"])
        runner.invoke(app, ["epic", "create", "--title", "Work Epic", "--priority", "HIGH"])

        start_result = runner.invoke(
            app,
            ["mission", "start", "--role", "Engineer", "--name", "atar", "--epic", "EPC-H-0001"],
        )
        assert start_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", start_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        result = runner.invoke(app, ["mission", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)

        mission = next(m for m in data["data"] if m["id"] == int(mission_id))
        assert mission["availability"] == f"Working (EPC-H-0001)"
        assert mission["minion_mode_active"] is False

    def test_availability_working_task(self, initialized_project):
        """Active mission with current task shows 'Working (TASK-ID)'."""
        runner.invoke(app, ["persona", "add", "atar", "--role", "Engineer"])
        start_result = runner.invoke(
            app,
            ["mission", "start", "--role", "Engineer", "--name", "atar", "--task", "Work"],
        )
        assert start_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", start_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

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

        result = runner.invoke(app, ["mission", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)

        mission = next(m for m in data["data"] if m["id"] == int(mission_id))
        assert mission["availability"] == f"Working ({task_id})"
        assert mission["current_task_id"] == task_id

    def test_availability_working_fallback(self, initialized_project):
        """Active general mission with no task shows 'Working' (fallback)."""
        runner.invoke(app, ["persona", "add", "atar", "--role", "Engineer"])
        start_result = runner.invoke(
            app,
            ["mission", "start", "--role", "Engineer", "--name", "atar", "--task", "Some work"],
        )
        assert start_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", start_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

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
        runner.invoke(app, ["persona", "add", "atar", "--role", "Engineer"])
        runner.invoke(app, ["epic", "create", "--title", "JSON Epic", "--priority", "HIGH"])

        start_result = runner.invoke(
            app,
            ["mission", "start", "--role", "Engineer", "--name", "atar", "--epic", "EPC-H-0001"],
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
            "minion_mode_active",
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
        runner.invoke(app, ["persona", "add", "atar", "--role", "Engineer"])
        runner.invoke(
            app,
            ["mission", "start", "--role", "Engineer", "--name", "atar", "--task", "Type test"],
        )

        result = runner.invoke(app, ["mission", "list", "--json"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        mission = data["data"][0]

        assert isinstance(mission["id"], int)
        assert isinstance(mission["persona_name"], str)
        assert isinstance(mission["role"], str)
        assert isinstance(mission["codename"], str)
        assert isinstance(mission["status"], str)
        assert isinstance(mission["minion_mode_active"], bool)
        assert isinstance(mission["availability"], str)
        assert mission["end_time"] is None or isinstance(mission["end_time"], str)
        assert mission["epic_id"] is None or isinstance(mission["epic_id"], str)
        assert mission["current_task_id"] is None or isinstance(mission["current_task_id"], str)

    def test_json_output_status_values(self, initialized_project):
        """JSON output status field uses enum values (uppercase)."""
        runner.invoke(app, ["persona", "add", "atar", "--role", "Engineer"])
        start_result = runner.invoke(
            app,
            ["mission", "start", "--role", "Engineer", "--name", "atar", "--task", "Status test"],
        )
        assert start_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", start_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        result = runner.invoke(app, ["mission", "list", "--json"])
        data = json.loads(result.output)
        active_mission = next(m for m in data["data"] if m["id"] == int(mission_id))
        assert active_mission["status"] == "ACTIVE"

        runner.invoke(app, ["mission", "end", mission_id])

        result = runner.invoke(app, ["mission", "list", "--json"])
        data = json.loads(result.output)
        ended_mission = next(m for m in data["data"] if m["id"] == int(mission_id))
        assert ended_mission["status"] == "EXORCISED"

    def test_json_output_with_current_task(self, initialized_project):
        """JSON output includes current_task_id when a task is claimed."""
        runner.invoke(app, ["persona", "add", "atar", "--role", "Engineer"])
        start_result = runner.invoke(
            app,
            ["mission", "start", "--role", "Engineer", "--name", "atar", "--task", "Task test"],
        )
        assert start_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", start_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

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

    def test_json_minion_mode_field(self, initialized_project):
        """JSON output includes minion_mode_active field accurately."""
        runner.invoke(app, ["persona", "add", "atar", "--role", "Engineer"])
        start_result = runner.invoke(
            app,
            ["mission", "start", "--role", "Engineer", "--name", "atar", "--task", "Desk test"],
        )
        assert start_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", start_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        result = runner.invoke(app, ["mission", "list", "--json"])
        data = json.loads(result.output)
        mission = next(m for m in data["data"] if m["id"] == int(mission_id))
        assert mission["minion_mode_active"] is False

        _set_minion_mode_via_db(initialized_project, mission_id)

        result = runner.invoke(app, ["mission", "list", "--json"])
        data = json.loads(result.output)
        mission = next(m for m in data["data"] if m["id"] == int(mission_id))
        assert mission["minion_mode_active"] is True


# ===========================================================================
# CLI TESTS: Minion mode missions in list context
# ===========================================================================


class TestMinionModeMissionsInList:
    """Test minion mode display in mission list."""

    def test_multiple_minion_mode_missions(self, initialized_project):
        """Multiple missions can be in minion mode simultaneously."""
        runner.invoke(app, ["persona", "add", "atar", "--role", "Engineer"])

        result1 = runner.invoke(
            app,
            ["mission", "start", "--role", "Engineer", "--name", "atar", "--task", "Desk 1"],
        )
        assert result1.exit_code == 0
        mid1 = re.search(r"#(\d+)", result1.output).group(1)

        result2 = runner.invoke(
            app,
            ["mission", "start", "--role", "Tester", "--name", "atar", "--task", "Desk 2"],
        )
        assert result2.exit_code == 0
        mid2 = re.search(r"#(\d+)", result2.output).group(1)

        _set_minion_mode_via_db(initialized_project, mid1)
        _set_minion_mode_via_db(initialized_project, mid2)

        result = runner.invoke(app, ["mission", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)

        minion_missions = [m for m in data["data"] if m["minion_mode_active"]]
        assert len(minion_missions) == 2

    def test_minion_mode_in_table_output(self, initialized_project):
        """Minion mode missions show minion availability in table output."""
        runner.invoke(app, ["persona", "add", "atar", "--role", "Engineer"])
        start_result = runner.invoke(
            app,
            ["mission", "start", "--role", "Engineer", "--name", "atar", "--task", "Desk display"],
        )
        assert start_result.exit_code == 0
        mid = re.search(r"#(\d+)", start_result.output).group(1)

        _set_minion_mode_via_db(initialized_project, mid)

        result = runner.invoke(app, ["mission", "list"])
        assert result.exit_code == 0
        assert "Minion" in result.output

    def test_minion_mode_off_changes_availability(self, initialized_project):
        """Turning minion mode off changes availability back."""
        runner.invoke(app, ["persona", "add", "atar", "--role", "Engineer"])
        start_result = runner.invoke(
            app,
            ["mission", "start", "--role", "Engineer", "--name", "atar", "--task", "Toggle minion"],
        )
        assert start_result.exit_code == 0
        mid = re.search(r"#(\d+)", start_result.output).group(1)

        _set_minion_mode_via_db(initialized_project, mid)

        result = runner.invoke(app, ["mission", "list", "--json"])
        data = json.loads(result.output)
        mission = next(m for m in data["data"] if m["id"] == int(mid))
        assert mission["availability"] == "Minion (All)"

        _set_minion_mode_via_db(initialized_project, mid, active=False)

        result = runner.invoke(app, ["mission", "list", "--json"])
        data = json.loads(result.output)
        mission = next(m for m in data["data"] if m["id"] == int(mid))
        assert mission["availability"] == "Working"
        assert mission["minion_mode_active"] is False


# ===========================================================================
# EDGE CASE TESTS
# ===========================================================================


class TestEdgeCases:
    """Edge cases for mission discovery."""

    def test_general_availability_no_task_no_epic(self, initialized_project):
        """General mission (no flags) shows 'Working' when ACTIVE, no task."""
        runner.invoke(app, ["persona", "add", "atar", "--role", "Engineer"])
        start_result = runner.invoke(
            app,
            ["mission", "start", "--role", "Engineer", "--name", "atar"],
        )
        assert start_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", start_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        result = runner.invoke(app, ["mission", "list", "--json"])
        data = json.loads(result.output)
        mission = next(m for m in data["data"] if m["id"] == int(mission_id))

        assert mission["availability"] == "Working"

    def test_list_possessions_ordered_by_created_at_desc(self, test_db):
        """Possessions are returned newest first (by created_at DESC)."""
        _create_daemon(test_db, "persona1", "Engineer")
        _create_daemon(test_db, "persona2", "Engineer")
        test_db.execute_query(
            """
            INSERT INTO possessions (
                daemon_name, role, possession_log,
                start_time, epic_id,
                status, created_at, updated_at
            ) VALUES (
                'persona1', 'Engineer',
                '.opencode/work/possessions/test1.md',
                datetime('now'), NULL,
                'ACTIVE', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z'
            ) RETURNING id
            """,
        )
        test_db.execute_query(
            """
            INSERT INTO possessions (
                daemon_name, role, possession_log,
                start_time, epic_id,
                status, created_at, updated_at
            ) VALUES (
                'persona2', 'Engineer',
                '.opencode/work/possessions/test2.md',
                datetime('now'), NULL,
                'ACTIVE', '2026-01-02T00:00:00Z', '2026-01-02T00:00:00Z'
            ) RETURNING id
            """,
        )

        manager = PossessionManager(test_db)
        results = manager.list_possessions()

        assert len(results) == 2
        # Most recently created should be first
        assert results[0].daemon_name == "persona2"
        assert results[1].daemon_name == "persona1"

    def test_availability_priority_minion_over_working(self, initialized_project):
        """Minion mode takes priority over working status for availability."""
        runner.invoke(app, ["persona", "add", "atar", "--role", "Engineer"])
        runner.invoke(app, ["epic", "create", "--title", "Priority Epic", "--priority", "HIGH"])
        start_result = runner.invoke(
            app,
            ["mission", "start", "--role", "Engineer", "--name", "atar", "--epic", "EPC-H-0001"],
        )
        assert start_result.exit_code == 0
        mid = re.search(r"#(\d+)", start_result.output).group(1)

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

        _set_minion_mode_via_db(initialized_project, mid)

        result = runner.invoke(app, ["mission", "list", "--json"])
        data = json.loads(result.output)
        mission = next(m for m in data["data"] if m["id"] == int(mid))

        assert mission["availability"] == "Minion (EPC-H-0001)"

    def test_ended_mission_ignores_minion_mode(self, initialized_project):
        """Ended status takes priority over minion mode for availability."""
        runner.invoke(app, ["persona", "add", "atar", "--role", "Engineer"])
        start_result = runner.invoke(
            app,
            ["mission", "start", "--role", "Engineer", "--name", "atar", "--task", "End test"],
        )
        assert start_result.exit_code == 0
        mid = re.search(r"#(\d+)", start_result.output).group(1)

        _set_minion_mode_via_db(initialized_project, mid)
        runner.invoke(app, ["mission", "end", mid])

        result = runner.invoke(app, ["mission", "list", "--json"])
        data = json.loads(result.output)
        mission = next(m for m in data["data"] if m["id"] == int(mid))

        assert mission["availability"] == "Ended"
