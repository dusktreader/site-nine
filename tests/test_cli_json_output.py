"""Integration tests for --json flag across CLI commands"""

import json
from pathlib import Path

from site_nine.cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def test_mission_list_json(initialized_project: Path):
    """Test mission list with JSON output"""
    result = runner.invoke(app, ["mission", "list", "--json"])

    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    # Parse JSON output
    data = json.loads(result.stdout)

    # Verify standard JSON response structure
    assert "data" in data
    assert "count" in data
    assert "timestamp" in data

    # Verify data is a list
    assert isinstance(data["data"], list)
    assert data["count"] == len(data["data"])


def test_mission_list_json_with_filters(initialized_project: Path):
    """Test mission list JSON output with filters"""
    result = runner.invoke(app, ["mission", "list", "--role", "Operator", "--json"])

    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    data = json.loads(result.stdout)
    assert "data" in data
    assert isinstance(data["data"], list)


def test_task_list_json(initialized_project: Path):
    """Test task list with JSON output"""
    result = runner.invoke(app, ["task", "list", "--json"])

    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    data = json.loads(result.stdout)
    assert "data" in data
    assert "count" in data
    assert "timestamp" in data
    assert isinstance(data["data"], list)


def test_task_list_json_with_filters(initialized_project: Path):
    """Test task list JSON output with role filter"""
    result = runner.invoke(app, ["task", "list", "--role", "Operator", "--json"])

    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    data = json.loads(result.stdout)
    assert "data" in data
    assert isinstance(data["data"], list)


def test_epic_list_json(initialized_project: Path):
    """Test epic list with JSON output"""
    result = runner.invoke(app, ["epic", "list", "--json"])

    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    data = json.loads(result.stdout)
    assert "data" in data
    assert "count" in data
    assert "timestamp" in data
    assert isinstance(data["data"], list)


def test_dashboard_json(initialized_project: Path):
    """Test dashboard with JSON output"""
    result = runner.invoke(app, ["dashboard", "--json"])

    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    data = json.loads(result.stdout)
    assert "data" in data
    assert "timestamp" in data

    # Verify dashboard structure
    assert "active_epics" in data["data"] or "role" in data["data"]
    assert "stats" in data["data"] or "available_tasks" in data["data"]


def test_dashboard_json_with_role_filter(initialized_project: Path):
    """Test dashboard JSON output with role filter"""
    result = runner.invoke(app, ["dashboard", "--role", "Operator", "--json"])

    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    data = json.loads(result.stdout)
    assert "data" in data
    assert "role" in data["data"]
    assert data["data"]["role"] == "Operator"
    assert "available_tasks" in data["data"]


def test_json_output_is_valid_json(initialized_project: Path):
    """Test that all JSON outputs are valid JSON (not mixed with other text)"""
    commands = [
        ["mission", "list", "--json"],
        ["task", "list", "--json"],
        ["epic", "list", "--json"],
        ["dashboard", "--json"],
    ]

    for cmd in commands:
        result = runner.invoke(app, cmd)
        assert result.exit_code == 0, f"Command failed: {' '.join(cmd)}: {result.stdout}"

        try:
            data = json.loads(result.stdout)
            # Verify it's a dict (standard response format)
            assert isinstance(data, dict), f"Expected dict, got {type(data)} for {' '.join(cmd)}"
        except json.JSONDecodeError as e:
            raise AssertionError(f"Invalid JSON for command {' '.join(cmd)}: {e}\n{result.stdout}")


def test_empty_results_json(initialized_project: Path):
    """Test that empty results return valid JSON"""
    # Filter for a role that likely has no missions
    result = runner.invoke(app, ["mission", "list", "--role", "NonexistentRole", "--json"])

    # Even if it errors, if --json flag is present, should return JSON
    if result.exit_code == 0:
        data = json.loads(result.stdout)
        assert "data" in data
        # Empty results should have count of 0
        if "count" in data:
            assert data["count"] == 0 or isinstance(data["data"], list)


def test_json_structure_consistency(initialized_project: Path):
    """Test that JSON responses have consistent structure"""
    commands = [
        ["mission", "list", "--json"],
        ["task", "list", "--json"],
        ["epic", "list", "--json"],
    ]

    for cmd in commands:
        result = runner.invoke(app, cmd)
        if result.exit_code == 0:
            data = json.loads(result.stdout)

            # All list commands should have these fields
            assert "data" in data, f"Missing 'data' field in {' '.join(cmd)}"
            assert "timestamp" in data, f"Missing 'timestamp' field in {' '.join(cmd)}"

            # List responses should include count
            if isinstance(data["data"], list):
                assert "count" in data, f"Missing 'count' field for list in {' '.join(cmd)}"
                assert data["count"] == len(data["data"]), f"Count mismatch in {' '.join(cmd)}"


def test_handoff_list_json(initialized_project: Path):
    """Test handoff list with JSON output"""
    result = runner.invoke(app, ["handoff", "list", "--json"])

    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    data = json.loads(result.stdout)
    assert "data" in data
    assert "count" in data
    assert "timestamp" in data
    assert isinstance(data["data"], list)


def test_handoff_show_json(initialized_project: Path):
    """Test handoff show with JSON output"""
    # First, list handoffs to get an ID
    list_result = runner.invoke(app, ["handoff", "list", "--json"])

    if list_result.exit_code == 0:
        list_data = json.loads(list_result.stdout)

        # If there are handoffs, test show command
        if list_data["count"] > 0:
            handoff_id = list_data["data"][0]["id"]
            result = runner.invoke(app, ["handoff", "show", str(handoff_id), "--json"])

            assert result.exit_code == 0, f"Command failed: {result.stdout}"

            data = json.loads(result.stdout)
            assert "data" in data
            assert "timestamp" in data
            assert isinstance(data["data"], dict)
            assert "id" in data["data"]


def test_review_list_json(initialized_project: Path):
    """Test review list with JSON output"""
    result = runner.invoke(app, ["review", "list", "--json"])

    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    data = json.loads(result.stdout)
    assert "data" in data
    assert "count" in data
    assert "timestamp" in data
    assert isinstance(data["data"], list)


def test_review_show_json(initialized_project: Path):
    """Test review show with JSON output"""
    # First, list reviews to get an ID
    list_result = runner.invoke(app, ["review", "list", "--json"])

    if list_result.exit_code == 0:
        list_data = json.loads(list_result.stdout)

        # If there are reviews, test show command
        if list_data["count"] > 0:
            review_id = list_data["data"][0]["id"]
            result = runner.invoke(app, ["review", "show", str(review_id), "--json"])

            assert result.exit_code == 0, f"Command failed: {result.stdout}"

            data = json.loads(result.stdout)
            assert "data" in data
            assert "timestamp" in data
            assert isinstance(data["data"], dict)
            assert "id" in data["data"]


def test_name_list_json(initialized_project: Path):
    """Test name list with JSON output"""
    result = runner.invoke(app, ["name", "list", "--json"])

    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    data = json.loads(result.stdout)
    assert "data" in data
    assert "count" in data
    assert "timestamp" in data
    assert isinstance(data["data"], list)


def test_name_suggest_json(initialized_project: Path):
    """Test name suggest with JSON output"""
    result = runner.invoke(app, ["name", "suggest", "Operator", "--json"])

    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    data = json.loads(result.stdout)
    assert "data" in data
    assert "count" in data
    assert "timestamp" in data
    assert isinstance(data["data"], list)


def test_name_show_json(initialized_project: Path):
    """Test name show with JSON output"""
    # First, list names to get one
    list_result = runner.invoke(app, ["name", "list", "--json"])

    if list_result.exit_code == 0:
        list_data = json.loads(list_result.stdout)

        # If there are personas, test show command
        if list_data["count"] > 0:
            persona_name = list_data["data"][0]["name"]
            result = runner.invoke(app, ["name", "show", persona_name, "--json"])

            assert result.exit_code == 0, f"Command failed: {result.stdout}"

            data = json.loads(result.stdout)
            assert "data" in data
            assert "timestamp" in data
            assert isinstance(data["data"], dict)
            assert "name" in data["data"]


def test_mission_summary_json(initialized_project: Path):
    """Test mission summary with JSON output"""
    # First, list missions to get an ID
    list_result = runner.invoke(app, ["mission", "list", "--json"])

    if list_result.exit_code == 0:
        list_data = json.loads(list_result.stdout)

        # If there are missions, test summary command
        if list_data["count"] > 0:
            mission_id = list_data["data"][0]["id"]
            result = runner.invoke(app, ["mission", "summary", str(mission_id), "--json"])

            assert result.exit_code == 0, f"Command failed: {result.stdout}"

            data = json.loads(result.stdout)
            assert "data" in data
            assert "timestamp" in data
            assert isinstance(data["data"], dict)

            # Verify mission summary structure
            assert "mission_id" in data["data"]
            assert "persona_name" in data["data"]
            assert "role" in data["data"]
            assert "files_changed" in data["data"]
            assert "commits" in data["data"]
            assert "tasks" in data["data"]

            # Verify data types
            assert isinstance(data["data"]["files_changed"], list)
            assert isinstance(data["data"]["commits"], list)
            assert isinstance(data["data"]["tasks"], list)


def test_mission_roles_json(initialized_project: Path):
    """Test mission roles with JSON output"""
    result = runner.invoke(app, ["mission", "roles", "--json"])

    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    data = json.loads(result.stdout)
    assert "data" in data
    assert "count" in data
    assert "timestamp" in data
    assert isinstance(data["data"], list)

    # Verify we have roles
    assert data["count"] > 0

    # Verify role structure
    for role in data["data"]:
        assert "name" in role
        assert "description" in role
        assert isinstance(role["name"], str)
        assert isinstance(role["description"], str)


def test_mission_show_not_found_json_error(initialized_project: Path):
    """Test that mission show returns JSON error for non-existent mission"""
    # Use a very large ID that doesn't exist
    result = runner.invoke(app, ["mission", "show", "999999", "--json"])

    # Command should exit with error code
    assert result.exit_code != 0, "Expected non-zero exit code for not found"

    # Parse JSON error response
    try:
        data = json.loads(result.stdout)

        # Verify error response structure
        assert "status" in data
        assert data["status"] == "error"
        assert "error" in data
        assert "timestamp" in data

        # Verify error details
        assert "mission" in data["error"].lower() or "not found" in data["error"].lower()

        # Check for optional error code and details
        if "error_code" in data:
            assert data["error_code"] == "MISSION_NOT_FOUND"
        if "details" in data:
            assert "mission_id" in data["details"]

    except json.JSONDecodeError as e:
        raise AssertionError(f"Expected JSON error response, got: {result.stdout}\nError: {e}")


def test_mission_summary_not_found_json_error(initialized_project: Path):
    """Test that mission summary returns JSON error for non-existent mission"""
    result = runner.invoke(app, ["mission", "summary", "999999", "--json"])

    # Command should exit with error code
    assert result.exit_code != 0, "Expected non-zero exit code for not found"

    # Parse JSON error response
    try:
        data = json.loads(result.stdout)

        # Verify error response structure
        assert "status" in data
        assert data["status"] == "error"
        assert "error" in data
        assert "timestamp" in data

    except json.JSONDecodeError as e:
        raise AssertionError(f"Expected JSON error response, got: {result.stdout}\nError: {e}")
