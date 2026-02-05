# Troubleshooting Guide

Common issues and solutions for developing site-nine.

## Quick Diagnostics

When something goes wrong, start here:

```bash
# Check installation
s9 --version

# Verify dependencies
uv sync

# Run all quality checks
make qa

# Check git status
git status
```

## Tests Failing

### Symptoms

- `make qa/test` fails
- pytest shows test failures
- CI/CD pipeline fails on tests

### Diagnosis

```bash
# Run with verbose output to see details
uv run pytest -vv

# Run specific failing test
uv run pytest tests/cli/test_task.py::test_create_task -vv

# Run with full traceback
uv run pytest --tb=long

# Check test coverage
uv run pytest --cov=src/site_nine --cov-report=term-missing
```

### Solutions

**Formatting issues:**
```bash
# Format code automatically
make qa/format

# Check what changed
git diff

# Run tests again
make qa/test
```

**Linting issues:**
```bash
# Check linting errors
make qa/lint

# Fix auto-fixable issues
ruff check --fix src/ tests/

# Run tests again
make qa/test
```

**Import errors in tests:**
```bash
# Reinstall in development mode
uv sync

# Verify package is installed
uv run python -c "import site_nine; print(site_nine.__file__)"
```

**Database state issues:**
```bash
# Test database might be stale
rm -f tests/.test.db

# Re-run tests
make qa/test
```

**Fixture issues:**
```bash
# Check fixture definitions
grep -r "@pytest.fixture" tests/

# Verify fixture usage matches definition
uv run pytest --fixtures
```

### Common Test Failures

**`ModuleNotFoundError: No module named 'site_nine'`**
```bash
# Solution: Reinstall package
uv sync
uv run pytest
```

**`AssertionError` in tests**
- Read the test output carefully
- Check if the test expectations match actual behavior
- Verify test data is correct
- Check for flaky tests (timing issues)

**`fixture 'xyz' not found`**
```bash
# Check conftest.py files
find tests/ -name conftest.py

# Verify fixture is defined
grep "def xyz" tests/conftest.py
```

## Database Issues

### Symptoms

- CLI commands fail with database errors
- `project.db` is locked or corrupted
- Missing tables or columns
- Data is missing or incorrect

### Diagnosis

```bash
# Check database exists
ls -la .opencode/data/project.db

# Verify schema
sqlite3 .opencode/data/project.db ".schema"

# Check tables
sqlite3 .opencode/data/project.db ".tables"

# Query data
sqlite3 .opencode/data/project.db "SELECT * FROM tasks LIMIT 5;"
```

### Solutions

**Database doesn't exist:**
```bash
# Run s9 init to create database
s9 init

# Verify database was created
ls -la .opencode/data/project.db
```

**Database is locked:**
```bash
# Check for stuck processes
ps aux | grep s9

# Kill stuck processes
kill <PID>

# Try command again
s9 task list
```

**Schema is wrong (missing tables/columns):**
```bash
# Backup existing database
cp .opencode/data/project.db .opencode/data/project.db.backup

# Check schema file
cat src/site_nine/templates/schema.sql

# Reinitialize database (WARNING: loses data)
rm .opencode/data/project.db
s9 init

# Or: Create migration script for schema changes
```

**Database is corrupted:**
```bash
# Try to recover
sqlite3 .opencode/data/project.db ".recover"

# If recovery fails, restore from backup
cp .opencode/data/project.db.backup .opencode/data/project.db

# If no backup, reinitialize (loses data)
rm .opencode/data/project.db
s9 init
```

**Foreign key constraint errors:**
```bash
# Check if foreign keys are enabled
sqlite3 .opencode/data/project.db "PRAGMA foreign_keys;"

# Verify referenced data exists
sqlite3 .opencode/data/project.db "SELECT * FROM tasks WHERE id = 'ENG-H-0001';"
```

## CLI Not Working

### Symptoms

- `s9: command not found`
- `ModuleNotFoundError: No module named 's9'`
- CLI commands hang or crash
- Wrong version installed

### Diagnosis

```bash
# Check if s9 is installed
which s9

# Check version
s9 --version

# Check Python path
uv run python -c "import sys; print(sys.path)"

# Verify package structure
ls -la src/site_nine/
```

### Solutions

**`s9: command not found`**

```bash
# Option 1: Install as uv tool (recommended)
uv tool uninstall site-nine  # Remove old version first
uv tool install --editable .
s9 --version

# Option 2: Use uv run (doesn't install globally)
uv run s9 --help

# Option 3: Install with pip
pip install --editable .
s9 --version
```

**`ModuleNotFoundError: No module named 's9'`**

This happens when the package was renamed from `s9` to `site_nine`:

```bash
# Uninstall old version
uv tool uninstall s9
uv tool uninstall site-nine

# Reinstall with correct name
uv tool install --editable .

# Verify
s9 --version
```

**CLI hangs or crashes:**
```bash
# Check for infinite loops or deadlocks
ps aux | grep s9

# Run with debugging
uv run python -m pdb -m site_nine.cli.main task list

# Check logs
tail -f ~/.local/share/site-nine/logs/site-nine.log  # If logging is configured
```

**Wrong version installed:**
```bash
# Check installed version
s9 --version

# Check git branch
git branch

# Reinstall from current branch
uv tool uninstall site-nine
uv tool install --editable .
s9 --version
```

## Import Errors

### Symptoms

- `ModuleNotFoundError: No module named 'site_nine'`
- `ImportError: cannot import name 'X' from 'site_nine.Y'`
- Circular import errors

### Diagnosis

```bash
# Check Python path
uv run python -c "import sys; print(sys.path)"

# Try importing directly
uv run python -c "import site_nine; print(site_nine.__file__)"

# Check for __init__.py files
find src/site_nine -name __init__.py

# Verify package structure
tree src/site_nine/
```

### Solutions

**Module not found:**
```bash
# Reinstall in development mode
uv sync

# Verify installation
uv run python -c "import site_nine; print(site_nine.__version__)"
```

**Circular imports:**
```python
# Identify the cycle
uv run python -c "import site_nine.module_name"
# Look for the circular dependency in the traceback

# Solutions:
# 1. Move import inside function
# 2. Use TYPE_CHECKING for type hints
# 3. Restructure code to break dependency cycle
```

**Missing __init__.py:**
```bash
# Find directories without __init__.py
find src/site_nine -type d -exec test ! -e {}/__init__.py \; -print

# Add __init__.py to each directory
touch src/site_nine/submodule/__init__.py
```

## Dependency Issues

### Symptoms

- `uv sync` fails
- Package conflicts
- Missing dependencies
- Wrong Python version

### Diagnosis

```bash
# Check Python version
python --version
uv run python --version

# Check pyproject.toml
cat pyproject.toml | grep requires-python

# List installed packages
uv pip list

# Check for conflicts
uv pip check
```

### Solutions

**Wrong Python version:**
```bash
# Use uv to manage Python versions
uv python install 3.12

# Set Python version for project
uv python pin 3.12
```

**Dependency conflicts:**
```bash
# Update dependencies
uv lock --upgrade

# Reinstall all dependencies
uv sync --reinstall
```

**Missing dependencies:**
```bash
# Install all dependencies from lock file
uv sync

# Install additional dependency
uv add <package-name>
```

## Git Issues

### Symptoms

- Merge conflicts
- Detached HEAD state
- Uncommitted changes blocking operations
- Wrong branch

### Diagnosis

```bash
# Check status
git status

# Check branch
git branch

# Check remote
git remote -v

# Check log
git log --oneline -10
```

### Solutions

**Merge conflicts:**
```bash
# See conflicted files
git status

# Resolve conflicts manually, then:
git add <resolved-files>
git commit

# Or abort merge
git merge --abort
```

**Detached HEAD:**
```bash
# Create branch from detached HEAD
git checkout -b fix/detached-head

# Or go back to main
git checkout main
```

**Uncommitted changes:**
```bash
# Stash changes
git stash

# Do operation
git checkout other-branch

# Restore changes
git stash pop

# Or discard changes (WARNING: destructive)
git reset --hard HEAD
```

**Wrong branch:**
```bash
# Switch to correct branch
git checkout main

# Move uncommitted changes to new branch
git stash
git checkout -b feature/new-branch
git stash pop
```

## Performance Issues

### Symptoms

- Slow tests
- Slow CLI commands
- High memory usage
- Slow database queries

### Diagnosis

```bash
# Profile tests
uv run pytest --profile

# Profile CLI command
uv run python -m cProfile -s cumtime -m site_nine.cli.main task list

# Check database query performance
sqlite3 .opencode/data/project.db "EXPLAIN QUERY PLAN SELECT * FROM tasks WHERE status='TODO';"
```

### Solutions

**Slow tests:**
```bash
# Run tests in parallel
uv run pytest -n auto

# Identify slow tests
uv run pytest --durations=10

# Skip slow tests during development
uv run pytest -m "not slow"
```

**Slow database queries:**
```sql
-- Add indexes
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_role ON tasks(role);

-- Verify indexes exist
.indexes tasks
```

**High memory usage:**
```bash
# Profile memory
uv run python -m memory_profiler script.py

# Check for memory leaks
# Use objgraph or tracemalloc
```

## Integration Test Issues

### Symptoms

- Integration tests fail
- Docker containers not starting
- Services not accessible
- Timeouts

### Diagnosis

```bash
# Check Docker status
docker ps

# Check service logs
docker compose logs

# Check network
docker network ls
docker network inspect site-nine_default
```

### Solutions

**Docker not running:**
```bash
# Start Docker daemon
# (varies by OS)

# Verify Docker is running
docker ps
```

**Services not starting:**
```bash
# Restart services
docker compose down
docker compose up -d

# Check logs for errors
docker compose logs -f
```

**Port conflicts:**
```bash
# Check what's using the port
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis

# Kill conflicting process or change port in docker-compose.yml
```

**Network issues:**
```bash
# Recreate network
docker compose down
docker network prune
docker compose up -d
```

## Getting Help

### Before Asking for Help

1. ✅ Check this troubleshooting guide
2. ✅ Search existing issues on GitHub
3. ✅ Read error messages carefully
4. ✅ Try basic diagnostics above
5. ✅ Check recent changes (git log)

### When Asking for Help

Include:
- **Error message** (full traceback)
- **Command you ran** (exact command)
- **Expected behavior** (what should happen)
- **Actual behavior** (what actually happened)
- **Environment** (OS, Python version, s9 version)
- **Recent changes** (git log -5)

### Useful Debug Commands

```bash
# Environment info
uv run python --version
s9 --version
git branch
git log -3 --oneline

# Full system info
uv run python -c "import sys; print(sys.version)"
uv run python -c "import platform; print(platform.platform())"

# Package versions
uv pip list

# Git state
git status
git diff
```

## Related Documentation

- **Testing Guide:** `.opencode/docs/guides/testing.md` - Test patterns and debugging
- **Commit Guidelines:** `.opencode/docs/guides/commit-guidelines.md` - Git workflow
- **Architecture Guide:** `.opencode/docs/guides/architecture.md` - System overview
- **Code Review Guide:** `.opencode/docs/guides/code-review.md` - Review checklist and best practices
