# Agent Roles for site-nine Development

This directory contains agent role definitions for developing site-nine itself.

## Available Roles

### Administrator
**Primary interface and coordinator**
- Understands project holistically
- Delegates to specialized agents
- Coordinates multi-step tasks
- Default agent for general development

**Use for:** Starting new features, complex tasks, planning, coordination

---

### Architect
**Design and planning specialist**
- Creates technical designs
- Makes architecture decisions
- Plans feature implementations
- Documents design rationale

**Use for:** Designing new features, refactoring plans, architecture decisions

---

### Builder
**Implementation specialist**
- Writes code according to designs
- Implements features
- Fixes bugs
- Creates tests (unit and integration)

**Use for:** Implementing features, fixing bugs, writing tests, refactoring

---

### Tester
**Quality assurance specialist**
- Runs tests and validates features
- Manual testing workflows
- Reports issues found
- Does NOT write tests (Builder does that)

**Use for:** Running test suites, manual validation, regression testing

---

### Documentarian
**Documentation specialist**
- Writes and updates documentation
- Maintains consistency across docs
- Creates examples and guides
- Updates docstrings

**Use for:** Writing/updating docs, README updates, API documentation

---

### Designer
**User experience specialist**
- Designs CLI output formats
- Plans user workflows
- Creates mockups and specifications
- Focuses on usability and clarity

**Use for:** CLI output design, UX improvements, user flow planning

---

### Inspector
**Code review specialist**
- Reviews code for issues
- Checks consistency
- Finds bugs and code smells
- Suggests improvements

**Use for:** Code review, finding issues, quality checks, refactoring suggestions

---

### Operator
**Meta-development specialist**
- Maintains `.opencode/` infrastructure
- Updates agent definitions
- Manages development workflows
- Improves development tooling

**Use for:** Updating agent configs, improving dev workflows, tooling maintenance

---

## General Workflow for All Agents

### 1. Read Essential Documentation
Before starting work:
- `.opencode/README.md` - Project overview
- `.opencode/docs/guides/AGENTS.md` - Development patterns
- `.opencode/docs/guides/TASK_SIZING.md` - **How to size tasks (use t-shirt sizes, not time estimates)**
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
git commit -m "feat(cli): add task dependency commands [Agent: Builder - Azazel]"
git commit -m "docs(readme): update quickstart guide [Agent: Documentarian - Thoth]"
git commit -m "fix(database): handle missing task files [Agent: Builder - Azazel]"
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
# .opencode/work/tasks/BLD-H-0003.md

## Size
**L** (Large - significant feature with testing requirements)

## Implementation Steps
1. Added CLI command for task dependencies
2. Updated database schema
3. Added tests

## Files Changed
- src/s9/cli/task.py - Added add-dependency command
- src/s9/tasks/manager.py - Added dependency tracking
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
from s9.core.database import Database

db = Database()
with db.get_session() as session:
    result = session.execute(
        "SELECT * FROM tasks WHERE status = :status",
        {"status": "TODO"}
    )
```

**Template Rendering (Jinja2):**
```python
from s9.core.renderer import TemplateRenderer

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
src/s9/
├── cli/            # Typer commands
├── core/           # Core business logic
├── tasks/          # Task management
├── agents/         # Agent sessions
└── templates/      # Jinja2 templates
```

---

## Role-Specific Guidance

### For Architect
- Read `guides/architecture.md` for system design
- Read `guides/TASK_SIZING.md` for how to size tasks
- Document design decisions
- Create clear technical specifications
- Use t-shirt sizes (XS, S, M, L, XL, XXL) for effort estimates, not time
- Consider future extensibility

### For Builder
- Write tests alongside code (TDD preferred)
- Follow existing code patterns
- Add type hints to all functions
- Update docstrings

### For Tester
- Run full test suite: `make qa/test`
- Test edge cases manually
- Report findings clearly
- Suggest test coverage improvements

### For Documentarian
- User docs: `docs/source/` (Sphinx/Markdown)
- Internal docs: `.opencode/docs/` (this directory)
- Keep examples up-to-date
- Maintain consistent formatting

### For Designer
- Focus on CLI usability
- Use Rich for beautiful output
- Design clear error messages
- Consider color-blind friendly colors

### For Inspector
- Look for code smells
- Check for consistency issues
- Validate test coverage
- Suggest refactoring opportunities

### For Operator
- Update this documentation when processes change
- Improve development workflows
- Maintain tooling and scripts
- Keep procedures up-to-date

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
