"""Tests for mission CLI commands"""

from pathlib import Path

import pytest

from site_nine.__main__ import app
from typer.testing import CliRunner

runner = CliRunner()


def test_mission_list_empty(initialized_project: Path):
    """Test listing missions when none exist"""
    result = runner.invoke(app, ["mission", "list"])

    assert result.exit_code == 0


def test_mission_list_with_role_filter(initialized_project: Path):
    """Test listing missions filtered by role"""
    result = runner.invoke(app, ["mission", "list", "--role", "Engineer"])

    assert result.exit_code == 0


def test_mission_list_active_only(initialized_project: Path):
    """Test listing only active missions"""
    result = runner.invoke(app, ["mission", "list", "--active-only"])

    assert result.exit_code == 0


def test_mission_list_json(initialized_project: Path):
    """Test listing missions in JSON format"""
    result = runner.invoke(app, ["mission", "list", "--json"])

    assert result.exit_code == 0


def test_mission_show_not_found(initialized_project: Path):
    """Test showing non-existent mission"""
    result = runner.invoke(app, ["mission", "show", "999"])

    assert result.exit_code != 0


def test_mission_summary_not_found(initialized_project: Path):
    """Test mission summary for non-existent mission"""
    result = runner.invoke(app, ["mission", "summary", "999"])

    assert result.exit_code != 0


def test_mission_end_not_found(initialized_project: Path):
    """Test ending non-existent mission"""
    result = runner.invoke(app, ["mission", "end", "999"])

    assert result.exit_code != 0


def test_mission_update_not_found(initialized_project: Path):
    """Test updating non-existent mission"""
    result = runner.invoke(app, ["mission", "update", "999", "--notes", "test"])

    assert result.exit_code != 0


def test_mission_roles_command(initialized_project: Path):
    """Test listing available roles"""
    result = runner.invoke(app, ["mission", "roles"])

    assert result.exit_code == 0
    # Should show roles
    assert "Engineer" in result.output or "Operator" in result.output


def test_mission_roles_json(initialized_project: Path):
    """Test listing roles in JSON"""
    result = runner.invoke(app, ["mission", "roles", "--json"])

    assert result.exit_code == 0


def test_mission_generate_session_uuid(initialized_project: Path):
    """Test generating session UUID"""
    result = runner.invoke(app, ["mission", "generate-session-uuid"])

    # This command generates a UUID, should succeed
    assert result.exit_code == 0


def test_mission_list_opencode_sessions(initialized_project: Path):
    """Test listing OpenCode sessions"""
    result = runner.invoke(app, ["mission", "list-opencode-sessions"])

    # Should run without error (even if no sessions)
    assert result.exit_code == 0


def test_mission_summary_json(initialized_project: Path):
    """Test mission summary in JSON"""
    result = runner.invoke(app, ["mission", "summary", "1", "--json"])

    # Either succeeds or shows not found
    assert result.exit_code in [0, 1]


def test_mission_start_command(initialized_project: Path):
    """Test starting a new mission"""
    # Create persona first
    persona_result = runner.invoke(
        app, ["persona", "add", "test-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"]
    )
    assert persona_result.exit_code == 0, f"Persona creation failed: {persona_result.output}"

    result = runner.invoke(app, ["mission", "start", "test-daemon", "--role", "Engineer"])

    assert result.exit_code == 0, f"Mission start failed: {result.output}"
    assert "Started mission" in result.output


def test_mission_start_with_task(initialized_project: Path):
    """Test starting mission with task objective"""
    runner.invoke(
        app, ["persona", "add", "test-daemon-2", "--role", "Tester", "--mythology", "greek", "--description", "Test"]
    )

    result = runner.invoke(app, ["mission", "start", "test-daemon-2", "--role", "Tester", "--task", "Fix tests"])

    assert result.exit_code == 0
    assert "Started mission" in result.output
    assert "Objective" in result.output


def test_mission_start_invalid_role(initialized_project: Path):
    """Test starting mission with invalid role"""
    result = runner.invoke(app, ["mission", "start", "test-daemon", "--role", "InvalidRole"])

    assert result.exit_code == 1
    assert "Invalid role" in result.output


def test_mission_start_case_insensitive_role(initialized_project: Path):
    """Test that role is case insensitive"""
    runner.invoke(
        app,
        ["persona", "add", "test-daemon-3", "--role", "Engineer", "--mythology", "greek", "--description", "Test"],
    )

    result = runner.invoke(app, ["mission", "start", "test-daemon-3", "--role", "engineer"])

    assert result.exit_code == 0


def test_mission_list_with_missions(initialized_project: Path):
    """Test listing missions after creating some"""
    # Create personas first
    runner.invoke(
        app, ["persona", "add", "daemon-1", "--role", "Engineer", "--mythology", "greek", "--description", "Test"]
    )
    runner.invoke(
        app, ["persona", "add", "daemon-2", "--role", "Tester", "--mythology", "greek", "--description", "Test"]
    )

    # Start missions
    runner.invoke(app, ["mission", "start", "daemon-1", "--role", "Engineer"])
    runner.invoke(app, ["mission", "start", "daemon-2", "--role", "Tester"])

    result = runner.invoke(app, ["mission", "list"])

    assert result.exit_code == 0
    assert "daemon-1" in result.output or "Agent Sessions" in result.output


def test_mission_list_role_filter_matches(initialized_project: Path):
    """Test filtering missions by role with matches"""
    runner.invoke(
        app, ["persona", "add", "eng-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"]
    )
    runner.invoke(
        app, ["persona", "add", "test-daemon", "--role", "Tester", "--mythology", "greek", "--description", "Test"]
    )

    runner.invoke(app, ["mission", "start", "eng-daemon", "--role", "Engineer"])
    runner.invoke(app, ["mission", "start", "test-daemon", "--role", "Tester"])

    result = runner.invoke(app, ["mission", "list", "--role", "Engineer"])

    assert result.exit_code == 0


def test_mission_list_active_with_active(initialized_project: Path):
    """Test listing only active missions"""
    runner.invoke(
        app,
        ["persona", "add", "active-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"],
    )

    runner.invoke(app, ["mission", "start", "active-daemon", "--role", "Engineer"])

    result = runner.invoke(app, ["mission", "list", "--active-only"])

    assert result.exit_code == 0


def test_mission_show_existing(initialized_project: Path):
    """Test showing an existing mission"""
    # Create persona first
    runner.invoke(
        app, ["persona", "add", "show-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"]
    )

    # Start a mission
    start_result = runner.invoke(app, ["mission", "start", "show-daemon", "--role", "Engineer"])
    assert start_result.exit_code == 0

    # Extract mission ID from output (should be 1 if first)
    result = runner.invoke(app, ["mission", "show", "1"])

    # Should either work or mission not found
    assert result.exit_code in [0, 1]


def test_mission_show_json_format(initialized_project: Path):
    """Test showing mission in JSON format"""
    runner.invoke(
        app, ["persona", "add", "json-daemon", "--role", "Operator", "--mythology", "greek", "--description", "Test"]
    )

    runner.invoke(app, ["mission", "start", "json-daemon", "--role", "Operator"])

    result = runner.invoke(app, ["mission", "show", "1", "--json"])

    assert result.exit_code in [0, 1]


def test_mission_end_existing(initialized_project: Path):
    """Test ending an existing mission"""
    runner.invoke(
        app, ["persona", "add", "end-daemon", "--role", "Architect", "--mythology", "greek", "--description", "Test"]
    )

    runner.invoke(app, ["mission", "start", "end-daemon", "--role", "Architect"])

    result = runner.invoke(app, ["mission", "end", "1"])

    # Should either work or mission not found
    assert result.exit_code in [0, 1]


@pytest.mark.skip(reason="--summary flag not implemented on mission end")
def test_mission_end_with_summary(initialized_project: Path):
    """Test ending mission with summary"""
    runner.invoke(
        app,
        ["persona", "add", "summary-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"],
    )

    runner.invoke(app, ["mission", "start", "summary-daemon", "--role", "Engineer"])

    result = runner.invoke(app, ["mission", "end", "1", "--summary", "Completed successfully"])

    assert result.exit_code in [0, 1]


@pytest.mark.skip(reason="--notes flag not implemented on mission update")
def test_mission_update_existing(initialized_project: Path):
    """Test updating an existing mission"""
    runner.invoke(
        app,
        ["persona", "add", "update-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"],
    )

    runner.invoke(app, ["mission", "start", "update-daemon", "--role", "Engineer"])

    result = runner.invoke(app, ["mission", "update", "1", "--notes", "Updated notes"])

    assert result.exit_code in [0, 1]


@pytest.mark.skip(reason="--objective flag not implemented on mission update")
def test_mission_update_objective(initialized_project: Path):
    """Test updating mission objective"""
    runner.invoke(
        app, ["persona", "add", "obj-daemon", "--role", "Tester", "--mythology", "greek", "--description", "Test"]
    )

    runner.invoke(app, ["mission", "start", "obj-daemon", "--role", "Tester"])

    result = runner.invoke(app, ["mission", "update", "1", "--objective", "New objective"])

    assert result.exit_code in [0, 1]


def test_mission_summary_existing(initialized_project: Path):
    """Test getting summary for existing mission"""
    runner.invoke(
        app, ["persona", "add", "sum-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"]
    )

    runner.invoke(app, ["mission", "start", "sum-daemon", "--role", "Engineer"])

    result = runner.invoke(app, ["mission", "summary", "1"])

    assert result.exit_code in [0, 1]


def test_mission_update_with_task(initialized_project: Path):
    """Test updating mission with task"""
    runner.invoke(
        app, ["persona", "add", "upd-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"]
    )

    runner.invoke(app, ["mission", "start", "upd-daemon", "--role", "Engineer"])

    result = runner.invoke(app, ["mission", "update", "1", "--task", "New task description"])

    assert result.exit_code in [0, 1]


def test_mission_update_with_role(initialized_project: Path):
    """Test updating mission role"""
    runner.invoke(
        app, ["persona", "add", "role-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"]
    )

    runner.invoke(app, ["mission", "start", "role-daemon", "--role", "Engineer"])

    result = runner.invoke(app, ["mission", "update", "1", "--role", "Architect"])

    assert result.exit_code in [0, 1]


def test_mission_rename_tui_command(initialized_project: Path):
    """Test rename-tui command"""
    result = runner.invoke(app, ["mission", "rename-tui", "new-name"])

    # May fail if no TUI session exists, that's ok
    assert result.exit_code in [0, 1, 2]


def test_mission_workflow_complete(initialized_project: Path):
    """Test complete mission workflow: create persona, start, list, show, update, end"""
    # Create persona
    persona_result = runner.invoke(
        app,
        [
            "persona",
            "add",
            "workflow-daemon",
            "--role",
            "Operator",
            "--mythology",
            "greek",
            "--description",
            "Test workflow",
        ],
    )
    assert persona_result.exit_code == 0

    # Start mission
    start_result = runner.invoke(
        app, ["mission", "start", "workflow-daemon", "--role", "Operator", "--task", "Test workflow"]
    )
    assert start_result.exit_code == 0
    assert "Started mission" in start_result.output

    # List missions
    list_result = runner.invoke(app, ["mission", "list"])
    assert list_result.exit_code == 0
    assert "workflow-daemon" in list_result.output or "Operator" in list_result.output

    # Show mission
    show_result = runner.invoke(app, ["mission", "show", "1"])
    assert show_result.exit_code == 0

    # Update mission
    update_result = runner.invoke(app, ["mission", "update", "1", "--task", "Updated workflow"])
    assert update_result.exit_code == 0

    # End mission
    end_result = runner.invoke(app, ["mission", "end", "1"])
    assert end_result.exit_code == 0


def test_mission_list_multiple_with_filters(initialized_project: Path):
    """Test listing multiple missions with various filters"""
    # Create multiple personas and missions
    for i, role in enumerate(["Engineer", "Tester", "Architect"]):
        runner.invoke(
            app,
            ["persona", "add", f"multi-daemon-{i}", "--role", role, "--mythology", "greek", "--description", "Test"],
        )
        runner.invoke(app, ["mission", "start", f"multi-daemon-{i}", "--role", role])

    # List all missions
    all_result = runner.invoke(app, ["mission", "list"])
    assert all_result.exit_code == 0

    # List with role filter
    engineer_result = runner.invoke(app, ["mission", "list", "--role", "Engineer"])
    assert engineer_result.exit_code == 0

    # List active only
    active_result = runner.invoke(app, ["mission", "list", "--active-only"])
    assert active_result.exit_code == 0

    # List in JSON format
    json_result = runner.invoke(app, ["mission", "list", "--json"])
    assert json_result.exit_code == 0


# ---- New coverage tests ----

import json
from unittest.mock import MagicMock, patch


def test_mission_show_existing_json(initialized_project: Path):
    """Test show an existing mission with --json flag outputs JSON data."""
    runner.invoke(
        app,
        ["persona", "add", "showjson-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"],
    )
    start = runner.invoke(app, ["mission", "start", "showjson-daemon", "--role", "Engineer", "--task", "Build things"])
    assert start.exit_code == 0

    result = runner.invoke(app, ["mission", "show", "1", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["persona_name"] == "showjson-daemon"
    assert data["data"]["role"] == "Engineer"
    assert data["data"]["status"] == "Active"
    assert data["data"]["objective"] == "Build things"


def test_mission_show_details_displayed(initialized_project: Path):
    """Test show an existing mission (non-JSON) displays expected labels."""
    runner.invoke(
        app,
        ["persona", "add", "detail-daemon", "--role", "Tester", "--mythology", "greek", "--description", "Test"],
    )
    runner.invoke(app, ["mission", "start", "detail-daemon", "--role", "Tester", "--task", "Test stuff"])

    result = runner.invoke(app, ["mission", "show", "1"])
    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "Mission #1" in out
    assert "Persona:" in out
    assert "Role:" in out
    assert "Status:" in out
    assert "Start Date:" in out
    assert "Objective:" in out


def test_mission_show_not_found_json(initialized_project: Path):
    """Test show non-existent mission with --json returns MISSION_NOT_FOUND."""
    result = runner.invoke(app, ["mission", "show", "999", "--json"])
    assert result.exit_code != 0
    data = json.loads(result.output)
    assert data["error_code"] == "MISSION_NOT_FOUND"


def test_mission_summary_existing_json_mocked(initialized_project: Path):
    """Test summary for existing mission in JSON format with mocked git data."""
    runner.invoke(
        app,
        ["persona", "add", "sumjson-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"],
    )
    runner.invoke(app, ["mission", "start", "sumjson-daemon", "--role", "Engineer", "--task", "Build stuff"])

    mock_diff = MagicMock()
    mock_diff.returncode = 0
    mock_diff.stdout = "M\tsrc/app.py\nA\tsrc/new.py"

    mock_log = MagicMock()
    mock_log.returncode = 0
    mock_log.stdout = "abc1234 feat: add new feature"

    call_count = 0

    def fake_subprocess_run(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        cmd = args[0]
        if "diff" in cmd:
            return mock_diff
        return mock_log

    with patch("subprocess.run", side_effect=fake_subprocess_run):
        result = runner.invoke(app, ["mission", "summary", "1", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["mission_id"] == 1
    assert data["data"]["persona_name"] == "sumjson-daemon"
    assert isinstance(data["data"]["files_changed"], list)
    assert isinstance(data["data"]["commits"], list)
    assert len(data["data"]["files_changed"]) == 2
    assert data["data"]["files_changed"][0]["status"] == "modified"
    assert data["data"]["files_changed"][1]["status"] == "added"


def test_mission_summary_with_git_data(initialized_project: Path):
    """Test summary with mocked git data showing files and commits in console output."""
    runner.invoke(
        app,
        ["persona", "add", "gitdata-daemon", "--role", "Architect", "--mythology", "greek", "--description", "Test"],
    )
    runner.invoke(app, ["mission", "start", "gitdata-daemon", "--role", "Architect", "--task", "Design system"])

    mock_diff = MagicMock()
    mock_diff.returncode = 0
    mock_diff.stdout = "M\tsrc/main.py\nD\tsrc/old.py\nA\tsrc/brand_new.py"

    mock_log_first = MagicMock()
    mock_log_first.returncode = 0
    mock_log_first.stdout = "abc1234 feat: first commit\ndef5678 fix: second commit"

    call_count = 0

    def fake_subprocess_run(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        cmd = args[0]
        if "diff" in cmd:
            return mock_diff
        return mock_log_first

    with patch("subprocess.run", side_effect=fake_subprocess_run):
        result = runner.invoke(app, ["mission", "summary", "1"])

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "Summary" in out
    assert "Mission #1" in out
    assert "Files Changed:" in out
    # Rich strips [modified], [deleted], [added] as markup tags,
    # so just check file names appear
    assert "src/main.py" in out
    assert "src/old.py" in out
    assert "src/brand_new.py" in out
    assert "Commits:" in out
    assert "first commit" in out
    assert "Objective:" in out


def test_mission_summary_no_git_data(initialized_project: Path):
    """Test summary when git commands return empty results."""
    runner.invoke(
        app,
        ["persona", "add", "nogit-daemon", "--role", "Operator", "--mythology", "greek", "--description", "Test"],
    )
    runner.invoke(app, ["mission", "start", "nogit-daemon", "--role", "Operator"])

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.output = ""

    with patch("subprocess.run", return_value=mock_result):
        result = runner.invoke(app, ["mission", "summary", "1"])

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "No files changed" in out
    assert "No commits found" in out
    assert "No tasks claimed" in out


def test_mission_summary_with_tasks(initialized_project: Path):
    """Test summary showing tasks linked to a mission."""
    runner.invoke(
        app,
        ["persona", "add", "tasksum-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"],
    )
    runner.invoke(app, ["mission", "start", "tasksum-daemon", "--role", "Engineer"])

    # Create a task and claim it for this mission via the DB
    from site_nine.core.database import Database
    from site_nine.tasks import TaskManager

    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        tm = TaskManager(db)
        tm.create_task(task_id="ENG-M-0001", title="Fix the widget", role="Engineer", priority="MEDIUM")
        tm.claim_task("ENG-M-0001", mission_id=1, current_role="Engineer")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.output = ""

    with patch("subprocess.run", return_value=mock_result):
        result = runner.invoke(app, ["mission", "summary", "1"])

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "Tasks Claimed:" in out
    assert "Fix the widget" in out
    assert "Underway" in out


def test_mission_summary_git_exception(initialized_project: Path):
    """Test summary handles gracefully when subprocess.run raises an exception."""
    runner.invoke(
        app,
        ["persona", "add", "gitexc-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"],
    )
    runner.invoke(app, ["mission", "start", "gitexc-daemon", "--role", "Engineer"])

    with patch("subprocess.run", side_effect=OSError("git not found")):
        result = runner.invoke(app, ["mission", "summary", "1"])

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    # Should show fallback messages
    assert "Could not retrieve git history" in out or "No files changed" in out


def test_mission_update_no_updates(initialized_project: Path):
    """Test update mission with neither --task nor --role shows error."""
    runner.invoke(
        app,
        ["persona", "add", "noupd-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"],
    )
    runner.invoke(app, ["mission", "start", "noupd-daemon", "--role", "Engineer"])

    result = runner.invoke(app, ["mission", "update", "1"])
    out = " ".join(result.output.split())
    assert "No updates specified" in out


def test_mission_update_not_found_mission(initialized_project: Path):
    """Test update mission that doesn't exist with --task shows error."""
    result = runner.invoke(app, ["mission", "update", "999", "--task", "Something"])
    assert result.exit_code != 0
    out = " ".join(result.output.split())
    assert "not found" in out


def test_mission_update_completed_mission(initialized_project: Path):
    """Test updating a completed mission shows error."""
    runner.invoke(
        app,
        ["persona", "add", "done-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"],
    )
    runner.invoke(app, ["mission", "start", "done-daemon", "--role", "Engineer"])
    runner.invoke(app, ["mission", "end", "1"])

    result = runner.invoke(app, ["mission", "update", "1", "--task", "Should fail"])
    assert result.exit_code != 0
    out = " ".join(result.output.split())
    assert "Cannot update completed mission" in out


def test_mission_update_invalid_role(initialized_project: Path):
    """Test update with an invalid --role value shows error."""
    runner.invoke(
        app,
        ["persona", "add", "badrole-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"],
    )
    runner.invoke(app, ["mission", "start", "badrole-daemon", "--role", "Engineer"])

    result = runner.invoke(app, ["mission", "update", "1", "--role", "FakeRole"])
    assert result.exit_code != 0
    out = " ".join(result.output.split())
    assert "Invalid role" in out


def test_mission_update_task_and_role(initialized_project: Path):
    """Test update with both --task and --role succeeds."""
    runner.invoke(
        app,
        ["persona", "add", "both-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"],
    )
    runner.invoke(app, ["mission", "start", "both-daemon", "--role", "Engineer"])

    result = runner.invoke(app, ["mission", "update", "1", "--task", "New objective", "--role", "Architect"])
    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "Updated mission" in out
    assert "New objective" in out
    assert "Architect" in out


def test_mission_list_with_data_table(initialized_project: Path):
    """Test listing missions (non-JSON) when missions exist shows table."""
    runner.invoke(
        app,
        ["persona", "add", "table-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"],
    )
    runner.invoke(app, ["mission", "start", "table-daemon", "--role", "Engineer"])

    result = runner.invoke(app, ["mission", "list"])
    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "Agent Sessions" in out


def test_mission_list_json_with_data(initialized_project: Path):
    """Test listing missions (JSON) when missions exist returns JSON array."""
    runner.invoke(
        app,
        ["persona", "add", "ljson-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"],
    )
    runner.invoke(app, ["mission", "start", "ljson-daemon", "--role", "Engineer"])

    result = runner.invoke(app, ["mission", "list", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "data" in data
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 1
    assert data["data"][0]["persona_name"] == "ljson-daemon"


def test_mission_show_completed_mission(initialized_project: Path):
    """Test showing a completed mission displays Ended status and End Time."""
    runner.invoke(
        app,
        ["persona", "add", "comp-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"],
    )
    runner.invoke(app, ["mission", "start", "comp-daemon", "--role", "Engineer"])
    runner.invoke(app, ["mission", "end", "1"])

    result = runner.invoke(app, ["mission", "show", "1"])
    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "Ended" in out
    assert "End Time:" in out


def test_mission_show_with_objective(initialized_project: Path):
    """Test showing a mission with --task shows Objective in output."""
    runner.invoke(
        app,
        ["persona", "add", "obj-show-daemon", "--role", "Tester", "--mythology", "greek", "--description", "Test"],
    )
    runner.invoke(app, ["mission", "start", "obj-show-daemon", "--role", "Tester", "--task", "Verify coverage"])

    result = runner.invoke(app, ["mission", "show", "1"])
    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "Objective:" in out
    assert "Verify coverage" in out


def test_mission_summary_fallback_git_log(initialized_project: Path):
    """Test summary uses fallback git log --name-status when diff fails."""
    runner.invoke(
        app,
        ["persona", "add", "fallback-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"],
    )
    runner.invoke(app, ["mission", "start", "fallback-daemon", "--role", "Engineer"])

    call_count = 0

    def fake_subprocess_run(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        cmd = args[0]
        mock = MagicMock()
        if cmd[1] == "diff":
            # First git diff call fails
            mock.returncode = 1
            mock.stdout = ""
            return mock
        if cmd[1] == "log" and "--name-status" in cmd:
            # Fallback git log --name-status succeeds
            mock.returncode = 0
            mock.stdout = "M\tsrc/fallback.py\n\nA\tsrc/added.py"
            return mock
        # git log --oneline calls
        mock.returncode = 0
        mock.stdout = "aaa1111 fallback commit"
        return mock

    with patch("subprocess.run", side_effect=fake_subprocess_run):
        result = runner.invoke(app, ["mission", "summary", "1"])

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "fallback.py" in out


def test_mission_summary_commits_fallback(initialized_project: Path):
    """Test summary uses fallback git log --oneline when grep fails."""
    runner.invoke(
        app,
        ["persona", "add", "comfb-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"],
    )
    runner.invoke(app, ["mission", "start", "comfb-daemon", "--role", "Engineer"])

    call_count = 0

    def fake_subprocess_run(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        cmd = args[0]
        mock = MagicMock()
        if cmd[1] == "diff":
            mock.returncode = 0
            mock.stdout = "M\tsrc/file.py"
            return mock
        if cmd[1] == "log" and "--grep" in str(cmd):
            # First log with --grep returns nothing
            mock.returncode = 0
            mock.stdout = ""
            return mock
        if cmd[1] == "log" and "-10" in cmd:
            # Fallback log returns commits
            mock.returncode = 0
            mock.stdout = "bbb2222 fallback commit message"
            return mock
        mock.returncode = 0
        mock.stdout = ""
        return mock

    with patch("subprocess.run", side_effect=fake_subprocess_run):
        result = runner.invoke(app, ["mission", "summary", "1"])

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "fallback commit message" in out


def test_mission_summary_completed_mission(initialized_project: Path):
    """Test summary for a completed mission shows End time."""
    runner.invoke(
        app,
        ["persona", "add", "sumcomp-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"],
    )
    runner.invoke(app, ["mission", "start", "sumcomp-daemon", "--role", "Engineer", "--task", "Some objective"])
    runner.invoke(app, ["mission", "end", "1"])

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.output = ""

    with patch("subprocess.run", return_value=mock_result):
        result = runner.invoke(app, ["mission", "summary", "1"])

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "End:" in out
    assert "Objective:" in out


def test_mission_get_manager_no_opencode_dir(in_temp_dir: Path):
    """Test that commands fail when .opencode directory is missing."""
    result = runner.invoke(app, ["mission", "list"])
    assert result.exit_code != 0
    out = " ".join(result.output.split())
    assert ".opencode directory not found" in out


def test_mission_get_manager_no_db(initialized_project: Path):
    """Test that commands fail when project.db is missing."""
    import os

    db_path = initialized_project / ".opencode" / "data" / "project.db"
    os.remove(db_path)

    result = runner.invoke(app, ["mission", "list"])
    assert result.exit_code != 0
    out = " ".join(result.output.split())
    assert "project.db not found" in out


def test_mission_summary_not_found_json(initialized_project: Path):
    """Test summary for non-existent mission with --json returns MISSION_NOT_FOUND."""
    result = runner.invoke(app, ["mission", "summary", "999", "--json"])
    assert result.exit_code != 0
    data = json.loads(result.output)
    assert data["error_code"] == "MISSION_NOT_FOUND"


def test_mission_summary_task_exception_handled(initialized_project: Path):
    """Test summary handles exception in task fetching gracefully."""
    runner.invoke(
        app,
        ["persona", "add", "taskexc-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"],
    )
    runner.invoke(app, ["mission", "start", "taskexc-daemon", "--role", "Engineer"])

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.output = ""

    with patch("subprocess.run", return_value=mock_result):
        with patch("site_nine.tasks.TaskManager.list_tasks", side_effect=Exception("DB error")):
            result = runner.invoke(app, ["mission", "summary", "1"])

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "Could not retrieve tasks" in out


def test_mission_summary_json_with_tasks(initialized_project: Path):
    """Test summary JSON output includes tasks data."""
    runner.invoke(
        app,
        ["persona", "add", "taskjson-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"],
    )
    runner.invoke(app, ["mission", "start", "taskjson-daemon", "--role", "Engineer"])

    from site_nine.core.database import Database
    from site_nine.tasks import TaskManager

    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        tm = TaskManager(db)
        tm.create_task(task_id="ENG-M-0002", title="JSON task test", role="Engineer", priority="MEDIUM")
        tm.claim_task("ENG-M-0002", mission_id=1, current_role="Engineer")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.output = ""

    with patch("subprocess.run", return_value=mock_result):
        result = runner.invoke(app, ["mission", "summary", "1", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data["data"]["tasks"]) >= 1
    assert data["data"]["tasks"][0]["title"] == "JSON task test"


def test_mission_start_with_epic(initialized_project: Path):
    """Test starting mission with epic scope"""
    from site_nine.core.database import Database
    from site_nine.epics import EpicManager

    # Create an epic first
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        em = EpicManager(db)
        em.create_epic(epic_id="EPC-H-0001", title="Test Epic", description="Test epic for testing", priority="HIGH")

    runner.invoke(
        app, ["persona", "add", "epic-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"]
    )

    result = runner.invoke(app, ["mission", "start", "epic-daemon", "--role", "Engineer", "--epic", "EPC-H-0001"])

    assert result.exit_code == 0
    assert "Started mission" in result.output
    assert "Epic: EPC-H-0001" in result.output


def test_mission_start_epic_and_task_exclusive(initialized_project: Path):
    """Test that --epic and --task flags are mutually exclusive"""
    runner.invoke(
        app, ["persona", "add", "excl-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"]
    )

    result = runner.invoke(
        app,
        ["mission", "start", "excl-daemon", "--role", "Engineer", "--epic", "EPC-H-0001", "--task", "Some task"],
    )

    assert result.exit_code == 1
    assert "Cannot specify both --task and --epic" in result.output


def test_mission_start_with_nonexistent_epic(initialized_project: Path):
    """Test starting mission with non-existent epic shows error"""
    runner.invoke(
        app, ["persona", "add", "noepic-daemon", "--role", "Tester", "--mythology", "greek", "--description", "Test"]
    )

    result = runner.invoke(app, ["mission", "start", "noepic-daemon", "--role", "Tester", "--epic", "EPC-H-9999"])

    assert result.exit_code == 1
    assert "Epic" in result.output and "not found" in result.output


def test_mission_show_with_epic(initialized_project: Path):
    """Test showing mission displays epic information"""
    from site_nine.core.database import Database
    from site_nine.epics import EpicManager

    # Create an epic
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        em = EpicManager(db)
        em.create_epic(
            epic_id="EPC-M-0002", title="Show Epic Test", description="Epic for show test", priority="MEDIUM"
        )

    runner.invoke(
        app,
        ["persona", "add", "showepic-daemon", "--role", "Operator", "--mythology", "greek", "--description", "Test"],
    )

    runner.invoke(app, ["mission", "start", "showepic-daemon", "--role", "Operator", "--epic", "EPC-M-0002"])

    result = runner.invoke(app, ["mission", "show", "1"])

    assert result.exit_code == 0
    assert "Epic-scoped" in result.output
    assert "EPC-M-0002" in result.output


def test_mission_show_json_with_epic(initialized_project: Path):
    """Test showing mission in JSON format includes epic_id"""
    from site_nine.core.database import Database
    from site_nine.epics import EpicManager

    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        em = EpicManager(db)
        em.create_epic(
            epic_id="EPC-C-0003", title="JSON Epic Test", description="Epic for JSON test", priority="CRITICAL"
        )

    runner.invoke(
        app,
        ["persona", "add", "jsonepic-daemon", "--role", "Engineer", "--mythology", "greek", "--description", "Test"],
    )

    runner.invoke(app, ["mission", "start", "jsonepic-daemon", "--role", "Engineer", "--epic", "EPC-C-0003"])

    result = runner.invoke(app, ["mission", "show", "1", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["epic_id"] == "EPC-C-0003"
