"""Tests for handoff CLI commands"""

import json
from pathlib import Path

from site_nine.__main__ import app
from site_nine.core.database import Database
from site_nine.handoffs import HandoffManager
from site_nine.tasks.manager import TaskManager
from typer.testing import CliRunner

runner = CliRunner()


def test_handoff_list_empty(initialized_project: Path):
    """Test listing handoffs when none exist"""
    result = runner.invoke(app, ["handoff", "list"])

    assert result.exit_code == 0


def test_handoff_list_with_role_filter(initialized_project: Path):
    """Test listing handoffs filtered by role"""
    result = runner.invoke(app, ["handoff", "list", "--role", "Tester"])

    assert result.exit_code == 0


def test_handoff_list_json(initialized_project: Path):
    """Test listing handoffs in JSON format"""
    result = runner.invoke(app, ["handoff", "list", "--json"])

    assert result.exit_code == 0


def test_handoff_show_nonexistent(initialized_project: Path):
    """Test showing non-existent handoff"""
    result = runner.invoke(app, ["handoff", "show", "999"])

    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert "not found" in output.lower()


def test_handoff_delete_nonexistent(initialized_project: Path):
    """Test deleting non-existent handoff"""
    result = runner.invoke(app, ["handoff", "delete", "999"])

    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert "not found" in output.lower()


def test_handoff_list_with_mission_filter(initialized_project: Path):
    """Test listing handoffs filtered by mission"""
    result = runner.invoke(app, ["handoff", "list", "--from-mission", "1"])

    assert result.exit_code == 0


def test_handoff_list_show_deleted(initialized_project: Path):
    """Test listing deleted handoffs"""
    result = runner.invoke(app, ["handoff", "list", "--include-deleted"])

    assert result.exit_code == 0


def test_handoff_show_json(initialized_project: Path):
    """Test showing handoff in JSON"""
    result = runner.invoke(app, ["handoff", "show", "1", "--json"])

    # Either succeeds or shows not found
    assert result.exit_code in [0, 1]


def test_handoff_create(initialized_project: Path):
    """Test creating a handoff"""
    from site_nine.missions.manager import MissionManager

    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        task_manager = TaskManager(db)
        task_manager.create_task("ENG-H-0001", "Test Task", "Engineer", "HIGH", description="Test")

        # Create a mission (need a persona first - use one seeded during init)
        mission_manager = MissionManager(db)
        mission_id = mission_manager.start_mission(
            persona_name="atlas",
            role="Engineer",
            objective="test-task",
        )

    # Create handoff using option-based syntax
    result = runner.invoke(
        app,
        [
            "handoff",
            "create",
            "--task",
            "ENG-H-0001",
            "--from-mission",
            str(mission_id),
            "--to-role",
            "Tester",
            "--summary",
            "Please test this",
        ],
    )

    assert result.exit_code == 0


def test_handoff_show_success(initialized_project: Path):
    """Test showing a handoff"""
    from site_nine.handoffs.manager import HandoffManager
    from site_nine.missions.manager import MissionManager

    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        task_manager = TaskManager(db)
        task_manager.create_task("ENG-H-0001", "Test Task", "Engineer", "HIGH", description="Test")

        mission_manager = MissionManager(db)
        mission_id = mission_manager.start_mission(
            persona_name="atlas",
            role="Engineer",
            objective="test-task",
        )

        handoff_manager = HandoffManager(db)
        handoff_id = handoff_manager.create_handoff("ENG-H-0001", mission_id, "Tester", "Test handoff")

    # Show it
    result = runner.invoke(app, ["handoff", "show", str(handoff_id)])

    assert result.exit_code == 0


def test_handoff_delete_success(initialized_project: Path):
    """Test deleting a handoff"""
    from site_nine.handoffs.manager import HandoffManager
    from site_nine.missions.manager import MissionManager

    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        task_manager = TaskManager(db)
        task_manager.create_task("ENG-H-0001", "Test Task", "Engineer", "HIGH", description="Test")

        mission_manager = MissionManager(db)
        mission_id = mission_manager.start_mission(
            persona_name="atlas",
            role="Engineer",
            objective="test-task",
        )

        handoff_manager = HandoffManager(db)
        handoff_id = handoff_manager.create_handoff("ENG-H-0001", mission_id, "Tester", "Test handoff")

    # Delete it
    result = runner.invoke(app, ["handoff", "delete", str(handoff_id)])

    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Comprehensive tests
# ---------------------------------------------------------------------------


def _get_db_path() -> Path:
    """Get the project database path."""
    return Path.cwd() / ".opencode" / "data" / "project.db"


def _seed_task_and_mission(db_path: Path) -> tuple[str, int]:
    """Seed a task and a mission, returning (task_id, mission_id)."""
    with Database(db_path) as db:
        # Pick an existing persona that was created by s9 init
        personas = db.execute_query("SELECT name, role FROM personas LIMIT 1")
        persona_name = personas[0]["name"]
        persona_role = personas[0]["role"]

        # Create task (role/priority must match task ID encoding)
        task_id = "ENG-H-0001"
        tm = TaskManager(db)
        tm.create_task(task_id, "Test Task", "Engineer", "HIGH", description="Test task for handoff")

        # Insert a mission referencing the existing persona
        db.execute_update(
            """
            INSERT INTO missions (persona_name, role, codename, mission_file, start_date, start_time, objective, created_at, updated_at)
            VALUES (:persona, :role, 'test-codename', '.opencode/work/missions/test.md', '2026-01-01', '10:00:00', 'Test objective', datetime('now'), datetime('now'))
            """,
            {"persona": persona_name, "role": persona_role},
        )

        rows = db.execute_query("SELECT id FROM missions ORDER BY id DESC LIMIT 1")
        mission_id = rows[0]["id"]

    return task_id, mission_id


def _seed_handoff(db_path: Path, task_id: str, mission_id: int, to_role: str = "Tester", **kwargs) -> int:
    """Create a handoff via the manager, returning the handoff_id."""
    with Database(db_path) as db:
        hm = HandoffManager(db)
        handoff_id = hm.create_handoff(
            task_id=task_id,
            from_mission_id=mission_id,
            to_role=to_role,
            summary=kwargs.get("summary", "Please test this feature"),
            files=kwargs.get("files"),
            acceptance_criteria=kwargs.get("acceptance_criteria"),
            notes=kwargs.get("notes"),
        )
    return handoff_id


def _seed_second_task_and_mission(db_path: Path) -> tuple[str, int]:
    """Seed a second task and mission with a different role persona."""
    with Database(db_path) as db:
        personas = db.execute_query("SELECT name, role FROM personas WHERE role = 'Tester' LIMIT 1")
        persona_name = personas[0]["name"]
        persona_role = personas[0]["role"]

        task_id = "TST-M-0001"
        tm = TaskManager(db)
        tm.create_task(task_id, "Second Test Task", "Tester", "MEDIUM", description="Another task")

        db.execute_update(
            """
            INSERT INTO missions (persona_name, role, codename, mission_file, start_date, start_time, objective, created_at, updated_at)
            VALUES (:persona, :role, 'second-codename', '.opencode/work/missions/test2.md', '2026-01-02', '11:00:00', 'Second objective', datetime('now'), datetime('now'))
            """,
            {"persona": persona_name, "role": persona_role},
        )

        rows = db.execute_query("SELECT id FROM missions ORDER BY id DESC LIMIT 1")
        mission_id = rows[0]["id"]

    return task_id, mission_id


# -- 1. create --


def test_handoff_create_success(initialized_project: Path):
    """Test creating a handoff via CLI with all options."""
    db_path = _get_db_path()
    task_id, mission_id = _seed_task_and_mission(db_path)

    result = runner.invoke(
        app,
        [
            "handoff",
            "create",
            "--task",
            task_id,
            "--from-mission",
            str(mission_id),
            "--to-role",
            "Tester",
            "--summary",
            "Please test this feature",
            "--criteria",
            "All tests pass",
            "--notes",
            "Focus on edge cases",
        ],
    )

    assert result.exit_code == 0, f"Unexpected output: {result.output}"
    out = " ".join(result.output.split())
    assert "Created handoff" in out
    assert task_id in out
    assert "Tester" in out
    assert "Please test this feature" in out


def test_handoff_create_with_files(initialized_project: Path):
    """Test creating a handoff with multiple --file options."""
    db_path = _get_db_path()
    task_id, mission_id = _seed_task_and_mission(db_path)

    result = runner.invoke(
        app,
        [
            "handoff",
            "create",
            "--task",
            task_id,
            "--from-mission",
            str(mission_id),
            "--to-role",
            "Tester",
            "--summary",
            "Review these files",
            "--file",
            "src/main.py",
            "--file",
            "tests/test_main.py",
        ],
    )

    assert result.exit_code == 0, f"Unexpected output: {result.output}"
    out = " ".join(result.output.split())
    assert "Created handoff" in out
    assert "2 file(s)" in out


def test_handoff_create_invalid_role(initialized_project: Path):
    """Test creating a handoff with an invalid --to-role."""
    db_path = _get_db_path()
    task_id, mission_id = _seed_task_and_mission(db_path)

    result = runner.invoke(
        app,
        [
            "handoff",
            "create",
            "--task",
            task_id,
            "--from-mission",
            str(mission_id),
            "--to-role",
            "InvalidRole",
            "--summary",
            "This should fail",
        ],
    )

    assert result.exit_code != 0
    out = " ".join(result.output.split()).lower()
    assert "invalid role" in out


# -- 2. list --


def test_handoff_list_table_with_data(initialized_project: Path):
    """Test listing handoffs in table format when data exists."""
    db_path = _get_db_path()
    task_id, mission_id = _seed_task_and_mission(db_path)
    _seed_handoff(db_path, task_id, mission_id, summary="First handoff")
    _seed_handoff(db_path, task_id, mission_id, to_role="Engineer", summary="Second handoff")

    result = runner.invoke(app, ["handoff", "list"])

    assert result.exit_code == 0, f"Unexpected output: {result.output}"
    # Normalize whitespace for rich table output
    out = " ".join(result.output.split())
    assert "Handoffs" in out
    assert "First handoff" in out
    assert "Second handoff" in out
    # Task ID may be truncated by Rich table column width (e.g. "ENG-H-0...")
    assert "ENG-H-0" in out


def test_handoff_list_json_with_data(initialized_project: Path):
    """Test listing handoffs in JSON format when data exists."""
    db_path = _get_db_path()
    task_id, mission_id = _seed_task_and_mission(db_path)
    _seed_handoff(
        db_path,
        task_id,
        mission_id,
        summary="JSON handoff",
        files=["a.py", "b.py"],
        acceptance_criteria="All good",
        notes="Some notes",
    )

    result = runner.invoke(app, ["handoff", "list", "--json"])

    assert result.exit_code == 0, f"Unexpected output: {result.stdout}"
    payload = json.loads(result.stdout)
    assert "data" in payload
    assert payload["count"] >= 1
    item = payload["data"][0]
    assert item["task_id"] == task_id
    assert item["summary"] == "JSON handoff"
    assert item["files"] == ["a.py", "b.py"]
    assert item["acceptance_criteria"] == "All good"
    assert item["notes"] == "Some notes"


def test_handoff_list_with_role_filter_new(initialized_project: Path):
    """Test listing handoffs filtered by --role returns only matching handoffs."""
    db_path = _get_db_path()
    task_id, mission_id = _seed_task_and_mission(db_path)
    _seed_handoff(db_path, task_id, mission_id, to_role="Tester", summary="For tester")
    _seed_handoff(db_path, task_id, mission_id, to_role="Engineer", summary="For engineer")

    result = runner.invoke(app, ["handoff", "list", "--role", "Tester"])

    assert result.exit_code == 0, f"Unexpected output: {result.output}"
    out = " ".join(result.output.split())
    assert "For tester" in out
    assert "For engineer" not in out


def test_handoff_list_empty_with_filter(initialized_project: Path):
    """Test listing handoffs with a filter that matches nothing shows a message."""
    db_path = _get_db_path()
    task_id, mission_id = _seed_task_and_mission(db_path)
    _seed_handoff(db_path, task_id, mission_id, to_role="Tester", summary="For tester")

    result = runner.invoke(app, ["handoff", "list", "--role", "Historian"])

    assert result.exit_code == 0
    out = " ".join(result.output.split()).lower()
    assert "no handoffs found" in out
    assert "historian" in out


def test_handoff_list_include_deleted(initialized_project: Path):
    """Test listing handoffs with --include-deleted shows deleted and active."""
    db_path = _get_db_path()
    task_id, mission_id = _seed_task_and_mission(db_path)
    hid_active = _seed_handoff(db_path, task_id, mission_id, summary="Active handoff")
    hid_deleted = _seed_handoff(db_path, task_id, mission_id, summary="Deleted handoff")

    # Soft-delete one
    with Database(db_path) as db:
        hm = HandoffManager(db)
        hm.delete_handoff(hid_deleted)

    # Without --include-deleted only active shows
    result_default = runner.invoke(app, ["handoff", "list"])
    out_default = " ".join(result_default.output.split())
    assert "Active handoff" in out_default
    assert "Deleted handoff" not in out_default

    # With --include-deleted both show, plus Status column
    result_incl = runner.invoke(app, ["handoff", "list", "--include-deleted"])
    assert result_incl.exit_code == 0
    out_incl = " ".join(result_incl.output.split())
    assert "Active handoff" in out_incl
    assert "Deleted handoff" in out_incl
    assert "active" in out_incl.lower()
    assert "deleted" in out_incl.lower()


# -- 3. show --


def test_handoff_show_rich_active(initialized_project: Path):
    """Test showing an active handoff in rich display."""
    db_path = _get_db_path()
    task_id, mission_id = _seed_task_and_mission(db_path)
    hid = _seed_handoff(
        db_path,
        task_id,
        mission_id,
        summary="Active handoff summary",
        files=["src/foo.py", "src/bar.py"],
        acceptance_criteria="Tests pass",
        notes="Check edge cases",
    )

    result = runner.invoke(app, ["handoff", "show", str(hid)])

    assert result.exit_code == 0, f"Unexpected output: {result.output}"
    out = " ".join(result.output.split())
    assert f"Handoff #{hid}" in out
    assert "Pending" in out
    assert task_id in out
    assert "Tester" in out
    assert "Active handoff summary" in out
    assert "Tests pass" in out
    assert "src/foo.py" in out
    assert "src/bar.py" in out
    assert "Check edge cases" in out


def test_handoff_show_rich_deleted(initialized_project: Path):
    """Test showing a deleted handoff in rich display."""
    db_path = _get_db_path()
    task_id, mission_id = _seed_task_and_mission(db_path)
    hid = _seed_handoff(db_path, task_id, mission_id, summary="Will be deleted")

    # Delete it
    with Database(db_path) as db:
        hm = HandoffManager(db)
        hm.delete_handoff(hid)

    result = runner.invoke(app, ["handoff", "show", str(hid)])

    assert result.exit_code == 0, f"Unexpected output: {result.output}"
    out = " ".join(result.output.split())
    assert f"Handoff #{hid}" in out
    assert "Deleted" in out
    # Should show "Deleted:" timestamp line
    assert "Deleted:" in result.output


def test_handoff_show_json_success(initialized_project: Path):
    """Test showing a handoff with --json output."""
    db_path = _get_db_path()
    task_id, mission_id = _seed_task_and_mission(db_path)
    hid = _seed_handoff(
        db_path,
        task_id,
        mission_id,
        summary="JSON show test",
        files=["x.py"],
        acceptance_criteria="Looks good",
        notes="Extra notes",
    )

    result = runner.invoke(app, ["handoff", "show", str(hid), "--json"])

    assert result.exit_code == 0, f"Unexpected output: {result.stdout}"
    payload = json.loads(result.stdout)
    data = payload["data"]
    assert data["id"] == hid
    assert data["task_id"] == task_id
    assert data["to_role"] == "Tester"
    assert data["summary"] == "JSON show test"
    assert data["files"] == ["x.py"]
    assert data["acceptance_criteria"] == "Looks good"
    assert data["notes"] == "Extra notes"
    assert data["deleted_at"] is None


# -- 4. delete --


def test_handoff_delete_success_new(initialized_project: Path):
    """Test successfully deleting a handoff."""
    db_path = _get_db_path()
    task_id, mission_id = _seed_task_and_mission(db_path)
    hid = _seed_handoff(db_path, task_id, mission_id, summary="Delete me")

    result = runner.invoke(app, ["handoff", "delete", str(hid)])

    assert result.exit_code == 0, f"Unexpected output: {result.output}"
    out = " ".join(result.output.split())
    assert f"Deleted handoff #{hid}" in out
    assert task_id in out

    # Verify it's actually soft-deleted
    with Database(db_path) as db:
        hm = HandoffManager(db)
        handoff = hm.get_handoff(hid)
        assert handoff is not None
        assert handoff.deleted_at is not None


def test_handoff_delete_already_deleted(initialized_project: Path):
    """Test deleting an already-deleted handoff shows a warning."""
    db_path = _get_db_path()
    task_id, mission_id = _seed_task_and_mission(db_path)
    hid = _seed_handoff(db_path, task_id, mission_id, summary="Already deleted")

    # Delete it first
    with Database(db_path) as db:
        hm = HandoffManager(db)
        hm.delete_handoff(hid)

    # Try to delete again via CLI
    result = runner.invoke(app, ["handoff", "delete", str(hid)])

    assert result.exit_code == 0
    out = " ".join(result.output.split()).lower()
    assert "already deleted" in out
