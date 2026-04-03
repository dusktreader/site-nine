# Python Usage Policy

> **⛔ AGENTS: ALWAYS USE `uv` FOR PYTHON ⛔**
>
> Never run `python`, `python3`, or `pytest` directly. Always prefix with `uv run`.
> Violating this causes hard-to-debug failures.

This policy applies to all agents working in the site-nine codebase. Follow it
without exception.

## The Rules

**Always use `uv run` for Python operations:**

```bash
# Run Python scripts
uv run python3 script.py

# Run tests
uv run pytest

# Run the site-nine CLI
uv run python -m site_nine <command>

# Sync dependencies before running anything
uv sync
```

**Never use bare Python commands:**

```bash
# WRONG: system Python, wrong version, missing dependencies
python script.py
python3 script.py
pytest
```

## Why

The site-nine codebase pins a specific Python version and manages dependencies
through `uv`. Running bare `python` or `python3` hits the system Python, which:

- May be a different version than `pyproject.toml` requires
- Does not have the project dependencies installed
- Produces `ModuleNotFoundError` failures with no obvious cause
- Behaves differently across machines and CI environments

`uv run` ensures every command runs in the correct virtual environment with the
correct Python version and all dependencies resolved.

## Before Running Commands

Run `uv sync` first if you haven't already, or if `pyproject.toml` has changed:

```bash
uv sync
```

This is particularly important after pulling changes or switching branches.

## Examples

### Running Tests

```bash
# All tests
uv run pytest

# Specific file
uv run pytest tests/test_tasks.py

# Specific test
uv run pytest tests/test_tasks.py::test_create_task

# With coverage
uv run pytest --cov=src/site_nine --cov-report=term-missing

# Verbose
uv run pytest -vv
```

### Running Scripts

```bash
# Python scripts
uv run python3 .opencode/tools/task_claim.py

# Inline one-liners
uv run python -c "import site_nine; print(site_nine.__version__)"

# Module invocation
uv run python -m site_nine task list
```

### Debugging

```bash
# Check Python version in uv environment
uv run python --version

# Check import paths
uv run python -c "import sys; print(sys.path)"

# Verify package installation
uv run python -c "import site_nine; print(site_nine.__file__)"
```

## Troubleshooting

**`ModuleNotFoundError: No module named 'site_nine'`**
Run `uv sync` and retry with `uv run`.

**`python: command not found` or wrong version**
You're on a system without Python installed, or using the wrong path. Use
`uv run python3` to let `uv` resolve the environment.

**Tests fail with import errors after pulling changes**
Run `uv sync` to pick up any new or changed dependencies, then rerun with
`uv run pytest`.

## See Also

- **Testing guide**: `.opencode/docs/guides/testing.md`
- **Troubleshooting guide**: `.opencode/docs/guides/troubleshooting.md`
- **uv documentation**: `https://docs.astral.sh/uv/`
