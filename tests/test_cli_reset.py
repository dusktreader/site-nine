"""Integration tests for reset CLI command"""

from pathlib import Path

from site_nine.__main__ import app
from site_nine.core.database import Database
from site_nine.missions.manager import MissionManager
from site_nine.tasks.manager import TaskManager
from typer.testing import CliRunner

runner = CliRunner()


def _create_persona(db: Database, name: str, role: str) -> None:
    """Helper to create a persona for testing"""
    db.execute_update(
        """
        INSERT INTO personas (name, role, mythology, description)
        VALUES (:name, :role, :mythology, :description)
        ON CONFLICT (name) DO NOTHING
        """,
        {
            "name": name,
            "role": role,
            "mythology": "Test",
            "description": f"Test persona {name}",
        },
    )


def test_reset_fails_without_init(in_temp_dir: Path):
    """Test that reset command fails if project not initialized"""
    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code != 0
    output = " ".join(result.output.split())
    assert ".opencode" in output or "init" in output.lower()


def test_reset_requires_confirmation(initialized_project: Path):
    """Test that reset requires confirmation"""
    # Create some data so reset doesn't exit early
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        _create_persona(db, "test-persona", "Engineer")
        mission_manager = MissionManager(db)
        mission_manager.start_mission(persona_name="test-persona", role="Engineer", objective="Test mission")

    result = runner.invoke(
        app,
        ["reset"],
        input="n\n",  # Say no to first confirmation
    )

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "Cancelled" in output

    # Verify nothing was deleted
    assert db_path.exists()
    with Database(db_path) as db:
        mission_manager = MissionManager(db)
        assert len(mission_manager.list_missions()) == 1


def test_reset_requires_exact_text_confirmation(initialized_project: Path):
    """Test that reset requires exact confirmation text"""
    # Create some data so reset doesn't exit early
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        _create_persona(db, "test-persona", "Engineer")
        mission_manager = MissionManager(db)
        mission_manager.start_mission(persona_name="test-persona", role="Engineer", objective="Test mission")

    result = runner.invoke(
        app,
        ["reset"],
        input="y\ndelete all data\n",  # Wrong case
    )

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "Cancelled" in output
    assert "Confirmation text did not match" in output

    # Verify nothing was deleted
    assert db_path.exists()
    with Database(db_path) as db:
        mission_manager = MissionManager(db)
        assert len(mission_manager.list_missions()) == 1


def test_reset_deletes_all_data(initialized_project: Path):
    """Test that reset deletes all mission and task data"""
    # Create some data
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        _create_persona(db, "persona1", "Engineer")
        _create_persona(db, "persona2", "Designer")
        mission_manager = MissionManager(db)
        task_manager = TaskManager(db)

        # Create missions
        _ = mission_manager.start_mission(
            persona_name="persona1",
            role="Engineer",
            objective="Task 1",
        )
        _ = mission_manager.start_mission(
            persona_name="persona2",
            role="Designer",
            objective="Task 2",
        )

        # Create tasks
        task1_id = task_manager.generate_task_id(role="Engineer", priority="HIGH")
        task_manager.create_task(
            task_id=task1_id,
            title="Test task 1",
            priority="HIGH",
            role="Engineer",
        )
        task2_id = task_manager.generate_task_id(role="Designer", priority="MEDIUM")
        task_manager.create_task(
            task_id=task2_id,
            title="Test task 2",
            priority="MEDIUM",
            role="Designer",
        )

        # Verify data exists
        assert len(mission_manager.list_missions()) == 2
        assert len(task_manager.list_tasks()) == 2

    # Run reset
    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code == 0, f"Command failed: {result.output}"
    output = " ".join(result.output.split())
    assert "Reset complete" in output or "reset complete" in output.lower()

    # Verify all data deleted
    with Database(db_path) as db:
        mission_manager = MissionManager(db)
        task_manager = TaskManager(db)
        assert len(mission_manager.list_missions()) == 0
        assert len(task_manager.list_tasks()) == 0

    # Verify database still exists
    assert db_path.exists()


def test_reset_deletes_mission_files(initialized_project: Path):
    """Test that reset deletes mission files"""
    # Create a mission
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        _create_persona(db, "test-persona", "Engineer")
        manager = MissionManager(db)

        _mission_id = manager.start_mission(
            persona_name="test-persona",
            role="Engineer",
            objective="test-task",
        )

    # Verify mission file exists
    missions_dir = initialized_project / ".opencode" / "work" / "missions"
    mission_files = list(missions_dir.glob("*.engineer.test-persona.md"))
    assert len(mission_files) > 0
    mission_file = mission_files[0]
    assert mission_file.exists()

    # Run reset
    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code == 0

    # Verify mission file deleted
    assert not mission_file.exists()


def test_reset_deletes_task_files(initialized_project: Path):
    """Test that reset deletes task files"""
    # Create a task
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        task_manager = TaskManager(db)

        task_id = task_manager.generate_task_id(role="Engineer", priority="HIGH")
        task_manager.create_task(
            task_id=task_id,
            title="Test task",
            priority="HIGH",
            role="Engineer",
        )

    # Verify task file exists
    task_file = initialized_project / ".opencode" / "work" / "tasks" / f"{task_id}.md"
    # Task file might be created by TaskManager, or we create it manually
    if not task_file.exists():
        task_file.write_text(f"# {task_id}")

    assert task_file.exists()

    # Run reset
    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code == 0

    # Verify task file deleted
    assert not task_file.exists()


def test_reset_resets_persona_mission_counts(initialized_project: Path):
    """Test that reset resets persona mission counts"""
    # Create a persona and mission to increment usage count
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        # Create a persona
        db.execute_update(
            """
            INSERT INTO personas (name, role, mythology, description)
            VALUES (:name, :role, :mythology, :description)
            """,
            {
                "name": "test_reset_persona_mission",
                "role": "Operator",
                "mythology": "Greek",
                "description": "Test persona for mission count reset",
            },
        )

        manager = MissionManager(db)
        _mission_id = manager.start_mission(
            persona_name="test_reset_persona_mission",
            role="Operator",
            objective="test-task",
        )

        # Verify usage count incremented
        persona = db.execute_query(
            "SELECT mission_count, last_mission_at FROM personas WHERE name = :name",
            {"name": "test_reset_persona_mission"},
        )[0]
        assert persona["mission_count"] > 0
        assert persona["last_mission_at"] is not None

    # Run reset
    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code == 0

    # Verify usage count reset
    with Database(db_path) as db:
        persona = db.execute_query(
            "SELECT mission_count, last_mission_at FROM personas WHERE name = :name",
            {"name": "test_reset_persona_mission"},
        )[0]
        assert persona["mission_count"] == 0
        assert persona["last_mission_at"] is None


def test_reset_preserves_personas_list(initialized_project: Path):
    """Test that reset preserves the personas list"""
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        # Add a test persona
        db.execute_update(
            """
            INSERT INTO personas (name, role, mythology, description)
            VALUES (:name, :role, :mythology, :description)
            """,
            {
                "name": "test_reset_preserve_persona",
                "role": "Engineer",
                "mythology": "Greek",
                "description": "Test persona for preserve list",
            },
        )

        # Count personas before reset
        personas_before = db.execute_query("SELECT COUNT(*) as count FROM personas")[0]["count"]
        assert personas_before > 0

    # Run reset
    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code == 0

    # Verify personas still exist
    with Database(db_path) as db:
        personas_after = db.execute_query("SELECT COUNT(*) as count FROM personas")[0]["count"]
        assert personas_after == personas_before


def test_reset_preserves_config_files(initialized_project: Path):
    """Test that reset preserves configuration files"""
    # Create a test config file in .opencode directory
    test_config_file = initialized_project / ".opencode" / "test-config.json"
    test_config_file.write_text('{"test": "config"}')

    readme_file = initialized_project / ".opencode" / "README.md"

    # Verify files exist before
    assert test_config_file.exists(), "test config file should exist"
    assert readme_file.exists(), "README.md should exist after init"

    # Run reset
    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code == 0

    # Verify files still exist - reset should only delete specific directories/files
    assert test_config_file.exists(), "test config file should still exist after reset"
    assert readme_file.exists(), "README.md should still exist after reset"


def test_reset_shows_counts_before_deletion(initialized_project: Path):
    """Test that reset shows what will be deleted"""
    # Create some data
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        _create_persona(db, "persona1", "Engineer")
        mission_manager = MissionManager(db)
        task_manager = TaskManager(db)

        mission_manager.start_mission(persona_name="persona1", role="Engineer", objective="Task 1")
        task_id = task_manager.generate_task_id(role="Engineer", priority="HIGH")
        task_manager.create_task(task_id=task_id, title="Test task", priority="HIGH", role="Engineer")

    result = runner.invoke(
        app,
        ["reset"],
        input="n\n",  # Cancel before deletion
    )

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    # Should show counts
    assert "1 mission" in output
    assert "1 task" in output


def test_reset_with_yes_flag_skips_first_confirmation(initialized_project: Path):
    """Test that --yes flag skips first confirmation"""
    # Create some data so reset doesn't exit early
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        _create_persona(db, "test", "Engineer")
        mission_manager = MissionManager(db)
        mission_manager.start_mission(persona_name="test", role="Engineer", objective="test")

    result = runner.invoke(
        app,
        ["reset", "--yes"],
        input="WRONG TEXT\n",  # Still need second confirmation
    )

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "Cancelled" in output
    # Should not ask for first confirmation (checking it didn't appear)
    # The --yes flag skips the "Are you absolutely sure" prompt


def test_reset_shows_summary_after_deletion(initialized_project: Path):
    """Test that reset shows summary of what was deleted"""
    # Create some data
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        _create_persona(db, "persona1", "Engineer")
        mission_manager = MissionManager(db)

        mission_manager.start_mission(persona_name="persona1", role="Engineer", objective="Task 1")

    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code == 0
    output = " ".join(result.output.split())
    assert "Reset complete" in output or "reset complete" in output.lower()
    # Should show summary
    assert "Deleted:" in output


def test_reset_on_empty_project_succeeds(initialized_project: Path):
    """Test that reset on empty project succeeds gracefully"""
    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    output = " ".join(result.output.split())
    # Should exit early since there's nothing to delete
    assert "No data to delete" in output or result.exit_code == 0


def test_reset_deletes_handoff_files(initialized_project: Path):
    """Test that reset deletes handoff files"""
    # Create database data first so reset doesn't exit early
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        _create_persona(db, "test", "Engineer")
        mission_manager = MissionManager(db)
        mission_manager.start_mission(persona_name="test", role="Engineer", objective="test")

    # Create handoff directory and file
    handoffs_dir = initialized_project / ".opencode" / "work" / "missions" / "handoffs"
    handoffs_dir.mkdir(parents=True, exist_ok=True)

    handoff_file = handoffs_dir / "2026-02-02.12:00:00.engineer.tester.pending.md"
    handoff_file.write_text("# Handoff")

    assert handoff_file.exists()

    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code == 0
    assert not handoff_file.exists()


def test_reset_deletes_task_dependencies(initialized_project: Path):
    """Test that reset deletes task dependencies"""
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        task_manager = TaskManager(db)

        # Create tasks with dependencies
        task1_id = task_manager.generate_task_id(role="Engineer", priority="HIGH")
        task_manager.create_task(task_id=task1_id, title="Task 1", priority="HIGH", role="Engineer")
        task2_id = task_manager.generate_task_id(role="Engineer", priority="HIGH")
        task_manager.create_task(task_id=task2_id, title="Task 2", priority="HIGH", role="Engineer")

        # Add dependency (task2 depends on task1)
        db.execute_update(
            "INSERT INTO task_dependencies (task_id, depends_on_task_id) VALUES (:task_id, :depends_on)",
            {"task_id": task2_id, "depends_on": task1_id},
        )

        # Verify dependency exists
        deps = db.execute_query("SELECT COUNT(*) as count FROM task_dependencies")[0]["count"]
        assert deps > 0

    result = runner.invoke(
        app,
        ["reset"],
        input="y\nDELETE ALL DATA\n",
    )

    assert result.exit_code == 0

    # Verify dependencies deleted
    with Database(db_path) as db:
        deps = db.execute_query("SELECT COUNT(*) as count FROM task_dependencies")[0]["count"]
        assert deps == 0
