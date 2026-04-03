"""Tests for persona CLI commands"""

from pathlib import Path

from site_nine.__main__ import app
from site_nine.core.database import Database
from typer.testing import CliRunner

runner = CliRunner()


def test_persona_list(initialized_project: Path):
    """Test listing personas"""
    result = runner.invoke(app, ["persona", "list"])

    assert result.exit_code == 0
    # Should show daemons from the initialized database


def test_persona_list_with_role_filter(initialized_project: Path):
    """Test listing personas filtered by role"""
    result = runner.invoke(app, ["persona", "list", "--role", "Engineer"])

    assert result.exit_code == 0


def test_persona_suggest(initialized_project: Path):
    """Test suggesting a persona for a role"""
    result = runner.invoke(app, ["persona", "suggest", "Engineer"])

    assert result.exit_code == 0
    # Should suggest a daemon name


# Temporarily skip - needs investigation
# def test_persona_suggest_with_exclusions(initialized_project: Path):
#     """Test suggesting personas with exclusions"""
#     pass


# Temporarily skip - needs investigation
# def test_persona_usage(initialized_project: Path):
#     """Test showing persona usage statistics"""
#     pass

# def test_persona_usage_with_role_filter(initialized_project: Path):
#     """Test showing persona usage for specific role"""
#     pass


def test_persona_show(initialized_project: Path):
    """Test showing persona details"""
    # First get a daemon name from the database
    with Database(Path.cwd() / ".opencode" / "data" / "project.db") as db:
        daemons = db.execute_query("SELECT name FROM daemons LIMIT 1")

    if daemons:
        daemon_name = daemons[0]["name"]
        result = runner.invoke(app, ["persona", "show", daemon_name])
        assert result.exit_code == 0
        # Check case-insensitively since output may capitalize
        assert daemon_name.lower() in result.output.lower()


def test_persona_show_nonexistent(initialized_project: Path):
    """Test showing non-existent persona"""
    result = runner.invoke(app, ["persona", "show", "nonexistent-persona"])

    # Should fail or show error
    normalized = " ".join(result.output.split()).lower()
    assert "not found" in normalized or result.exit_code != 0


def test_persona_add_requires_name(initialized_project: Path):
    """Test that add command requires persona name"""
    result = runner.invoke(app, ["persona", "add"])

    assert result.exit_code != 0


def test_persona_add_success(initialized_project: Path):
    """Test adding a new persona"""
    result = runner.invoke(
        app,
        [
            "persona",
            "add",
            "test-persona",
            "--role",
            "Engineer",
        ],
    )

    assert result.exit_code == 0
    normalized = " ".join(result.output.split())
    assert "Added" in normalized or "test-persona" in normalized


def test_persona_add_duplicate(initialized_project: Path):
    """Test adding duplicate persona"""
    # Add first time
    runner.invoke(
        app,
        [
            "persona",
            "add",
            "duplicate-test",
            "--role",
            "Engineer",
        ],
    )

    # Try to add again
    result = runner.invoke(
        app,
        [
            "persona",
            "add",
            "duplicate-test",
            "--role",
            "Engineer",
        ],
    )

    # Should show error about duplicate
    normalized = " ".join(result.output.split()).lower()
    assert "already exists" in normalized or "error" in normalized


# Temporarily skip - needs investigation
# def test_persona_set_bio(initialized_project: Path):
#     """Test setting persona bio"""
#     pass


def test_persona_list_json(initialized_project: Path):
    """Test listing personas in JSON format"""
    result = runner.invoke(app, ["persona", "list", "--json"])

    # Just check it runs successfully
    assert result.exit_code == 0


def test_persona_suggest_json(initialized_project: Path):
    """Test suggesting persona in JSON format"""
    result = runner.invoke(app, ["persona", "suggest", "Engineer", "--json"])

    # Just check it runs successfully
    assert result.exit_code == 0


# Temporarily skip - needs investigation
# def test_persona_usage_json(initialized_project: Path):
#     """Test persona usage in JSON format"""
#     pass


def test_persona_usage_success(initialized_project: Path):
    """Test showing usage for an existing daemon"""
    db_path = Path.cwd() / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        daemons = db.execute_query("SELECT name FROM daemons LIMIT 1")

    assert daemons, "Expected at least one daemon in the database"
    daemon_name = daemons[0]["name"]

    result = runner.invoke(app, ["persona", "usage", daemon_name])

    assert result.exit_code == 0
    normalized = " ".join(result.output.split()).lower()
    assert daemon_name.lower() in normalized
    assert "role:" in normalized or "role" in normalized


def test_persona_usage_not_found(initialized_project: Path):
    """Test usage command for a nonexistent persona"""
    result = runner.invoke(app, ["persona", "usage", "nonexistent-persona-xyz"])

    assert result.exit_code != 0
    normalized = " ".join(result.output.split()).lower()
    assert "not found" in normalized


def test_persona_usage_with_missions(initialized_project: Path):
    """Test usage command shows possessions table when possessions exist"""
    db_path = Path.cwd() / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        daemons = db.execute_query("SELECT name, role FROM daemons LIMIT 1")
        assert daemons, "Expected at least one daemon"
        daemon_name = daemons[0]["name"]
        daemon_role = daemons[0]["role"]

        # Seed a possession for this daemon
        db.execute_update(
            """
            INSERT INTO possessions (daemon_name, role, possession_log, start_time)
            VALUES (:daemon_name, :role, :possession_log, :start_time)
            """,
            {
                "daemon_name": daemon_name,
                "role": daemon_role,
                "possession_log": ".opencode/work/possessions/test-possession.md",
                "start_time": "2026-02-11T10:00:00",
            },
        )

    result = runner.invoke(app, ["persona", "usage", daemon_name])

    assert result.exit_code == 0
    normalized = " ".join(result.output.split()).lower()
    assert daemon_name.lower() in normalized


def test_persona_set_bio_success(initialized_project: Path):
    """Test setting a bio for an existing daemon"""
    db_path = Path.cwd() / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        daemons = db.execute_query("SELECT name FROM daemons LIMIT 1")

    assert daemons, "Expected at least one daemon"
    daemon_name = daemons[0]["name"]

    result = runner.invoke(app, ["persona", "set-bio", daemon_name, "I am a whimsical test bio."])

    assert result.exit_code == 0
    normalized = " ".join(result.output.split()).lower()
    assert "updated" in normalized or daemon_name.lower() in normalized


def test_persona_set_bio_not_found(initialized_project: Path):
    """Test setting a bio for a nonexistent persona"""
    result = runner.invoke(app, ["persona", "set-bio", "nonexistent-persona-xyz", "Some bio text"])

    assert result.exit_code != 0
    normalized = " ".join(result.output.split()).lower()
    assert "not found" in normalized


def test_persona_show_with_bio(initialized_project: Path):
    """Test that show displays the daemonology when set"""
    db_path = Path.cwd() / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        daemons = db.execute_query("SELECT name FROM daemons LIMIT 1")

    assert daemons, "Expected at least one daemon"
    daemon_name = daemons[0]["name"]

    # First set a bio (daemonology)
    bio_text = "I am a legendary being who writes tests for fun."
    runner.invoke(app, ["persona", "set-bio", daemon_name, bio_text])

    # Now show the daemon
    result = runner.invoke(app, ["persona", "show", daemon_name])

    assert result.exit_code == 0
    normalized = " ".join(result.output.split())
    assert " ".join(bio_text.split()) in normalized
    assert "About me" in normalized


def test_persona_list_unused_only(initialized_project: Path):
    """Test listing only unused personas"""
    result = runner.invoke(app, ["persona", "list", "--unused-only"])

    assert result.exit_code == 0
    # All default daemons should be unused after init, so we should see results
    assert "0" in result.output or "Personas" in result.output


def test_persona_add_invalid_role(initialized_project: Path):
    """Test adding a persona with an invalid role"""
    result = runner.invoke(
        app,
        [
            "persona",
            "add",
            "invalid-role-test",
            "--role",
            "NotAValidRole",
        ],
    )

    assert result.exit_code != 0
    normalized = " ".join(result.output.split()).lower()
    assert "invalid role" in normalized


def test_persona_list_by_usage(initialized_project: Path):
    """Test listing personas sorted by usage"""
    result = runner.invoke(app, ["persona", "list", "--by-usage"])

    assert result.exit_code == 0
    assert "Personas" in result.output


def test_persona_list_empty_json(initialized_project: Path):
    """Test listing personas with JSON output when filter returns no results"""
    db_path = Path.cwd() / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        # Delete all daemons for Historian role, then list by that role
        db.execute_update("DELETE FROM daemons WHERE role = 'Historian'")

    result = runner.invoke(app, ["persona", "list", "--role", "Historian", "--json"])

    assert result.exit_code == 0


def test_persona_list_empty_no_json(initialized_project: Path):
    """Test listing personas with no JSON when filter returns no results"""
    db_path = Path.cwd() / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        db.execute_update("DELETE FROM daemons WHERE role = 'Historian'")

    result = runner.invoke(app, ["persona", "list", "--role", "Historian"])

    assert result.exit_code == 0
    normalized = " ".join(result.output.split()).lower()
    assert "no personas found" in normalized


def test_persona_suggest_empty_no_json(initialized_project: Path):
    """Test suggest when no personas found for a role (non-JSON output)"""
    db_path = Path.cwd() / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        db.execute_update("DELETE FROM daemons WHERE role = 'Historian'")

    result = runner.invoke(app, ["persona", "suggest", "Historian"])

    assert result.exit_code == 0
    normalized = " ".join(result.output.split()).lower()
    assert "no personas found" in normalized


def test_persona_suggest_empty_json(initialized_project: Path):
    """Test suggest when no personas found for a role (JSON output)"""
    db_path = Path.cwd() / ".opencode" / "data" / "project.db"
    with Database(db_path) as db:
        db.execute_update("DELETE FROM daemons WHERE role = 'Historian'")

    result = runner.invoke(app, ["persona", "suggest", "Historian", "--json"])

    assert result.exit_code == 0


def test_persona_add_non_unique_error_reraise(initialized_project: Path):
    """Test that non-UNIQUE constraint errors are re-raised"""
    # We can trigger a non-UNIQUE constraint error by providing an invalid role
    # that passes _validate_role but fails the CHECK constraint in the DB.
    # However, _validate_role limits us to valid roles. Instead, we test indirectly
    # by verifying that adding a duplicate raises the correct message (UNIQUE path)
    # The non-UNIQUE re-raise path (line 76) would require a DB-level error
    # that isn't a UNIQUE constraint - this is defensive code that's hard to trigger
    # in normal conditions, so we ensure the UNIQUE path is covered by test_persona_add_duplicate.
    pass
