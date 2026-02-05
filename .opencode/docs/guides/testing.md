# Testing Guide

Guidelines and patterns for testing in site-nine.

## Philosophy

- **Engineers write tests** - Tests are written as part of implementation
- **Testers run tests** - Testers validate and do manual testing
- **Test coverage matters** - Aim for >85% coverage
- **Test behavior, not implementation** - Focus on what code does, not how

## Running Tests

### Basic Test Commands

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/cli/test_task.py

# Specific test
uv run pytest tests/cli/test_task.py::test_create_task

# With coverage
uv run pytest --cov=src/site_nine --cov-report=term-missing

# Verbose output
uv run pytest -vv
```

### Using Make Commands

```bash
# Run all quality checks (format + lint + test)
make qa

# Run only tests
make qa/test

# Run integration tests (requires docker)
make qa/test-integration
```

## Writing Tests

### Test File Location

Follow the mirror structure convention:

```
src/site_nine/cli/task.py      →  tests/cli/test_task.py
src/site_nine/core/renderer.py →  tests/core/test_renderer.py
src/site_nine/tasks/manager.py →  tests/tasks/test_manager.py
```

### Test Structure

Use the **Arrange-Act-Assert (AAA)** pattern:

```python
import pytest
from site_nine.cli.task import create_task

def test_create_task_success():
    """Test successful task creation"""
    # Arrange - Set up test data
    title = "Test task"
    role = "Engineer"
    priority = "HIGH"
    
    # Act - Execute the code being tested
    result = create_task(title=title, role=role, priority=priority)
    
    # Assert - Verify the results
    assert result.id.startswith("ENG-H-")
    assert result.title == title
```

### Test Naming Convention

- **Test files:** `test_<module_name>.py`
- **Test functions:** `test_<behavior>_<condition>`
- **Test classes:** `Test<ClassName>`

**Examples:**
```python
def test_create_task_with_valid_data()
def test_create_task_raises_error_when_title_empty()
def test_update_task_changes_status()

class TestTaskManager:
    def test_list_tasks_returns_all_tasks()
    def test_list_tasks_filters_by_status()
```

### Docstrings

Every test should have a clear docstring:

```python
def test_create_task_generates_correct_id():
    """Test that task IDs follow ROLE-PRIORITY-NUMBER format"""
    # ...

def test_claim_task_fails_when_already_claimed():
    """Test that claiming an already-claimed task raises ValueError"""
    # ...
```

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

Site-nine provides these common fixtures:

- `temp_db` - Temporary database with schema
- `mock_console` - Mock Rich console for CLI testing
- `sample_task` - Pre-created task for testing

## Mocking

### Mocking External Dependencies

Use `unittest.mock` or `pytest-mock`:

```python
from unittest.mock import Mock, patch
import pytest

def test_fetch_data_from_api():
    """Test API call without actually calling the API"""
    with patch('site_nine.api.requests.get') as mock_get:
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {'status': 'ok'}
        mock_get.return_value = mock_response
        
        # Act
        result = fetch_data()
        
        # Assert
        assert result['status'] == 'ok'
        mock_get.assert_called_once()
```

### Mocking Database Calls

```python
def test_list_tasks_handles_empty_db(mocker):
    """Test listing tasks when database is empty"""
    # Mock the database query
    mock_db = mocker.Mock()
    mock_db.execute_query.return_value = []
    
    manager = TaskManager(mock_db)
    tasks = manager.list_tasks()
    
    assert tasks == []
```

## Test Categories

### Unit Tests

Test individual functions/methods in isolation:

```python
def test_format_task_id():
    """Test task ID formatting logic"""
    role = "Engineer"
    priority = "HIGH"
    number = 42
    
    result = format_task_id(role, priority, number)
    
    assert result == "ENG-H-0042"
```

### Integration Tests

Test multiple components working together:

```python
def test_task_workflow_end_to_end(temp_db):
    """Test complete task lifecycle"""
    # Create task
    task = create_task(db=temp_db, title="Test", role="Engineer")
    
    # Claim task
    claim_task(db=temp_db, task_id=task.id, agent="TestAgent")
    
    # Update task
    update_task(db=temp_db, task_id=task.id, status="IN_PROGRESS")
    
    # Close task
    close_task(db=temp_db, task_id=task.id, status="COMPLETE")
    
    # Verify final state
    final_task = get_task(db=temp_db, task_id=task.id)
    assert final_task.status == "COMPLETE"
```

## Parametrized Tests

Test multiple scenarios with one test function:

```python
@pytest.mark.parametrize("role,priority,expected", [
    ("Engineer", "HIGH", "ENG-H"),
    ("Architect", "MEDIUM", "ARC-M"),
    ("Tester", "LOW", "TST-L"),
])
def test_task_id_prefix(role, priority, expected):
    """Test task ID prefix generation for different roles"""
    result = generate_task_prefix(role, priority)
    assert result == expected
```

## Testing CLI Commands

Use Typer's testing utilities:

```python
from typer.testing import CliRunner
from site_nine.cli.main import app

runner = CliRunner()

def test_task_create_command():
    """Test task create CLI command"""
    result = runner.invoke(app, [
        "task", "create",
        "--title", "Test task",
        "--role", "Engineer",
        "--priority", "HIGH"
    ])
    
    assert result.exit_code == 0
    assert "ENG-H-" in result.stdout
```

## Edge Cases and Error Handling

Always test edge cases:

```python
def test_create_task_with_empty_title():
    """Test that empty title raises ValueError"""
    with pytest.raises(ValueError, match="Title cannot be empty"):
        create_task(title="", role="Engineer")

def test_create_task_with_invalid_role():
    """Test that invalid role raises ValueError"""
    with pytest.raises(ValueError, match="Invalid role"):
        create_task(title="Test", role="InvalidRole")

def test_get_task_with_nonexistent_id():
    """Test that nonexistent task returns None"""
    result = get_task(task_id="FAKE-H-9999")
    assert result is None
```

## Test Coverage

### Checking Coverage

```bash
# Run tests with coverage report
uv run pytest --cov=src/site_nine --cov-report=term-missing

# Generate HTML coverage report
uv run pytest --cov=src/site_nine --cov-report=html
open htmlcov/index.html
```

### Coverage Goals

- **Overall:** >85% coverage
- **Core modules:** >90% coverage
- **CLI commands:** >80% coverage
- **Utility functions:** 100% coverage

### What to Cover

✅ **Do test:**
- Happy path scenarios
- Edge cases (empty, null, max values)
- Error conditions
- Boundary conditions
- Integration points

❌ **Don't need to test:**
- Third-party library code
- Simple getters/setters
- Auto-generated code
- Trivial one-liners

## Continuous Integration

Tests run automatically on:
- Every pull request
- Every commit to main
- Nightly builds

Make sure tests pass locally before pushing:

```bash
make qa
```

## Related Documentation

- **Commit Guidelines:** `.opencode/docs/guides/commit-guidelines.md` - Includes "run tests before commit"
- **Troubleshooting Guide:** `.opencode/docs/guides/troubleshooting.md` - Debugging test failures
- **Agent Guide:** `.opencode/docs/guides/agents.md` - Testing workflow for agents
