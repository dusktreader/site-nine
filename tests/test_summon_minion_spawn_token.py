"""Tests for summon_minion.py tool — spawn-token mechanism (ENG-M-0261).

Covers:
- Spawn token is generated and passed to the worker command
- Status file polling replaces role-based DB query
- Correct possession ID is returned (not mixed up with a concurrent same-role spawn)
- Cleanup of the token file after a successful read
- Timeout / worker-crash error paths still work
"""

import importlib.util
import json
import sys
import time
from io import StringIO
from pathlib import Path
from threading import Thread
from unittest.mock import MagicMock, patch

import pytest

TOOLS_DIR = Path(__file__).parent.parent / ".opencode" / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

REPO_ROOT = Path(__file__).parent.parent


def load_summon_minion():
    """Load summon_minion.py as a module."""
    spec = importlib.util.spec_from_file_location("summon_minion_tool", TOOLS_DIR / "summon_minion.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_db(tmp_path):
    """Create a temporary test database."""
    from site_nine.core.database import Database

    db_path = tmp_path / ".opencode" / "data"
    db_path.mkdir(parents=True, exist_ok=True)
    db_file = db_path / "project.db"
    db = Database(db_file)
    db.initialize_schema()
    return db_file


@pytest.fixture
def workers_dir(tmp_path):
    """Return a temporary workers status directory and redirect Path.home()."""
    d = tmp_path / ".local" / "state" / "site-nine" / "workers"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_token_file(workers_dir: Path, spawn_token: str, possession_id: int, daemon: str) -> None:
    """Simulate the worker writing its status file."""
    payload = {
        "session_id": f"ses_{possession_id}",
        "possession_id": possession_id,
        "daemon": daemon,
        "status": "ready",
    }
    status_file = workers_dir / f"{spawn_token}.json"
    tmp = status_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    tmp.rename(status_file)


# ---------------------------------------------------------------------------
# spawn-token unit tests
# ---------------------------------------------------------------------------


def test_spawn_token_is_added_to_worker_command(tmp_path, test_db, workers_dir):
    """summon_minion passes --spawn-token to the worker process command."""
    mod = load_summon_minion()
    db_path = test_db

    captured_cmd = []
    captured_token = []

    def fake_popen(cmd, **kwargs):
        captured_cmd.extend(cmd)
        # Extract the token from the command so we can write the status file
        idx = cmd.index("--spawn-token")
        token = cmd[idx + 1]
        captured_token.append(token)

        # Write the status file immediately so the poll loop finds it
        _write_token_file(workers_dir, token, possession_id=99, daemon="hephaestus")

        proc = MagicMock()
        proc.poll.return_value = None
        proc.returncode = None
        return proc

    # Insert a matching possession row so journal_path derivation works
    from site_nine.core.database import Database

    db = Database(db_path)
    db.execute_update(
        "INSERT INTO daemons (name, role, incarnations) VALUES ('hephaestus', 'Engineer', 0)",
        {},
    )
    db.execute_insert(
        """
        INSERT INTO possessions (
            id, daemon_name, role, possession_log,
            opencode_session_id, start_time,
            status, created_at, updated_at
        ) VALUES (
            99, 'hephaestus', 'Engineer',
            '.opencode/work/possessions/test.md',
            'ses_99', datetime('now'),
            'ACTIVE', datetime('now'), datetime('now')
        )
        """,
        {},
    )

    import pathlib

    real_home = pathlib.Path.home
    pathlib.Path.home = staticmethod(lambda: tmp_path)

    try:
        with patch("sys.stdin", StringIO(json.dumps({"role": "Engineer"}))):
            with patch.object(mod, "get_db_path", return_value=db_path):
                with patch.object(mod, "get_project_root", return_value=tmp_path):
                    with patch("subprocess.Popen", side_effect=fake_popen):
                        result_str = mod.main()
    finally:
        pathlib.Path.home = staticmethod(real_home)

    result = json.loads(result_str)
    assert "error" not in result, f"Unexpected error: {result}"
    assert "--spawn-token" in captured_cmd
    assert len(captured_token) == 1
    token = captured_token[0]
    assert len(token) == 32  # uuid4().hex is 32 hex chars


def test_spawn_token_possession_id_returned(tmp_path, test_db, workers_dir):
    """summon_minion returns the possession ID from the spawn-token file."""
    mod = load_summon_minion()
    db_path = test_db

    expected_possession_id = 42

    def fake_popen(cmd, **kwargs):
        idx = cmd.index("--spawn-token")
        token = cmd[idx + 1]
        _write_token_file(workers_dir, token, possession_id=expected_possession_id, daemon="malphas")

        proc = MagicMock()
        proc.poll.return_value = None
        return proc

    from site_nine.core.database import Database

    db = Database(db_path)
    db.execute_update(
        "INSERT INTO daemons (name, role, incarnations) VALUES ('malphas', 'Engineer', 0)",
        {},
    )
    db.execute_insert(
        f"""
        INSERT INTO possessions (
            id, daemon_name, role, possession_log,
            opencode_session_id, start_time,
            status, created_at, updated_at
        ) VALUES (
            {expected_possession_id}, 'malphas', 'Engineer',
            '.opencode/work/possessions/test.md',
            'ses_{expected_possession_id}', datetime('now'),
            'ACTIVE', datetime('now'), datetime('now')
        )
        """,
        {},
    )

    import pathlib

    real_home = pathlib.Path.home
    pathlib.Path.home = staticmethod(lambda: tmp_path)

    try:
        with patch("sys.stdin", StringIO(json.dumps({"role": "Engineer"}))):
            with patch.object(mod, "get_db_path", return_value=db_path):
                with patch.object(mod, "get_project_root", return_value=tmp_path):
                    with patch("subprocess.Popen", side_effect=fake_popen):
                        result_str = mod.main()
    finally:
        pathlib.Path.home = staticmethod(real_home)

    result = json.loads(result_str)
    assert "error" not in result, f"Unexpected error: {result}"
    assert result["possession_id"] == expected_possession_id


def test_spawn_token_file_cleaned_up_after_read(tmp_path, test_db, workers_dir):
    """summon_minion deletes the spawn-token status file after reading it."""
    mod = load_summon_minion()
    db_path = test_db

    written_token_file = []

    def fake_popen(cmd, **kwargs):
        idx = cmd.index("--spawn-token")
        token = cmd[idx + 1]
        status_file = workers_dir / f"{token}.json"
        written_token_file.append(status_file)
        _write_token_file(workers_dir, token, possession_id=7, daemon="bifrons")

        proc = MagicMock()
        proc.poll.return_value = None
        return proc

    from site_nine.core.database import Database

    db = Database(db_path)
    db.execute_update(
        "INSERT INTO daemons (name, role, incarnations) VALUES ('bifrons', 'Engineer', 0)",
        {},
    )
    db.execute_insert(
        """
        INSERT INTO possessions (
            id, daemon_name, role, possession_log,
            opencode_session_id, start_time,
            status, created_at, updated_at
        ) VALUES (
            7, 'bifrons', 'Engineer',
            '.opencode/work/possessions/test.md',
            'ses_7', datetime('now'),
            'ACTIVE', datetime('now'), datetime('now')
        )
        """,
        {},
    )

    import pathlib

    real_home = pathlib.Path.home
    pathlib.Path.home = staticmethod(lambda: tmp_path)

    try:
        with patch("sys.stdin", StringIO(json.dumps({"role": "Engineer"}))):
            with patch.object(mod, "get_db_path", return_value=db_path):
                with patch.object(mod, "get_project_root", return_value=tmp_path):
                    with patch("subprocess.Popen", side_effect=fake_popen):
                        result_str = mod.main()
    finally:
        pathlib.Path.home = staticmethod(real_home)

    result = json.loads(result_str)
    assert "error" not in result, f"Unexpected error: {result}"

    assert len(written_token_file) == 1
    assert not written_token_file[0].exists(), "Token file should have been deleted after reading"


def test_concurrent_same_role_spawns_return_different_ids(tmp_path, test_db, workers_dir):
    """Two concurrent same-role spawns return different possession IDs (no cross-assignment)."""
    mod = load_summon_minion()
    db_path = test_db

    from site_nine.core.database import Database

    db = Database(db_path)

    # Create two daemons and possessions that will be returned by each spawn
    db.execute_update(
        "INSERT INTO daemons (name, role, incarnations) VALUES ('halphas', 'Engineer', 0)",
        {},
    )
    db.execute_update(
        "INSERT INTO daemons (name, role, incarnations) VALUES ('ipos', 'Engineer', 0)",
        {},
    )
    db.execute_insert(
        """
        INSERT INTO possessions (
            id, daemon_name, role, possession_log,
            opencode_session_id, start_time, status, created_at, updated_at
        ) VALUES (
            101, 'halphas', 'Engineer', '.opencode/work/possessions/a.md',
            'ses_101', datetime('now'), 'ACTIVE', datetime('now'), datetime('now')
        )
        """,
        {},
    )
    db.execute_insert(
        """
        INSERT INTO possessions (
            id, daemon_name, role, possession_log,
            opencode_session_id, start_time, status, created_at, updated_at
        ) VALUES (
            102, 'ipos', 'Engineer', '.opencode/work/possessions/b.md',
            'ses_102', datetime('now'), 'ACTIVE', datetime('now'), datetime('now')
        )
        """,
        {},
    )

    # Simulate two workers: the first spawn gets possession 101, second gets 102
    spawn_call_count = [0]
    possession_ids_for_spawn = [101, 102]
    daemon_names_for_spawn = ["halphas", "ipos"]

    def fake_popen(cmd, **kwargs):
        spawn_index = spawn_call_count[0]
        spawn_call_count[0] += 1

        idx = cmd.index("--spawn-token")
        token = cmd[idx + 1]
        pid = possession_ids_for_spawn[spawn_index]
        daemon = daemon_names_for_spawn[spawn_index]
        _write_token_file(workers_dir, token, possession_id=pid, daemon=daemon)

        proc = MagicMock()
        proc.poll.return_value = None
        return proc

    results = []

    import pathlib

    real_home = pathlib.Path.home
    pathlib.Path.home = staticmethod(lambda: tmp_path)

    try:
        for _ in range(2):
            with patch("sys.stdin", StringIO(json.dumps({"role": "Engineer"}))):
                with patch.object(mod, "get_db_path", return_value=db_path):
                    with patch.object(mod, "get_project_root", return_value=tmp_path):
                        with patch("subprocess.Popen", side_effect=fake_popen):
                            result_str = mod.main()
            results.append(json.loads(result_str))
    finally:
        pathlib.Path.home = staticmethod(real_home)

    assert len(results) == 2
    for r in results:
        assert "error" not in r, f"Unexpected error: {r}"

    ids = [r["possession_id"] for r in results]
    assert ids[0] != ids[1], f"Both spawns returned the same possession ID: {ids}"
    assert set(ids) == {101, 102}, f"Expected IDs {{101, 102}}, got {ids}"


def test_summon_minion_timeout_returns_error(tmp_path, test_db, workers_dir):
    """summon_minion returns init_timeout error when status file never appears."""
    mod = load_summon_minion()
    db_path = test_db

    def fake_popen(cmd, **kwargs):
        proc = MagicMock()
        proc.poll.return_value = None  # process stays "alive" but never writes file
        return proc

    import pathlib

    real_home = pathlib.Path.home
    pathlib.Path.home = staticmethod(lambda: tmp_path)

    try:
        with patch("sys.stdin", StringIO(json.dumps({"role": "Engineer"}))):
            with patch.object(mod, "get_db_path", return_value=db_path):
                with patch.object(mod, "get_project_root", return_value=tmp_path):
                    with patch("subprocess.Popen", side_effect=fake_popen):
                        with patch("time.sleep"):  # speed up the poll loop
                            result_str = mod.main()
    finally:
        pathlib.Path.home = staticmethod(real_home)

    result = json.loads(result_str)
    assert result.get("error") == "init_timeout"


def test_summon_minion_worker_crash_returns_error(tmp_path, test_db, workers_dir):
    """summon_minion returns worker_died error when the process exits unexpectedly."""
    mod = load_summon_minion()
    db_path = test_db

    attempt_count = [0]

    def fake_popen(cmd, **kwargs):
        proc = MagicMock()

        def poll_side_effect():
            attempt_count[0] += 1
            # Return non-None after 12 calls (after the 10s grace period in the tool)
            if attempt_count[0] > 12:
                return 1
            return None

        proc.poll.side_effect = poll_side_effect
        proc.returncode = 1
        return proc

    import pathlib

    real_home = pathlib.Path.home
    pathlib.Path.home = staticmethod(lambda: tmp_path)

    try:
        with patch("sys.stdin", StringIO(json.dumps({"role": "Engineer"}))):
            with patch.object(mod, "get_db_path", return_value=db_path):
                with patch.object(mod, "get_project_root", return_value=tmp_path):
                    with patch("subprocess.Popen", side_effect=fake_popen):
                        with patch("time.sleep"):
                            result_str = mod.main()
    finally:
        pathlib.Path.home = staticmethod(real_home)

    result = json.loads(result_str)
    assert result.get("error") == "worker_died"
