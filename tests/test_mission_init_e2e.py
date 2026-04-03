"""End-to-end tests for possession initialization flow (TST-H-0175).

.. deprecated::
    These tests cover ``mission_init``, ``mission_role_record``,
    ``mission_persona_record``, ``persona_suggest``, and
    ``mission_rename_session`` — all of which were removed as part of
    ENG-H-0253.  The entire module is skipped until these tests are
    rewritten (or removed) to target the replacement ``possession_init``,
    ``possession_role_record``, ``possession_daemon_record``,
    ``daemon_suggest``, and ``possession_rename_session`` tools.

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

# All tests in this module target removed tools — skip the entire file.
pytestmark = pytest.mark.skip(reason="Tests target removed mission_*/persona_* tools (ENG-H-0253)")

from site_nine.core.database import Database
from site_nine.core.paths import get_db_path
from site_nine.possessions.types import PossessionStatus

# ---------------------------------------------------------------------------
# Tool loader: import .opencode/tools/*.py by file path (not a package)
# ---------------------------------------------------------------------------

_TOOLS_DIR = Path(__file__).parent.parent / ".opencode" / "tools"

# Ensure tool_logging (and any other shared modules in .opencode/tools/) is importable
# when tool scripts are loaded via importlib in tests.
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))


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
    mock_result.new_title = "Operation Azazel - Engineer"
    mock_result.warning = None

    with patch(
        "site_nine.opencode.manager.OpenCodeSessionManager.update_session_title",
        return_value=mock_result,
    ):
        yield


# ---------------------------------------------------------------------------
# Helper: run the full 3-step init sequence
# ---------------------------------------------------------------------------


def _full_init(session_id: str = "test-session-001", role: str = "Engineer", persona: str = "azazel") -> dict:
    """Run mission_init → mission_role_record → mission_persona_record.

    Returns the final persona_record response dict.
    """
    init = _call_mission_init(session_id)
    assert "error" not in init, f"mission_init failed: {init}"

    role_result = _call_mission_role_record(init["mission_id"], role)
    assert "error" not in role_result, f"mission_role_record failed: {role_result}"

    persona_result = _call_mission_persona_record(init["mission_id"], persona)
    # carry mission_id forward for convenience
    if "mission_id" not in persona_result and "error" not in persona_result:
        persona_result["mission_id"] = init["mission_id"]
    return persona_result


# ===========================================================================
# 1. Full happy-path: ROLE_PENDING → DAEMON_PENDING → ACTIVE
# ===========================================================================


class TestFullInitSequence:
    def test_mission_init_creates_role_pending_possession(self, initialized_project: Path):
        result = _call_mission_init("session-full-01")

        assert "error" not in result
        assert "mission_id" in result
        assert isinstance(result["mission_id"], int)
        assert result["mission_id"] > 0

        # Verify DB state
        db = Database(get_db_path())
        rows = db.execute_query(
            "SELECT status, opencode_session_id FROM possessions WHERE id = :id",
            {"id": result["mission_id"]},
        )
        assert rows[0]["status"] == PossessionStatus.ROLE_PENDING.value
        assert rows[0]["opencode_session_id"] == "session-full-01"

    def test_mission_role_record_transitions_to_daemon_pending(self, initialized_project: Path):
        init = _call_mission_init("session-full-02")
        result = _call_mission_role_record(init["mission_id"], "Engineer")

        assert "error" not in result
        assert result["status"] == PossessionStatus.DAEMON_PENDING.value
        assert result["role"] == "Engineer"
        assert result["mission_id"] == init["mission_id"]

        db = Database(get_db_path())
        rows = db.execute_query(
            "SELECT status, role FROM possessions WHERE id = :id",
            {"id": init["mission_id"]},
        )
        assert rows[0]["status"] == PossessionStatus.DAEMON_PENDING.value
        assert rows[0]["role"] == "Engineer"

    def test_mission_persona_record_transitions_to_active(self, initialized_project: Path):
        result = _full_init("session-full-03", role="Engineer", persona="azazel")

        assert "error" not in result
        assert result["status"] == PossessionStatus.ACTIVE.value
        assert result["persona"] == "azazel"
        assert result["role"] == "Engineer"

        db = Database(get_db_path())
        rows = db.execute_query(
            "SELECT status, daemon_name, role FROM possessions WHERE id = :id",
            {"id": result["mission_id"]},
        )
        assert rows[0]["status"] == PossessionStatus.ACTIVE.value
        assert rows[0]["daemon_name"] == "azazel"

    def test_full_sequence_produces_active_possession(self, initialized_project: Path):
        """Complete 3-step sequence ends with ACTIVE possession."""
        result = _full_init("session-full-04", persona="azazel")

        assert result["status"] == PossessionStatus.ACTIVE.value

    def test_possession_log_path_set_after_persona_record(self, initialized_project: Path):
        """mission_persona_record sets the possession_log path in the DB."""
        result = _full_init("session-full-05", persona="azazel")

        assert "error" not in result
        assert "mission_file" in result
        # The path is stored in the DB
        db = Database(get_db_path())
        rows = db.execute_query(
            "SELECT possession_log FROM possessions WHERE id = :id",
            {"id": result["mission_id"]},
        )
        assert rows[0]["possession_log"] == result["mission_file"]

    def test_daemon_incarnation_count_incremented(self, initialized_project: Path):
        """Completing init increments the daemon's incarnations count."""
        db = Database(get_db_path())
        before = db.execute_query("SELECT incarnations FROM daemons WHERE lower(name) = 'azazel'")[0]["incarnations"]

        _full_init("session-full-06", persona="azazel")

        after = db.execute_query("SELECT incarnations FROM daemons WHERE lower(name) = 'azazel'")[0]["incarnations"]
        assert after == before + 1

    def test_mission_init_does_not_return_codename(self, initialized_project: Path):
        """mission_init no longer generates or returns a codename."""
        result = _call_mission_init("session-full-07")

        assert "error" not in result
        assert "mission_id" in result
        # codename is no longer part of the init response
        assert "codename" not in result

    def test_different_missions_get_unique_session_bindings(self, initialized_project: Path):
        """Two possessions bound to different sessions are independent."""
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

    def test_double_binding_does_not_create_second_possession(self, initialized_project: Path):
        """No second possession row is created on double-bind attempt."""
        first = _call_mission_init("session-bind-02")
        _call_mission_init("session-bind-02")  # second call

        db = Database(get_db_path())
        rows = db.execute_query("SELECT id FROM possessions WHERE opencode_session_id = 'session-bind-02'")
        assert len(rows) == 1
        assert rows[0]["id"] == first["mission_id"]

    def test_double_binding_session_id_permanently_bound(self, initialized_project: Path):
        """A session_id remains permanently bound even after the possession is EXORCISED.

        The opencode_session_id column has a UNIQUE constraint, so a new
        possession cannot reuse a session_id regardless of the prior possession's
        status. When the prior possession is EXORCISED, the double-binding check
        (which only looks at active statuses) does not catch it, and the INSERT
        raises an IntegrityError, which surfaces as an ``unexpected_error`` response.
        """
        first = _call_mission_init("session-bind-03")
        # Manually exorcise the first possession
        db = Database(get_db_path())
        db.execute_update(
            "UPDATE possessions SET status = 'EXORCISED' WHERE id = :id",
            {"id": first["mission_id"]},
        )
        # The UNIQUE constraint prevents a new possession from using the same
        # session_id; since the EXORCISED possession is not caught by the active-status
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

    def test_role_record_on_daemon_pending_possession_fails(self, initialized_project: Path):
        """Cannot call mission_role_record when already in DAEMON_PENDING."""
        init = _call_mission_init("session-role-02")
        _call_mission_role_record(init["mission_id"], "Engineer")  # → DAEMON_PENDING
        result = _call_mission_role_record(init["mission_id"], "Tester")  # should fail

        assert result.get("error") == "invalid_status"
        assert result.get("current_status") == PossessionStatus.DAEMON_PENDING.value

    def test_role_record_on_active_possession_fails(self, initialized_project: Path):
        """Cannot call mission_role_record when already ACTIVE."""
        full = _full_init("session-role-03")
        result = _call_mission_role_record(full["mission_id"], "Tester")

        assert result.get("error") == "invalid_status"
        assert result.get("current_status") == PossessionStatus.ACTIVE.value


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
        assert result.get("current_status") == PossessionStatus.ROLE_PENDING.value

    def test_persona_record_on_active_possession_fails(self, initialized_project: Path):
        """Cannot call mission_persona_record when already ACTIVE."""
        full = _full_init("session-persona-03")
        result = _call_mission_persona_record(full["mission_id"], "test-persona")

        assert result.get("error") == "invalid_status"
        assert result.get("current_status") == PossessionStatus.ACTIVE.value

    def test_persona_name_is_normalized_to_lowercase(self, initialized_project: Path):
        """Persona names with uppercase are normalized."""
        init = _call_mission_init("session-persona-04")
        _call_mission_role_record(init["mission_id"], "Engineer")
        result = _call_mission_persona_record(init["mission_id"], "AZAZEL")

        # azazel exists in DB; uppercase should be normalized and matched
        assert "error" not in result
        assert result["persona"] == "azazel"

    def test_persona_record_mission_not_found(self, initialized_project: Path):
        result = _call_mission_persona_record(99999, "test-persona")
        assert result.get("error") == "mission_not_found"

    def test_possession_log_path_includes_role_and_persona(self, initialized_project: Path):
        """The generated possession_log path encodes role and persona."""
        result = _full_init("session-persona-05", role="Tester", persona="lilith")

        assert "error" not in result
        mission_file = result["mission_file"]
        assert "tester" in mission_file
        assert "lilith" in mission_file


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

    def test_unused_daemons_preferred(self, initialized_project: Path):
        """Unused daemons (incarnations=0) appear before used ones."""
        # Mark one Engineer daemon as used
        db = Database(get_db_path())
        db.execute_update("UPDATE daemons SET incarnations = 5 WHERE name = 'atar'")

        result = _call_persona_suggest("Engineer", count=3)
        assert "error" not in result

        unused = [p for p in result["data"] if p["is_unused"]]
        used = [p for p in result["data"] if not p["is_unused"]]

        # Unused daemons should come first (lower incarnations sorts first)
        if unused and used:
            for u in unused:
                for v in used:
                    assert u["incarnations"] <= v["incarnations"]

    def test_suggestion_fields_present(self, initialized_project: Path):
        result = _call_persona_suggest("Engineer")

        for daemon in result["data"]:
            assert "name" in daemon
            assert "role" in daemon
            assert "daemonology" in daemon
            assert "incarnations" in daemon
            assert "last_possession" in daemon
            assert "is_unused" in daemon


# ===========================================================================
# 6. mission_rename_session
# ===========================================================================


class TestMissionRenameSession:
    def test_rename_session_builds_correct_title(self, initialized_project: Path):
        """Title format: 'Operation <Persona> - <Role>'."""
        full = _full_init("session-rename-01", role="Engineer", persona="azazel")
        session_id = "session-rename-01"

        # Capture the title passed to update_session_title
        with patch("site_nine.opencode.manager.OpenCodeSessionManager.update_session_title") as mock_update:
            mock_result = MagicMock()
            mock_result.old_title = "Old"
            mock_result.new_title = "Operation Azazel - Engineer"
            mock_result.warning = None
            mock_update.return_value = mock_result

            result = _call_mission_rename_session(session_id)

        assert "error" not in result
        called_title = mock_update.call_args[0][1]
        assert "Azazel" in called_title or "azazel" in called_title.lower()
        assert "Engineer" in called_title

    def test_rename_session_no_active_possession_returns_error(self, initialized_project: Path):
        """No possession bound to session returns no_active_mission error."""
        result = _call_mission_rename_session("session-nobody-bound")

        assert result.get("error") == "no_active_mission"

    def test_rename_session_returns_old_and_new_titles(self, initialized_project: Path):
        _full_init("session-rename-02")

        result = _call_mission_rename_session("session-rename-02")
        assert "error" not in result
        assert "old_title" in result
        assert "new_title" in result
        assert "mission_id" in result

    def test_rename_session_works_on_role_pending_possession(self, initialized_project: Path):
        """Rename should work even before role/daemon are recorded (partial titles OK)."""
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

    def test_status_sequence_role_pending_to_daemon_pending(self, initialized_project: Path):
        init = _call_mission_init("session-seq-01")
        assert _get_possession_status(init["mission_id"]) == PossessionStatus.ROLE_PENDING.value

        _call_mission_role_record(init["mission_id"], "Tester")
        assert _get_possession_status(init["mission_id"]) == PossessionStatus.DAEMON_PENDING.value

    def test_status_sequence_daemon_pending_to_active(self, initialized_project: Path):
        init = _call_mission_init("session-seq-02")
        _call_mission_role_record(init["mission_id"], "Tester")

        _call_mission_persona_record(init["mission_id"], "lilith")
        assert _get_possession_status(init["mission_id"]) == PossessionStatus.ACTIVE.value

    def test_role_record_idempotent_prevention(self, initialized_project: Path):
        """Calling role_record twice on the same possession is rejected."""
        init = _call_mission_init("session-idem-01")
        _call_mission_role_record(init["mission_id"], "Engineer")
        result = _call_mission_role_record(init["mission_id"], "Architect")

        assert result.get("error") == "invalid_status"

    def test_persona_record_idempotent_prevention(self, initialized_project: Path):
        """Calling persona_record twice on the same possession is rejected."""
        full = _full_init("session-idem-02")
        # azazel is already used; try any daemon — status check should block it
        result = _call_mission_persona_record(full["mission_id"], "azazel")

        assert result.get("error") == "invalid_status"


# ===========================================================================
# Utility
# ===========================================================================


def _get_possession_status(mission_id: int) -> str:
    db = Database(get_db_path())
    rows = db.execute_query("SELECT status FROM possessions WHERE id = :id", {"id": mission_id})
    return rows[0]["status"]
