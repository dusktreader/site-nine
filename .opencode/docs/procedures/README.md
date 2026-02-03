# Development Procedures for site-nine

Quick reference guides for common development tasks.

---

## Commit Guidelines

### Format

```
type(scope): brief description [Agent: Role - Name]

Optional longer description explaining why (not just what).

- Key changes listed
- Files affected
```

### Types

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `test:` - Tests
- `refactor:` - Code refactoring
- `chore:` - Maintenance, dependencies
- `perf:` - Performance improvements
- `style:` - Code style/formatting
- `ci:` - CI/CD changes

### Scopes (site-nine specific)

- `cli` - CLI commands
- `core` - Core business logic
- `tasks` - Task management
- `agents` - Agent sessions
- `templates` - Template rendering
- `database` - Database operations
- `config` - Configuration
- `docs` - Documentation

### Examples

**Good commits:**
```bash
feat(cli): add task dependency command [Agent: Builder - Azazel]
fix(database): handle missing daemon names [Agent: Builder - Lucifer]
docs(readme): update quickstart guide [Agent: Documentarian - Thoth]
test(cli): add agent session tests [Agent: Builder - Azazel]
refactor(core): simplify template rendering [Agent: Builder - Mephistopheles]
```

**Bad commits:**
```bash
Updated stuff
Fix
wip
changes
```

### Workflow

1. Make changes
2. Run quality checks: `make qa`
3. Stage changes: `git add <files>`
4. Commit with proper format
5. Push when ready

---

## Testing Procedures

### Before Every Commit

```bash
# Run all quality checks
make qa

# Or run individually:
make qa/format    # Format code with ruff
make qa/lint      # Lint with ruff
make qa/test      # Run pytest
```

### Running Tests

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/cli/test_task.py

# Specific test
uv run pytest tests/cli/test_task.py::test_create_task

# With coverage
uv run pytest --cov=src/s9 --cov-report=term-missing

# Verbose output
uv run pytest -vv
```

### Writing Tests

**Test file location:**
```
src/s9/cli/task.py  →  tests/cli/test_task.py
src/s9/core/renderer.py  →  tests/core/test_renderer.py
```

**Test structure:**
```python
import pytest
from s9.cli.task import create_task

def test_create_task_success():
    """Test successful task creation"""
    # Arrange
    title = "Test task"
    role = "Builder"
    priority = "HIGH"
    
    # Act
    result = create_task(title=title, role=role, priority=priority)
    
    # Assert
    assert result.id.startswith("BLD-H-")
    assert result.title == title
```

---

## Task Management Workflow

### Creating Tasks

```bash
# Create a new task (auto-generates ID)
s9 task create \
  --title "Add CLI command for X" \
  --role Builder \
  --priority HIGH \
  --objective "Implement feature X with tests"

# Returns: BLD-H-0001
```

### Working on Tasks

```bash
# List available tasks
s9 task list --status TODO

# Claim a task
s9 task claim BLD-H-0001 --agent azazel

# Update progress
s9 task update BLD-H-0001 --status IN_PROGRESS

# Add notes (in task markdown file)
# Edit .opencode/work/tasks/BLD-H-0001.md

# Close task
s9 task close BLD-H-0001 --status COMPLETE
```

### Task Artifact Structure

Task files (`.opencode/work/tasks/TASK_ID.md`) should include:

```markdown
# Task: BLD-H-0001 - Add CLI command

## Objective
Implement feature X with full test coverage

## Implementation Steps
1. Added CLI command in src/s9/cli/task.py
2. Added tests in tests/cli/test_task.py
3. Updated documentation

## Files Changed
- src/s9/cli/task.py - New add_dependency command
- tests/cli/test_task.py - Added 5 test cases
- docs/source/reference.md - Documented new command

## Testing Performed
```bash
make qa/test  # All tests pass
uv run s9 task add-dependency --help  # Command works
```

## Commits
- abc123: feat(cli): add task dependency command
- def456: test(cli): add dependency tests
- ghi789: docs(cli): document add-dependency command

## Status
COMPLETE - Merged and deployed
```

---

## Agent Session Workflow

### Starting a Session

```bash
# Start agent session
s9 agent start azazel \
  --role Builder \
  --task "Implement task dependencies"

# Returns agent ID: 42
```

### During Session

- Update task artifacts as you work
- Commit frequently with proper format
- Run tests before committing

### Ending Session

```bash
# End session
s9 agent end 42 --status completed

# Or if interrupted
s9 agent end 42 --status aborted --reason "Need to switch tasks"
```

### Session Files

Sessions auto-create files in `.opencode/work/sessions/`:
```
2026-02-02.14:30:00.builder.azazel.implement-dependencies.md
```

Update these files with:
- Work log (what you did)
- Decisions made
- Issues encountered
- Next steps

---

## Code Review Checklist

Before submitting PR or merging:

**Code Quality:**
- [ ] Follows existing code patterns
- [ ] Has type hints on all functions
- [ ] Has docstrings on public APIs
- [ ] No commented-out code
- [ ] No debug print statements

**Testing:**
- [ ] All tests pass (`make qa/test`)
- [ ] New features have tests
- [ ] Edge cases covered
- [ ] Test coverage >85%

**Documentation:**
- [ ] User docs updated (if user-facing)
- [ ] Docstrings added/updated
- [ ] CHANGELOG entry (if applicable)
- [ ] README updated (if needed)

**Git:**
- [ ] Commits follow Conventional Commits
- [ ] Agent attribution in commits
- [ ] Commit messages are clear
- [ ] No merge commits (rebase preferred)

---

## Troubleshooting

### Tests Failing

```bash
# Run with verbose output
uv run pytest -vv

# Run specific failing test
uv run pytest tests/cli/test_task.py::test_create_task -vv

# Check if it's a formatting issue
make qa/format

# Check if it's a linting issue
make qa/lint
```

### Database Issues

```bash
# Check database exists
ls -la .opencode/data/project.db

# Verify schema
sqlite3 .opencode/data/project.db ".schema"

# Query data
sqlite3 .opencode/data/project.db "SELECT * FROM tasks;"
```

### CLI Not Working

```bash
# Reinstall dependencies
uv sync

# Verify installation
which s9
s9 --version

# Run from source
uv run s9 --help
```

### Import Errors

```bash
# Check Python path
uv run python -c "import sys; print(sys.path)"

# Verify package structure
ls -la src/s9/

# Reinstall in development mode
uv sync
```

---

## Common Development Tasks

### Adding a New CLI Command

1. Add command to appropriate CLI module (`src/s9/cli/`)
2. Add tests (`tests/cli/`)
3. Update reference docs (`docs/source/reference.md`)
4. Update usage examples if needed (`docs/source/usage.md`)
5. Run `make qa` to verify
6. Commit with `feat(cli):` type

### Adding a New Database Table

1. Update schema in `src/s9/core/database.py`
2. Create migration (if using Alembic)
3. Add tests for new table operations
4. Update architecture docs if significant
5. Commit with `feat(database):` type

### Updating Documentation

1. User docs: Edit files in `docs/source/`
2. Internal docs: Edit files in `.opencode/docs/`
3. Build docs locally (if Sphinx): `cd docs && make html`
4. Verify formatting and links
5. Commit with `docs():` type

### Fixing a Bug

1. Write failing test that reproduces bug
2. Fix the bug
3. Verify test now passes
4. Add regression test if needed
5. Commit with `fix():` type

---

## Quick Reference

| Task | Command |
|------|---------|
| Install deps | `uv sync` |
| Run all QA | `make qa` |
| Run tests | `make qa/test` |
| Format code | `make qa/format` |
| Lint code | `make qa/lint` |
| Run CLI | `uv run s9 <command>` |
| Create task | `s9 task create --title "..." --role X --priority Y` |
| Start session | `s9 agent start <name> --role X --task "..."` |
| View dashboard | `s9 dashboard` |
| Generate changelog | `s9 changelog --since YYYY-MM-DD` |

---

## Related Documentation

- **Architecture:** `.opencode/docs/guides/architecture.md`
- **Design Philosophy:** `.opencode/docs/guides/design-philosophy.md`
- **Agent Roles:** `.opencode/docs/agents/README.md`
- **Development Patterns:** `.opencode/docs/guides/AGENTS.md`
- **Project Overview:** `.opencode/README.md`
