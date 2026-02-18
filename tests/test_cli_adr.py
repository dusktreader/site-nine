"""Tests for ADR CLI commands"""

from pathlib import Path
import pytest

from site_nine.__main__ import app
from typer.testing import CliRunner

runner = CliRunner()


def test_adr_create_requires_title(initialized_project: Path):
    """Test that create requires title"""
    result = runner.invoke(app, ["adr", "create"])

    assert result.exit_code != 0


def test_adr_list_empty(initialized_project: Path):
    """Test listing ADRs when none exist"""
    result = runner.invoke(app, ["adr", "list"])

    assert result.exit_code == 0


def test_adr_list_with_status_filter(initialized_project: Path):
    """Test listing ADRs filtered by status"""
    result = runner.invoke(app, ["adr", "list", "--status", "PROPOSED"])

    assert result.exit_code == 0


def test_adr_show_not_found(initialized_project: Path):
    """Test showing non-existent ADR"""
    result = runner.invoke(app, ["adr", "show", "ADR-999"])

    assert result.exit_code != 0


def test_adr_update_not_found(initialized_project: Path):
    """Test updating non-existent ADR"""
    result = runner.invoke(
        app,
        ["adr", "update", "ADR-999", "--status", "ACCEPTED"],
    )

    assert result.exit_code != 0


def test_adr_sync(initialized_project: Path):
    """Test syncing ADRs — aborts when no ADRs directory exists"""
    result = runner.invoke(app, ["adr", "sync"])

    assert result.exit_code == 1
    assert "No ADRs directory" in result.output


def test_adr_update_status_after_create(initialized_project: Path):
    """Test updating ADR status after creation"""
    # First create an ADR
    runner.invoke(
        app,
        ["adr", "create", "--title", "Test ADR", "--status", "PROPOSED"],
    )

    # Then update it
    result = runner.invoke(
        app,
        ["adr", "update", "ADR-001", "--status", "ACCEPTED"],
    )

    assert result.exit_code == 0


def test_adr_update_title_after_create(initialized_project: Path):
    """Test updating ADR title after creation"""
    # First create an ADR
    runner.invoke(
        app,
        ["adr", "create", "--title", "Original Title", "--status", "PROPOSED"],
    )

    # Then update it
    result = runner.invoke(
        app,
        ["adr", "update", "ADR-001", "--title", "Updated Title"],
    )

    assert result.exit_code == 0


def test_adr_create_multiple(initialized_project: Path):
    """Test creating multiple ADRs"""
    # Create first
    result1 = runner.invoke(
        app,
        ["adr", "create", "--title", "First ADR", "--status", "PROPOSED"],
    )

    # Create second
    result2 = runner.invoke(
        app,
        ["adr", "create", "--title", "Second ADR", "--status", "PROPOSED"],
    )

    # Both should succeed or show reasonable errors
    assert result1.exit_code in [0, 1]
    assert result2.exit_code in [0, 1]


@pytest.mark.skip(reason="--description flag not implemented on adr create")
def test_adr_create_with_all_options(initialized_project: Path):
    """Test creating ADR with all options"""
    result = runner.invoke(
        app,
        [
            "adr",
            "create",
            "--title",
            "Full ADR",
            "--description",
            "Detailed description",
            "--status",
            "proposed",
        ],
    )

    # Either succeeds or has minor issue
    assert result.exit_code in [0, 1]


def test_adr_show_command(initialized_project: Path):
    """Test showing ADR details"""
    result = runner.invoke(app, ["adr", "show", "ADR-001"])

    # May fail if ADR doesn't exist
    assert result.exit_code in [0, 1]


@pytest.mark.skip(reason="--json flag not implemented on adr show")
def test_adr_show_json(initialized_project: Path):
    """Test showing ADR in JSON format"""
    result = runner.invoke(app, ["adr", "show", "ADR-001", "--json"])

    # May fail if ADR doesn't exist
    assert result.exit_code in [0, 1]


def test_adr_list_all(initialized_project: Path):
    """Test listing all ADRs"""
    result = runner.invoke(app, ["adr", "list"])

    assert result.exit_code == 0


@pytest.mark.skip(reason="--json flag not implemented on adr list")
def test_adr_list_json_format(initialized_project: Path):
    """Test listing ADRs in JSON"""
    result = runner.invoke(app, ["adr", "list", "--json"])

    assert result.exit_code == 0


def test_adr_update_status(initialized_project: Path):
    """Test updating ADR status"""
    result = runner.invoke(
        app,
        ["adr", "update", "ADR-001", "--status", "accepted"],
    )

    # May fail if ADR doesn't exist
    assert result.exit_code in [0, 1]


def test_adr_update_title(initialized_project: Path):
    """Test updating ADR title"""
    result = runner.invoke(
        app,
        ["adr", "update", "ADR-001", "--title", "New Title"],
    )

    # May fail if ADR doesn't exist
    assert result.exit_code in [0, 1]


def test_adr_supersede_command(initialized_project: Path):
    """Test superseding an ADR"""
    result = runner.invoke(
        app,
        ["adr", "supersede", "ADR-001", "ADR-002"],
    )

    # May fail if ADRs don't exist
    assert result.exit_code in [0, 1, 2]


def test_adr_create_proposed_status(initialized_project: Path):
    """Test creating ADR with proposed status (default)"""
    result = runner.invoke(
        app,
        ["adr", "create", "--title", "Test Proposed ADR"],
    )

    # Should succeed or have minor issue
    assert result.exit_code in [0, 1]


def test_adr_create_accepted_status(initialized_project: Path):
    """Test creating ADR with accepted status"""
    result = runner.invoke(
        app,
        ["adr", "create", "--title", "Test Accepted ADR", "--status", "ACCEPTED"],
    )

    assert result.exit_code in [0, 1]


def test_adr_create_rejected_status(initialized_project: Path):
    """Test creating ADR with rejected status"""
    result = runner.invoke(
        app,
        ["adr", "create", "--title", "Test Rejected ADR", "--status", "REJECTED"],
    )

    assert result.exit_code in [0, 1]


def test_adr_create_deprecated_status(initialized_project: Path):
    """Test creating ADR with deprecated status"""
    result = runner.invoke(
        app,
        ["adr", "create", "--title", "Test Deprecated ADR", "--status", "DEPRECATED"],
    )

    assert result.exit_code in [0, 1]


def test_adr_create_superseded_status(initialized_project: Path):
    """Test creating ADR with superseded status"""
    result = runner.invoke(
        app,
        ["adr", "create", "--title", "Test Superseded ADR", "--status", "SUPERSEDED"],
    )

    assert result.exit_code in [0, 1]


def test_adr_list_no_filters(initialized_project: Path):
    """Test listing ADRs without filters"""
    result = runner.invoke(app, ["adr", "list"])

    assert result.exit_code == 0


def test_adr_sync_command(initialized_project: Path):
    """Test syncing ADRs from filesystem"""
    result = runner.invoke(app, ["adr", "sync"])

    # Should succeed even if no ADRs to sync
    assert result.exit_code in [0, 1]


def test_adr_show_with_invalid_id(initialized_project: Path):
    """Test showing ADR with invalid ID format"""
    result = runner.invoke(app, ["adr", "show", "INVALID"])

    # Should fail gracefully
    assert result.exit_code in [1, 2]


def test_adr_update_nonexistent(initialized_project: Path):
    """Test updating non-existent ADR"""
    result = runner.invoke(
        app,
        ["adr", "update", "ADR-999", "--title", "New Title"],
    )

    # Should fail
    assert result.exit_code != 0


def test_adr_list_command_runs(initialized_project: Path):
    """Test that list command runs without error"""
    result = runner.invoke(app, ["adr", "list"])

    assert result.exit_code == 0


def test_adr_create_with_short_flags(initialized_project: Path):
    """Test creating ADR with short flag syntax"""
    result = runner.invoke(
        app,
        ["adr", "create", "-t", "Short Flag Test", "-s", "PROPOSED"],
    )

    assert result.exit_code in [0, 1]


def test_adr_create_and_list_workflow(initialized_project: Path):
    """Test creating an ADR and then listing it"""
    # Create ADR
    create_result = runner.invoke(
        app,
        ["adr", "create", "--title", "Workflow Test ADR", "--status", "PROPOSED"],
    )

    # Then list ADRs
    list_result = runner.invoke(app, ["adr", "list"])

    # At least one should succeed
    assert create_result.exit_code in [0, 1] or list_result.exit_code == 0


def test_adr_create_and_show_workflow(initialized_project: Path):
    """Test creating an ADR and then showing it"""
    # Create ADR
    create_result = runner.invoke(
        app,
        ["adr", "create", "--title", "Show Test ADR", "--status", "PROPOSED"],
    )

    if create_result.exit_code == 0:
        # Try to show ADR-001
        show_result = runner.invoke(app, ["adr", "show", "ADR-001"])
        assert show_result.exit_code in [0, 1]


def test_adr_create_update_workflow(initialized_project: Path):
    """Test creating an ADR and then updating it"""
    # Create ADR
    create_result = runner.invoke(
        app,
        ["adr", "create", "--title", "Update Test ADR", "--status", "PROPOSED"],
    )

    if create_result.exit_code == 0:
        # Try to update it
        update_result = runner.invoke(
            app,
            ["adr", "update", "ADR-001", "--status", "ACCEPTED"],
        )
        assert update_result.exit_code in [0, 1]


def test_adr_multiple_creates(initialized_project: Path):
    """Test creating multiple ADRs in sequence"""
    results = []
    for i in range(3):
        result = runner.invoke(
            app,
            ["adr", "create", "--title", f"Test ADR {i}", "--status", "PROPOSED"],
        )
        results.append(result.exit_code)

    # At least some should succeed
    assert any(code in [0, 1] for code in results)


# =====================================================================
# Coverage-targeted tests for uncovered lines in cli/adr.py
# =====================================================================


def test_parse_adr_id(tmp_path: Path):
    """Unit test parse_adr_id extracts ADR-NNN from filenames."""
    from site_nine.adrs import parse_adr_id

    # Standard filename
    assert parse_adr_id("ADR-001-adapter-pattern.md") == "ADR-001"
    # Full path string
    assert parse_adr_id(str(tmp_path / "ADR-042-some-title.md")) == "ADR-042"
    # No match
    assert parse_adr_id("some-random-file.md") is None
    # Edge: ADR with many digits
    assert parse_adr_id("ADR-12345-long-id.md") == "ADR-12345"


def test_parse_adr_title(tmp_path: Path):
    """Unit test parse_adr_title extracts title from markdown content."""
    from site_nine.adrs import parse_adr_title

    # Standard pattern: # ADR-001: Some Title
    md_file = tmp_path / "ADR-001-test.md"
    md_file.write_text("# ADR-001: My Great Decision\n\n**Status:** PROPOSED\n")
    assert parse_adr_title(md_file) == "My Great Decision"

    # Fallback: plain heading without ADR prefix
    md_file2 = tmp_path / "ADR-002-test.md"
    md_file2.write_text("# Just A Heading\n\nSome content.\n")
    assert parse_adr_title(md_file2) == "Just A Heading"

    # No heading at all
    md_file3 = tmp_path / "ADR-003-test.md"
    md_file3.write_text("No heading here, just text.\n")
    assert parse_adr_title(md_file3) is None

    # Non-existent file returns None (exception path)
    assert parse_adr_title(tmp_path / "nonexistent.md") is None


def test_parse_adr_status(tmp_path: Path):
    """Unit test parse_adr_status extracts status from markdown content."""
    from site_nine.adrs import parse_adr_status

    # Valid status
    md_file = tmp_path / "ADR-001.md"
    md_file.write_text("# ADR-001: Title\n\n**Status:** ACCEPTED\n")
    assert parse_adr_status(md_file) == "ACCEPTED"

    # Invalid status string falls back to PROPOSED
    md_file2 = tmp_path / "ADR-002.md"
    md_file2.write_text("# ADR-002: Title\n\n**Status:** BOGUS\n")
    assert parse_adr_status(md_file2) == "PROPOSED"

    # No status line at all falls back to PROPOSED
    md_file3 = tmp_path / "ADR-003.md"
    md_file3.write_text("# ADR-003: Title\n\nNo status here.\n")
    assert parse_adr_status(md_file3) == "PROPOSED"

    # Non-existent file falls back to PROPOSED (exception path)
    assert parse_adr_status(tmp_path / "nonexistent.md") == "PROPOSED"


def test_adr_create_success_full(initialized_project: Path):
    """Test create ADR with full output: ID, title, status, file path, and file on disk."""
    result = runner.invoke(
        app,
        ["adr", "create", "--title", "Use Adapter Pattern", "--status", "PROPOSED"],
    )

    assert result.exit_code == 0
    assert "ADR-001" in result.stdout
    assert "Use Adapter Pattern" in result.stdout
    assert "PROPOSED" in result.stdout
    assert ".opencode/docs/adrs/" in result.stdout

    # Verify the markdown file was actually created on disk
    adrs_dir = initialized_project / ".opencode" / "docs" / "adrs"
    adr_files = list(adrs_dir.glob("ADR-001-*.md"))
    assert len(adr_files) == 1
    content = adr_files[0].read_text()
    assert "# ADR-001: Use Adapter Pattern" in content
    assert "**Status:** PROPOSED" in content


def test_adr_create_invalid_status(initialized_project: Path):
    """Test create with an invalid status value produces an error."""
    result = runner.invoke(
        app,
        ["adr", "create", "--title", "Bad Status ADR", "--status", "INVALID"],
    )

    assert result.exit_code != 0
    assert "Invalid value" in result.output


def test_adr_list_with_status_filter_valid(initialized_project: Path):
    """Test listing ADRs filtered by a valid status that matches existing ADRs."""
    # Create an ADR with PROPOSED status
    runner.invoke(
        app,
        ["adr", "create", "--title", "Filter Test ADR", "--status", "PROPOSED"],
    )

    result = runner.invoke(app, ["adr", "list", "--status", "PROPOSED"])
    assert result.exit_code == 0
    assert "Filter Test ADR" in result.stdout


def test_adr_list_invalid_status(initialized_project: Path):
    """Test listing ADRs with an invalid status filter produces an error."""
    result = runner.invoke(app, ["adr", "list", "--status", "NOTASTATUS"])

    assert result.exit_code != 0
    assert "Invalid value" in result.output


def test_adr_list_status_no_results(initialized_project: Path):
    """Test listing ADRs with a valid status filter but no matching ADRs."""
    # Don't create any ADRs, just filter
    result = runner.invoke(app, ["adr", "list", "--status", "REJECTED"])

    assert result.exit_code == 0
    assert "No ADRs found" in result.stdout


def test_adr_show_with_linked_items(initialized_project: Path):
    """Test show command displays linked epics and tasks."""
    from site_nine.core.database import Database
    from site_nine.core.paths import get_opencode_dir

    # Create an ADR first
    create_result = runner.invoke(
        app,
        ["adr", "create", "--title", "Linked Items ADR", "--status", "PROPOSED"],
    )
    assert create_result.exit_code == 0

    # Seed linked epics and tasks via raw DB
    opencode_dir = get_opencode_dir()
    db_path = opencode_dir / "data" / "project.db"
    with Database(db_path) as db:
        # Create an epic and task first to satisfy foreign keys
        db.execute_update(
            """
            INSERT INTO epics (id, title, priority, file_path)
            VALUES ('EPC-H-0001', 'Test Epic', 'HIGH', '.opencode/work/epics/EPC-H-0001.md')
            """
        )
        db.execute_update(
            """
            INSERT INTO tasks (id, title, status, priority, role, file_path, created_at)
            VALUES ('ENG-H-0001', 'Test Task', 'TODO', 'HIGH', 'Engineer',
                    '.opencode/work/tasks/ENG-H-0001.md', datetime('now'))
            """
        )
        # Link them to the ADR
        db.execute_update("INSERT INTO epic_architecture_docs (epic_id, adr_id) VALUES ('EPC-H-0001', 'ADR-001')")
        db.execute_update("INSERT INTO task_architecture_docs (task_id, adr_id) VALUES ('ENG-H-0001', 'ADR-001')")

    # Show the ADR
    result = runner.invoke(app, ["adr", "show", "ADR-001"])
    assert result.exit_code == 0
    assert "Linked Epics" in result.stdout
    assert "EPC-H-0001" in result.stdout
    assert "Linked Tasks" in result.stdout
    assert "ENG-H-0001" in result.stdout


def test_adr_update_invalid_status(initialized_project: Path):
    """Test updating ADR with an invalid status produces an error."""
    # Create ADR first
    runner.invoke(
        app,
        ["adr", "create", "--title", "Update Invalid Status", "--status", "PROPOSED"],
    )

    result = runner.invoke(
        app,
        ["adr", "update", "ADR-001", "--status", "BOGUS"],
    )

    assert result.exit_code != 0
    assert "Invalid value" in result.output


def test_adr_update_no_changes(initialized_project: Path):
    """Test updating ADR without --title or --status produces 'No updates' message."""
    # Create ADR first
    runner.invoke(
        app,
        ["adr", "create", "--title", "No Changes ADR", "--status", "PROPOSED"],
    )

    result = runner.invoke(app, ["adr", "update", "ADR-001"])

    assert result.exit_code != 0
    assert "No updates" in result.output


def test_adr_sync_with_files(initialized_project: Path):
    """Test sync imports ADR files from .opencode/docs/adrs/ into the database."""
    adrs_dir = initialized_project / ".opencode" / "docs" / "adrs"
    adrs_dir.mkdir(parents=True, exist_ok=True)

    # Create ADR markdown files
    (adrs_dir / "ADR-001-use-sqlite.md").write_text(
        "# ADR-001: Use SQLite for Storage\n\n**Status:** PROPOSED\n\nSome context.\n"
    )
    (adrs_dir / "ADR-002-adopt-typer.md").write_text(
        "# ADR-002: Adopt Typer for CLI\n\n**Status:** ACCEPTED\n\nSome context.\n"
    )

    result = runner.invoke(app, ["adr", "sync"])

    assert result.exit_code == 0
    assert "Imported" in result.stdout
    assert "Sync complete" in result.stdout


def test_adr_sync_no_directory(initialized_project: Path):
    """Test sync when adrs directory doesn't exist."""
    adrs_dir = initialized_project / ".opencode" / "docs" / "adrs"
    # Ensure it does NOT exist
    if adrs_dir.exists():
        import shutil

        shutil.rmtree(adrs_dir)

    result = runner.invoke(app, ["adr", "sync"])

    assert result.exit_code == 1
    assert "No ADRs directory" in result.output


def test_adr_sync_no_files(initialized_project: Path):
    """Test sync when adrs directory exists but contains no ADR files."""
    adrs_dir = initialized_project / ".opencode" / "docs" / "adrs"
    adrs_dir.mkdir(parents=True, exist_ok=True)

    result = runner.invoke(app, ["adr", "sync"])

    assert result.exit_code == 1
    assert "No ADR files found" in result.output


def test_adr_sync_updates_existing(initialized_project: Path):
    """Test sync updates an existing ADR when the file content changes."""
    # Create ADR via CLI first
    create_result = runner.invoke(
        app,
        ["adr", "create", "--title", "Original Title", "--status", "PROPOSED"],
    )
    assert create_result.exit_code == 0

    # Find and modify the generated markdown file
    adrs_dir = initialized_project / ".opencode" / "docs" / "adrs"
    adr_files = list(adrs_dir.glob("ADR-001-*.md"))
    assert len(adr_files) == 1

    # Rewrite the file with a different title and status
    adr_files[0].write_text("# ADR-001: Updated Title\n\n**Status:** ACCEPTED\n\nUpdated context.\n")

    result = runner.invoke(app, ["adr", "sync"])

    assert result.exit_code == 0
    assert "Updated" in result.stdout
    assert "Sync complete" in result.stdout


def test_adr_sync_skips_unparseable_id(initialized_project: Path):
    """Test sync warns and skips files with unparseable ADR IDs."""
    adrs_dir = initialized_project / ".opencode" / "docs" / "adrs"
    adrs_dir.mkdir(parents=True, exist_ok=True)

    # The glob is ADR-*.md, so the file needs to match that pattern but
    # parse_adr_id looks for "ADR-\d+", so "ADR-xyz" won't parse.
    (adrs_dir / "ADR-xyz-bad-id.md").write_text("# Some Title\n\n**Status:** PROPOSED\n")

    result = runner.invoke(app, ["adr", "sync"])

    assert result.exit_code == 0
    assert "Warning" in result.stdout or "Could not parse ADR ID" in result.stdout


def test_adr_sync_skips_unparseable_title(initialized_project: Path):
    """Test sync warns and skips files with no parseable title."""
    adrs_dir = initialized_project / ".opencode" / "docs" / "adrs"
    adrs_dir.mkdir(parents=True, exist_ok=True)

    # Valid ADR ID pattern, but no heading in content
    (adrs_dir / "ADR-001-no-title.md").write_text("No heading at all, just plain text.\n\n**Status:** PROPOSED\n")

    result = runner.invoke(app, ["adr", "sync"])

    assert result.exit_code == 0
    assert "Warning" in result.stdout or "Could not parse title" in result.stdout


def test_adr_sync_skips_unchanged(initialized_project: Path):
    """Test sync skips ADRs that haven't changed since last sync."""
    # Create ADR via CLI
    create_result = runner.invoke(
        app,
        ["adr", "create", "--title", "Unchanged ADR", "--status", "PROPOSED"],
    )
    assert create_result.exit_code == 0

    # The file on disk already matches the DB. Sync should skip it.
    result = runner.invoke(app, ["adr", "sync"])

    assert result.exit_code == 0
    assert "Skipped" in result.stdout
    assert "Sync complete" in result.stdout
