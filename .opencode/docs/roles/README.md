# Agent Roles for site-nine Development

This directory contains documentation for the 8 specialized agent roles used in site-nine development.

## Role Overview

### [Administrator](./administrator.md)
Primary interface and coordinator. Delegates to specialized agents.

**Use for:** Starting new features, complex tasks, planning, coordination

### [Architect](./architect.md)
Design and planning specialist. Creates technical designs.

**Use for:** Designing new features, refactoring plans, architecture decisions

### [Engineer](./engineer.md)
Implementation specialist. Writes code and tests.

**Use for:** Implementing features, fixing bugs, writing tests, refactoring

### [Tester](./tester.md)
Quality assurance specialist. Runs tests, validates features.

**Use for:** Running test suites, manual validation, regression testing

### [Documentarian](./documentarian.md)
Documentation specialist. Writes and maintains docs.

**Use for:** Writing/updating docs, README updates, API documentation

### [Designer](./designer.md)
User experience specialist. Designs CLI output and workflows.

**Use for:** CLI output design, UX improvements, user flow planning

### [Inspector](./inspector.md)
Code review specialist. Reviews code, finds issues.

**Use for:** Code review, finding issues, quality checks, refactoring suggestions

### [Operator](./operator.md)
Meta-development specialist. Maintains `.opencode/` infrastructure.

**Use for:** Updating agent configs, improving dev workflows, tooling maintenance

---

## General Workflow for All Agents

### 1. Read Essential Documentation

Before starting work:
- `.opencode/README.md` - Project overview
- `.opencode/docs/guides/AGENTS.md` - Development patterns
- `.opencode/docs/guides/TASK_SIZING.md` - How to size tasks (use t-shirt sizes, not time estimates)
- `.opencode/docs/guides/architecture.md` - System design
- `.opencode/docs/procedures/COMMIT_GUIDELINES.md` - Commit format

### 2. Follow Development Standards

**Testing:**
```bash
# Always run before committing
uv sync                  # Install dependencies
make qa/format           # Format code
make qa/lint             # Lint code
make qa/test             # Run tests
```

**Commit Format:**
```bash
# Use Conventional Commits with agent attribution
git commit -m "feat(cli): add task dependency commands [Agent: Engineer - Azazel]"
git commit -m "docs(readme): update quickstart guide [Agent: Documentarian - Thoth]"
git commit -m "fix(database): handle missing task files [Agent: Engineer - Azazel]"
```

**Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `test:` - Tests
- `refactor:` - Code refactoring
- `chore:` - Maintenance

### 3. Update Task Artifacts

If working on a task, update the task file:
```markdown
# .opencode/work/tasks/ENG-H-0003.md

## Size
**L** (Large - significant feature with testing requirements)

## Implementation Steps
1. Added CLI command for task dependencies
2. Updated database schema
3. Added tests

## Files Changed
- src/site_nine/cli/task.py - Added add-dependency command
- src/site_nine/tasks/manager.py - Added dependency tracking
- tests/cli/test_task.py - Added tests

## Commits
- abc123: feat(cli): add task dependency command
- def456: test(cli): add dependency tests
```

### 4. Code Patterns

**CLI Commands (Typer):**
```python
import typer
from rich.console import Console

console = Console()

@app.command()
def my_command(
    option: str = typer.Option(..., help="Description")
) -> None:
    """Command description"""
    console.print("[green]Success![/green]")
```

**Database Operations (SQLAlchemy):**
```python
from site_nine.core.database import Database

db = Database()
with db.get_session() as session:
    result = session.execute(
        "SELECT * FROM tasks WHERE status = :status",
        {"status": "TODO"}
    )
```

**Template Rendering (Jinja2):**
```python
from site_nine.core.renderer import TemplateRenderer

renderer = TemplateRenderer()
output = renderer.render("template.j2", {
    "project_name": "my-project",
    "features": ["task_management"]
})
```

### 5. Tech Stack Reference

**Core Technologies:**
- **Python 3.12+** - Modern Python
- **Typer** - CLI framework
- **Rich** - Terminal formatting
- **SQLAlchemy** - Database ORM
- **Jinja2** - Template engine
- **pytest** - Testing framework
- **ruff** - Linting/formatting

**Project Structure:**
```
src/site_nine/
├── cli/            # Typer commands
├── core/           # Core business logic
├── tasks/          # Task management
├── agents/         # Agent sessions
└── templates/      # Jinja2 templates
```

---

## Common Pitfalls

### ❌ Don't Skip Tests
Always run `make qa/test` before committing.

### ❌ Don't Hardcode Paths
Use `Path` from pathlib, not string concatenation.

### ❌ Don't Forget Type Hints
All functions should have proper type annotations.

### ❌ Don't Mix Concerns
Keep CLI logic separate from business logic.

### ❌ Don't Write Generic Commit Messages
Use Conventional Commits with clear descriptions.

---

## Quick Reference

| Task | Command |
|------|---------|
| Install deps | `uv sync` |
| Format code | `make qa/format` |
| Lint code | `make qa/lint` |
| Run tests | `make qa/test` |
| Run CLI | `uv run s9 --help` |
| Check types | `make qa/types` |
| All QA checks | `make qa` |

---

## Getting Help

- **Project overview:** `.opencode/README.md`
- **Development patterns:** `.opencode/docs/guides/AGENTS.md`
- **Architecture:** `.opencode/docs/guides/architecture.md`
- **Commit format:** `.opencode/docs/procedures/COMMIT_GUIDELINES.md`
- **User docs:** `docs/source/`
- **CLI help:** `uv run s9 --help`
