"""Integration tests for epic CLI commands"""

from pathlib import Path

from site_nine.cli.main import app
from site_nine.core.database import Database
from site_nine.epics.manager import EpicManager
from site_nine.tasks.manager import TaskManager
from typer.testing import CliRunner

runner = CliRunner()


def test_epic_create_requires_title(initialized_project: Path):
    """Test that epic create command requires --title option"""
    result = runner.invoke(
        app,
        ["epic", "create", "--priority", "HIGH"],
    )

    # Should fail because --title is required
    assert result.exit_code != 0


def test_epic_create_requires_priority(initialized_project: Path):
    """Test that epic create command requires --priority option"""
    result = runner.invoke(
        app,
        ["epic", "create", "--title", "Test Epic"],
    )

    # Should fail because --priority is required
    assert result.exit_code != 0


def test_epic_create_success(initialized_project: Path):
    """Test creating an epic"""
    result = runner.invoke(
        app,
        ["epic", "create", "--title", "Test Epic", "--priority", "HIGH"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "Created epic" in result.stdout
    assert "EPC-H-0001" in result.stdout
    assert "Test Epic" in result.stdout


def test_epic_create_with_description(initialized_project: Path):
    """Test creating an epic with description"""
    result = runner.invoke(
        app,
        [
            "epic",
            "create",
            "--title",
            "Epic with Description",
            "--priority",
            "MEDIUM",
            "--description",
            "This is a test description",
        ],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "Created epic" in result.stdout
    assert "EPC-M-0001" in result.stdout


def test_epic_create_invalid_priority(initialized_project: Path):
    """Test creating epic with invalid priority"""
    result = runner.invoke(
        app,
        ["epic", "create", "--title", "Test", "--priority", "INVALID"],
    )

    assert result.exit_code != 0
    assert "Invalid priority" in result.stdout or "Error" in result.stdout


def test_epic_create_generates_file(initialized_project: Path):
    """Test that creating epic generates markdown file"""
    result = runner.invoke(
        app,
        ["epic", "create", "--title", "File Test", "--priority", "HIGH"],
    )

    assert result.exit_code == 0

    # Check that file was created
    epic_file = initialized_project / ".opencode" / "work" / "epics" / "EPC-H-0001.md"
    assert epic_file.exists()

    # Check file contents
    content = epic_file.read_text()
    assert "Epic EPC-H-0001: File Test" in content
    assert "Status:" in content
    assert "Priority:" in content


def test_epic_list_empty(initialized_project: Path):
    """Test listing epics when none exist"""
    result = runner.invoke(
        app,
        ["epic", "list"],
    )

    assert result.exit_code == 0
    assert "No epics found" in result.stdout


def test_epic_list_shows_epics(initialized_project: Path):
    """Test listing epics"""
    # Create some epics
    runner.invoke(
        app,
        ["epic", "create", "--title", "Epic 1", "--priority", "HIGH"],
    )
    runner.invoke(
        app,
        ["epic", "create", "--title", "Epic 2", "--priority", "MEDIUM"],
    )

    # List epics
    result = runner.invoke(
        app,
        ["epic", "list"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "Epic 1" in result.stdout
    assert "Epic 2" in result.stdout
    assert "EPC-H-0001" in result.stdout
    assert "EPC-M-0002" in result.stdout


def test_epic_list_filter_by_status(initialized_project: Path):
    """Test filtering epics by status"""
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    manager = EpicManager(db)
    task_manager = TaskManager(db)

    # Create two epics
    epic1 = manager.create_epic("Epic 1", "HIGH")
    epic2 = manager.create_epic("Epic 2", "MEDIUM")

    # Make epic1 UNDERWAY by creating and starting a task
    task_id = task_manager.generate_task_id("Engineer", "HIGH")
    task_manager.create_task(task_id, "Test Task", "Engineer", "HIGH")
    manager.link_task(task_id, epic1.id)
    task_manager.update_status(task_id, "UNDERWAY")

    # List TODO epics
    result = runner.invoke(
        app,
        ["epic", "list", "--status", "TODO"],
    )

    assert result.exit_code == 0
    assert "Epic 2" in result.stdout
    assert "Epic 1" not in result.stdout

    # List UNDERWAY epics
    result = runner.invoke(
        app,
        ["epic", "list", "--status", "UNDERWAY"],
    )

    assert result.exit_code == 0
    assert "Epic 1" in result.stdout
    assert "Epic 2" not in result.stdout


def test_epic_list_filter_by_priority(initialized_project: Path):
    """Test filtering epics by priority"""
    runner.invoke(
        app,
        ["epic", "create", "--title", "High Priority", "--priority", "HIGH"],
    )
    runner.invoke(
        app,
        ["epic", "create", "--title", "Medium Priority", "--priority", "MEDIUM"],
    )

    # List HIGH priority epics
    result = runner.invoke(
        app,
        ["epic", "list", "--priority", "HIGH"],
    )

    assert result.exit_code == 0
    assert "High Priority" in result.stdout
    assert "Medium Priority" not in result.stdout


def test_epic_list_invalid_status_filter(initialized_project: Path):
    """Test listing with invalid status filter"""
    result = runner.invoke(
        app,
        ["epic", "list", "--status", "INVALID"],
    )

    assert result.exit_code != 0
    assert "Invalid status" in result.stdout


def test_epic_show_displays_details(initialized_project: Path):
    """Test showing epic details"""
    runner.invoke(
        app,
        ["epic", "create", "--title", "Detailed Epic", "--priority", "HIGH", "--description", "Test description"],
    )

    result = runner.invoke(
        app,
        ["epic", "show", "EPC-H-0001"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "Epic EPC-H-0001" in result.stdout
    assert "Detailed Epic" in result.stdout
    assert "HIGH" in result.stdout
    assert "TODO" in result.stdout
    assert "Test description" in result.stdout


def test_epic_show_with_subtasks(initialized_project: Path):
    """Test showing epic with subtasks"""
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    manager = EpicManager(db)
    task_manager = TaskManager(db)

    # Create epic
    epic = manager.create_epic("Epic with Tasks", "HIGH")

    # Create tasks
    task1_id = task_manager.generate_task_id("Engineer", "HIGH")
    task_manager.create_task(task1_id, "Task 1", "Engineer", "HIGH")
    manager.link_task(task1_id, epic.id)

    task2_id = task_manager.generate_task_id("Tester", "MEDIUM")
    task_manager.create_task(task2_id, "Task 2", "Tester", "MEDIUM")
    manager.link_task(task2_id, epic.id)

    # Show epic
    result = runner.invoke(
        app,
        ["epic", "show", epic.id],
    )

    assert result.exit_code == 0
    assert "Subtasks" in result.stdout
    assert "Task 1" in result.stdout
    assert "Task 2" in result.stdout


def test_epic_show_not_found(initialized_project: Path):
    """Test showing non-existent epic"""
    result = runner.invoke(
        app,
        ["epic", "show", "EPC-H-9999"],
    )

    assert result.exit_code != 0
    assert "not found" in result.stdout


def test_epic_update_title(initialized_project: Path):
    """Test updating epic title"""
    runner.invoke(
        app,
        ["epic", "create", "--title", "Original Title", "--priority", "HIGH"],
    )

    result = runner.invoke(
        app,
        ["epic", "update", "EPC-H-0001", "--title", "New Title"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "Updated epic" in result.stdout
    assert "New Title" in result.stdout


def test_epic_update_description(initialized_project: Path):
    """Test updating epic description"""
    runner.invoke(
        app,
        ["epic", "create", "--title", "Test Epic", "--priority", "HIGH"],
    )

    result = runner.invoke(
        app,
        ["epic", "update", "EPC-H-0001", "--description", "New description"],
    )

    assert result.exit_code == 0
    assert "Updated epic" in result.stdout


def test_epic_update_priority(initialized_project: Path):
    """Test updating epic priority"""
    runner.invoke(
        app,
        ["epic", "create", "--title", "Test Epic", "--priority", "HIGH"],
    )

    result = runner.invoke(
        app,
        ["epic", "update", "EPC-H-0001", "--priority", "CRITICAL"],
    )

    assert result.exit_code == 0
    assert "Updated epic" in result.stdout
    assert "CRITICAL" in result.stdout


def test_epic_update_invalid_priority(initialized_project: Path):
    """Test updating with invalid priority"""
    runner.invoke(
        app,
        ["epic", "create", "--title", "Test Epic", "--priority", "HIGH"],
    )

    result = runner.invoke(
        app,
        ["epic", "update", "EPC-H-0001", "--priority", "INVALID"],
    )

    assert result.exit_code != 0
    assert "Invalid priority" in result.stdout or "Error" in result.stdout


def test_epic_update_not_found(initialized_project: Path):
    """Test updating non-existent epic"""
    result = runner.invoke(
        app,
        ["epic", "update", "EPC-H-9999", "--title", "New Title"],
    )

    assert result.exit_code != 0
    assert "not found" in result.stdout


def test_epic_update_no_changes(initialized_project: Path):
    """Test updating epic with no changes"""
    runner.invoke(
        app,
        ["epic", "create", "--title", "Test Epic", "--priority", "HIGH"],
    )

    result = runner.invoke(
        app,
        ["epic", "update", "EPC-H-0001"],
    )

    assert result.exit_code == 0
    assert "No updates provided" in result.stdout


def test_epic_abort_requires_reason(initialized_project: Path):
    """Test that abort command requires reason"""
    runner.invoke(
        app,
        ["epic", "create", "--title", "Test Epic", "--priority", "HIGH"],
    )

    result = runner.invoke(
        app,
        ["epic", "abort", "EPC-H-0001"],
    )

    # Should fail because --reason is required
    assert result.exit_code != 0


def test_epic_abort_with_confirmation(initialized_project: Path):
    """Test aborting epic with confirmation"""
    runner.invoke(
        app,
        ["epic", "create", "--title", "Test Epic", "--priority", "HIGH"],
    )

    # Use --yes to skip confirmation
    result = runner.invoke(
        app,
        ["epic", "abort", "EPC-H-0001", "--reason", "Test abort", "--yes"],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert "Aborted epic" in result.stdout
    assert "EPC-H-0001" in result.stdout


def test_epic_abort_with_subtasks(initialized_project: Path):
    """Test aborting epic aborts all subtasks"""
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    manager = EpicManager(db)
    task_manager = TaskManager(db)

    # Create epic with tasks
    epic = manager.create_epic("Test Epic", "HIGH")

    task1_id = task_manager.generate_task_id("Engineer", "HIGH")
    task_manager.create_task(task1_id, "Task 1", "Engineer", "HIGH")
    manager.link_task(task1_id, epic.id)

    task2_id = task_manager.generate_task_id("Tester", "MEDIUM")
    task_manager.create_task(task2_id, "Task 2", "Tester", "MEDIUM")
    manager.link_task(task2_id, epic.id)

    # Abort epic
    result = runner.invoke(
        app,
        ["epic", "abort", epic.id, "--reason", "Test abort", "--yes"],
    )

    assert result.exit_code == 0
    assert "Subtasks aborted: 2" in result.stdout

    # Verify tasks are aborted
    task1 = task_manager.get_task(task1_id)
    task2 = task_manager.get_task(task2_id)
    assert task1.status == "ABORTED"
    assert task2.status == "ABORTED"


def test_epic_abort_already_aborted(initialized_project: Path):
    """Test aborting an already aborted epic"""
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    manager = EpicManager(db)

    epic = manager.create_epic("Test Epic", "HIGH")
    manager.abort_epic(epic.id, "First abort")

    # Try to abort again
    result = runner.invoke(
        app,
        ["epic", "abort", epic.id, "--reason", "Second abort", "--yes"],
    )

    assert result.exit_code == 0
    assert "already aborted" in result.stdout


def test_epic_abort_not_found(initialized_project: Path):
    """Test aborting non-existent epic"""
    result = runner.invoke(
        app,
        ["epic", "abort", "EPC-H-9999", "--reason", "Test", "--yes"],
    )

    assert result.exit_code != 0
    assert "not found" in result.stdout


def test_epic_sync_single_epic(initialized_project: Path):
    """Test syncing a single epic file"""
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    manager = EpicManager(db)

    epic = manager.create_epic("Test Epic", "HIGH")

    result = runner.invoke(
        app,
        ["epic", "sync", "--epic", epic.id],
    )

    assert result.exit_code == 0, f"Command failed: {result.stdout}"
    assert f"Synced epic {epic.id}" in result.stdout

    # Verify file exists
    epic_file = initialized_project / ".opencode" / "work" / "epics" / f"{epic.id}.md"
    assert epic_file.exists()


def test_epic_sync_all_epics(initialized_project: Path):
    """Test syncing all epic files"""
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    manager = EpicManager(db)

    manager.create_epic("Epic 1", "HIGH")
    manager.create_epic("Epic 2", "MEDIUM")
    manager.create_epic("Epic 3", "LOW")

    result = runner.invoke(
        app,
        ["epic", "sync"],
    )

    assert result.exit_code == 0
    assert "Synced 3 epic(s)" in result.stdout


def test_epic_sync_not_found(initialized_project: Path):
    """Test syncing non-existent epic"""
    result = runner.invoke(
        app,
        ["epic", "sync", "--epic", "EPC-H-9999"],
    )

    assert result.exit_code != 0
    assert "not found" in result.stdout


def test_epic_sync_updates_existing_file(initialized_project: Path):
    """Test that sync preserves custom content in epic files"""
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    manager = EpicManager(db)

    epic = manager.create_epic("Test Epic", "HIGH")

    # Create initial file via sync
    runner.invoke(app, ["epic", "sync", "--epic", epic.id])

    # Add custom content
    epic_file = initialized_project / ".opencode" / "work" / "epics" / f"{epic.id}.md"
    content = epic_file.read_text()
    custom_content = content + "\n## Custom Section\n\nThis is my custom content\n"
    epic_file.write_text(custom_content)

    # Update epic in database
    manager.update_epic(epic.id, title="Updated Title")

    # Sync again
    runner.invoke(app, ["epic", "sync", "--epic", epic.id])

    # Check that custom content is preserved
    updated_content = epic_file.read_text()
    assert "Updated Title" in updated_content
    assert "Custom Section" in updated_content
    assert "This is my custom content" in updated_content


def test_epic_file_reflects_status_changes(initialized_project: Path):
    """Test that epic files reflect status changes"""
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    manager = EpicManager(db)
    task_manager = TaskManager(db)

    epic = manager.create_epic("Test Epic", "HIGH")

    # Create initial file
    runner.invoke(app, ["epic", "sync", "--epic", epic.id])

    epic_file = initialized_project / ".opencode" / "work" / "epics" / f"{epic.id}.md"
    initial_content = epic_file.read_text()
    assert "TODO" in initial_content

    # Create and start a task to make epic UNDERWAY
    task_id = task_manager.generate_task_id("Engineer", "HIGH")
    task_manager.create_task(task_id, "Test Task", "Engineer", "HIGH")
    manager.link_task(task_id, epic.id)
    task_manager.update_status(task_id, "UNDERWAY")

    # Sync again
    runner.invoke(app, ["epic", "sync", "--epic", epic.id])

    updated_content = epic_file.read_text()
    assert "UNDERWAY" in updated_content
    assert "🚧" in updated_content  # UNDERWAY emoji


def test_epic_file_shows_progress(initialized_project: Path):
    """Test that epic files show task progress"""
    db_path = initialized_project / ".opencode" / "data" / "project.db"
    db = Database(db_path)
    manager = EpicManager(db)
    task_manager = TaskManager(db)

    epic = manager.create_epic("Test Epic", "HIGH")

    # Create tasks
    task1_id = task_manager.generate_task_id("Engineer", "HIGH")
    task_manager.create_task(task1_id, "Task 1", "Engineer", "HIGH")
    manager.link_task(task1_id, epic.id)

    task2_id = task_manager.generate_task_id("Tester", "MEDIUM")
    task_manager.create_task(task2_id, "Task 2", "Tester", "MEDIUM")
    manager.link_task(task2_id, epic.id)

    # Complete one task
    task_manager.update_status(task1_id, "COMPLETE")

    # Sync
    runner.invoke(app, ["epic", "sync", "--epic", epic.id])

    epic_file = initialized_project / ".opencode" / "work" / "epics" / f"{epic.id}.md"
    content = epic_file.read_text()

    assert "Progress" in content
    assert "1/2" in content
    assert "50%" in content
