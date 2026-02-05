# Development Procedures for site-nine

Quick command references for common development tasks.

> **Note:** For commit message guidelines, see `.opencode/docs/guides/commit-guidelines.md`  
> **Note:** For testing guidelines and patterns, see `.opencode/docs/guides/testing.md`  
> **Note:** For task management workflow, use the `task-management` skill  
> **Note:** For mission/session workflows, use the `session-start` and `session-end` skills

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
- [ ] Persona attribution in commits
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
| Start mission | `s9 mission start <name> --role X --task "..."` |
| View dashboard | `s9 dashboard` |
| Generate changelog | `s9 changelog --since YYYY-MM-DD` |

---

## Related Documentation

- **Architecture:** `.opencode/docs/guides/architecture.md`
- **Design Philosophy:** `.opencode/docs/guides/design-philosophy.md`
- **Agent Roles:** `.opencode/docs/roles/README.md`
- **Development Patterns:** `.opencode/docs/guides/AGENTS.md`
- **Project Overview:** `.opencode/README.md`
