# Testing Guide

> **Python policy:** Always use `uv run pytest` — never bare `pytest`. See `.opencode/docs/guides/python-usage-policy.md`.

Testing patterns for site-nine.


## Philosophy

- Engineers and Testers write tests
- Testers validate and run comprehensive suites
- Aim for >85% coverage
- Test behavior, not implementation

## Running Tests

```bash
uv run pytest                                   # All tests
uv run pytest tests/cli/test_task.py           # Specific file
uv run pytest tests/cli/test_task.py::test_create_task  # Specific test
uv run pytest --cov=src/site_nine --cov-report=term-missing  # With coverage
make qa                                         # All quality checks
make qa/test                                    # Tests only
```

## Writing Tests

### Structure and Naming

**Location:** Mirror source structure: `src/site_nine/cli/task.py` → `tests/cli/test_task.py`

**AAA Pattern:**
```python
def test_create_task_success():
    """Test successful task creation"""
    # Arrange - Set up
    title, role, priority = "Test", "Engineer", "HIGH"
    # Act - Execute
    result = create_task(title=title, role=role, priority=priority)
    # Assert - Verify
    assert result.id.startswith("ENG-H-")
```

**Naming:** `test_<behavior>_<condition>`, e.g., `test_create_task_with_valid_data`

## Fixtures

### Using Fixtures

```python
import pytest
from pathlib import Path
from site_nine.core.database import Database

@pytest.fixture
def temp_db(tmp_path: Path) -> Database:
    """Create a temporary test database"""
    db_path = tmp_path / "test.db"
    db = Database(db_path)
    db.initialize_schema()
    return db

def test_create_task_with_db(temp_db):
    """Test task creation with database"""
    # temp_db is automatically created and cleaned up
    task = temp_db.create_task(title="Test", role="Engineer")
    assert task is not None
```

### Common Fixtures

- `temp_db` - Temporary database with schema
- `mock_console` - Mock Rich console for CLI testing
- `sample_task` - Pre-created task for testing

## Mocking

Use `unittest.mock` or `pytest-mock` for external dependencies:

```python
from unittest.mock import Mock, patch

def test_fetch_data_from_api():
    with patch('site_nine.api.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.json.return_value = {'status': 'ok'}
        mock_get.return_value = mock_response
        
        result = fetch_data()
        assert result['status'] == 'ok'
        mock_get.assert_called_once()
```

## Test Categories

**Unit Tests** - Test individual functions in isolation:

```python
def test_format_task_id():
    result = format_task_id("Engineer", "HIGH", 42)
    assert result == "ENG-H-0042"
```

**Integration Tests** - Test multiple components together:

```python
def test_task_workflow_end_to_end(temp_db):
    task = create_task(db=temp_db, title="Test", role="Engineer")
    claim_task(db=temp_db, task_id=task.id, agent="TestAgent")
    update_task(db=temp_db, task_id=task.id, status="IN_PROGRESS")
    close_task(db=temp_db, task_id=task.id, status="COMPLETE")
    
    final_task = get_task(db=temp_db, task_id=task.id)
    assert final_task.status == "COMPLETE"
```

## Parametrized Tests

Test multiple scenarios with one function:

```python
@pytest.mark.parametrize("role,priority,expected", [
    ("Engineer", "HIGH", "ENG-H"),
    ("Architect", "MEDIUM", "ARC-M"),
    ("Tester", "LOW", "TST-L"),
])
def test_task_id_prefix(role, priority, expected):
    result = generate_task_prefix(role, priority)
    assert result == expected
```

## Testing CLI Commands

Use Typer's `CliRunner`:

```python
from typer.testing import CliRunner
from site_nine.cli.main import app

runner = CliRunner()

def test_task_create_command():
    result = runner.invoke(app, [
        "task", "create",
        "--title", "Test task",
        "--role", "Engineer",
        "--priority", "HIGH"
    ])
    
    assert result.exit_code == 0
    assert "ENG-H-" in result.stdout
```

## Edge Cases

Always test edge cases and error conditions:

```python
def test_create_task_with_empty_title():
    with pytest.raises(ValueError, match="Title cannot be empty"):
        create_task(title="", role="Engineer")

def test_get_task_with_nonexistent_id():
    result = get_task(task_id="FAKE-H-9999")
    assert result is None
```

## Coverage

```bash
# Run with coverage report
uv run pytest --cov=src/site_nine --cov-report=term-missing

# HTML report
uv run pytest --cov=src/site_nine --cov-report=html
open htmlcov/index.html
```

**Goals:**
- Overall: >85% coverage
- Core modules: >90% coverage
- CLI commands: >80% coverage
- Utility functions: 100% coverage

**Test:** Happy paths, edge cases, errors, boundaries, integrations
**Skip:** Third-party code, simple getters, auto-generated code, trivial one-liners

## Continuous Integration

Tests run on every PR, commit to main, and nightly builds. Run locally before pushing:

```bash
make qa
```

## Related Documentation

- **Commit Guidelines:** `.opencode/docs/guides/commit-guidelines.md` - Includes "run tests before commit"
- **Troubleshooting Guide:** `.opencode/docs/guides/troubleshooting.md` - Debugging test failures
- **Development Guide:** `.opencode/docs/guides/README.md` - Testing workflow for agents
