"""End-to-end tests for mission initialization flow (TST-H-0175).

Validates the complete tool-layer sequence:
    mission_init → mission_role_record → mission_persona_record

and the supporting tools:
    persona_suggest, mission_rename_session

Tests operate directly against the underlying Python functions, using the
``initialized_project`` fixture so that ``get_db_path()`` resolves correctly.
``OpenCodeSessionManager.update_session_title`` is mocked throughout to avoid
touching the real OpenCode SQLite database.
"""

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.missions.types import MissionStatus

# ---------------------------------------------------------------------------
# Tool loader: import .opencode/tools/*.py by file path (not a package)
# ---------------------------------------------------------------------------

_TOOLS_DIR = Path(__file__).parent.parent / ".opencode" / "tools"


def _load_tool(name: str):
    """Dynamically import a tool script from .opencode/tools/ and return its module."""
    module_name = f"_opencode_tool_{name}"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, _TOOLS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[module_name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


# ---------------------------------------------------------------------------
# Helpers to invoke tool main() functions in-process
# ---------------------------------------------------------------------------


def _call_mission_init(session_id: str) -> dict:
    """Invoke mission_init.main() with a fake session_id."""
    main = _load_tool("mission_init").main
    context = json.dumps({"session_id": session_id})
    with patch("sys.stdin") as mock_stdin:
        mock_stdin.read.return_value = context
        result_json = main()
    return json.loads(result_json)


def _call_mission_role_record(mission_id: int, role: str) -> dict:
    main = _load_tool("mission_role_record").main
    context = json.dumps({"mission_id": mission_id, "role": role})
    with patch("sys.stdin") as mock_stdin:
        mock_stdin.read.return_value = context
        result_json = main()
    return json.loads(result_json)


def _call_mission_persona_record(mission_id: int, persona: str) -> dict:
    main = _load_tool("mission_persona_record").main
    context = json.dumps({"mission_id": mission_id, "persona": persona})
    with patch("sys.stdin") as mock_stdin:
        mock_stdin.read.return_value = context
        result_json = main()
    return json.loads(result_json)


def _call_persona_suggest(role: str, count: int = 3) -> dict:
    main = _load_tool("persona_suggest").main
    context = json.dumps({"role": role, "count": count})
    with patch("sys.stdin") as mock_stdin:
        mock_stdin.read.return_value = context
        result_json = main()
    return json.loads(result_json)


def _call_mission_rename_session(session_id: str) -> dict:
    main = _load_tool("mission_rename_session").main
    context = json.dumps({"session_id": session_id})
    with patch("sys.stdin") as mock_stdin:
        mock_stdin.read.return_value = context
        result_json = main()
    return json.loads(result_json)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _mock_opencode_session_manager():
    """Prevent all tests from touching the real OpenCode SQLite DB."""
    mock_result = MagicMock()
    mock_result.old_title = "Old Title"
    mock_result.new_title = "Operation test-codename: Persona - Role"
    mock_result.warning = None

    with patch(
        "site_nine.opencode.manager.OpenCodeSessionManager.update_session_title",
        return_value=mock_result,
    ):
        yield


# ---------------------------------------------------------------------------
# Helper: run the full 3-step init sequence
# ---------------------------------------------------------------------------


def _full_init(session_id: str = "test-session-001", role: str = "Engineer", persona: str = "atar") -> dict:
    """Run mission_init → mission_role_record → mission_persona_record.

    Returns the final persona_record response dict.
    """
    init = _call_mission_init(session_id)
    assert "error" not in init, f"mission_init failed: {init}"

    role_result = _call_mission_role_record(init["mission_id"], role)
    assert "error" not in role_result, f"mission_role_record failed: {role_result}"

    persona_result = _call_mission_persona_record(init["mission_id"], persona)
    return persona_result


# ===========================================================================
# 1. Full happy-path: ROLE_PENDING → PERSONA_PENDING → ACTIVE
# ===========================================================================


class TestFullInitSequence:
    def test_mission_init_creates_role_pending_mission(self, initialized_project: Path):
        result = _call_mission_init("session-full-01")

        assert "error" not in result
        assert "mission_id" in result
        assert "codename" in result
        assert isinstance(result["mission_id"], int)
        assert result["mission_id"] > 0

        # Verify DB state
        db = Database(get_db_path())
        rows = db.execute_query(
            "SELECT status, opencode_session_id FROM missions WHERE id = :id",
            {"id": result["mission_id"]},
        )
        assert rows[0]["status"] == MissionStatus.ROLE_PENDING.value
        assert rows[0]["opencode_session_id"] == "session-full-01"

    def test_mission_role_record_transitions_to_persona_pending(self, initialized_project: Path):
        init = _call_mission_init("session-full-02")
        result = _call_mission_role_record(init["mission_id"], "Engineer")

        assert "error" not in result
        assert result["status"] == MissionStatus.PERSONA_PENDING.value
        assert result["role"] == "Engineer"
        assert result["mission_id"] == init["mission_id"]

        db = Database(get_db_path())
        rows = db.execute_query(
            "SELECT status, role FROM missions WHERE id = :id",
            {"id": init["mission_id"]},
        )
        assert rows[0]["status"] == MissionStatus.PERSONA_PENDING.value
        assert rows[0]["role"] == "Engineer"

    def test_mission_persona_record_transitions_to_active(self, initialized_project: Path):
        result = _full_init("session-full-03", role="Engineer", persona="atar")

        assert "error" not in result
        assert result["status"] == MissionStatus.ACTIVE.value
        assert result["persona"] == "atar"
        assert result["role"] == "Engineer"

        db = Database(get_db_path())
        rows = db.execute_query(
            "SELECT status, persona_name, role FROM missions WHERE id = :id",
            {"id": result["mission_id"]},
        )
        assert rows[0]["status"] == MissionStatus.ACTIVE.value
        assert rows[0]["persona_name"] == "atar"

    def test_full_sequence_produces_active_mission(self, initialized_project: Path):
        """Complete 3-step sequence ends with ACTIVE mission."""
        result = _full_init("session-full-04", persona="azazel")

        assert result["status"] == MissionStatus.ACTIVE.value

    def test_mission_file_created_after_persona_record(self, initialized_project: Path):
        """mission_persona_record creates the .md mission file on disk."""
        result = _full_init("session-full-05", persona="belial")

        assert "error" not in result
        assert "mission_file" in result

        mission_file = Path(result["mission_file"])
        assert mission_file.exists(), f"Mission file not found: {mission_file}"

    def test_persona_mission_count_incremented(self, initialized_project: Path):
        """Completing init increments the persona's mission_count."""
        db = Database(get_db_path())
        before = db.execute_query("SELECT mission_count FROM personas WHERE name = 'gibil'")[0]["mission_count"]

        _full_init("session-full-06", persona="gibil")

        after = db.execute_query("SELECT mission_count FROM personas WHERE name = 'gibil'")[0]["mission_count"]
        assert after == before + 1

    def test_codename_format_is_adjective_noun(self, initialized_project: Path):
        """Codenames follow the <adjective>-<noun> pattern."""
        result = _call_mission_init("session-full-07")

        codename = result["codename"]
        parts = codename.split("-")
        assert len(parts) == 2, f"Unexpected codename format: {codename}"

    def test_codename_is_deterministic(self, initialized_project: Path):
        """The same mission_id always generates the same codename."""
        from site_nine.missions.manager import generate_mission_codename

        for mission_id in [1, 5, 42, 100, 1000]:
            assert generate_mission_codename(mission_id) == generate_mission_codename(mission_id)

    def test_different_missions_get_unique_session_bindings(self, initialized_project: Path):
        """Two missions bound to different sessions are independent."""
        r1 = _call_mission_init("session-unique-A")
        r2 = _call_mission_init("session-unique-B")

        assert "error" not in r1
        assert "error" not in r2
        assert r1["mission_id"] != r2["mission_id"]


# ===========================================================================
# 2. mission_init: double-binding prevention
# ===========================================================================


class TestMissionInitDoubleBinding:
    def test_double_binding_same_session_returns_error(self, initialized_project: Path):
        """Calling mission_init twice with the same session_id returns double_binding."""
        _call_mission_init("session-bind-01")
        result = _call_mission_init("session-bind-01")

        assert result.get("error") == "double_binding"
        assert "mission_id" in result
        assert "codename" in result

    def test_double_binding_does_not_create_second_mission(self, initialized_project: Path):
        """No second mission row is created on double-bind attempt."""
        first = _call_mission_init("session-bind-02")
        _call_mission_init("session-bind-02")  # second call

        db = Database(get_db_path())
        rows = db.execute_query("SELECT id FROM missions WHERE opencode_session_id = 'session-bind-02'")
        assert len(rows) == 1
        assert rows[0]["id"] == first["mission_id"]

    def test_double_binding_session_id_permanently_bound(self, initialized_project: Path):
        """A session_id remains permanently bound even after the mission is ENDED.

        The opencode_session_id column has a UNIQUE constraint, so a new
        mission cannot reuse a session_id regardless of the prior mission's
        status.  When the prior mission is ENDED, the double-binding check
        in mission_init (which only looks at active statuses) does not catch
        it, and the INSERT raises an IntegrityError, which surfaces as an
        ``unexpected_error`` response.
        """
        first = _call_mission_init("session-bind-03")
        # Manually end the first mission
        db = Database(get_db_path())
        db.execute_update(
            "UPDATE missions SET status = 'ENDED' WHERE id = :id",
            {"id": first["mission_id"]},
        )
        # The UNIQUE constraint prevents a new mission from using the same
        # session_id; since the ENDED mission is not caught by the active-status
        # check, the INSERT fails and mission_init returns an unexpected_error.
        result = _call_mission_init("session-bind-03")
        assert "error" in result


# ===========================================================================
# 3. mission_role_record: validation errors
# ===========================================================================


class TestMissionRoleRecord:
    def test_invalid_role_returns_error(self, initialized_project: Path):
        init = _call_mission_init("session-role-01")
        result = _call_mission_role_record(init["mission_id"], "NotARealRole")

        assert result.get("error") == "invalid_role"

    def test_all_valid_roles_accepted(self, initialized_project: Path):
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
            session_id = f"session-role-valid-{i}"
            init = _call_mission_init(session_id)
            result = _call_mission_role_record(init["mission_id"], role)
            assert "error" not in result, f"Valid role '{role}' was rejected: {result}"
            assert result["role"] == role

    def test_mission_not_found_returns_error(self, initialized_project: Path):
        result = _call_mission_role_record(99999, "Engineer")

        assert result.get("error") == "mission_not_found"

    def test_role_record_on_persona_pending_mission_fails(self, initialized_project: Path):
        """Cannot call mission_role_record when already in PERSONA_PENDING."""
        init = _call_mission_init("session-role-02")
        _call_mission_role_record(init["mission_id"], "Engineer")  # → PERSONA_PENDING
        result = _call_mission_role_record(init["mission_id"], "Tester")  # should fail

        assert result.get("error") == "invalid_status"
        assert result.get("current_status") == MissionStatus.PERSONA_PENDING.value

    def test_role_record_on_active_mission_fails(self, initialized_project: Path):
        """Cannot call mission_role_record when already ACTIVE."""
        full = _full_init("session-role-03")
        result = _call_mission_role_record(full["mission_id"], "Tester")

        assert result.get("error") == "invalid_status"
        assert result.get("current_status") == MissionStatus.ACTIVE.value


# ===========================================================================
# 4. mission_persona_record: validation errors
# ===========================================================================


class TestMissionPersonaRecord:
    def test_persona_not_found_returns_error(self, initialized_project: Path):
        init = _call_mission_init("session-persona-01")
        _call_mission_role_record(init["mission_id"], "Engineer")
        result = _call_mission_persona_record(init["mission_id"], "nonexistent-persona")

        assert result.get("error") == "persona_not_found"

    def test_persona_record_on_role_pending_fails(self, initialized_project: Path):
        """Cannot call mission_persona_record while still in ROLE_PENDING."""
        init = _call_mission_init("session-persona-02")
        # Skip role record — go straight to persona record
        result = _call_mission_persona_record(init["mission_id"], "test-persona")

        assert result.get("error") == "invalid_status"
        assert result.get("current_status") == MissionStatus.ROLE_PENDING.value

    def test_persona_record_on_active_mission_fails(self, initialized_project: Path):
        """Cannot call mission_persona_record when already ACTIVE."""
        full = _full_init("session-persona-03")
        result = _call_mission_persona_record(full["mission_id"], "test-persona")

        assert result.get("error") == "invalid_status"
        assert result.get("current_status") == MissionStatus.ACTIVE.value

    def test_persona_name_is_normalized_to_lowercase(self, initialized_project: Path):
        """Persona names with uppercase are normalized."""
        init = _call_mission_init("session-persona-04")
        _call_mission_role_record(init["mission_id"], "Engineer")
        result = _call_mission_persona_record(init["mission_id"], "ATAR")

        # atar exists in DB; uppercase should be normalized and matched
        assert "error" not in result
        assert result["persona"] == "atar"

    def test_persona_record_mission_not_found(self, initialized_project: Path):
        result = _call_mission_persona_record(99999, "test-persona")
        assert result.get("error") == "mission_not_found"

    def test_mission_file_path_includes_role_and_persona(self, initialized_project: Path):
        """The generated mission_file path encodes role and persona."""
        result = _full_init("session-persona-05", role="Tester", persona="aeacus")

        assert "error" not in result
        mission_file = result["mission_file"]
        assert "tester" in mission_file
        assert "aeacus" in mission_file


# ===========================================================================
# 5. persona_suggest
# ===========================================================================


class TestPersonaSuggest:
    def test_returns_suggestions_for_valid_role(self, initialized_project: Path):
        result = _call_persona_suggest("Engineer")

        assert "error" not in result
        assert result["role"] == "Engineer"
        assert isinstance(result["data"], list)
        assert result["count"] == len(result["data"])

    def test_count_parameter_respected(self, initialized_project: Path):
        result = _call_persona_suggest("Engineer", count=2)

        assert len(result["data"]) <= 2

    def test_missing_role_returns_error(self, initialized_project: Path):
        main = _load_tool("persona_suggest").main
        context = json.dumps({})  # no role
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.read.return_value = context
            result = json.loads(main())

        assert result.get("error") == "missing_role"

    def test_unused_personas_preferred(self, initialized_project: Path):
        """Unused personas (mission_count=0) appear before used ones."""
        # Mark one Engineer persona as used
        db = Database(get_db_path())
        db.execute_update("UPDATE personas SET mission_count = 5 WHERE name = 'atar'")

        result = _call_persona_suggest("Engineer", count=3)
        assert "error" not in result

        unused = [p for p in result["data"] if p["is_unused"]]
        used = [p for p in result["data"] if not p["is_unused"]]

        # Unused personas should come first (lower mission_count sorts first)
        if unused and used:
            for u in unused:
                for v in used:
                    assert u["mission_count"] <= v["mission_count"]

    def test_suggestion_fields_present(self, initialized_project: Path):
        result = _call_persona_suggest("Engineer")

        for persona in result["data"]:
            assert "name" in persona
            assert "role" in persona
            assert "mythology" in persona
            assert "description" in persona
            assert "mission_count" in persona
            assert "is_unused" in persona


# ===========================================================================
# 6. mission_rename_session
# ===========================================================================


class TestMissionRenameSession:
    def test_rename_session_builds_correct_title(self, initialized_project: Path):
        """Title format: 'Operation <codename>: <Persona> - <Role>'."""
        full = _full_init("session-rename-01", role="Engineer", persona="atar")
        session_id = "session-rename-01"

        # Capture the title passed to update_session_title
        with patch("site_nine.opencode.manager.OpenCodeSessionManager.update_session_title") as mock_update:
            mock_result = MagicMock()
            mock_result.old_title = "Old"
            mock_result.new_title = f"Operation {full['codename']}: Atar - Engineer"
            mock_result.warning = None
            mock_update.return_value = mock_result

            result = _call_mission_rename_session(session_id)

        assert "error" not in result
        called_title = mock_update.call_args[0][1]
        assert called_title.startswith("Operation ")
        assert "Atar" in called_title or "atar" in called_title.lower()
        assert "Engineer" in called_title

    def test_rename_session_no_active_mission_returns_error(self, initialized_project: Path):
        """No mission bound to session returns no_active_mission error."""
        result = _call_mission_rename_session("session-nobody-bound")

        assert result.get("error") == "no_active_mission"

    def test_rename_session_returns_old_and_new_titles(self, initialized_project: Path):
        _full_init("session-rename-02")

        result = _call_mission_rename_session("session-rename-02")
        assert "error" not in result
        assert "old_title" in result
        assert "new_title" in result
        assert "mission_id" in result

    def test_rename_session_works_on_role_pending_mission(self, initialized_project: Path):
        """Rename should work even before role/persona are recorded (partial titles OK)."""
        _call_mission_init("session-rename-partial")

        result = _call_mission_rename_session("session-rename-partial")
        assert "error" not in result


# ===========================================================================
# 7. State transition integrity
# ===========================================================================


class TestStateTransitionIntegrity:
    def test_cannot_skip_role_pending_state(self, initialized_project: Path):
        """Going directly from ROLE_PENDING to ACTIVE via persona_record fails."""
        init = _call_mission_init("session-skip-01")
        result = _call_mission_persona_record(init["mission_id"], "test-persona")

        assert result.get("error") == "invalid_status"

    def test_status_sequence_role_pending_to_persona_pending(self, initialized_project: Path):
        init = _call_mission_init("session-seq-01")
        assert _get_mission_status(init["mission_id"]) == MissionStatus.ROLE_PENDING.value

        _call_mission_role_record(init["mission_id"], "Tester")
        assert _get_mission_status(init["mission_id"]) == MissionStatus.PERSONA_PENDING.value

    def test_status_sequence_persona_pending_to_active(self, initialized_project: Path):
        init = _call_mission_init("session-seq-02")
        _call_mission_role_record(init["mission_id"], "Tester")

        _call_mission_persona_record(init["mission_id"], "aeacus")
        assert _get_mission_status(init["mission_id"]) == MissionStatus.ACTIVE.value

    def test_role_record_idempotent_prevention(self, initialized_project: Path):
        """Calling role_record twice on the same mission is rejected."""
        init = _call_mission_init("session-idem-01")
        _call_mission_role_record(init["mission_id"], "Engineer")
        result = _call_mission_role_record(init["mission_id"], "Architect")

        assert result.get("error") == "invalid_status"

    def test_persona_record_idempotent_prevention(self, initialized_project: Path):
        """Calling persona_record twice on the same mission is rejected."""
        full = _full_init("session-idem-02")
        result = _call_mission_persona_record(full["mission_id"], "azar")

        assert result.get("error") == "invalid_status"


# ===========================================================================
# Utility
# ===========================================================================


def _get_mission_status(mission_id: int) -> str:
    db = Database(get_db_path())
    rows = db.execute_query("SELECT status FROM missions WHERE id = :id", {"id": mission_id})
    return rows[0]["status"]
