# Development Guide for OpenCode Agents

## Overview

This guide is for AI agents (like Claude, ChatGPT, Copilot, etc.) working on **projects enhanced with site-nine** through OpenCode.

**Important:** This .opencode configuration is for working on projects that **USE** site-nine, not for developing site-nine itself. If you need to develop site-nine, see the site-nine repository's own .opencode configuration.

---

## Before You Start: Mission Initialization

### Understanding Sessions vs Missions

**OpenCode Session**: Your conversation with the Director in the OpenCode TUI (the chat interface)

**Mission**: A tracked unit of work within site-nine, registered in the database with a persona, role, and codename

**Key distinction**: One OpenCode session may contain multiple missions, or you may resume a previous mission in a new session.

### Mission Start Protocol

**Quick start:** The Director initiates missions using the `/summon` command, which loads the `session-start` skill.

**The skill handles:**
- Role selection (or uses role from `/summon <role>`)
- Persona selection (automatic or via `--persona` flag)
- Mission registration in database
- Task assignment (via `--task` or `--auto-assign` flags)
- Setting up the mission file

**Your responsibility:** Follow the session-start skill workflow. See `.opencode/skills/session-start/SKILL.md` for details.

### Required Reading Order

You MUST read these files IN ORDER before starting work:

1. This file (`.opencode/docs/guides/agents.md`) - Complete development guide (CRITICAL)
2. `.opencode/site-nine-dev/development/SITE_NINE_DEV.md` - Site-nine specific patterns (if exists)
3. `.opencode/docs/guides/commit-guidelines.md` - Commit format

Use the Read tool to read ALL files. Do NOT skip this step.

### Mission Tracking

Every mission creates a markdown file in `.opencode/work/missions/` with format:  
`YYYY-MM-DD.HH:MM:SS.role.persona.codename.md`

**Track in mission file:**
- Work performed
- Decisions made
- Files changed
- Time spent
- Tasks claimed/completed

**Use CLI commands:**
```bash
s9 mission start <persona> --role <Role> --task "objective"    # Start mission
s9 mission update <mission-id> --notes "progress update"       # Update mission
s9 mission pause <mission-id> --reason "break for lunch"       # Pause mission
s9 mission resume <mission-id>                                 # Resume mission  
s9 mission end <mission-id>                                    # End mission
```

---

## Task Management

### Task Database

Tasks are stored in SQLite database (`.opencode/data/project.db`)

### s9 CLI Commands

```bash
# Quick project overview
s9 dashboard                # Show current status, active work, and available tasks

# View available persona names
s9 persona suggest <Role>

# Start mission (auto-registers and tracks usage)
s9 mission start <name> --role <Role> --task "..."

# Manage missions
s9 mission pause <mission-id> [--reason "reason"]     # Pause active mission
s9 mission resume <mission-id>                        # Resume paused mission
s9 mission update <mission-id> [--task "..."] [--role NewRole]  # Update mission

# Manage tasks
s9 task next --role <Role>                    # Get smart task suggestions
s9 task search "<keyword>" --active-only      # Search for tasks
s9 task mine --agent-name <name>              # Show your claimed tasks
s9 task list --role <Role> --active-only
s9 task report --active-only                  # Generate task summary report
s9 task create --title "..." --objective "..." --role <Role> --priority <PRIORITY>
s9 task claim <TASK_ID> --agent-name <name> --agent-id <ID>
s9 task update <TASK_ID> --notes "..." --actual-hours X.X
s9 task close <TASK_ID> --status COMPLETE

# End mission
s9 mission end <mission-id>
```

**Documentation:**
- **`.opencode/data/README.md`** - Complete reference (schema, commands, workflows)
- **`.opencode/data/project.db`** - SQLite database (personas, tasks, missions)

---

## Development Workflow

### 13-Step Development Process

1. Read required files (see Required Reading Order section above)
2. Follow MISSION START PROTOCOL (via `/summon` command - loads session-start skill)
3. Find work: `s9 task list --status TODO --role [YourRole]` (or use `--auto-assign` flag)
4. Claim task: `s9 task claim TASK_ID` (auto-claims if using `--task` or `--auto-assign`)
5. Review `.opencode/docs/guides/agents.md` patterns before implementing
6. Do the work assigned to your role
7. Update task: `s9 task update TASK_ID --status UNDERWAY --notes 'Progress update'`
8. Update mission file with progress in Work Log section
9. Run tests and quality checks before committing
10. Commit with format: `type(scope): description [Persona: Name - Role]` or `[Mission: codename]`
11. Commit incrementally (not one large commit!)
12. Close task: `s9 task close TASK_ID --notes 'Summary'`
13. At mission end: Use `/handoff` skill or load `session-end` skill to properly close mission

### Commit Guidelines

**Format:**
```bash
git commit -m "feat(database): add connection pooling [Persona: Azazel - Engineer]"
git commit -m "docs(readme): update setup guide [Persona: Seraphina - Documentarian]"
```

**Note**: Include the persona name in the commit message attribution.

**Common types**: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `perf:`, `style:`, `ci:`

**Workflow**:
1. Make changes
2. Update task artifact in `.opencode/work/tasks/TASK_ID.md`
3. Run `make qa`
4. Commit with conventional format
5. Repeat for next unit of work

**See**: `.opencode/docs/guides/commit-guidelines.md` for complete reference and examples.

### Task Artifact Updates

**Document your work in task artifacts as you go!**

Task artifacts are located in `.opencode/work/tasks/{TASK_ID}.md`

**What to update during work:**
- **Implementation Steps** - Chronological log of what you did
- **Files Changed** - List of files modified with descriptions
- **Notes** - Important observations or decisions
- **Testing Performed** - Tests run and results

**When completing a task:**
- **Solutions Implemented** - High-level summary
- **Verification Results** - How acceptance criteria were met
- **Key Learnings** - Insights for future work
- **Git Commits** - List of commit SHAs

**Generate changelog from tasks:**
```bash
s9 changelog --since 2026-01-29
```

---

## Development Commands

These are examples of common project commands. Your project may have different commands - check your project's README or Makefile.

```bash
# site-nine CLI (available in all projects using site-nine)
s9 dashboard                 # Show project status
s9 task list                 # List available tasks
s9 mission start <persona>   # Start a mission
s9 changelog                 # Generate changelog

# Project-specific commands (examples - check your project)
make test                    # Run tests
make lint                    # Lint code
make format                  # Format code
make help                    # Show available commands
```

---

## Agent Roles System

For detailed role documentation, see `.opencode/docs/roles/README.md` and individual role files.

**Available Roles:**

### Administrator
**Primary interface and coordinator**
- Understands project holistically
- Delegates to specialized agents
- Coordinates multi-step tasks
- Default agent for general development

**Use for:** Starting new features, complex tasks, planning, coordination

### Architect
**Design and planning specialist**
- Creates technical designs
- Makes architecture decisions
- Plans feature implementations
- Documents design rationale

**Use for:** Designing new features, refactoring plans, architecture decisions

### Engineer
**Implementation specialist**
- Writes code according to designs
- Implements features
- Fixes bugs
- Creates tests (unit and integration)

**Use for:** Implementing features, fixing bugs, writing tests, refactoring

### Tester
**Quality assurance specialist**
- Runs tests and validates features
- Manual testing workflows
- Reports issues found
- Does NOT write tests (Engineer does that)

**Use for:** Running test suites, manual validation, regression testing

### Documentarian
**Documentation specialist**
- Writes and updates documentation
- Maintains consistency across docs
- Creates examples and guides
- Updates docstrings

**Use for:** Writing/updating docs, README updates, API documentation

### Designer
**User experience specialist**
- Designs CLI output formats
- Plans user workflows
- Creates mockups and specifications
- Focuses on usability and clarity

**Use for:** CLI output design, UX improvements, user flow planning

### Inspector
**Code review specialist**
- Reviews code for issues
- Checks consistency
- Finds bugs and code smells
- Suggests improvements

**Use for:** Code review, finding issues, quality checks, refactoring suggestions

### Operator
**Meta-development specialist**
- Maintains `.opencode/` infrastructure
- Updates agent definitions
- Manages development workflows
- Improves development tooling

**Use for:** Updating agent configs, improving dev workflows, tooling maintenance

---

## Tips for Success

### 1. Mission initialization via `/summon`

Each development mission begins when the Director invokes `/summon`, which loads the `session-start` skill. The skill handles role and persona selection automatically. This creates consistency and accountability:

- Agent uses the same persona throughout the mission
- Commits include the persona: `[Persona: Azazel - Engineer]` or `[Mission: codename]`
- Task artifacts document all work done
- Mission file tracks all work performed
- Mission is registered in the database

### 2. Start with the Administrator (or Pick Your Role)

If you're starting a new task and aren't sure which role is best, choose Administrator. It will coordinate and delegate. If you know what you need, pick the specific role.

### 3. Be Specific About Goals

✅ Good: "Add rate limiting to database queries with 50/minute limit"  
❌ Less good: "Make it faster"

### 4. Agents Read agents.md

The agents are configured to read `.opencode/docs/guides/agents.md` for patterns. Keep it updated with lessons learned.

### 5. Engineer Writes Tests, Tester Runs Them

- **Engineer**: Implements features AND writes tests
- **Tester**: Runs tests, manual testing, validation

This distinction ensures tests are written as part of implementation.

### 6. Approve Designs Before Implementation

When Architect proposes a design, review and approve it before Engineer starts. This saves time.

### 7. Inspector for Reviews, Not Just Bugs

Use Inspector for:
- Security audits
- Consistency checks
- Finding missing documentation
- Pattern validation

---

## Code Patterns

### Logging Patterns

**Standard:** site-nine uses **structured logging** with `loguru` for consistent log aggregation and monitoring.

**✅ Correct Pattern (Structured Logging):**
```python
# Good - Structured logging with event name + key-value parameters
logger.info("cli_command_executed", command="init", project_path=path)
logger.info("database_initialized", task_count=task_count, agent_count=agent_count)
logger.info("template_rendered", template_name=template_name, output_file=output_file)
logger.error("template_rendering_failed", template_name=template_name, error=str(e))
```

**❌ Incorrect Pattern (F-string Logging):**
```python
# Bad - F-string formatting (harder to query in log aggregation systems)
logger.info(f"site-nine starting (version={__version__})")
logger.info(f"Database initialized with {task_count} tasks")
logger.info(f"Rendering template: {template_name}")
```

**Why Structured Logging?**
- **Queryable:** Log aggregation systems (Datadog, Splunk, CloudWatch) can filter by specific fields
- **Consistent:** Event names follow `snake_case` convention
- **Type-safe:** Values are properly serialized (no f-string escaping issues)
- **Parseable:** Structured data is easier to analyze programmatically

**Event Naming Convention:**
- Use `snake_case` for event names: `cli_command_executed`, `database_initialized`
- Use action verbs: `rendering_template`, `creating_task`, `validating_input`
- Be specific but concise: `task_claimed_by_agent` (not just `claimed`)

**Examples by Log Level:**

```python
# INFO - Normal operations
logger.info("task_created", task_id=task.id, role=task.role, priority=task.priority)
logger.info("agent_session_started", agent_name=agent.name, role=agent.role)

# WARNING - Non-critical issues
logger.warning("database_file_not_found", db_path=db_path, creating_new=True)
logger.warning("template_variable_missing", template_name=template_name, variable=var_name)

# ERROR - Failures that need attention
logger.error("database_migration_failed", migration_version=version, error=str(e))
logger.error("invalid_task_id_format", task_id=task_id, expected_format="ROLE-PRIORITY-NUMBER")

# DEBUG - Detailed diagnostics
logger.debug("template_context_prepared", template_name=template_name, context_keys=list(context.keys()))
logger.debug("sql_query_executed", query=query[:100], row_count=len(results))
```

### CLI Commands (Typer)

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

### Database Operations (SQLAlchemy)

```python
from site_nine.core.database import Database

db = Database()
with db.get_session() as session:
    result = session.execute(
        "SELECT * FROM tasks WHERE status = :status",
        {"status": "TODO"}
    )
```

### Template Rendering (Jinja2)

```python
from site_nine.core.renderer import TemplateRenderer

renderer = TemplateRenderer()
output = renderer.render("template.j2", {
    "project_name": "my-project",
    "features": ["task_management"]
})
```

---

## Common Workflows

### Adding a Feature

1. Administrator → @architect (design)
2. Administrator → @designer (UI/UX specs, if user-facing)
3. You approve
4. Administrator → @builder (implement + tests)
5. Administrator → @tester (validate)
6. Administrator → @documentarian (docs)
7. Administrator → @inspector (review)

### Fixing a Bug

1. Administrator → @tester (reproduce)
2. Administrator → @builder (fix + test)
3. Administrator → @tester (verify)

**See**: `.opencode/docs/procedures/WORKFLOWS.md` for detailed workflows, parallel work patterns, and more examples.

---

## Troubleshooting

**s9 command not found or ModuleNotFoundError?**
```bash
# Reinstall with uv tool
uv tool uninstall site-nine
uv tool install --editable .
s9 --help  # Verify it works
```
**Why this happens**: Stale installations from when the module was named `s9` instead of `site_nine`.

**Alternative**: Use `uv run s9` to run from project virtual environment instead of global tool.

**Tests failing?**
```bash
make docker/up          # Start services first
make qa/test-integration
```

**Which agent to use?** → Choose a role based on your task

**Command not working?** → Run `make help`

**Database connection error?** → Check `.env` configuration

**See**: `.opencode/docs/guides/troubleshooting.md` for comprehensive troubleshooting guide.

---

## Important Files

### For Development
- **`.opencode/docs/guides/agents.md`** - Development patterns (READ THIS FIRST!)
- **`.opencode/docs/guides/markdown-style.md`** - Markdown formatting standards (REQUIRED for all markdown files)
- **`s9`** - Unified project management CLI (tasks, missions, personas)
- **`.opencode/data/README.md`** - Complete s9 system reference
- **`.opencode/docs/guides/commit-guidelines.md`** - Commit format reference
- **`.opencode/docs/procedures/TASK_WORKFLOW.md`** - Task-first documentation workflow
- **`Makefile`** - Development commands (if your project uses make)
- **`.env.example`** - Configuration template (if your project needs it)

### For Reference
- **`.opencode/docs/roles/README.md`** - Agent role definitions
- **`.opencode/docs/procedures/WORKFLOWS.md`** - Common development workflows
- **`.opencode/docs/guides/design-system.md`** - Design system documentation (if created)

---

## Project Structure

```
your-project/
├── src/                     # Your application source code
├── tests/                   # Your application tests
├── .opencode/               # site-nine configuration directory
│   ├── docs/                # Static instructions
│   │   ├── roles/           # Agent role definitions
│   │   ├── commands/        # Slash command instructions
│   │   ├── guides/          # Development patterns
│   │   ├── procedures/      # Operational how-tos
│   │   └── skills/          # Reusable skill workflows
│   ├── work/                # Tracking documents
│   │   ├── missions/        # Mission tracking files
│   │   ├── tasks/           # Task artifacts
│   │   └── planning/        # Strategic planning docs
│   ├── data/                # Data storage
│   │   └── project.db       # SQLite database
│   └── scripts/             # Utility scripts (optional)
├── .env.example             # Configuration template (if your project needs it)
├── Makefile                 # Development tasks (if your project uses make)
└── pyproject.toml           # Python project config (or package.json, etc.)
```

**Note:** The `.opencode/` directory structure is created by `s9 init` and is the same for all projects using site-nine.

---

## Questions?

- **Development patterns**: See `.opencode/docs/guides/agents.md` (this file)
- **Commands**: Run `make help` (if your project uses make) or `s9 --help`
- **Commit format**: See `.opencode/docs/guides/commit-guidelines.md`
- **Task workflow**: See `.opencode/docs/procedures/TASK_WORKFLOW.md`
- **Change history**: Run `s9 changelog`
- **Workflows**: See `.opencode/docs/procedures/WORKFLOWS.md`
- **Troubleshooting**: See `.opencode/docs/guides/troubleshooting.md` (if exists)

---

**Remember**: This `.opencode/` configuration is for working on **projects that use site-nine** (projects enhanced with the framework), not for developing site-nine itself (building the site-nine codebase).

Happy building! 🚀
