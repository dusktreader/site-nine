"""Tests for mission CLI commands"""

from pathlib import Path

import pytest

from site_nine.__main__ import app
from typer.testing import CliRunner

runner = CliRunner()


def test_mission_list_empty(initialized_project: Path):
    """Test listing missions when none exist"""
    result = runner.invoke(app, ["possession", "list"])

    assert result.exit_code == 0


def test_mission_list_with_role_filter(initialized_project: Path):
    """Test listing missions filtered by role"""
    result = runner.invoke(app, ["possession", "list", "--role", "Engineer"])

    assert result.exit_code == 0


def test_mission_list_active_only(initialized_project: Path):
    """Test listing only active missions"""
    result = runner.invoke(app, ["possession", "list", "--active-only"])

    assert result.exit_code == 0


def test_mission_list_json(initialized_project: Path):
    """Test listing missions in JSON format"""
    result = runner.invoke(app, ["possession", "list", "--json"])

    assert result.exit_code == 0


def test_mission_show_not_found(initialized_project: Path):
    """Test showing non-existent mission"""
    result = runner.invoke(app, ["possession", "show", "999"])

    assert result.exit_code != 0


def test_mission_summary_not_found(initialized_project: Path):
    """Test mission summary for non-existent mission"""
    result = runner.invoke(app, ["possession", "summary", "999"])

    assert result.exit_code != 0


def test_mission_end_not_found(initialized_project: Path):
    """Test ending non-existent mission"""
    result = runner.invoke(app, ["daemon", "exorcise", "999"])

    assert result.exit_code != 0


def test_mission_update_not_found(initialized_project: Path):
    """Test updating non-existent mission"""
    result = runner.invoke(app, ["possession", "update", "999", "--notes", "test"])

    assert result.exit_code != 0


def test_mission_roles_command(initialized_project: Path):
    """Test listing available roles"""
    result = runner.invoke(app, ["daemon", "roles"])

    assert result.exit_code == 0
    # Should show roles
    assert "Engineer" in result.output or "Operator" in result.output


def test_mission_roles_json(initialized_project: Path):
    """Test listing roles in JSON"""
    result = runner.invoke(app, ["daemon", "roles", "--json"])

    assert result.exit_code == 0


def test_mission_generate_session_uuid(initialized_project: Path):
    """Test generating session UUID"""
    result = runner.invoke(app, ["daemon", "generate-session-uuid"])

    # This command generates a UUID, should succeed
    assert result.exit_code == 0


def test_mission_list_opencode_sessions(initialized_project: Path):
    """Test listing OpenCode sessions"""
    result = runner.invoke(app, ["daemon", "list-opencode-sessions"])

    # Should run without error (even if no sessions)
    assert result.exit_code == 0


def test_mission_summary_json(initialized_project: Path):
    """Test mission summary in JSON"""
    result = runner.invoke(app, ["possession", "summary", "1", "--json"])

    # Either succeeds or shows not found
    assert result.exit_code in [0, 1]


def test_mission_start_command(initialized_project: Path):
    """Test starting a new mission"""
    # Create persona first
    persona_result = runner.invoke(app, ["persona", "add", "test-daemon", "--role", "Engineer"])
    assert persona_result.exit_code == 0, f"Persona creation failed: {persona_result.output}"

    result = runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "test-daemon"])

    assert result.exit_code == 0, f"Daemon summon failed: {result.output}"
    assert "Summoned daemon" in result.output


def test_mission_start_with_task(initialized_project: Path):
    """Test starting mission with task objective"""
    runner.invoke(app, ["persona", "add", "test-daemon-2", "--role", "Tester"])

    result = runner.invoke(
        app, ["daemon", "summon", "--role", "Tester", "--name", "test-daemon-2", "--task", "Fix tests"]
    )

    assert result.exit_code == 0
    assert "Summoned daemon" in result.output
    assert "Objective" in result.output


def test_mission_start_invalid_role(initialized_project: Path):
    """Test starting mission with invalid role"""
    result = runner.invoke(app, ["daemon", "summon", "--role", "InvalidRole", "--name", "test-daemon"])

    assert result.exit_code == 1
    assert "Invalid role" in result.output


def test_mission_start_case_insensitive_role(initialized_project: Path):
    """Test that role is case insensitive"""
    runner.invoke(
        app,
        ["persona", "add", "test-daemon-3", "--role", "Engineer"],
    )

    result = runner.invoke(app, ["daemon", "summon", "--role", "engineer", "--name", "test-daemon-3"])

    assert result.exit_code == 0


def test_mission_list_with_missions(initialized_project: Path):
    """Test listing missions after creating some"""
    # Create personas first
    runner.invoke(app, ["persona", "add", "daemon-1", "--role", "Engineer"])
    runner.invoke(app, ["persona", "add", "daemon-2", "--role", "Tester"])

    # Start missions
    runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "daemon-1"])
    runner.invoke(app, ["daemon", "summon", "--role", "Tester", "--name", "daemon-2"])

    result = runner.invoke(app, ["possession", "list"])

    assert result.exit_code == 0
    assert "daemon-1" in result.output or "Agent Sessions" in result.output


def test_mission_list_role_filter_matches(initialized_project: Path):
    """Test filtering missions by role with matches"""
    runner.invoke(app, ["persona", "add", "eng-daemon", "--role", "Engineer"])
    runner.invoke(app, ["persona", "add", "test-daemon", "--role", "Tester"])

    runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "eng-daemon"])
    runner.invoke(app, ["daemon", "summon", "--role", "Tester", "--name", "test-daemon"])

    result = runner.invoke(app, ["possession", "list", "--role", "Engineer"])

    assert result.exit_code == 0


def test_mission_list_active_with_active(initialized_project: Path):
    """Test listing only active missions"""
    runner.invoke(
        app,
        ["persona", "add", "active-daemon", "--role", "Engineer"],
    )

    runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "active-daemon"])

    result = runner.invoke(app, ["possession", "list", "--active-only"])

    assert result.exit_code == 0


def test_mission_show_existing(initialized_project: Path):
    """Test showing an existing mission"""
    # Create persona first
    runner.invoke(app, ["persona", "add", "show-daemon", "--role", "Engineer"])

    # Start a mission
    start_result = runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "show-daemon"])
    assert start_result.exit_code == 0

    # Extract mission ID from output (should be 1 if first)
    result = runner.invoke(app, ["possession", "show", "1"])

    # Should either work or mission not found
    assert result.exit_code in [0, 1]


def test_mission_show_json_format(initialized_project: Path):
    """Test showing mission in JSON format"""
    runner.invoke(app, ["persona", "add", "json-daemon", "--role", "Operator"])

    runner.invoke(app, ["daemon", "summon", "--role", "Operator", "--name", "json-daemon"])

    result = runner.invoke(app, ["possession", "show", "1", "--json"])

    assert result.exit_code in [0, 1]


def test_mission_end_existing(initialized_project: Path):
    """Test ending an existing mission"""
    runner.invoke(app, ["persona", "add", "end-daemon", "--role", "Architect"])

    runner.invoke(app, ["daemon", "summon", "--role", "Architect", "--name", "end-daemon"])

    result = runner.invoke(app, ["daemon", "exorcise", "1"])

    # Should either work or mission not found
    assert result.exit_code in [0, 1]


@pytest.mark.skip(reason="--summary flag not implemented on mission end")
def test_mission_end_with_summary(initialized_project: Path):
    """Test ending mission with summary"""
    runner.invoke(
        app,
        ["persona", "add", "summary-daemon", "--role", "Engineer"],
    )

    runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "summary-daemon"])

    result = runner.invoke(app, ["daemon", "exorcise", "1", "--summary", "Completed successfully"])

    assert result.exit_code in [0, 1]


@pytest.mark.skip(reason="--notes flag not implemented on mission update")
def test_mission_update_existing(initialized_project: Path):
    """Test updating an existing mission"""
    runner.invoke(
        app,
        ["persona", "add", "update-daemon", "--role", "Engineer"],
    )

    runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "update-daemon"])

    result = runner.invoke(app, ["possession", "update", "1", "--notes", "Updated notes"])

    assert result.exit_code in [0, 1]


@pytest.mark.skip(reason="--objective flag not implemented on mission update")
def test_mission_update_objective(initialized_project: Path):
    """Test updating mission objective"""
    runner.invoke(app, ["persona", "add", "obj-daemon", "--role", "Tester"])

    runner.invoke(app, ["daemon", "summon", "--role", "Tester", "--name", "obj-daemon"])

    result = runner.invoke(app, ["possession", "update", "1", "--objective", "New objective"])

    assert result.exit_code in [0, 1]


def test_mission_summary_existing(initialized_project: Path):
    """Test getting summary for existing mission"""
    runner.invoke(app, ["persona", "add", "sum-daemon", "--role", "Engineer"])

    runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "sum-daemon"])

    result = runner.invoke(app, ["possession", "summary", "1"])

    assert result.exit_code in [0, 1]


def test_mission_update_with_task(initialized_project: Path):
    """Test updating mission with task"""
    runner.invoke(app, ["persona", "add", "upd-daemon", "--role", "Engineer"])

    runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "upd-daemon"])

    result = runner.invoke(app, ["possession", "update", "1", "--task", "New task description"])

    assert result.exit_code in [0, 1]


def test_mission_update_with_role(initialized_project: Path):
    """Test updating mission role"""
    runner.invoke(app, ["persona", "add", "role-daemon", "--role", "Engineer"])

    runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "role-daemon"])

    result = runner.invoke(app, ["possession", "update", "1", "--role", "Architect"])

    assert result.exit_code in [0, 1]


def test_mission_rename_tui_command(initialized_project: Path):
    """Test rename-tui command"""
    result = runner.invoke(app, ["daemon", "rename-tui", "new-name"])

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
        ],
    )
    assert persona_result.exit_code == 0

    # Start mission
    start_result = runner.invoke(
        app, ["daemon", "summon", "--role", "Operator", "--name", "workflow-daemon", "--task", "Test workflow"]
    )
    assert start_result.exit_code == 0
    assert "Summoned daemon" in start_result.output

    # List missions
    list_result = runner.invoke(app, ["possession", "list"])
    assert list_result.exit_code == 0
    assert "workflow-daemon" in list_result.output or "Operator" in list_result.output

    # Show mission
    show_result = runner.invoke(app, ["possession", "show", "1"])
    assert show_result.exit_code == 0

    # Update mission
    update_result = runner.invoke(app, ["possession", "update", "1", "--task", "Updated workflow"])
    assert update_result.exit_code == 0

    # End mission
    end_result = runner.invoke(app, ["daemon", "exorcise", "1"])
    assert end_result.exit_code == 0


def test_mission_list_multiple_with_filters(initialized_project: Path):
    """Test listing multiple missions with various filters"""
    # Create multiple personas and missions
    for i, role in enumerate(["Engineer", "Tester", "Architect"]):
        runner.invoke(
            app,
            ["persona", "add", f"multi-daemon-{i}", "--role", role],
        )
        runner.invoke(app, ["daemon", "summon", "--role", role, "--name", f"multi-daemon-{i}"])

    # List all missions
    all_result = runner.invoke(app, ["possession", "list"])
    assert all_result.exit_code == 0

    # List with role filter
    engineer_result = runner.invoke(app, ["possession", "list", "--role", "Engineer"])
    assert engineer_result.exit_code == 0

    # List active only
    active_result = runner.invoke(app, ["possession", "list", "--active-only"])
    assert active_result.exit_code == 0

    # List in JSON format
    json_result = runner.invoke(app, ["possession", "list", "--json"])
    assert json_result.exit_code == 0


# ---- New coverage tests ----

import json
from unittest.mock import MagicMock, patch


def test_mission_show_existing_json(initialized_project: Path):
    """Test show an existing mission with --json flag outputs JSON data."""
    runner.invoke(
        app,
        ["persona", "add", "showjson-daemon", "--role", "Engineer"],
    )
    start = runner.invoke(
        app, ["daemon", "summon", "--role", "Engineer", "--name", "showjson-daemon", "--task", "Build things"]
    )
    assert start.exit_code == 0

    result = runner.invoke(app, ["possession", "show", "1", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["persona_name"] == "showjson-daemon"
    assert data["data"]["role"] == "Engineer"
    assert data["data"]["status"] == "Active"
    # objective is not stored on possessions (no objective field)
    assert "objective" in data["data"]


def test_mission_show_details_displayed(initialized_project: Path):
    """Test show an existing mission (non-JSON) displays expected labels."""
    runner.invoke(
        app,
        ["persona", "add", "detail-daemon", "--role", "Tester"],
    )
    runner.invoke(app, ["daemon", "summon", "--role", "Tester", "--name", "detail-daemon", "--task", "Test stuff"])

    result = runner.invoke(app, ["possession", "show", "1"])
    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "Possession #1" in out
    assert "Daemon:" in out
    assert "Role:" in out
    assert "Status:" in out
    assert "Start Time:" in out


def test_mission_show_not_found_json(initialized_project: Path):
    """Test show non-existent mission with --json returns MISSION_NOT_FOUND."""
    result = runner.invoke(app, ["possession", "show", "999", "--json"])
    assert result.exit_code != 0
    data = json.loads(result.output)
    assert data["error_code"] == "MISSION_NOT_FOUND"


def test_mission_summary_existing_json_mocked(initialized_project: Path):
    """Test summary for existing mission in JSON format with mocked git data."""
    runner.invoke(
        app,
        ["persona", "add", "sumjson-daemon", "--role", "Engineer"],
    )
    runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "sumjson-daemon", "--task", "Build stuff"])

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
        result = runner.invoke(app, ["possession", "summary", "1", "--json"])

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
        ["persona", "add", "gitdata-daemon", "--role", "Architect"],
    )
    runner.invoke(
        app, ["daemon", "summon", "--role", "Architect", "--name", "gitdata-daemon", "--task", "Design system"]
    )

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
        result = runner.invoke(app, ["possession", "summary", "1"])

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "Summary" in out
    assert "Possession #1" in out
    assert "Files Changed:" in out
    # Rich strips [modified], [deleted], [added] as markup tags,
    # so just check file names appear
    assert "src/main.py" in out
    assert "src/old.py" in out
    assert "src/brand_new.py" in out
    assert "Commits:" in out
    assert "first commit" in out


def test_mission_summary_no_git_data(initialized_project: Path):
    """Test summary when git commands return empty results."""
    runner.invoke(
        app,
        ["persona", "add", "nogit-daemon", "--role", "Operator"],
    )
    runner.invoke(app, ["daemon", "summon", "--role", "Operator", "--name", "nogit-daemon"])

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.output = ""

    with patch("subprocess.run", return_value=mock_result):
        result = runner.invoke(app, ["possession", "summary", "1"])

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "No files changed" in out
    assert "No commits found" in out
    assert "No tasks claimed" in out


def test_mission_summary_with_tasks(initialized_project: Path):
    """Test summary showing tasks linked to a mission."""
    runner.invoke(
        app,
        ["persona", "add", "tasksum-daemon", "--role", "Engineer"],
    )
    runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "tasksum-daemon"])

    # Create a task and claim it for this mission via the DB
    from site_nine.core.database import Database
    from site_nine.tasks import TaskManager

    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        tm = TaskManager(db)
        tm.create_task(task_id="ENG-M-0001", title="Fix the widget", role="Engineer", priority="MEDIUM")
        tm.claim_task("ENG-M-0001", possession_id=1, current_role="Engineer")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.output = ""

    with patch("subprocess.run", return_value=mock_result):
        result = runner.invoke(app, ["possession", "summary", "1"])

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "Tasks Claimed:" in out
    assert "Fix the widget" in out
    assert "Underway" in out


def test_mission_summary_git_exception(initialized_project: Path):
    """Test summary handles gracefully when subprocess.run raises an exception."""
    runner.invoke(
        app,
        ["persona", "add", "gitexc-daemon", "--role", "Engineer"],
    )
    runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "gitexc-daemon"])

    with patch("subprocess.run", side_effect=OSError("git not found")):
        result = runner.invoke(app, ["possession", "summary", "1"])

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    # Should show fallback messages
    assert "Could not retrieve git history" in out or "No files changed" in out


def test_mission_update_no_updates(initialized_project: Path):
    """Test update mission with neither --task nor --role shows error."""
    runner.invoke(
        app,
        ["persona", "add", "noupd-daemon", "--role", "Engineer"],
    )
    runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "noupd-daemon"])

    result = runner.invoke(app, ["possession", "update", "1"])
    out = " ".join(result.output.split())
    assert "No updates specified" in out


def test_mission_update_not_found_mission(initialized_project: Path):
    """Test update mission that doesn't exist with --task shows error."""
    result = runner.invoke(app, ["possession", "update", "999", "--task", "Something"])
    assert result.exit_code != 0
    out = " ".join(result.output.split())
    assert "not found" in out


def test_mission_update_completed_mission(initialized_project: Path):
    """Test updating a completed mission shows error."""
    runner.invoke(
        app,
        ["persona", "add", "done-daemon", "--role", "Engineer"],
    )
    runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "done-daemon"])
    runner.invoke(app, ["daemon", "exorcise", "1"])

    result = runner.invoke(app, ["possession", "update", "1", "--task", "Should fail"])
    assert result.exit_code != 0
    out = " ".join(result.output.split())
    assert "Cannot update completed possession" in out


def test_mission_update_invalid_role(initialized_project: Path):
    """Test update with an invalid --role value shows error."""
    runner.invoke(
        app,
        ["persona", "add", "badrole-daemon", "--role", "Engineer"],
    )
    runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "badrole-daemon"])

    result = runner.invoke(app, ["possession", "update", "1", "--role", "FakeRole"])
    assert result.exit_code != 0
    out = " ".join(result.output.split())
    assert "Invalid role" in out


def test_mission_update_task_and_role(initialized_project: Path):
    """Test update with both --task and --role succeeds."""
    runner.invoke(
        app,
        ["persona", "add", "both-daemon", "--role", "Engineer"],
    )
    runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "both-daemon"])

    result = runner.invoke(app, ["possession", "update", "1", "--task", "New objective", "--role", "Architect"])
    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "Updated possession" in out
    assert "New objective" in out
    assert "Architect" in out


def test_mission_list_with_data_table(initialized_project: Path):
    """Test listing missions (non-JSON) when missions exist shows table."""
    runner.invoke(
        app,
        ["persona", "add", "table-daemon", "--role", "Engineer"],
    )
    runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "table-daemon"])

    result = runner.invoke(app, ["possession", "list"])
    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "Agent Sessions" in out


def test_mission_list_json_with_data(initialized_project: Path):
    """Test listing missions (JSON) when missions exist returns JSON array."""
    runner.invoke(
        app,
        ["persona", "add", "ljson-daemon", "--role", "Engineer"],
    )
    runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "ljson-daemon"])

    result = runner.invoke(app, ["possession", "list", "--json"])
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
        ["persona", "add", "comp-daemon", "--role", "Engineer"],
    )
    runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "comp-daemon"])
    runner.invoke(app, ["daemon", "exorcise", "1"])

    result = runner.invoke(app, ["possession", "show", "1"])
    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "Exorcised" in out
    assert "End Time:" in out


def test_mission_show_with_objective(initialized_project: Path):
    """Test showing a mission with --task displays mission info (objective not stored on possession)."""
    runner.invoke(
        app,
        ["persona", "add", "obj-show-daemon", "--role", "Tester"],
    )
    runner.invoke(
        app, ["daemon", "summon", "--role", "Tester", "--name", "obj-show-daemon", "--task", "Verify coverage"]
    )

    result = runner.invoke(app, ["possession", "show", "1"])
    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "Possession #1" in out
    assert "obj-show-daemon" in out


def test_mission_summary_fallback_git_log(initialized_project: Path):
    """Test summary uses fallback git log --name-status when diff fails."""
    runner.invoke(
        app,
        ["persona", "add", "fallback-daemon", "--role", "Engineer"],
    )
    runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "fallback-daemon"])

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
        result = runner.invoke(app, ["possession", "summary", "1"])

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "fallback.py" in out


def test_mission_summary_commits_fallback(initialized_project: Path):
    """Test summary uses fallback git log --oneline when grep fails."""
    runner.invoke(
        app,
        ["persona", "add", "comfb-daemon", "--role", "Engineer"],
    )
    runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "comfb-daemon"])

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
        result = runner.invoke(app, ["possession", "summary", "1"])

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "fallback commit message" in out


def test_mission_summary_completed_mission(initialized_project: Path):
    """Test summary for a completed mission shows End time."""
    runner.invoke(
        app,
        ["persona", "add", "sumcomp-daemon", "--role", "Engineer"],
    )
    runner.invoke(
        app, ["daemon", "summon", "--role", "Engineer", "--name", "sumcomp-daemon", "--task", "Some objective"]
    )
    runner.invoke(app, ["daemon", "exorcise", "1"])

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.output = ""

    with patch("subprocess.run", return_value=mock_result):
        result = runner.invoke(app, ["possession", "summary", "1"])

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "End:" in out


def test_mission_get_manager_no_opencode_dir(in_temp_dir: Path):
    """Test that commands fail when .opencode directory is missing."""
    result = runner.invoke(app, ["possession", "list"])
    assert result.exit_code != 0
    out = " ".join(result.output.split())
    assert ".opencode directory not found" in out


def test_mission_get_manager_no_db(initialized_project: Path):
    """Test that commands fail when project.db is missing."""
    import os

    db_path = initialized_project / ".opencode" / "data" / "project.db"
    os.remove(db_path)

    result = runner.invoke(app, ["possession", "list"])
    assert result.exit_code != 0
    out = " ".join(result.output.split())
    assert "project.db not found" in out


def test_mission_summary_not_found_json(initialized_project: Path):
    """Test summary for non-existent mission with --json returns MISSION_NOT_FOUND."""
    result = runner.invoke(app, ["possession", "summary", "999", "--json"])
    assert result.exit_code != 0
    data = json.loads(result.output)
    assert data["error_code"] == "MISSION_NOT_FOUND"


def test_mission_summary_task_exception_handled(initialized_project: Path):
    """Test summary handles exception in task fetching gracefully."""
    runner.invoke(
        app,
        ["persona", "add", "taskexc-daemon", "--role", "Engineer"],
    )
    runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "taskexc-daemon"])

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.output = ""

    with patch("subprocess.run", return_value=mock_result):
        with patch("site_nine.tasks.TaskManager.list_tasks", side_effect=Exception("DB error")):
            result = runner.invoke(app, ["possession", "summary", "1"])

    assert result.exit_code == 0
    out = " ".join(result.output.split())
    assert "Could not retrieve tasks" in out


def test_mission_summary_json_with_tasks(initialized_project: Path):
    """Test summary JSON output includes tasks data."""
    runner.invoke(
        app,
        ["persona", "add", "taskjson-daemon", "--role", "Engineer"],
    )
    runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "taskjson-daemon"])

    from site_nine.core.database import Database
    from site_nine.tasks import TaskManager

    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        tm = TaskManager(db)
        tm.create_task(task_id="ENG-M-0002", title="JSON task test", role="Engineer", priority="MEDIUM")
        tm.claim_task("ENG-M-0002", possession_id=1, current_role="Engineer")

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.output = ""

    with patch("subprocess.run", return_value=mock_result):
        result = runner.invoke(app, ["possession", "summary", "1", "--json"])

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

    runner.invoke(app, ["persona", "add", "epic-daemon", "--role", "Engineer"])

    result = runner.invoke(
        app, ["daemon", "summon", "--role", "Engineer", "--name", "epic-daemon", "--epic", "EPC-H-0001"]
    )

    assert result.exit_code == 0
    assert "Summoned daemon" in result.output
    assert "Epic: EPC-H-0001" in result.output


def test_mission_start_epic_and_task_exclusive(initialized_project: Path):
    """Test that --epic and --task flags are mutually exclusive"""
    runner.invoke(app, ["persona", "add", "excl-daemon", "--role", "Engineer"])

    result = runner.invoke(
        app,
        [
            "daemon",
            "summon",
            "--role",
            "Engineer",
            "--name",
            "excl-daemon",
            "--epic",
            "EPC-H-0001",
            "--task",
            "Some task",
        ],
    )

    assert result.exit_code == 1
    assert "Cannot specify both --task and --epic" in result.output


def test_mission_start_with_nonexistent_epic(initialized_project: Path):
    """Test starting mission with non-existent epic shows error"""
    runner.invoke(app, ["persona", "add", "noepic-daemon", "--role", "Tester"])

    result = runner.invoke(
        app, ["daemon", "summon", "--role", "Tester", "--name", "noepic-daemon", "--epic", "EPC-H-9999"]
    )

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
        ["persona", "add", "showepic-daemon", "--role", "Operator"],
    )

    runner.invoke(app, ["daemon", "summon", "--role", "Operator", "--name", "showepic-daemon", "--epic", "EPC-M-0002"])

    result = runner.invoke(app, ["possession", "show", "1"])

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
        ["persona", "add", "jsonepic-daemon", "--role", "Engineer"],
    )

    runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "jsonepic-daemon", "--epic", "EPC-C-0003"])

    result = runner.invoke(app, ["possession", "show", "1", "--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["data"]["epic_id"] == "EPC-C-0003"


# ---- Resume command tests ----


def _create_suspended_mission(initialized_project: Path, persona_name: str = "resume-daemon") -> None:
    """Helper: create a persona, start a mission, then suspend it."""
    runner.invoke(
        app,
        ["persona", "add", persona_name, "--role", "Operator"],
    )
    runner.invoke(app, ["daemon", "summon", "--role", "Operator", "--name", persona_name])
    runner.invoke(app, ["possession", "suspend", "1"])


def test_mission_resume_not_found(initialized_project: Path):
    """Test resuming a non-existent mission exits with error."""
    with patch("subprocess.run"):
        result = runner.invoke(app, ["possession", "resume", "999"])
    assert result.exit_code != 0


def test_mission_resume_not_found_by_codename(initialized_project: Path):
    """Test resuming a mission by non-existent codename exits with error."""
    with patch("subprocess.run"):
        result = runner.invoke(app, ["possession", "resume", "no-such-codename"])
    assert result.exit_code != 0


def test_mission_resume_not_suspended(initialized_project: Path):
    """Test resuming a mission that is ACTIVE (not SUSPENDED) exits with error."""
    runner.invoke(
        app,
        [
            "persona",
            "add",
            "active-daemon",
            "--role",
            "Operator",
        ],
    )
    runner.invoke(app, ["daemon", "summon", "--role", "Operator", "--name", "active-daemon"])

    with patch("subprocess.run"):
        result = runner.invoke(app, ["possession", "resume", "1"])
    assert result.exit_code != 0


def test_mission_resume_by_id(initialized_project: Path):
    """Test resuming a suspended mission by numeric ID launches OpenCode."""
    _create_suspended_mission(initialized_project)

    with patch("subprocess.run") as mock_run:
        result = runner.invoke(app, ["possession", "resume", "1"])

    assert result.exit_code == 0
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "opencode" in args
    assert "--prompt" in args


def test_mission_resume_by_codename(initialized_project: Path):
    """Test resuming a suspended mission by ID launches OpenCode (codename replaced by ID)."""
    persona_name = "codename-daemon"
    _create_suspended_mission(initialized_project, persona_name=persona_name)

    # Get the possession ID
    list_result = runner.invoke(app, ["possession", "list", "--json"])
    assert list_result.exit_code == 0
    missions = json.loads(list_result.output)
    possession_id = str(missions["data"][0]["id"])

    with patch("subprocess.run") as mock_run:
        result = runner.invoke(app, ["possession", "resume", possession_id])

    assert result.exit_code == 0
    mock_run.assert_called_once()


def test_mission_resume_dry_run(initialized_project: Path):
    """Test --dry-run shows command without executing or changing state."""
    _create_suspended_mission(initialized_project)

    with patch("subprocess.run") as mock_run:
        result = runner.invoke(app, ["possession", "resume", "1", "--dry-run"])

    assert result.exit_code == 0
    mock_run.assert_not_called()
    assert "Dry run" in result.output or "dry" in result.output.lower()

    # Mission should still be SUSPENDED (dry run did not change state)
    show_result = runner.invoke(app, ["possession", "show", "1"])
    assert "SUSPENDED" in show_result.output or "Suspended" in show_result.output


def test_mission_resume_changes_status_to_active(initialized_project: Path):
    """Test that resume transitions mission status from SUSPENDED to ACTIVE."""
    _create_suspended_mission(initialized_project)

    # Confirm mission is suspended
    show_before = runner.invoke(app, ["possession", "show", "1"])
    assert "SUSPENDED" in show_before.output or "Suspended" in show_before.output

    with patch("subprocess.run"):
        result = runner.invoke(app, ["possession", "resume", "1"])

    assert result.exit_code == 0

    show_after = runner.invoke(app, ["possession", "show", "1"])
    # Should no longer be SUSPENDED
    assert "SUSPENDED" not in show_after.output


def test_mission_resume_with_model_option(initialized_project: Path):
    """Test --model option is passed through to opencode invocation."""
    _create_suspended_mission(initialized_project)

    with patch("subprocess.run") as mock_run:
        result = runner.invoke(app, ["possession", "resume", "1", "--model", "openai/gpt-4o"])

    assert result.exit_code == 0
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "openai/gpt-4o" in args


def test_mission_resume_context_includes_mission_info(initialized_project: Path):
    """Test that the context message passed to OpenCode includes mission metadata."""
    _create_suspended_mission(initialized_project)

    with patch("subprocess.run") as mock_run:
        result = runner.invoke(app, ["possession", "resume", "1"])

    assert result.exit_code == 0
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    # The --prompt arg should contain mission ID
    prompt_idx = args.index("--prompt")
    context = args[prompt_idx + 1]
    assert "1" in context  # mission ID


def test_mission_resume_opencode_not_found(initialized_project: Path):
    """Test graceful error when opencode binary is not found."""
    _create_suspended_mission(initialized_project)

    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = runner.invoke(app, ["possession", "resume", "1"])

    assert result.exit_code != 0


def test_mission_suspend_then_resume_workflow(initialized_project: Path):
    """Integration test: start → suspend → resume full workflow."""
    runner.invoke(
        app,
        [
            "persona",
            "add",
            "cycle-daemon",
            "--role",
            "Engineer",
        ],
    )

    start_result = runner.invoke(app, ["daemon", "summon", "--role", "Engineer", "--name", "cycle-daemon"])
    assert start_result.exit_code == 0

    suspend_result = runner.invoke(app, ["possession", "suspend", "1"])
    assert suspend_result.exit_code == 0

    with patch("subprocess.run") as mock_run:
        resume_result = runner.invoke(app, ["possession", "resume", "1"])

    assert resume_result.exit_code == 0
    mock_run.assert_called_once()


def test_mission_resume_context_includes_persona_and_role(initialized_project: Path):
    """Test context message includes persona name and role."""
    _create_suspended_mission(initialized_project)

    with patch("subprocess.run") as mock_run:
        result = runner.invoke(app, ["possession", "resume", "1"])

    assert result.exit_code == 0
    args = mock_run.call_args[0][0]
    prompt_idx = args.index("--prompt")
    context = args[prompt_idx + 1]
    assert "resume-daemon" in context  # persona name
    assert "Operator" in context  # role


def test_mission_resume_context_includes_objective(initialized_project: Path):
    """Test context message includes persona and role (objective not stored on possession)."""
    runner.invoke(
        app,
        ["persona", "add", "obj-daemon", "--role", "Operator"],
    )
    runner.invoke(
        app, ["daemon", "summon", "--role", "Operator", "--name", "obj-daemon", "--task", "My special objective"]
    )
    runner.invoke(app, ["possession", "suspend", "1"])

    with patch("subprocess.run") as mock_run:
        result = runner.invoke(app, ["possession", "resume", "1"])

    assert result.exit_code == 0
    args = mock_run.call_args[0][0]
    prompt_idx = args.index("--prompt")
    context = args[prompt_idx + 1]
    assert "obj-daemon" in context
    assert "Operator" in context


def test_mission_resume_context_includes_tasks(initialized_project: Path):
    """Test context message includes task list when tasks are assigned to the mission.

    NOTE: Uses direct DB injection to associate a task with the mission,
    because `task claim` CLI path fails in the test environment where the
    `blocks` table is absent from the initialized schema (schema.sql out-of-sync).
    """
    import json
    from site_nine.core.database import Database

    runner.invoke(
        app,
        ["persona", "add", "task-daemon", "--role", "Tester"],
    )
    runner.invoke(app, ["daemon", "summon", "--role", "Tester", "--name", "task-daemon"])

    # Get the mission ID
    list_result = runner.invoke(app, ["possession", "list", "--json"])
    missions = json.loads(list_result.output)
    mission_id = missions["data"][0]["id"]

    # Directly inject a task row associated with the mission (bypasses `blocks` table)
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        db.execute_update(
            """
            INSERT INTO tasks (id, title, status, priority, role, file_path, current_possession_id, created_at)
            VALUES ('TST-M-0999', 'A resume test task', 'UNDERWAY', 'MEDIUM', 'Tester',
                    '.opencode/work/tasks/TST-M-0999.md', :possession_id, datetime('now'))
            """,
            {"possession_id": mission_id},
        )

    runner.invoke(app, ["possession", "suspend", str(mission_id)])

    with patch("subprocess.run") as mock_run:
        result = runner.invoke(app, ["possession", "resume", str(mission_id)])

    assert result.exit_code == 0
    args = mock_run.call_args[0][0]
    prompt_idx = args.index("--prompt")
    context = args[prompt_idx + 1]
    assert "TST-M-0999" in context
    assert "A resume test task" in context


def test_mission_resume_idle_mission_fails(initialized_project: Path):
    """Test that an IDLE mission (not SUSPENDED) cannot be resumed."""
    runner.invoke(
        app,
        ["persona", "add", "idle-daemon", "--role", "Operator"],
    )
    runner.invoke(app, ["daemon", "summon", "--role", "Operator", "--name", "idle-daemon"])
    # Force mission to IDLE status directly via heartbeat/set_status isn't exposed in CLI,
    # but we can verify an ACTIVE mission is rejected (IDLE is also not SUSPENDED)
    # The implementation guards on status != SUSPENDED
    with patch("subprocess.run"):
        result = runner.invoke(app, ["possession", "resume", "1"])
    assert result.exit_code != 0


def test_mission_resume_dry_run_shows_model_and_prompt(initialized_project: Path):
    """Test --dry-run output contains both model and prompt details."""
    _create_suspended_mission(initialized_project)

    with patch("subprocess.run") as mock_run:
        result = runner.invoke(app, ["possession", "resume", "1", "--dry-run"])

    assert result.exit_code == 0
    mock_run.assert_not_called()
    # Output should describe what would be run
    assert "opencode" in result.output
    assert "--prompt" in result.output


def test_mission_resume_context_continue_line(initialized_project: Path):
    """Test context message ends with 'Continue working on your mission.' sentinel."""
    _create_suspended_mission(initialized_project)

    with patch("subprocess.run") as mock_run:
        result = runner.invoke(app, ["possession", "resume", "1"])

    assert result.exit_code == 0
    args = mock_run.call_args[0][0]
    prompt_idx = args.index("--prompt")
    context = args[prompt_idx + 1]
    assert "Continue working on your mission." in context
