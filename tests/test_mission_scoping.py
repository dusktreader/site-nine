"""Tests for possession scoping and task claiming validation (TST-H-0096).

Covers ADR-009 Phase 1:
- Possession scoping modes: task/epic/general
- Mutual exclusivity validation (CLI layer)
- Epic-scoped task claiming with role matching
- get_next_epic_task unit tests
- s9 task next edge cases
"""

import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from site_nine.__main__ import app
from site_nine.core.database import Database
from site_nine.possessions.manager import PossessionManager
from site_nine.tasks.exceptions import TaskError
from site_nine.tasks.manager import TaskManager
from site_nine.tasks.types import TaskStatus

runner = CliRunner()


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


def _create_task(
    db: Database,
    task_id: str,
    role: str = "Engineer",
    priority: str = "MEDIUM",
    status: str = "TODO",
    epic_id: str | None = None,
) -> None:
    """Insert a task row."""
    db.execute_update(
        """
        INSERT INTO tasks (id, title, description, status, priority, role, epic_id, file_path, created_at, updated_at)
        VALUES (:id, :title, 'Test description', :status, :priority, :role, :epic_id,
                '.opencode/work/tasks/' || :id || '.md', datetime('now'), datetime('now'))
        """,
        {
            "id": task_id,
            "title": f"Task {task_id}",
            "status": status,
            "priority": priority,
            "role": role,
            "epic_id": epic_id,
        },
    )


def _create_possession(
    db: Database,
    daemon_name: str = "test-persona",
    role: str = "Engineer",
    epic_id: str | None = None,
) -> int:
    """Insert a possession row and return its ID."""
    # Ensure daemon exists
    db.execute_update(
        "INSERT OR IGNORE INTO daemons (name, role, incarnations) VALUES (:name, :role, 0)",
        {"name": daemon_name, "role": role},
    )
    result = db.execute_query(
        """
        INSERT INTO possessions (
            daemon_name, role, possession_log,
            start_time, epic_id,
            status, last_heartbeat_at,
            created_at, updated_at
        ) VALUES (
            :daemon_name, :role,
            '.opencode/work/possessions/test.md',
            datetime('now'), :epic_id,
            'ACTIVE', datetime('now'),
            datetime('now'), datetime('now')
        ) RETURNING id
        """,
        {"daemon_name": daemon_name, "role": role, "epic_id": epic_id},
    )
    return result[0]["id"]


# ===========================================================================
# UNIT TESTS: Possession scoping modes (manager layer)
# ===========================================================================


class TestMissionScopingModes:
    """Test that possessions correctly store and retrieve scoping modes."""

    def test_start_possession_general_scope(self, test_db):
        """General possession: no epic_id."""
        mid = _create_possession(test_db, daemon_name="test-persona", role="Engineer")
        manager = PossessionManager(test_db)

        possession = manager.get_possession(mid)
        assert possession is not None
        assert possession.epic_id is None

    def test_start_possession_epic_scope(self, test_db):
        """Epic-scoped possession: epic_id set."""
        _create_epic(test_db, "EPC-H-0001")
        mid = _create_possession(test_db, daemon_name="test-persona", role="Engineer", epic_id="EPC-H-0001")
        manager = PossessionManager(test_db)

        possession = manager.get_possession(mid)
        assert possession is not None
        assert possession.epic_id == "EPC-H-0001"

    def test_start_possession_task_scope_has_no_epic(self, test_db):
        """Task-scoped possession (no epic) has no epic_id."""
        mid = _create_possession(test_db, daemon_name="test-persona", role="Engineer")
        manager = PossessionManager(test_db)

        possession = manager.get_possession(mid)
        assert possession is not None
        assert possession.epic_id is None

    def test_list_possessions_filter_by_epic(self, test_db):
        """Filtering possessions by epic_id returns only matching possessions."""
        _create_epic(test_db, "EPC-H-0001")
        _create_epic(test_db, "EPC-H-0002")

        _create_possession(test_db, daemon_name="persona1", role="Engineer", epic_id="EPC-H-0001")
        _create_possession(test_db, daemon_name="persona2", role="Tester", epic_id="EPC-H-0002")
        _create_possession(test_db, daemon_name="persona3", role="Engineer")  # general

        manager = PossessionManager(test_db)
        results = manager.list_possessions(epic_id="EPC-H-0001")
        assert len(results) == 1
        assert results[0].epic_id == "EPC-H-0001"

    def test_get_possession_includes_epic_id(self, test_db):
        """get_possession returns the epic_id field correctly."""
        _create_epic(test_db, "EPC-H-0010")
        mid = _create_possession(test_db, daemon_name="test-persona", role="Engineer", epic_id="EPC-H-0010")
        manager = PossessionManager(test_db)

        possession = manager.get_possession(mid)
        assert possession.epic_id == "EPC-H-0010"

    def test_get_possession_without_epic_returns_none(self, test_db):
        """get_possession for general possession returns epic_id as None."""
        mid = _create_possession(test_db, daemon_name="test-persona", role="Engineer")
        manager = PossessionManager(test_db)

        possession = manager.get_possession(mid)
        assert possession.epic_id is None


# ===========================================================================
# UNIT TESTS: Mutual exclusivity validation (CLI layer)
# ===========================================================================


class TestMutualExclusivityValidation:
    """Test --task and --epic mutual exclusivity on `s9 mission start`."""

    def test_mission_start_both_task_and_epic_rejected(self, initialized_project):
        """Providing both --task and --epic should fail."""
        result = runner.invoke(
            app,
            [
                "mission",
                "start",
                "--name",
                "azazel",
                "--role",
                "Engineer",
                "--task",
                "Some task description",
                "--epic",
                "EPC-H-0001",
            ],
        )
        assert result.exit_code != 0
        assert "Cannot specify both --task and --epic" in result.output

    def test_mission_start_with_task_only(self, initialized_project):
        """Providing only --task should succeed."""
        result = runner.invoke(
            app,
            [
                "mission",
                "start",
                "--name",
                "azazel",
                "--role",
                "Engineer",
                "--task",
                "Do some work",
            ],
        )
        assert result.exit_code == 0
        assert "Started mission" in result.output

    def test_mission_start_with_epic_only(self, initialized_project):
        """Providing only --epic should succeed (if epic exists)."""
        # First create an epic
        runner.invoke(
            app,
            ["epic", "create", "--title", "Test Epic", "--priority", "HIGH"],
        )

        result = runner.invoke(
            app,
            [
                "mission",
                "start",
                "--name",
                "azazel",
                "--role",
                "Engineer",
                "--epic",
                "EPC-H-0001",
            ],
        )
        assert result.exit_code == 0
        assert "Started mission" in result.output
        assert "EPC-H-0001" in result.output

    def test_mission_start_with_neither_flag(self, initialized_project):
        """Providing neither --task nor --epic should succeed (general possession)."""
        result = runner.invoke(
            app,
            [
                "mission",
                "start",
                "--name",
                "azazel",
                "--role",
                "Engineer",
            ],
        )
        assert result.exit_code == 0
        assert "Started mission" in result.output

    def test_mission_start_epic_not_found(self, initialized_project):
        """Providing --epic with non-existent epic should fail."""
        result = runner.invoke(
            app,
            [
                "mission",
                "start",
                "--name",
                "azazel",
                "--role",
                "Engineer",
                "--epic",
                "EPC-H-9999",
            ],
        )
        assert result.exit_code != 0
        assert "not found" in result.output.lower()


# ===========================================================================
# UNIT TESTS: Epic-scoped task claiming
# ===========================================================================


class TestEpicScopedTaskClaiming:
    """Test claim_task epic scoping validation in TaskManager."""

    def test_epic_scoped_possession_can_claim_matching_epic_task(self, test_db):
        """Epic-scoped possession can claim a task in the same epic."""
        _create_epic(test_db, "EPC-H-0001")
        mid = _create_possession(test_db, epic_id="EPC-H-0001")
        _create_task(test_db, "ENG-M-0001", epic_id="EPC-H-0001")

        manager = TaskManager(test_db)
        manager.claim_task("ENG-M-0001", possession_id=mid, current_role="Engineer")

        task = manager.get_task("ENG-M-0001")
        assert task.current_possession_id == mid
        assert task.status == TaskStatus.UNDERWAY.value

    def test_epic_scoped_possession_cannot_claim_different_epic_task(self, test_db):
        """Epic-scoped possession cannot claim a task in a different epic."""
        _create_epic(test_db, "EPC-H-0001")
        _create_epic(test_db, "EPC-H-0002")
        mid = _create_possession(test_db, epic_id="EPC-H-0001")
        _create_task(test_db, "ENG-M-0001", epic_id="EPC-H-0002")

        manager = TaskManager(test_db)
        with pytest.raises(TaskError, match="Cannot claim task.*from epic EPC-H-0002.*scoped to epic EPC-H-0001"):
            manager.claim_task("ENG-M-0001", possession_id=mid, current_role="Engineer")

    def test_epic_scoped_possession_cannot_claim_unscoped_task(self, test_db):
        """Epic-scoped possession cannot claim a task with no epic."""
        _create_epic(test_db, "EPC-H-0001")
        mid = _create_possession(test_db, epic_id="EPC-H-0001")
        _create_task(test_db, "ENG-M-0001", epic_id=None)

        manager = TaskManager(test_db)
        with pytest.raises(TaskError, match="Cannot claim task.*scoped to epic EPC-H-0001"):
            manager.claim_task("ENG-M-0001", possession_id=mid, current_role="Engineer")

    def test_general_possession_can_claim_any_task(self, test_db):
        """General possession (no epic_id) can claim tasks regardless of epic."""
        _create_epic(test_db, "EPC-H-0001")
        mid = _create_possession(test_db, epic_id=None)
        _create_task(test_db, "ENG-M-0001", epic_id="EPC-H-0001")

        manager = TaskManager(test_db)
        manager.claim_task("ENG-M-0001", possession_id=mid, current_role="Engineer")

        task = manager.get_task("ENG-M-0001")
        assert task.current_possession_id == mid

    def test_general_possession_can_claim_unscoped_task(self, test_db):
        """General possession can claim a task with no epic."""
        mid = _create_possession(test_db, epic_id=None)
        _create_task(test_db, "ENG-M-0001", epic_id=None)

        manager = TaskManager(test_db)
        manager.claim_task("ENG-M-0001", possession_id=mid, current_role="Engineer")

        task = manager.get_task("ENG-M-0001")
        assert task.current_possession_id == mid

    def test_epic_scoped_possession_claims_multiple_tasks_in_same_epic(self, test_db):
        """Epic-scoped possession can claim and release multiple tasks within the same epic."""
        _create_epic(test_db, "EPC-H-0001")
        mid = _create_possession(test_db, epic_id="EPC-H-0001")
        _create_task(test_db, "ENG-M-0001", epic_id="EPC-H-0001")
        _create_task(test_db, "ENG-M-0002", epic_id="EPC-H-0001")

        manager = TaskManager(test_db)

        manager.claim_task("ENG-M-0001", possession_id=mid, current_role="Engineer")
        assert manager.get_task("ENG-M-0001").current_possession_id == mid

        manager.release_task("ENG-M-0001")
        manager.claim_task("ENG-M-0002", possession_id=mid, current_role="Engineer")
        assert manager.get_task("ENG-M-0002").current_possession_id == mid

    def test_claim_task_nonexistent_possession_raises_error(self, test_db):
        """Claiming with a non-existent possession ID should fail."""
        _create_task(test_db, "ENG-M-0001")

        manager = TaskManager(test_db)
        with pytest.raises(TaskError, match="Possession 999 not found"):
            manager.claim_task("ENG-M-0001", possession_id=999, current_role="Engineer")


# ===========================================================================
# UNIT TESTS: Role matching on claim (CLI layer)
# ===========================================================================


class TestRoleMatchingOnClaim:
    """Test that task claim validates role matches at the CLI layer."""

    def test_claim_with_matching_role_succeeds(self, initialized_project):
        """Claiming with matching role should succeed."""
        # Create a task
        create_result = runner.invoke(
            app,
            ["task", "create", "--title", "Test Task", "--role", "Engineer", "--priority", "MEDIUM"],
        )
        assert create_result.exit_code == 0
        match = re.search(r"Created task ([A-Z]+-[A-Z]-\d+)", create_result.output)
        assert match
        task_id = match.group(1)

        # Start a possession
        mission_result = runner.invoke(
            app,
            ["mission", "start", "--name", "azazel", "--role", "Engineer", "--task", "Test"],
        )
        assert mission_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", mission_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        # Claim task
        claim_result = runner.invoke(
            app,
            ["task", "claim", task_id, "--mission", mission_id, "--role", "Engineer"],
        )
        assert claim_result.exit_code == 0
        assert "claimed" in claim_result.output.lower()

    def test_claim_with_mismatched_role_fails(self, initialized_project):
        """Claiming with non-matching role should fail at CLI validation."""
        # Create an Engineer task
        create_result = runner.invoke(
            app,
            ["task", "create", "--title", "Engineer Task", "--role", "Engineer", "--priority", "MEDIUM"],
        )
        assert create_result.exit_code == 0
        match = re.search(r"Created task ([A-Z]+-[A-Z]-\d+)", create_result.output)
        assert match
        task_id = match.group(1)

        # Start a Tester possession
        mission_result = runner.invoke(
            app,
            ["mission", "start", "--name", "lilith", "--role", "Tester", "--task", "Test"],
        )
        assert mission_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", mission_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        # Try to claim with Tester role — should fail
        claim_result = runner.invoke(
            app,
            ["task", "claim", task_id, "--mission", mission_id, "--role", "Tester"],
        )
        assert claim_result.exit_code != 0
        assert "does not match" in claim_result.output


# ===========================================================================
# UNIT TESTS: get_next_epic_task
# ===========================================================================


class TestGetNextEpicTask:
    """Test TaskManager.get_next_epic_task for epic auto-claim logic."""

    def test_returns_next_todo_task_in_epic_matching_role(self, test_db):
        """Should return the highest-priority TODO task in the possession's epic for that role."""
        _create_epic(test_db, "EPC-H-0001")
        mid = _create_possession(test_db, role="Engineer", epic_id="EPC-H-0001")
        _create_task(test_db, "ENG-M-0001", role="Engineer", priority="MEDIUM", epic_id="EPC-H-0001")
        _create_task(test_db, "ENG-H-0002", role="Engineer", priority="HIGH", epic_id="EPC-H-0001")
        _create_task(test_db, "TST-H-0003", role="Tester", priority="HIGH", epic_id="EPC-H-0001")

        manager = TaskManager(test_db)
        task = manager.get_next_epic_task(mid)

        assert task is not None
        assert task.id == "ENG-H-0002"  # HIGH priority Engineer task

    def test_skips_non_todo_tasks(self, test_db):
        """Should only return TODO tasks, not UNDERWAY/COMPLETE."""
        _create_epic(test_db, "EPC-H-0001")
        mid = _create_possession(test_db, role="Engineer", epic_id="EPC-H-0001")
        _create_task(test_db, "ENG-H-0001", role="Engineer", priority="HIGH", status="UNDERWAY", epic_id="EPC-H-0001")
        _create_task(test_db, "ENG-H-0002", role="Engineer", priority="HIGH", status="COMPLETE", epic_id="EPC-H-0001")
        _create_task(test_db, "ENG-M-0003", role="Engineer", priority="MEDIUM", status="TODO", epic_id="EPC-H-0001")

        manager = TaskManager(test_db)
        task = manager.get_next_epic_task(mid)

        assert task is not None
        assert task.id == "ENG-M-0003"

    def test_returns_none_when_no_todo_tasks(self, test_db):
        """Should return None when all tasks in epic are complete."""
        _create_epic(test_db, "EPC-H-0001")
        mid = _create_possession(test_db, role="Engineer", epic_id="EPC-H-0001")
        _create_task(test_db, "ENG-H-0001", role="Engineer", priority="HIGH", status="COMPLETE", epic_id="EPC-H-0001")

        manager = TaskManager(test_db)
        task = manager.get_next_epic_task(mid)

        assert task is None

    def test_returns_none_when_no_tasks_for_role(self, test_db):
        """Should return None when no tasks match the possession's role."""
        _create_epic(test_db, "EPC-H-0001")
        mid = _create_possession(test_db, role="Engineer", epic_id="EPC-H-0001")
        _create_task(test_db, "TST-H-0001", role="Tester", priority="HIGH", epic_id="EPC-H-0001")

        manager = TaskManager(test_db)
        task = manager.get_next_epic_task(mid)

        assert task is None

    def test_returns_none_when_epic_has_no_tasks(self, test_db):
        """Should return None when epic has no tasks at all."""
        _create_epic(test_db, "EPC-H-0001")
        mid = _create_possession(test_db, role="Engineer", epic_id="EPC-H-0001")

        manager = TaskManager(test_db)
        task = manager.get_next_epic_task(mid)

        assert task is None

    def test_raises_error_for_non_epic_scoped_possession(self, test_db):
        """Should raise TaskError if possession has no epic_id."""
        mid = _create_possession(test_db, role="Engineer", epic_id=None)

        manager = TaskManager(test_db)
        with pytest.raises(TaskError, match="not epic-scoped"):
            manager.get_next_epic_task(mid)

    def test_raises_error_for_nonexistent_possession(self, test_db):
        """Should raise TaskError if possession doesn't exist."""
        manager = TaskManager(test_db)
        with pytest.raises(TaskError, match="Possession 999 not found"):
            manager.get_next_epic_task(999)

    def test_priority_ordering_critical_first(self, test_db):
        """Should pick CRITICAL over HIGH over MEDIUM over LOW."""
        _create_epic(test_db, "EPC-H-0001")
        mid = _create_possession(test_db, role="Engineer", epic_id="EPC-H-0001")
        _create_task(test_db, "ENG-L-0001", role="Engineer", priority="LOW", epic_id="EPC-H-0001")
        _create_task(test_db, "ENG-M-0002", role="Engineer", priority="MEDIUM", epic_id="EPC-H-0001")
        _create_task(test_db, "ENG-C-0003", role="Engineer", priority="CRITICAL", epic_id="EPC-H-0001")
        _create_task(test_db, "ENG-H-0004", role="Engineer", priority="HIGH", epic_id="EPC-H-0001")

        manager = TaskManager(test_db)
        task = manager.get_next_epic_task(mid)

        assert task is not None
        assert task.id == "ENG-C-0003"

    def test_does_not_return_tasks_from_other_epics(self, test_db):
        """Should only return tasks from the possession's epic, not other epics."""
        _create_epic(test_db, "EPC-H-0001")
        _create_epic(test_db, "EPC-H-0002")
        mid = _create_possession(test_db, role="Engineer", epic_id="EPC-H-0001")
        _create_task(test_db, "ENG-H-0001", role="Engineer", priority="HIGH", epic_id="EPC-H-0002")
        _create_task(test_db, "ENG-M-0002", role="Engineer", priority="MEDIUM", epic_id="EPC-H-0001")

        manager = TaskManager(test_db)
        task = manager.get_next_epic_task(mid)

        assert task is not None
        assert task.id == "ENG-M-0002"  # Only task in EPC-H-0001


# ===========================================================================
# CLI INTEGRATION TESTS: s9 task next edge cases
# ===========================================================================


class TestTaskNextEdgeCases:
    """Test `s9 task next` command edge cases."""

    def test_next_suggestion_mode_no_tasks(self, initialized_project):
        """Suggestion mode with no TODO tasks shows appropriate message."""
        result = runner.invoke(app, ["task", "next"])
        # Should succeed (exit 0) but show "no tasks" message
        assert result.exit_code == 0

    def test_next_suggestion_mode_with_wrong_role(self, initialized_project):
        """Suggestion mode with non-existent role tasks."""
        # Create a task for Engineer
        runner.invoke(
            app,
            ["task", "create", "--title", "Engineer Task", "--role", "Engineer", "--priority", "HIGH"],
        )

        # Query for Tester - no tasks
        result = runner.invoke(app, ["task", "next", "--role", "Tester"])
        assert result.exit_code == 0
        assert "no todo tasks" in result.output.lower() or "warning" in result.output.lower()

    def test_next_epic_mode_without_epic_scoped_mission(self, initialized_project):
        """Epic mode with non-epic-scoped possession should fail."""
        # Start a general possession (no --epic)
        mission_result = runner.invoke(
            app,
            ["mission", "start", "--name", "azazel", "--role", "Engineer", "--task", "General work"],
        )
        assert mission_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", mission_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        # Try epic auto-claim
        result = runner.invoke(app, ["task", "next", "--mission", mission_id])
        assert result.exit_code != 0
        assert "not epic-scoped" in result.output.lower() or "epic" in result.output.lower()

    def test_next_epic_mode_no_tasks_in_epic(self, initialized_project):
        """Epic mode with no TODO tasks in epic shows info message."""
        # Create an epic
        runner.invoke(
            app,
            ["epic", "create", "--title", "Empty Epic", "--priority", "HIGH"],
        )

        # Start an epic-scoped possession
        mission_result = runner.invoke(
            app,
            [
                "mission",
                "start",
                "--name",
                "azazel",
                "--role",
                "Engineer",
                "--epic",
                "EPC-H-0001",
            ],
        )
        assert mission_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", mission_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        # Try to get next task - none available
        result = runner.invoke(app, ["task", "next", "--mission", mission_id])
        assert result.exit_code == 0
        assert "no available" in result.output.lower() or "info" in result.output.lower()

    def test_next_epic_mode_claims_task_successfully(self, initialized_project):
        """Epic mode auto-claims the next TODO task in the epic."""
        # Create an epic
        runner.invoke(
            app,
            ["epic", "create", "--title", "Work Epic", "--priority", "HIGH"],
        )

        # Create a task and link it to the epic
        create_result = runner.invoke(
            app,
            [
                "task",
                "create",
                "--title",
                "Epic Task",
                "--role",
                "Engineer",
                "--priority",
                "HIGH",
                "--epic",
                "EPC-H-0001",
            ],
        )
        assert create_result.exit_code == 0

        # Start an epic-scoped possession
        mission_result = runner.invoke(
            app,
            [
                "mission",
                "start",
                "--name",
                "azazel",
                "--role",
                "Engineer",
                "--epic",
                "EPC-H-0001",
            ],
        )
        assert mission_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", mission_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        # Auto-claim next task
        result = runner.invoke(app, ["task", "next", "--mission", mission_id])
        assert result.exit_code == 0
        assert "claimed" in result.output.lower()

    def test_next_epic_mode_nonexistent_mission(self, initialized_project):
        """Epic mode with non-existent possession ID should fail."""
        result = runner.invoke(app, ["task", "next", "--mission", "99999"])
        assert result.exit_code != 0

    def test_next_suggestion_mode_json_output(self, initialized_project):
        """Suggestion mode with --json returns valid JSON."""
        runner.invoke(
            app,
            ["task", "create", "--title", "JSON Test", "--role", "Engineer", "--priority", "HIGH"],
        )

        result = runner.invoke(app, ["task", "next", "--json"])
        assert result.exit_code == 0
        # Should contain JSON structure
        assert "todo_tasks" in result.output

    def test_next_epic_mode_json_output(self, initialized_project):
        """Epic mode with --json returns claimed task in JSON."""
        # Create epic
        runner.invoke(
            app,
            ["epic", "create", "--title", "JSON Epic", "--priority", "HIGH"],
        )

        # Create task in epic
        runner.invoke(
            app,
            [
                "task",
                "create",
                "--title",
                "JSON Epic Task",
                "--role",
                "Engineer",
                "--priority",
                "HIGH",
                "--epic",
                "EPC-H-0001",
            ],
        )

        # Start epic-scoped possession
        mission_result = runner.invoke(
            app,
            [
                "mission",
                "start",
                "--name",
                "azazel",
                "--role",
                "Engineer",
                "--epic",
                "EPC-H-0001",
            ],
        )
        mid_match = re.search(r"#(\d+)", mission_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        result = runner.invoke(app, ["task", "next", "--mission", mission_id, "--json"])
        assert result.exit_code == 0
        assert "UNDERWAY" in result.output


# ===========================================================================
# CLI INTEGRATION TESTS: Mission show scope display
# ===========================================================================


class TestMissionShowScopeDisplay:
    """Test that `s9 mission show` displays scope correctly."""

    def test_show_general_mission_scope(self, initialized_project):
        """General possession shows 'General' scope."""
        mission_result = runner.invoke(
            app,
            ["mission", "start", "--name", "azazel", "--role", "Engineer"],
        )
        assert mission_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", mission_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        show_result = runner.invoke(app, ["mission", "show", mission_id])
        assert show_result.exit_code == 0
        assert "General" in show_result.output

    def test_show_epic_scoped_mission_scope(self, initialized_project):
        """Epic-scoped possession shows 'Epic-scoped (EPC-X-NNNN)' scope."""
        runner.invoke(
            app,
            ["epic", "create", "--title", "Show Epic", "--priority", "HIGH"],
        )

        mission_result = runner.invoke(
            app,
            [
                "mission",
                "start",
                "--name",
                "azazel",
                "--role",
                "Engineer",
                "--epic",
                "EPC-H-0001",
            ],
        )
        assert mission_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", mission_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        show_result = runner.invoke(app, ["mission", "show", mission_id])
        assert show_result.exit_code == 0
        assert "Epic-scoped" in show_result.output
        assert "EPC-H-0001" in show_result.output

    def test_show_task_scoped_mission_scope(self, initialized_project):
        """Task-scoped possession shows 'Task-scoped (TASK-ID)' after claiming a task."""
        # Start possession
        mission_result = runner.invoke(
            app,
            ["mission", "start", "--name", "azazel", "--role", "Engineer", "--task", "Do work"],
        )
        assert mission_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", mission_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        # Create and claim a task
        create_result = runner.invoke(
            app,
            ["task", "create", "--title", "Scoped Task", "--role", "Engineer", "--priority", "MEDIUM"],
        )
        assert create_result.exit_code == 0
        task_match = re.search(r"Created task ([A-Z]+-[A-Z]-\d+)", create_result.output)
        assert task_match
        task_id = task_match.group(1)

        runner.invoke(
            app,
            ["task", "claim", task_id, "--mission", mission_id, "--role", "Engineer"],
        )

        show_result = runner.invoke(app, ["mission", "show", mission_id])
        assert show_result.exit_code == 0
        assert "Task-scoped" in show_result.output
        assert task_id in show_result.output


# ===========================================================================
# UNIT TESTS: Claim error cases
# ===========================================================================


class TestClaimErrorCases:
    """Test various error conditions when claiming tasks."""

    def test_claim_nonexistent_task_at_cli(self, initialized_project):
        """Claiming a non-existent task should fail."""
        mission_result = runner.invoke(
            app,
            ["mission", "start", "--name", "azazel", "--role", "Engineer", "--task", "Test"],
        )
        mid_match = re.search(r"#(\d+)", mission_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        result = runner.invoke(
            app,
            ["task", "claim", "ENG-H-9999", "--mission", mission_id, "--role", "Engineer"],
        )
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_claim_blocked_task(self, initialized_project):
        """Claiming a blocked task should fail at CLI level."""
        # Create task
        create_result = runner.invoke(
            app,
            ["task", "create", "--title", "Blocked Task", "--role", "Engineer", "--priority", "HIGH"],
        )
        assert create_result.exit_code == 0
        task_match = re.search(r"Created task ([A-Z]+-[A-Z]-\d+)", create_result.output)
        assert task_match
        task_id = task_match.group(1)

        # Create a dependency task that's not complete
        dep_result = runner.invoke(
            app,
            ["task", "create", "--title", "Dependency", "--role", "Engineer", "--priority", "HIGH"],
        )
        assert dep_result.exit_code == 0
        dep_match = re.search(r"Created task ([A-Z]+-[A-Z]-\d+)", dep_result.output)
        assert dep_match
        dep_id = dep_match.group(1)

        # Add dependency
        runner.invoke(app, ["task", "add-dependency", task_id, dep_id])

        # Start possession
        mission_result = runner.invoke(
            app,
            ["mission", "start", "--name", "azazel", "--role", "Engineer", "--task", "Test"],
        )
        mid_match = re.search(r"#(\d+)", mission_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        # Try to claim blocked task
        result = runner.invoke(
            app,
            ["task", "claim", task_id, "--mission", mission_id, "--role", "Engineer"],
        )
        assert result.exit_code != 0
        assert "blocked" in result.output.lower() or "dependency" in result.output.lower()

    def test_claim_epic_mismatch_at_cli(self, initialized_project):
        """Claiming an epic-mismatched task should fail via manager layer."""
        # Create two epics
        runner.invoke(app, ["epic", "create", "--title", "Epic 1", "--priority", "HIGH"])
        runner.invoke(app, ["epic", "create", "--title", "Epic 2", "--priority", "HIGH"])

        # Create task in Epic 2
        create_result = runner.invoke(
            app,
            [
                "task",
                "create",
                "--title",
                "Epic 2 Task",
                "--role",
                "Engineer",
                "--priority",
                "HIGH",
                "--epic",
                "EPC-H-0002",
            ],
        )
        assert create_result.exit_code == 0
        task_match = re.search(r"Created task ([A-Z]+-[A-Z]-\d+)", create_result.output)
        assert task_match
        task_id = task_match.group(1)

        # Start epic-scoped possession for Epic 1
        mission_result = runner.invoke(
            app,
            [
                "mission",
                "start",
                "--name",
                "azazel",
                "--role",
                "Engineer",
                "--epic",
                "EPC-H-0001",
            ],
        )
        assert mission_result.exit_code == 0
        mid_match = re.search(r"#(\d+)", mission_result.output)
        assert mid_match
        mission_id = mid_match.group(1)

        # Try to claim task from Epic 2 with Epic 1 possession
        result = runner.invoke(
            app,
            ["task", "claim", task_id, "--mission", mission_id, "--role", "Engineer"],
        )
        assert result.exit_code != 0
        assert "cannot claim" in result.output.lower() or "epic" in result.output.lower()
