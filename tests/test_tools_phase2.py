"""Unit tests for all Phase 2 OpenCode tool scripts.

Tools under test (.opencode/tools/):
  Possession lifecycle (8): possession_init, possession_role_record, possession_daemon_record,
                             possession_rename_session, possession_rename_exorcised,
                             possession_end, possession_summary, possession_dashboard
  Task management     (6): task_claim, task_release, task_close, task_update,
                             task_show, task_create
  Daemon              (3): daemon_show, daemon_suggest, daemon_set_bio

Testing strategy:
- Each tool's main() function is called directly (no subprocess).
- sys.stdin is monkeypatched to supply JSON input.
- get_db_path() is monkeypatched to return the in-memory test DB path.
- All assertions are made on the returned JSON string.
"""

import importlib.util
import json
import sys
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from site_nine.core.database import Database

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TOOLS_DIR = Path(__file__).parent.parent / ".opencode" / "tools"

# Ensure tool_logging (and any other shared modules in .opencode/tools/) is importable
# when tool scripts are loaded via importlib in tests.
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


def load_tool(name: str):
    """Dynamically load a tool module from .opencode/tools/."""
    spec = importlib.util.spec_from_file_location(name, TOOLS_DIR / f"{name}.py")
    assert spec is not None and spec.loader is not None, f"Cannot find tool: {name}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def call_tool(name: str, payload: dict[str, Any], db_path: Path) -> dict:
    """Call a tool's main() with mocked stdin and db_path, return parsed JSON.

    Tools use ``from site_nine.core.paths import get_db_path`` which binds a
    local reference in each dynamically-loaded module's namespace at import
    time.  Patching the source module (``site_nine.core.paths.get_db_path``)
    does NOT intercept those already-bound local names.  We must patch the
    attribute directly on the loaded module object instead.
    """
    mod = load_tool(name)
    stdin_data = json.dumps(payload)

    # Build per-module patches only for attributes that the tool actually has.
    opencode_dir = db_path.parent  # .opencode/data  → parent = .opencode
    project_root = db_path.parent.parent  # .opencode        → parent = tmp_path

    patches = [patch("sys.stdin", StringIO(stdin_data))]
    if hasattr(mod, "get_db_path"):
        patches.append(patch.object(mod, "get_db_path", return_value=db_path))
    if hasattr(mod, "get_opencode_dir"):
        patches.append(patch.object(mod, "get_opencode_dir", return_value=opencode_dir))
    if hasattr(mod, "get_project_root"):
        patches.append(patch.object(mod, "get_project_root", return_value=project_root))

    from contextlib import ExitStack

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        result = mod.main()

    assert isinstance(result, str), f"Tool {name} returned non-string: {type(result)}"
    return json.loads(result)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tool_db(tmp_path):
    """Initialised database with seed daemons and a couple of test tasks."""
    import sqlite3

    db_dir = tmp_path / ".opencode" / "data"
    db_dir.mkdir(parents=True)
    db_path = db_dir / "project.db"

    with Database(db_path) as db:
        db.initialize_schema()

        # Ensure the blocks table exists (may not be in base schema yet).
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS blocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    block_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    resolved_at TEXT,
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
                )
                """
            )
            conn.commit()

        # Daemons (replaces old personas seeding)
        db.execute_update(
            """
            INSERT INTO daemons (name, role, daemonology, personality, incarnations)
            VALUES
                ('hermes', 'Engineer',  'Greek messenger daemon', 'Swift and clever', 0),
                ('athena', 'Tester',    'Greek wisdom daemon',    'Methodical',       0),
                ('odin',   'Architect', 'Norse all-father daemon','Visionary',        0)
            """
        )

        # Tasks
        db.execute_update(
            """
            INSERT INTO tasks (id, title, description, status, priority, role,
                               file_path, created_at, updated_at)
            VALUES
                ('ENG-H-0001', 'Engineer task 1', 'Desc 1', 'TODO', 'HIGH',
                 'Engineer', '.opencode/work/tasks/ENG-H-0001.md',
                 datetime('now'), datetime('now')),
                ('TST-M-0002', 'Tester task 2',   'Desc 2', 'TODO', 'MEDIUM',
                 'Tester',   '.opencode/work/tasks/TST-M-0002.md',
                 datetime('now'), datetime('now')),
                ('TST-H-0003', 'Tester task 3',   'Desc 3', 'TODO', 'HIGH',
                 'Tester',   '.opencode/work/tasks/TST-H-0003.md',
                 datetime('now'), datetime('now'))
            """
        )

        yield db_path


@pytest.fixture
def tool_db_with_mission(tool_db):
    """tool_db plus an ACTIVE possession (id=1) and an UNDERWAY task."""
    with Database(tool_db) as db:
        db.execute_update(
            """
            INSERT INTO possessions (id, daemon_name, role, status,
                                     opencode_session_id, possession_log,
                                     start_time,
                                     created_at, updated_at, last_heartbeat_at)
            VALUES (1, 'hermes', 'Engineer', 'ACTIVE',
                    'sess-abc', '.opencode/work/possessions/test.md',
                    time('now'),
                    datetime('now'), datetime('now'), datetime('now'))
            """
        )
        # Claim ENG-H-0001 for possession 1
        db.execute_update(
            """
            UPDATE tasks
            SET status = 'UNDERWAY', current_possession_id = 1,
                claimed_at = datetime('now'), updated_at = datetime('now')
            WHERE id = 'ENG-H-0001'
            """
        )
    return tool_db




# TASK MANAGEMENT TOOLS (6)
# ===========================================================================


class TestTaskClaim:
    def test_claims_todo_task(self, tool_db_with_mission):
        result = call_tool(
            "task_claim",
            {"task_id": "TST-M-0002", "mission_id": 1, "role": "Tester"},
            tool_db_with_mission,
        )
        assert result["status"] == "UNDERWAY"
        assert result["task_id"] == "TST-M-0002"
        assert result["possession_id"] == 1

    def test_task_not_found_returns_error(self, tool_db_with_mission):
        result = call_tool(
            "task_claim",
            {"task_id": "TST-H-9999", "mission_id": 1, "role": "Tester"},
            tool_db_with_mission,
        )
        assert result.get("error") == "task_not_found"

    def test_role_mismatch_returns_error(self, tool_db_with_mission):
        result = call_tool(
            "task_claim",
            {"task_id": "TST-M-0002", "mission_id": 1, "role": "Engineer"},
            tool_db_with_mission,
        )
        assert result.get("error") == "role_mismatch"
        assert "task_role" in result
        assert "claiming_role" in result

    def test_blocked_task_returns_error(self, tool_db_with_mission):
        # Insert an unresolved external blocker
        with Database(tool_db_with_mission) as db:
            db.execute_update(
                """
                INSERT INTO blocks (task_id, block_type, description)
                VALUES ('TST-H-0003', 'external', 'Waiting for third party')
                """
            )
        result = call_tool(
            "task_claim",
            {"task_id": "TST-H-0003", "mission_id": 1, "role": "Tester"},
            tool_db_with_mission,
        )
        assert result.get("error") == "task_blocked"
        assert "blockers" in result


class TestTaskRelease:
    def test_releases_underway_task_back_to_todo(self, tool_db_with_mission):
        result = call_tool(
            "task_release",
            {"task_id": "ENG-H-0001"},
            tool_db_with_mission,
        )
        assert result["status"] == "TODO"
        assert result["task_id"] == "ENG-H-0001"

    def test_task_not_found_returns_error(self, tool_db):
        result = call_tool(
            "task_release",
            {"task_id": "ENG-H-9999"},
            tool_db,
        )
        assert result.get("error") == "task_not_found"


class TestTaskClose:
    def test_closes_task_as_complete(self, tool_db_with_mission):
        result = call_tool(
            "task_close",
            {"task_id": "ENG-H-0001", "status": "COMPLETE"},
            tool_db_with_mission,
        )
        assert result["status"] == "COMPLETE"

    def test_closes_task_as_aborted(self, tool_db_with_mission):
        result = call_tool(
            "task_close",
            {"task_id": "ENG-H-0001", "status": "ABORTED"},
            tool_db_with_mission,
        )
        assert result["status"] == "ABORTED"

    def test_invalid_status_returns_error(self, tool_db):
        result = call_tool(
            "task_close",
            {"task_id": "TST-M-0002", "status": "PENDING"},
            tool_db,
        )
        assert result.get("error") == "invalid_status"

    def test_task_not_found_returns_error(self, tool_db):
        result = call_tool(
            "task_close",
            {"task_id": "ENG-H-9999", "status": "COMPLETE"},
            tool_db,
        )
        assert result.get("error") == "task_not_found"

    def test_status_is_case_insensitive(self, tool_db_with_mission):
        result = call_tool(
            "task_close",
            {"task_id": "ENG-H-0001", "status": "complete"},
            tool_db_with_mission,
        )
        assert result["status"] == "COMPLETE"


class TestTaskUpdate:
    def test_updates_title(self, tool_db):
        result = call_tool(
            "task_update",
            {"task_id": "TST-M-0002", "title": "New title"},
            tool_db,
        )
        assert result["task"]["title"] == "New title"

    def test_updates_priority(self, tool_db):
        result = call_tool(
            "task_update",
            {"task_id": "TST-M-0002", "priority": "HIGH"},
            tool_db,
        )
        assert result["task"]["priority"] == "HIGH"

    def test_updates_notes(self, tool_db):
        result = call_tool(
            "task_update",
            {"task_id": "TST-M-0002", "notes": "Some notes"},
            tool_db,
        )
        assert result["task"]["notes"] == "Some notes"

    def test_invalid_status_returns_error(self, tool_db):
        result = call_tool(
            "task_update",
            {"task_id": "TST-M-0002", "status": "FLYING"},
            tool_db,
        )
        assert result.get("error") == "invalid_status"

    def test_invalid_priority_returns_error(self, tool_db):
        result = call_tool(
            "task_update",
            {"task_id": "TST-M-0002", "priority": "EXTREME"},
            tool_db,
        )
        assert result.get("error") == "invalid_priority"

    def test_task_not_found_returns_error(self, tool_db):
        result = call_tool(
            "task_update",
            {"task_id": "TST-H-9999", "title": "Nope"},
            tool_db,
        )
        assert result.get("error") == "task_not_found"

    def test_no_fields_returns_error(self, tool_db):
        result = call_tool(
            "task_update",
            {"task_id": "TST-M-0002"},
            tool_db,
        )
        assert result.get("error") == "no_updates"


class TestTaskShow:
    def test_shows_single_task_by_id(self, tool_db):
        result = call_tool(
            "task_show",
            {"task_id": "TST-M-0002"},
            tool_db,
        )
        assert result["data"]["id"] == "TST-M-0002"
        assert result["data"]["role"] == "Tester"

    def test_task_not_found_returns_error(self, tool_db):
        result = call_tool(
            "task_show",
            {"task_id": "ENG-H-9999"},
            tool_db,
        )
        assert result.get("error") == "task_not_found"

    def test_list_all_tasks(self, tool_db):
        result = call_tool("task_show", {}, tool_db)
        assert "data" in result
        assert result["count"] == 3

    def test_list_tasks_filtered_by_role(self, tool_db):
        result = call_tool("task_show", {"role": "Tester"}, tool_db)
        assert result["count"] == 2
        for task in result["data"]:
            assert task["role"] == "Tester"

    def test_list_tasks_filtered_by_status(self, tool_db):
        result = call_tool("task_show", {"status": "TODO"}, tool_db)
        assert result["count"] == 3

    def test_report_mode(self, tool_db):
        result = call_tool("task_show", {"report": True}, tool_db)
        assert "data" in result
        assert "total" in result["data"]
        assert "by_status" in result["data"]
        assert result["data"]["total"] == 3

    def test_report_active_only(self, tool_db_with_mission):
        # ENG-H-0001 is UNDERWAY, TST-M-0002 and TST-H-0003 are TODO
        result = call_tool("task_show", {"report": True, "active_only": True}, tool_db_with_mission)
        assert result["data"]["total"] == 3  # none are COMPLETE or ABORTED


class TestTaskCreate:
    def test_creates_task_with_required_fields(self, tool_db):
        result = call_tool(
            "task_create",
            {"title": "New test task", "role": "Tester", "priority": "HIGH"},
            tool_db,
        )
        assert "task_id" in result
        assert result["role"] == "Tester"
        assert result["priority"] == "HIGH"

    def test_invalid_role_returns_error(self, tool_db):
        result = call_tool(
            "task_create",
            {"title": "Bad role task", "role": "Wizard"},
            tool_db,
        )
        assert result.get("error") == "invalid_role"

    def test_invalid_priority_returns_error(self, tool_db):
        result = call_tool(
            "task_create",
            {"title": "Bad prio task", "role": "Tester", "priority": "EXTREME"},
            tool_db,
        )
        assert result.get("error") == "invalid_priority"

    def test_default_priority_is_medium(self, tool_db):
        result = call_tool(
            "task_create",
            {"title": "Default prio task", "role": "Engineer"},
            tool_db,
        )
        assert result["priority"] == "MEDIUM"

    def test_task_id_format_matches_role_priority(self, tool_db):
        result = call_tool(
            "task_create",
            {"title": "Format test", "role": "Tester", "priority": "HIGH"},
            tool_db,
        )
        task_id = result["task_id"]
        assert task_id.startswith("TST-H-")


# ===========================================================================
