"""Unit tests for all Phase 2 OpenCode tool scripts.

Tools under test (.opencode/tools/):
  Mission lifecycle (7): mission_init, mission_role_record, mission_persona_record,
                          mission_rename_session, mission_rename_dismissed,
                          mission_end, mission_summary
  Task management  (6): task_claim, task_release, task_close, task_update,
                          task_show, task_create
  Handoff          (3): handoff_create, handoff_list, handoff_delete
  Persona          (3): persona_show, persona_suggest, persona_set_bio
  Dashboard        (1): mission_dashboard

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
    """Initialised database with seed personas and a couple of test tasks.

    The schema.sql in the package does not yet include the ``blocks`` table
    or the ``deleted_at`` column on ``handoffs`` (those live in the application
    but haven't been merged into the base schema yet).  We add them manually
    here so that the managers that reference them work correctly in tests.
    """
    import sqlite3

    db_dir = tmp_path / ".opencode" / "data"
    db_dir.mkdir(parents=True)
    db_path = db_dir / "project.db"

    with Database(db_path) as db:
        db.initialize_schema()

        # Apply missing DDL that hasn't landed in schema.sql yet.
        with sqlite3.connect(str(db_path)) as conn:
            # blocks table (used by BlockManager / task_claim)
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
            # deleted_at column on handoffs (used by HandoffManager soft-delete)
            try:
                conn.execute("ALTER TABLE handoffs ADD COLUMN deleted_at TEXT")
            except sqlite3.OperationalError:
                pass  # column already exists (idempotent)
            conn.commit()

        # Personas
        db.execute_update(
            """
            INSERT INTO personas (name, role, mythology, description)
            VALUES
                ('hermes', 'Engineer',  'Greek',    'Messenger god'),
                ('athena', 'Tester',    'Greek',    'Goddess of wisdom'),
                ('odin',   'Architect', 'Norse',    'All-father')
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
    """tool_db plus an ACTIVE mission (id=1) and an UNDERWAY task."""
    with Database(tool_db) as db:
        db.execute_update(
            """
            INSERT INTO missions (id, persona_name, role, codename, status,
                                  opencode_session_id, mission_file,
                                  start_date, start_time,
                                  created_at, updated_at, last_active_at)
            VALUES (1, 'hermes', 'Engineer', 'iron-falcon', 'ACTIVE',
                    'sess-abc', '.opencode/work/missions/test.md',
                    date('now'), time('now'),
                    datetime('now'), datetime('now'), datetime('now'))
            """
        )
        # Claim ENG-H-0001 for mission 1
        db.execute_update(
            """
            UPDATE tasks
            SET status = 'UNDERWAY', current_mission_id = 1,
                claimed_at = datetime('now'), updated_at = datetime('now')
            WHERE id = 'ENG-H-0001'
            """
        )
    return tool_db


# ===========================================================================
# MISSION LIFECYCLE TOOLS (7)
# ===========================================================================


class TestMissionInit:
    def test_creates_mission_returns_id_and_codename(self, tool_db):
        result = call_tool("mission_init", {"session_id": "sess-new-001"}, tool_db)
        assert "mission_id" in result
        assert "codename" in result
        assert isinstance(result["mission_id"], int)
        assert "-" in result["codename"]

    def test_double_binding_returns_error(self, tool_db):
        # First init — binds the session
        call_tool("mission_init", {"session_id": "sess-dup"}, tool_db)
        # Second init with same session — should report double_binding
        result = call_tool("mission_init", {"session_id": "sess-dup"}, tool_db)
        assert result.get("error") == "double_binding"
        assert "mission_id" in result

    def test_different_sessions_get_independent_missions(self, tool_db):
        r1 = call_tool("mission_init", {"session_id": "sess-A"}, tool_db)
        r2 = call_tool("mission_init", {"session_id": "sess-B"}, tool_db)
        assert r1["mission_id"] != r2["mission_id"]

    def test_codename_format_two_words(self, tool_db):
        result = call_tool("mission_init", {"session_id": "sess-fmt"}, tool_db)
        parts = result["codename"].split("-")
        assert len(parts) == 2


class TestMissionRoleRecord:
    def _init_mission(self, tool_db, session_id="sess-role-test") -> int:
        r = call_tool("mission_init", {"session_id": session_id}, tool_db)
        return r["mission_id"]

    def test_records_role_transitions_to_persona_pending(self, tool_db):
        mid = self._init_mission(tool_db)
        result = call_tool(
            "mission_role_record",
            {"mission_id": mid, "role": "Engineer"},
            tool_db,
        )
        assert result["role"] == "Engineer"
        assert result["status"] == "PERSONA_PENDING"
        assert result["mission_id"] == mid

    def test_invalid_role_returns_error(self, tool_db):
        mid = self._init_mission(tool_db, "sess-bad-role")
        result = call_tool(
            "mission_role_record",
            {"mission_id": mid, "role": "Wizard"},
            tool_db,
        )
        assert result.get("error") == "invalid_role"

    def test_mission_not_found_returns_error(self, tool_db):
        result = call_tool(
            "mission_role_record",
            {"mission_id": 99999, "role": "Engineer"},
            tool_db,
        )
        assert result.get("error") == "mission_not_found"

    def test_wrong_status_returns_error(self, tool_db, tool_db_with_mission):
        # Mission 1 is ACTIVE, not ROLE_PENDING
        result = call_tool(
            "mission_role_record",
            {"mission_id": 1, "role": "Engineer"},
            tool_db_with_mission,
        )
        assert result.get("error") == "invalid_status"

    def test_all_valid_roles_accepted(self, tool_db):
        valid_roles = [
            "Administrator",
            "Architect",
            "Engineer",
            "Tester",
            "Documentarian",
            "Designer",
            "Inspector",
            "Operator",
            "Historian",
        ]
        for i, role in enumerate(valid_roles):
            mid = self._init_mission(tool_db, f"sess-role-{i}")
            result = call_tool(
                "mission_role_record",
                {"mission_id": mid, "role": role},
                tool_db,
            )
            assert "error" not in result, f"Role {role} should be valid"


class TestMissionPersonaRecord:
    def _setup_persona_pending(self, tool_db, session_id="sess-pp") -> int:
        r = call_tool("mission_init", {"session_id": session_id}, tool_db)
        mid = r["mission_id"]
        call_tool("mission_role_record", {"mission_id": mid, "role": "Engineer"}, tool_db)
        return mid

    def test_records_persona_transitions_to_active(self, tool_db, tmp_path):
        mid = self._setup_persona_pending(tool_db)
        # Patch MissionManager._create_mission_file to avoid file I/O
        with patch("site_nine.missions.manager.MissionManager._create_mission_file"):
            result = call_tool(
                "mission_persona_record",
                {"mission_id": mid, "persona": "hermes"},
                tool_db,
            )
        assert result["status"] == "ACTIVE"
        assert result["persona"] == "hermes"
        assert result["role"] == "Engineer"

    def test_persona_not_found_returns_error(self, tool_db):
        mid = self._setup_persona_pending(tool_db, "sess-pp2")
        with patch("site_nine.missions.manager.MissionManager._create_mission_file"):
            result = call_tool(
                "mission_persona_record",
                {"mission_id": mid, "persona": "nonexistent"},
                tool_db,
            )
        assert result.get("error") == "persona_not_found"

    def test_wrong_status_returns_error(self, tool_db_with_mission):
        # Mission 1 is ACTIVE, not PERSONA_PENDING
        with patch("site_nine.missions.manager.MissionManager._create_mission_file"):
            result = call_tool(
                "mission_persona_record",
                {"mission_id": 1, "persona": "hermes"},
                tool_db_with_mission,
            )
        assert result.get("error") == "invalid_status"

    def test_mission_not_found_returns_error(self, tool_db):
        with patch("site_nine.missions.manager.MissionManager._create_mission_file"):
            result = call_tool(
                "mission_persona_record",
                {"mission_id": 99999, "persona": "hermes"},
                tool_db,
            )
        assert result.get("error") == "mission_not_found"


class TestMissionRenameSession:
    def test_no_active_mission_returns_error(self, tool_db):
        result = call_tool(
            "mission_rename_session",
            {"session_id": "sess-unknown"},
            tool_db,
        )
        assert result.get("error") == "no_active_mission"

    def test_renames_session_returns_titles(self, tool_db_with_mission):
        mock_result = MagicMock()
        mock_result.old_title = "Old Title"
        mock_result.new_title = "Operation iron-falcon: Hermes - Engineer"
        mock_result.warning = None

        with patch(
            "site_nine.opencode.manager.OpenCodeSessionManager.update_session_title",
            return_value=mock_result,
        ):
            result = call_tool(
                "mission_rename_session",
                {"session_id": "sess-abc"},
                tool_db_with_mission,
            )

        assert result["new_title"] == "Operation iron-falcon: Hermes - Engineer"
        assert result["old_title"] == "Old Title"
        assert result["mission_id"] == 1


class TestMissionRenameDismissed:
    def _make_session_manager_mock(self, current_title: str):
        """Create a mock OpenCodeSessionManager that returns current_title."""
        mock_manager = MagicMock()
        mock_manager.find_db.return_value = Path("/fake/opencode.db")

        rename_result = MagicMock()
        rename_result.old_title = current_title
        rename_result.new_title = f"{current_title} [DISMISSED]"
        rename_result.warning = None
        mock_manager.update_session_title.return_value = rename_result
        return mock_manager

    def test_appends_dismissed_suffix(self, tool_db):
        import sqlite3

        with (
            patch(
                "site_nine.opencode.manager.OpenCodeSessionManager.find_db",
                return_value=Path("/fake/oc.db"),
            ),
            patch("sqlite3.connect") as mock_connect,
        ):
            mock_conn = MagicMock()
            mock_conn.__enter__ = lambda s: s
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.row_factory = None
            mock_row = MagicMock()
            mock_row.__getitem__ = lambda s, k: "My Session"
            mock_conn.execute.return_value.fetchone.return_value = mock_row
            mock_connect.return_value = mock_conn

            rename_result = MagicMock()
            rename_result.old_title = "My Session"
            rename_result.new_title = "My Session [DISMISSED]"
            rename_result.warning = None

            with patch(
                "site_nine.opencode.manager.OpenCodeSessionManager.update_session_title",
                return_value=rename_result,
            ):
                result = call_tool(
                    "mission_rename_dismissed",
                    {"session_id": "sess-dismiss"},
                    tool_db,
                )

        assert result["new_title"].endswith("[DISMISSED]")

    def test_no_opencode_db_returns_error(self, tool_db):
        with patch(
            "site_nine.opencode.manager.OpenCodeSessionManager.find_db",
            return_value=None,
        ):
            result = call_tool(
                "mission_rename_dismissed",
                {"session_id": "sess-nodb"},
                tool_db,
            )
        assert result.get("error") == "no_opencode_db"


class TestMissionEnd:
    def test_ends_active_mission(self, tool_db_with_mission):
        result = call_tool(
            "mission_end",
            {"session_id": "sess-abc"},
            tool_db_with_mission,
        )
        assert result["status"] == "ENDED"
        assert result["mission_id"] == 1

    def test_ends_mission_by_id_override(self, tool_db_with_mission):
        result = call_tool(
            "mission_end",
            {"session_id": None, "mission_id": 1},
            tool_db_with_mission,
        )
        assert result["status"] == "ENDED"

    def test_no_active_mission_returns_error(self, tool_db):
        result = call_tool(
            "mission_end",
            {"session_id": "sess-nobody"},
            tool_db,
        )
        assert result.get("error") == "no_active_mission"

    def test_mission_not_found_by_id_returns_error(self, tool_db):
        result = call_tool(
            "mission_end",
            {"session_id": None, "mission_id": 99999},
            tool_db,
        )
        assert result.get("error") == "mission_not_found"

    def test_no_session_and_no_mission_id_returns_error(self, tool_db):
        result = call_tool(
            "mission_end",
            {},
            tool_db,
        )
        assert result.get("error") in ("no_session_id", "no_active_mission", "unexpected_error")


class TestMissionSummary:
    def test_generates_summary_by_session(self, tool_db_with_mission):
        with patch("site_nine.missions.manager.MissionManager.generate_summary") as mock_summary:
            mock_summary.return_value = MagicMock(
                files_changed=[],
                commits=[],
                tasks=[],
                warnings=[],
            )
            result = call_tool(
                "mission_summary",
                {"session_id": "sess-abc"},
                tool_db_with_mission,
            )
        assert result["mission_id"] == 1
        assert result["codename"] == "iron-falcon"
        assert "files_changed" in result

    def test_generates_summary_by_mission_id(self, tool_db_with_mission):
        with patch("site_nine.missions.manager.MissionManager.generate_summary") as mock_summary:
            mock_summary.return_value = MagicMock(
                files_changed=[],
                commits=[],
                tasks=[],
                warnings=[],
            )
            result = call_tool(
                "mission_summary",
                {"session_id": None, "mission_id": 1},
                tool_db_with_mission,
            )
        assert result["mission_id"] == 1

    def test_no_mission_returns_error(self, tool_db):
        result = call_tool(
            "mission_summary",
            {"session_id": "sess-ghost"},
            tool_db,
        )
        assert result.get("error") == "no_mission"

    def test_mission_not_found_by_id_returns_error(self, tool_db):
        result = call_tool(
            "mission_summary",
            {"session_id": None, "mission_id": 99999},
            tool_db,
        )
        assert result.get("error") == "mission_not_found"


# ===========================================================================
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
        assert result["mission_id"] == 1

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
# HANDOFF TOOLS (3)
# ===========================================================================


@pytest.fixture
def tool_db_with_handoff(tool_db_with_mission):
    """Add a handoff record for testing list/delete."""
    with Database(tool_db_with_mission) as db:
        db.execute_update(
            """
            INSERT INTO handoffs (task_id, from_mission_id, to_role, summary, created_at)
            VALUES ('ENG-H-0001', 1, 'Tester', 'Ready for review', datetime('now'))
            """
        )
    return tool_db_with_mission


class TestHandoffCreate:
    def test_creates_handoff_with_required_fields(self, tool_db_with_mission):
        result = call_tool(
            "handoff_create",
            {
                "task_id": "ENG-H-0001",
                "from_mission_id": 1,
                "to_role": "Tester",
                "summary": "Ready for testing",
            },
            tool_db_with_mission,
        )
        assert "handoff_id" in result
        assert result["to_role"] == "Tester"
        assert result["task_id"] == "ENG-H-0001"

    def test_creates_handoff_with_files(self, tool_db_with_mission):
        files = ["src/main.py", "tests/test_main.py"]
        result = call_tool(
            "handoff_create",
            {
                "task_id": "ENG-H-0001",
                "from_mission_id": 1,
                "to_role": "Tester",
                "summary": "With files",
                "files": json.dumps(files),
            },
            tool_db_with_mission,
        )
        assert "handoff_id" in result

    def test_invalid_role_returns_error(self, tool_db_with_mission):
        result = call_tool(
            "handoff_create",
            {
                "task_id": "ENG-H-0001",
                "from_mission_id": 1,
                "to_role": "Wizard",
                "summary": "Bad role",
            },
            tool_db_with_mission,
        )
        assert result.get("error") == "invalid_role"

    def test_invalid_files_json_returns_error(self, tool_db_with_mission):
        result = call_tool(
            "handoff_create",
            {
                "task_id": "ENG-H-0001",
                "from_mission_id": 1,
                "to_role": "Tester",
                "summary": "Bad files",
                "files": "not-valid-json",
            },
            tool_db_with_mission,
        )
        assert result.get("error") == "invalid_files"


class TestHandoffList:
    def test_lists_all_handoffs(self, tool_db_with_handoff):
        result = call_tool("handoff_list", {}, tool_db_with_handoff)
        assert result["count"] >= 1

    def test_filters_by_to_role(self, tool_db_with_handoff):
        result = call_tool("handoff_list", {"to_role": "Tester"}, tool_db_with_handoff)
        assert result["count"] >= 1
        for h in result["data"]:
            assert h["to_role"] == "Tester"

    def test_filters_by_from_mission(self, tool_db_with_handoff):
        result = call_tool("handoff_list", {"from_mission_id": 1}, tool_db_with_handoff)
        assert result["count"] >= 1

    def test_returns_empty_when_no_match(self, tool_db_with_handoff):
        result = call_tool("handoff_list", {"to_role": "Architect"}, tool_db_with_handoff)
        assert result["count"] == 0

    def test_empty_db_returns_zero(self, tool_db):
        result = call_tool("handoff_list", {}, tool_db)
        assert result["count"] == 0


class TestHandoffDelete:
    def _get_handoff_id(self, tool_db_with_handoff) -> int:
        result = call_tool("handoff_list", {}, tool_db_with_handoff)
        return result["data"][0]["id"]

    def test_deletes_existing_handoff(self, tool_db_with_handoff):
        hid = self._get_handoff_id(tool_db_with_handoff)
        result = call_tool("handoff_delete", {"handoff_id": hid}, tool_db_with_handoff)
        assert result["handoff_id"] == hid

    def test_deleted_handoff_not_in_list(self, tool_db_with_handoff):
        hid = self._get_handoff_id(tool_db_with_handoff)
        call_tool("handoff_delete", {"handoff_id": hid}, tool_db_with_handoff)
        result = call_tool("handoff_list", {}, tool_db_with_handoff)
        ids = [h["id"] for h in result["data"]]
        assert hid not in ids

    def test_double_delete_returns_error(self, tool_db_with_handoff):
        hid = self._get_handoff_id(tool_db_with_handoff)
        call_tool("handoff_delete", {"handoff_id": hid}, tool_db_with_handoff)
        result = call_tool("handoff_delete", {"handoff_id": hid}, tool_db_with_handoff)
        assert result.get("error") == "already_deleted"

    def test_not_found_returns_error(self, tool_db):
        result = call_tool("handoff_delete", {"handoff_id": 99999}, tool_db)
        assert result.get("error") == "handoff_not_found"


# ===========================================================================
# PERSONA TOOLS (3)
# ===========================================================================


class TestPersonaShow:
    def test_shows_existing_persona(self, tool_db):
        result = call_tool("persona_show", {"name": "hermes"}, tool_db)
        assert result["persona"]["name"] == "hermes"
        assert result["persona"]["mythology"] == "Greek"

    def test_shows_persona_case_insensitive(self, tool_db):
        result = call_tool("persona_show", {"name": "HERMES"}, tool_db)
        assert result["persona"]["name"] == "hermes"

    def test_persona_not_found_returns_error(self, tool_db):
        result = call_tool("persona_show", {"name": "nobody"}, tool_db)
        assert result.get("error") == "persona_not_found"

    def test_missing_name_returns_error(self, tool_db):
        result = call_tool("persona_show", {}, tool_db)
        assert result.get("error") == "missing_name"

    def test_bio_is_null_when_not_set(self, tool_db):
        result = call_tool("persona_show", {"name": "hermes"}, tool_db)
        assert result["persona"]["whimsical_bio"] is None


class TestPersonaSuggest:
    def test_suggests_personas_for_role(self, tool_db):
        result = call_tool("persona_suggest", {"role": "Tester"}, tool_db)
        assert "data" in result
        assert result["count"] >= 1

    def test_respects_count_parameter(self, tool_db):
        result = call_tool("persona_suggest", {"role": "Engineer", "count": 1}, tool_db)
        assert len(result["data"]) <= 1

    def test_missing_role_returns_error(self, tool_db):
        result = call_tool("persona_suggest", {}, tool_db)
        assert result.get("error") == "missing_role"

    def test_suggestions_include_expected_fields(self, tool_db):
        result = call_tool("persona_suggest", {"role": "Engineer"}, tool_db)
        for p in result["data"]:
            assert "name" in p
            assert "mythology" in p
            assert "mission_count" in p
            assert "is_unused" in p

    def test_unused_personas_suggested_first(self, tool_db):
        # hermes has mission_count=0, should appear in suggestions
        result = call_tool("persona_suggest", {"role": "Engineer"}, tool_db)
        names = [p["name"] for p in result["data"]]
        assert "hermes" in names


class TestPersonaSetBio:
    def test_sets_bio(self, tool_db):
        bio = "I am Hermes, the swift messenger of the gods."
        result = call_tool(
            "persona_set_bio",
            {"name": "hermes", "bio": bio},
            tool_db,
        )
        assert result["whimsical_bio"] == bio
        assert result["name"] == "hermes"

    def test_overwrites_existing_bio(self, tool_db):
        call_tool("persona_set_bio", {"name": "hermes", "bio": "First bio."}, tool_db)
        result = call_tool("persona_set_bio", {"name": "hermes", "bio": "Updated bio."}, tool_db)
        assert result["whimsical_bio"] == "Updated bio."

    def test_bio_persists_in_show(self, tool_db):
        bio = "Persistent bio text."
        call_tool("persona_set_bio", {"name": "hermes", "bio": bio}, tool_db)
        show_result = call_tool("persona_show", {"name": "hermes"}, tool_db)
        assert show_result["persona"]["whimsical_bio"] == bio

    def test_missing_name_returns_error(self, tool_db):
        result = call_tool("persona_set_bio", {"bio": "Some bio"}, tool_db)
        assert result.get("error") == "missing_name"

    def test_missing_bio_returns_error(self, tool_db):
        result = call_tool("persona_set_bio", {"name": "hermes"}, tool_db)
        assert result.get("error") == "missing_bio"

    def test_nonexistent_persona_returns_error(self, tool_db):
        result = call_tool(
            "persona_set_bio",
            {"name": "nobody", "bio": "Some bio"},
            tool_db,
        )
        assert result.get("error") == "update_failed"


# ===========================================================================
# DASHBOARD TOOL (1)
# ===========================================================================


class TestMissionDashboard:
    def test_returns_todo_and_underway_tasks_for_role(self, tool_db_with_mission):
        # Tester has 2 TODO tasks
        result = call_tool("mission_dashboard", {"role": "Tester"}, tool_db_with_mission)
        assert result["role"] == "Tester"
        assert result["task_count"] == 2

    def test_engineer_sees_underway_task(self, tool_db_with_mission):
        # ENG-H-0001 is UNDERWAY (counts as available in dashboard)
        result = call_tool("mission_dashboard", {"role": "Engineer"}, tool_db_with_mission)
        assert result["task_count"] == 1
        assert result["available_tasks"][0]["id"] == "ENG-H-0001"

    def test_invalid_role_returns_error(self, tool_db):
        result = call_tool("mission_dashboard", {"role": "Wizard"}, tool_db)
        assert result.get("error") == "invalid_role"

    def test_missing_role_returns_error(self, tool_db):
        result = call_tool("mission_dashboard", {}, tool_db)
        assert result.get("error") == "missing_role"

    def test_architect_with_no_tasks_returns_zero(self, tool_db):
        result = call_tool("mission_dashboard", {"role": "Architect"}, tool_db)
        assert result["task_count"] == 0
        assert result["available_tasks"] == []

    def test_response_includes_expected_fields(self, tool_db_with_mission):
        result = call_tool("mission_dashboard", {"role": "Tester"}, tool_db_with_mission)
        assert "role" in result
        assert "available_tasks" in result
        assert "task_count" in result
        for task in result["available_tasks"]:
            assert "id" in task
            assert "title" in task
            assert "status" in task
            assert "priority" in task
