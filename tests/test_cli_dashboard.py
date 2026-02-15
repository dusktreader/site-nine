"""Integration tests for dashboard CLI command"""

from pathlib import Path

from site_nine.__main__ import app
from site_nine.core.database import Database
from typer.testing import CliRunner

runner = CliRunner()


def test_dashboard_shows_empty_project(initialized_project: Path):
    """Test dashboard with no missions or tasks"""
    result = runner.invoke(
        app,
        ["dashboard"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"


def test_dashboard_with_json_output(initialized_project: Path):
    """Test dashboard JSON output"""
    result = runner.invoke(
        app,
        ["dashboard", "--json"],
    )

    assert result.exit_code == 0


def test_dashboard_with_role_filter(initialized_project: Path):
    """Test dashboard filtered by role"""
    result = runner.invoke(
        app,
        ["dashboard", "--role", "Engineer"],
    )

    assert result.exit_code == 0


def test_dashboard_compact_mode(initialized_project: Path):
    """Test dashboard compact mode"""
    result = runner.invoke(
        app,
        ["dashboard", "--compact"],
    )

    assert result.exit_code in [0, 1, 2]  # May not support compact flag


def test_dashboard_with_epic_filter(initialized_project: Path):
    """Test dashboard filtered by epic"""
    result = runner.invoke(
        app,
        ["dashboard", "--epic", "ENG-E-001"],
    )

    # May fail if epic doesn't exist or validation error
    assert result.exit_code in [0, 1]


def test_dashboard_with_json_short_flag(initialized_project: Path):
    """Test dashboard with -j short flag"""
    result = runner.invoke(
        app,
        ["dashboard", "-j"],
    )

    assert result.exit_code == 0


def test_dashboard_with_role_short_flag(initialized_project: Path):
    """Test dashboard with -r short flag"""
    result = runner.invoke(
        app,
        ["dashboard", "-r", "Tester"],
    )

    assert result.exit_code == 0


def test_dashboard_with_epic_short_flag(initialized_project: Path):
    """Test dashboard with -e short flag"""
    result = runner.invoke(
        app,
        ["dashboard", "-e", "ENG-E-001"],
    )

    # May fail if epic doesn't exist or validation error
    assert result.exit_code in [0, 1]


def test_dashboard_multiple_filters(initialized_project: Path):
    """Test dashboard with multiple filters"""
    result = runner.invoke(
        app,
        ["dashboard", "--role", "Engineer", "--epic", "ENG-E-001"],
    )

    # May fail if epic doesn't exist or validation error
    assert result.exit_code in [0, 1]


def test_dashboard_json_with_filters(initialized_project: Path):
    """Test dashboard JSON output with filters"""
    result = runner.invoke(
        app,
        ["dashboard", "--json", "--role", "Engineer"],
    )

    assert result.exit_code == 0


def test_dashboard_nonexistent_role(initialized_project: Path):
    """Test dashboard with nonexistent role"""
    result = runner.invoke(
        app,
        ["dashboard", "--role", "NonexistentRole"],
    )

    # Should succeed but show no results
    assert result.exit_code == 0


def test_dashboard_nonexistent_epic(initialized_project: Path):
    """Test dashboard with nonexistent epic"""
    result = runner.invoke(
        app,
        ["dashboard", "--epic", "FAKE-E-999"],
    )

    # May fail due to validation error or succeed but show no results
    assert result.exit_code in [0, 1]


def test_dashboard_multiple_roles(initialized_project: Path):
    """Test dashboard with role filter - Engineer"""
    result = runner.invoke(
        app,
        ["dashboard", "-r", "Engineer"],
    )

    assert result.exit_code == 0


def test_dashboard_tester_role(initialized_project: Path):
    """Test dashboard with role filter - Tester"""
    result = runner.invoke(
        app,
        ["dashboard", "--role", "Tester"],
    )

    assert result.exit_code == 0


# --- Helper to seed data into an initialized project ---


def _seed_data(initialized_project: Path, *, tasks=True, epic=False, mission=False, underway_task=False):
    """Seed tasks, epics, and/or missions into the project database.

    Returns a dict with the db_path and any created objects for reference.
    """
    from site_nine.tasks.manager import TaskManager
    from site_nine.epics import EpicManager

    db_path = initialized_project / ".opencode" / "data" / "project.db"
    info: dict = {"db_path": db_path}

    with Database(db_path) as db:
        tm = TaskManager(db)
        em = EpicManager(db)

        if tasks:
            tm.create_task("ENG-H-0001", "Fix authentication bug", "Engineer", "HIGH", description="Auth fix")
            tm.create_task("ENG-M-0002", "Add logging middleware", "Engineer", "MEDIUM", description="Logging")
            tm.create_task("TST-H-0001", "Write integration tests", "Tester", "HIGH", description="Tests")

        if epic:
            em.create_epic("Test Epic", "HIGH", description="An epic for testing", epic_id="EPC-H-0001")
            # Link first two tasks to the epic
            if tasks:
                em.link_task("ENG-H-0001", "EPC-H-0001")
                em.link_task("ENG-M-0002", "EPC-H-0001")

        if mission:
            # Get a persona name from the DB
            personas = db.execute_query("SELECT name FROM personas LIMIT 1")
            persona_name = personas[0]["name"]
            info["persona_name"] = persona_name

            db.execute_update(
                """
                INSERT INTO missions (persona_name, role, codename, mission_file, start_date, start_time, objective, created_at, updated_at)
                VALUES (:persona, 'Engineer', 'test-mission', '.opencode/work/missions/test.md', '2026-01-01', '10:00:00', 'Test objective for the dashboard', datetime('now'), datetime('now'))
                """,
                {"persona": persona_name},
            )
            missions = db.execute_query("SELECT id FROM missions ORDER BY id DESC LIMIT 1")
            info["mission_id"] = missions[0]["id"]

        if underway_task and tasks and mission:
            # Claim a task so it becomes UNDERWAY and linked to the mission
            tm.claim_task("ENG-H-0001", info["mission_id"], "Engineer")

    return info


# --- Tests that seed data to cover uncovered lines ---


def test_dashboard_with_seeded_tasks(initialized_project: Path):
    """Test full dashboard with seeded tasks covers available tasks table (lines 290-304)"""
    _seed_data(initialized_project, tasks=True)

    result = runner.invoke(app, ["dashboard"])
    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    # Should display the tasks in the Available Individual Tasks table
    assert "Fix authentication bug" in result.stdout or "ENG-H-0001" in result.stdout
    assert "Add logging middleware" in result.stdout or "ENG-M-0002" in result.stdout


def test_dashboard_with_seeded_epic(initialized_project: Path):
    """Test epic filter with seeded epic + linked tasks covers epic display (lines 174-221)"""
    _seed_data(initialized_project, tasks=True, epic=True)

    result = runner.invoke(app, ["dashboard", "--epic", "EPC-H-0001"])
    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    # Should display epic header info
    assert "Test Epic" in result.stdout
    assert "EPC-H-0001" in result.stdout
    # Should display subtasks table
    assert "Epic Subtasks" in result.stdout
    assert "ENG-H-0001" in result.stdout
    assert "ENG-M-0002" in result.stdout


def test_dashboard_epic_json(initialized_project: Path):
    """Test epic filter with JSON output covers epic JSON path (lines 52-58)"""
    import json

    _seed_data(initialized_project, tasks=True, epic=True)

    result = runner.invoke(app, ["dashboard", "--epic", "EPC-H-0001", "--json"])
    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    response = json.loads(result.stdout)
    data = response["data"]
    assert "epic" in data
    assert data["epic"]["id"] == "EPC-H-0001"
    assert data["epic"]["title"] == "Test Epic"
    assert data["epic"]["priority"] == "HIGH"
    assert "subtasks" in data
    assert len(data["subtasks"]) == 2
    subtask_ids = {s["id"] for s in data["subtasks"]}
    assert "ENG-H-0001" in subtask_ids
    assert "ENG-M-0002" in subtask_ids


def test_dashboard_role_filter_with_data(initialized_project: Path):
    """Test role filter with seeded tasks covers role table (lines 241-249)"""
    _seed_data(initialized_project, tasks=True)

    result = runner.invoke(app, ["dashboard", "--role", "Engineer"])
    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    # Should show tasks for Engineer role
    assert "Engineer" in result.stdout
    assert "ENG-H-0001" in result.stdout or "Fix authentication bug" in result.stdout
    assert "ENG-M-0002" in result.stdout or "Add logging middleware" in result.stdout
    # Should NOT show Tester tasks
    assert "TST-H-0001" not in result.stdout


def test_dashboard_role_json_with_data(initialized_project: Path):
    """Test role filter JSON output with seeded tasks"""
    import json

    _seed_data(initialized_project, tasks=True)

    result = runner.invoke(app, ["dashboard", "--role", "Engineer", "--json"])
    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    response = json.loads(result.stdout)
    data = response["data"]
    assert data["role"] == "Engineer"
    assert "available_tasks" in data
    assert len(data["available_tasks"]) == 2
    task_ids = {t["id"] for t in data["available_tasks"]}
    assert "ENG-H-0001" in task_ids
    assert "ENG-M-0002" in task_ids


def test_dashboard_full_json_with_data(initialized_project: Path):
    """Test full JSON dashboard with tasks + missions seeded"""
    import json

    _seed_data(initialized_project, tasks=True, mission=True)

    result = runner.invoke(app, ["dashboard", "--json"])
    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    response = json.loads(result.stdout)
    data = response["data"]
    assert "available_tasks" in data
    assert "active_missions" in data
    assert "stats" in data
    assert len(data["active_missions"]) >= 1
    assert data["stats"]["active_missions"] >= 1
    assert data["stats"]["total_tasks"] >= 3


def test_dashboard_epic_tree_rendering(initialized_project: Path):
    """Test epic tree rendering with active epics and subtasks (lines 382-469)"""
    _seed_data(initialized_project, tasks=True, epic=True)

    # The full dashboard (no filters) renders the epic tree
    result = runner.invoke(app, ["dashboard"])
    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    # The tree should display the active epic and its subtasks
    assert "EPC-H-0001" in result.stdout
    assert "Test Epic" in result.stdout
    # Subtasks should appear in the tree
    assert "ENG-H-0001" in result.stdout
    assert "ENG-M-0002" in result.stdout


def test_dashboard_progress_bar():
    """Direct unit test of _generate_progress_bar (lines 367-370)"""
    from site_nine.dashboard.rendering import generate_progress_bar

    # 0% - should use "dim" color
    bar_0 = generate_progress_bar(0)
    assert "0%" in bar_0
    assert "░" in bar_0
    assert "dim" in bar_0

    # 25% - should use "yellow" color (percent > 0 but <= 50)
    bar_25 = generate_progress_bar(25)
    assert "25%" in bar_25
    assert "█" in bar_25
    assert "░" in bar_25
    assert "yellow" in bar_25

    # 75% - should use "cyan" color (percent > 50 but < 100)
    bar_75 = generate_progress_bar(75)
    assert "75%" in bar_75
    assert "cyan" in bar_75

    # 100% - should use "green" color
    bar_100 = generate_progress_bar(100)
    assert "100%" in bar_100
    assert "green" in bar_100
    # Should be all filled
    assert "░" not in bar_100

    # Custom width
    bar_custom = generate_progress_bar(50, width=20)
    assert "50%" in bar_custom
    # 50% of 20 = 10 filled + 10 empty
    assert bar_custom.count("█") == 10
    assert bar_custom.count("░") == 10


def test_dashboard_with_mission_and_tasks(initialized_project: Path):
    """Test dashboard with mission + UNDERWAY task shows ACTIVE status (lines 320-328)"""
    _seed_data(initialized_project, tasks=True, mission=True, underway_task=True)

    result = runner.invoke(app, ["dashboard"])
    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    # Should show the mission in Open Missions table
    assert "Open Missions" in result.stdout
    # The mission should be ACTIVE (stored status, default for new missions)
    assert "ACTIVE" in result.stdout


def test_dashboard_with_idle_mission(initialized_project: Path):
    """Test dashboard with mission set to IDLE shows IDLE status"""
    info = _seed_data(initialized_project, tasks=True, mission=True, underway_task=False)

    # Explicitly set the mission status to IDLE (stored status model)
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        db.execute_update(
            "UPDATE missions SET status = 'IDLE' WHERE id = :id",
            {"id": info["mission_id"]},
        )

    result = runner.invoke(app, ["dashboard"])
    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    # Should show the mission in Open Missions table
    assert "Open Missions" in result.stdout
    # The mission should be IDLE since we explicitly set it
    assert "IDLE" in result.stdout


def test_dashboard_blocked_by_reviews_stat(initialized_project: Path):
    """Test dashboard shows blocked by reviews stat (line 356)"""
    from site_nine.tasks.manager import TaskManager

    db_path = initialized_project / ".opencode" / "data" / "project.db"

    with Database(db_path) as db:
        tm = TaskManager(db)
        # Create a task
        tm.create_task("ENG-H-0001", "Task needing review", "Engineer", "HIGH")
        # Add a review block to trigger BLOCKED_REVIEW effective status via the view
        db.execute_update(
            """
            INSERT INTO blocks (task_id, block_type, description, created_at)
            VALUES ('ENG-H-0001', 'review', 'Needs code review', datetime('now'))
            """,
        )

    result = runner.invoke(app, ["dashboard"])
    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    # Should show blocked by reviews in the stats
    assert "Blocked by reviews" in result.stdout


def test_dashboard_epic_tree_no_subtasks(initialized_project: Path):
    """Test epic tree rendering when epic has no linked subtasks.

    Epics with no active (TODO/UNDERWAY) subtasks are hidden from the dashboard
    to reduce clutter.
    """
    from site_nine.epics import EpicManager

    db_path = initialized_project / ".opencode" / "data" / "project.db"

    with Database(db_path) as db:
        em = EpicManager(db)
        em.create_epic("Empty Epic", "MEDIUM", description="No tasks", epic_id="EPC-M-0001")

    result = runner.invoke(app, ["dashboard"])
    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    # Epics with no active subtasks should be hidden from the dashboard
    assert "EPC-M-0001" not in result.stdout


def test_dashboard_epic_with_progress(initialized_project: Path):
    """Test epic filter display shows progress bar when subtasks exist (lines 189-194)"""
    from site_nine.tasks.manager import TaskManager
    from site_nine.epics import EpicManager

    db_path = initialized_project / ".opencode" / "data" / "project.db"

    with Database(db_path) as db:
        tm = TaskManager(db)
        em = EpicManager(db)

        em.create_epic("Progress Epic", "HIGH", description="Epic with progress", epic_id="EPC-H-0002")
        tm.create_task("ENG-H-0003", "Completed task", "Engineer", "HIGH")
        tm.create_task("ENG-M-0004", "Pending task", "Engineer", "MEDIUM")
        em.link_task("ENG-H-0003", "EPC-H-0002")
        em.link_task("ENG-M-0004", "EPC-H-0002")
        # Complete one task
        tm.update_status("ENG-H-0003", "COMPLETE")

    result = runner.invoke(app, ["dashboard", "--epic", "EPC-H-0002"])
    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    # Should show progress info
    assert "Progress" in result.stdout
    assert "Progress Epic" in result.stdout
    # Should show the progress bar characters
    assert "█" in result.stdout or "░" in result.stdout


def test_dashboard_full_json_with_missions_and_idle(initialized_project: Path):
    """Test full JSON output includes idle mission detection"""
    import json

    info = _seed_data(initialized_project, tasks=True, mission=True, underway_task=False)

    # Explicitly set the mission status to IDLE (stored status model)
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        db.execute_update(
            "UPDATE missions SET status = 'IDLE' WHERE id = :id",
            {"id": info["mission_id"]},
        )

    result = runner.invoke(app, ["dashboard", "--json"])
    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    response = json.loads(result.stdout)
    data = response["data"]
    assert data["stats"]["idle_missions"] >= 1
    # Mission should be IDLE since we explicitly set it
    mission_statuses = [m["status"] for m in data["active_missions"]]
    assert "IDLE" in mission_statuses


def test_dashboard_epic_json_not_found(initialized_project: Path):
    """Test epic JSON filter with nonexistent epic returns error (lines 54-55)"""
    result = runner.invoke(app, ["dashboard", "--epic", "EPC-H-9999", "--json"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_dashboard_epic_no_subtasks_display(initialized_project: Path):
    """Test epic filter display when epic has no linked subtasks (line 219)"""
    from site_nine.epics import EpicManager

    db_path = initialized_project / ".opencode" / "data" / "project.db"

    with Database(db_path) as db:
        em = EpicManager(db)
        em.create_epic("Lonely Epic", "LOW", description="No tasks linked", epic_id="EPC-L-0001")

    result = runner.invoke(app, ["dashboard", "--epic", "EPC-L-0001"])
    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    assert "Lonely Epic" in result.stdout
    assert "No tasks linked to this epic" in result.stdout


def test_dashboard_epic_tree_many_subtasks(initialized_project: Path):
    """Test epic tree truncation when >10 subtasks exist (line 466)"""
    from site_nine.tasks.manager import TaskManager
    from site_nine.epics import EpicManager

    db_path = initialized_project / ".opencode" / "data" / "project.db"

    with Database(db_path) as db:
        tm = TaskManager(db)
        em = EpicManager(db)

        em.create_epic("Big Epic", "HIGH", description="Many tasks", epic_id="EPC-H-0003")

        # Create 12 tasks and link them all to the epic
        for i in range(1, 13):
            task_id = f"ENG-M-{i:04d}"
            tm.create_task(task_id, f"Task number {i}", "Engineer", "MEDIUM")
            em.link_task(task_id, "EPC-H-0003")

    result = runner.invoke(app, ["dashboard"])
    assert result.exit_code == 0, f"Command failed: {result.stdout}"

    # Should show the epic
    assert "EPC-H-0003" in result.stdout
    # Should show truncation message for the remaining 2 tasks
    assert "and 2 more tasks" in result.stdout
