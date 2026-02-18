# Troubleshooting Guide

Common issues and solutions.

## Quick Diagnostics

```bash
s9 --version        # Check installation
uv sync             # Verify dependencies
make qa             # Run quality checks
git status          # Check git status
```

## Tests Failing

**Diagnosis:**
```bash
uv run pytest -vv                                              # Verbose output
uv run pytest tests/cli/test_task.py::test_create_task -vv   # Specific test
uv run pytest --tb=long                                        # Full traceback
uv run pytest --cov=src/site_nine --cov-report=term-missing  # Coverage
```

**Solutions:**

Formatting issues:
```bash
make qa/format && make qa/test
```

Linting issues:
```bash
ruff check --fix src/ tests/ && make qa/test
```

Import errors:
```bash
uv sync
uv run python -c "import site_nine; print(site_nine.__file__)"
```

Database state:
```bash
rm -f tests/.test.db && make qa/test
```

Fixture issues:
```bash
uv run pytest --fixtures  # List all fixtures
```

**Common Failures:**

- `ModuleNotFoundError: No module named 'site_nine'` → `uv sync && uv run pytest`
- `AssertionError` → Read test output, verify expectations match behavior, check for flaky tests
- `fixture 'xyz' not found` → Check `tests/conftest.py` for fixture definition

## Database Issues

**Diagnosis:**
```bash
ls -la .opencode/data/project.db                            # Check existence
sqlite3 .opencode/data/project.db ".schema"                 # View schema
sqlite3 .opencode/data/project.db ".tables"                 # List tables
sqlite3 .opencode/data/project.db "SELECT * FROM tasks;"   # Query data
```

**Solutions:**

Database doesn't exist:
```bash
s9 init
ls -la .opencode/data/project.db
```

Database locked:
```bash
ps aux | grep s9    # Find stuck processes
kill <PID>          # Kill them
s9 task list        # Retry
```

Wrong schema:
```bash
cp .opencode/data/project.db .opencode/data/project.db.backup
rm .opencode/data/project.db && s9 init  # WARNING: loses data
# Or create migration script
```

Database corrupted:
```bash
sqlite3 .opencode/data/project.db ".recover"
# If fails: cp .opencode/data/project.db.backup .opencode/data/project.db
```

Foreign key errors:
```bash
sqlite3 .opencode/data/project.db "PRAGMA foreign_keys;"
sqlite3 .opencode/data/project.db "SELECT * FROM tasks WHERE id = 'ENG-H-0001';"
```

## CLI Not Working

**Diagnosis:**
```bash
which s9                                             # Check if installed
s9 --version                                         # Check version
uv run python -c "import sys; print(sys.path)"      # Check Python path
ls -la src/site_nine/                               # Verify structure
```

**Solutions:**

`s9: command not found`:
```bash
# Option 1: uv tool (recommended)
uv tool uninstall site-nine
uv tool install --editable .
s9 --version

# Option 2: uv run (no global install)
uv run s9 --help

# Option 3: pip
pip install --editable .
```

`ModuleNotFoundError: No module named 's9'` (old package name):
```bash
uv tool uninstall s9
uv tool uninstall site-nine
uv tool install --editable .
s9 --version
```

CLI hangs/crashes:
```bash
ps aux | grep s9                                         # Check for deadlocks
uv run python -m pdb -m site_nine.cli.main task list   # Debug
```

Wrong version:
```bash
s9 --version && git branch
uv tool uninstall site-nine
uv tool install --editable .
```

## Import Errors

**Diagnosis:**
```bash
uv run python -c "import sys; print(sys.path)"
uv run python -c "import site_nine; print(site_nine.__file__)"
find src/site_nine -name __init__.py
tree src/site_nine/
```

**Solutions:**

Module not found:
```bash
uv sync
uv run python -c "import site_nine; print(site_nine.__version__)"
```

Circular imports:
```python
# Identify cycle
uv run python -c "import site_nine.module_name"
# Check traceback for cycle

# Fix: Move import inside function, use TYPE_CHECKING, or restructure code
```

Missing `__init__.py`:
```bash
find src/site_nine -type d -exec test ! -e {}/__init__.py \; -print
touch src/site_nine/submodule/__init__.py
```

## Dependency Issues

**Diagnosis:**
```bash
python --version && uv run python --version
cat pyproject.toml | grep requires-python
uv pip list
uv pip check
```

**Solutions:**

Wrong Python version:
```bash
uv python install 3.12
uv python pin 3.12
```

Dependency conflicts:
```bash
uv lock --upgrade
uv sync --reinstall
```

Missing dependencies:
```bash
uv sync
uv add <package-name>
```

## Git Issues

**Diagnosis:**
```bash
git status
git branch
git remote -v
git log --oneline -10
```

**Solutions:**

Merge conflicts:
```bash
git status                       # See conflicts
# Resolve manually, then:
git add <resolved-files>
git commit
# Or: git merge --abort
```

Detached HEAD:
```bash
git checkout -b fix/detached-head  # Create branch
# Or: git checkout main            # Go back
```

Uncommitted changes:
```bash
git stash                          # Save changes
git checkout other-branch
git stash pop                      # Restore
# Or: git reset --hard HEAD        # WARNING: destroys changes
```

Wrong branch:
```bash
git checkout main
# Or move changes: git stash && git checkout -b feature/new && git stash pop
```

## Performance Issues

**Diagnosis:**
```bash
uv run pytest --profile                                                # Profile tests
uv run python -m cProfile -s cumtime -m site_nine.cli.main task list  # Profile CLI
sqlite3 .opencode/data/project.db "EXPLAIN QUERY PLAN SELECT * FROM tasks WHERE status='TODO';"
```

**Solutions:**

Slow tests:
```bash
uv run pytest -n auto              # Parallel
uv run pytest --durations=10       # Find slow tests
uv run pytest -m "not slow"        # Skip slow tests
```

Slow queries:
```sql
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_role ON tasks(role);
```

High memory:
```bash
uv run python -m memory_profiler script.py
```

## Integration Test Issues

**Diagnosis:**
```bash
docker ps
docker compose logs
docker network ls
docker network inspect site-nine_default
```

**Solutions:**

Docker not running:
```bash
docker ps  # Verify Docker daemon is up
```

Services not starting:
```bash
docker compose down
docker compose up -d
docker compose logs -f
```

Port conflicts:
```bash
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
# Kill process or change port in docker-compose.yml
```

Network issues:
```bash
docker compose down
docker network prune
docker compose up -d
```

## Getting Help

**Before asking:**
1. Check this guide
2. Search GitHub issues
3. Read error messages carefully
4. Try basic diagnostics
5. Check recent changes (`git log`)

**When asking, include:**
- Error message (full traceback)
- Command you ran
- Expected vs actual behavior
- Environment (OS, Python version, s9 version)
- Recent changes (`git log -5`)

**Debug commands:**
```bash
uv run python --version
s9 --version
git branch && git log -3 --oneline
uv pip list
git status && git diff
```

## Related Documentation

- **Testing Guide:** `.opencode/docs/guides/testing.md`
- **Commit Guidelines:** `.opencode/docs/guides/commit-guidelines.md`
- **Code Review Guide:** `.opencode/docs/guides/code-review.md`
