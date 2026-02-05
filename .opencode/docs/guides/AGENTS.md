# Development Guide for OpenCode Agents

## Overview

This guide is for AI agents (like Claude, ChatGPT, Copilot, etc.) working on the **site-nine** project through OpenCode.

**Important:** This .opencode configuration is for **DEVELOPING** site-nine itself, not for using/operating it.

---

## Before You Start: Session Initialization

### Required Reading Order

You MUST read these files IN ORDER before responding:

1. This file (`.opencode/docs/guides/AGENTS.md`) - Complete development guide (CRITICAL)
2. `.opencode/site-nine-dev/development/SITE_NINE_DEV.md` - Site-nine specific patterns
3. `.opencode/docs/guides/commit-guidelines.md` - Commit format

Use the Read tool to read ALL files. Do NOT skip this step.

### Session Start Protocol

Sessions are initiated by the Director using the `/summon` command.

**How sessions start:**

1. **Director invokes:** `/summon` command (or `/summon <role>` to skip role selection)

2. Agent asks: **"Which role should I assume?"** (skipped if role provided)
   - Administrator, Architect, Engineer, Tester, Documentarian, Designer, Inspector, or Operator
   - **Pro tip:** Use `/summon operator` to start an Operator session immediately

3. Agent suggests or asks for a **persona name** (from any religion's mythology)
   - **Prefer unused names first** - use `s9 persona suggest <Role>` to get unused name suggestions
   - 142+ names available from various mythologies (Greek, Egyptian, Norse, Hindu, Celtic, Japanese, and more)
   - **Reusing names is OK** when good unused names are exhausted, but try fresh names first
   - If name used before, adds roman numeral: `-ii`, `-iii`, `-iv`, etc.

4. Agent introduces itself with **full name including suffix**: **"I'm [Name], your [Role] agent."**
   - ✅ If first use: "I'm Seraphina, your Designer agent."
   - ✅ If reused name: "I'm Seraphina-iii, your Designer agent." (includes `-iii` suffix)
   - ❌ Wrong: "I'm Seraphina, your Designer agent." (when name is Seraphina-iii)

5. Session file is created in `.opencode/work/sessions/` with format:  
   `YYYY-mm-dd.HH:MM:SS.role.name.task-summary.md`

6. Agent uses that name (with suffix if applicable) in all commits, changelog entries, and docs

**Example (Choosing an Unused Name - Preferred):**
```
User: /summon
Agent: Which role should I assume for this session?
User: Engineer
Agent: Let me suggest an unused name for Engineer role...
       
       I suggest "Belial" - a demon king from Hebrew tradition who taught humans metalworking.
       This name hasn't been used yet.
       Would you like to use this name or choose another?
User: That works
Agent: Great! I'm Belial, your Engineer agent. What would you like me to work on?
```

**Example (Direct Mode - Skip Role Selection):**
```
User: /summon operator
Agent: I suggest "Hemera" (Greek goddess of day). Would you like to use this name?
User: yes
Agent: Great! I'm Hemera, your Operator agent. What would you like me to work on?
```

**Available mythologies:**
- **Greek/Roman** - Zeus, Athena, Hephaestus, etc.
- **Egyptian** - Ra, Thoth, Anubis, etc.
- **Norse** - Odin, Thor, Freya, etc.
- **Hindu/Buddhist** - Brahma, Shiva, Kali, etc.
- **Celtic/Gaelic** - Brigid, Lugh, Morrigan, etc.
- **Japanese** - Amaterasu, Susanoo, Benzaiten, etc.
- **Mesopotamian** - Marduk, Ishtar, Enki, etc.
- **Aztec/Mayan/African** - Quetzalcoatl, Anansi, etc.

**Browse available names:**
```bash
s9 persona list --role <Role>        # See all names for a role
s9 persona list --unused-only        # See only unused names
s9 persona suggest <Role> --count 3  # Get 3 unused suggestions
```

---

## About This Project

**Project:** site-nine (s9) - Generic orchestration framework for AI agent workflows in software development

**Purpose:** This .opencode configuration is for DEVELOPING site-nine, not for operating/using it.

**Current Status:** See `.opencode/work/planning/PROJECT_STATUS.md` for current status and roadmap.

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
2. Follow SESSION START PROTOCOL (choose role, pick name, create session file)
3. Find work: `s9 task list --status TODO --role [YourRole]`
4. Claim task: `s9 task claim TASK_ID --agent [YourName]`
5. Review `.opencode/docs/guides/AGENTS.md` patterns before implementing
6. Do the work assigned to your role
7. Update task: `s9 task update TASK_ID --status UNDERWAY --notes 'Progress update'`
8. Update session file with progress in Work Log section
9. Run tests and quality checks before committing
10. Commit with format: `type(scope): description [Agent: Role - Name]`
11. Commit incrementally (not one large commit!)
12. Close task: `s9 task close TASK_ID --notes 'Summary'`
13. At session end: Update session file with end_time, status, outcomes, and files changed

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

```bash
# Development
make demo                    # Start docker services + open web demo

# Quality checks
make qa                      # Run all checks (test + lint + types)
make qa/test                 # Run unit tests
make qa/test-integration     # Run integration tests (needs docker)
make qa/format               # Format code
make qa/lint                 # Lint code

# Docker (advanced)
docker compose up -d         # Start services
docker compose down          # Stop services
docker compose logs -f       # View logs

# Help
make help                    # Show all available commands
```

---

## Key Principles

When working on site-nine:

1. **Safety First**: Database access is read-only only
2. **Human in the Loop**: Propose solutions, get approval
3. **Guided Access**: Provide context (schema docs, query templates)
4. **Testing Required**: All features need tests
5. **Security**: Query validation, no hardcoded credentials

---

## Technology Stack

- **Python 3.12+** with uv for package management
- **FastMCP** - Python framework
- **SQLAlchemy** - Database access (PostgreSQL, MySQL, SQLite)
- **DuckDB** - Knowledge base (embedded analytics)
- **pytest/pytest-bdd** - Testing
- **ruff** - Formatting and linting
- **basedpyright** - Type checking

---

## Architecture Overview

**Hybrid MCP Pattern**: site-nine acts as both:
- **MCP Server**: Exposes tools to AI agents
- **MCP Client**: Delegates to external MCPs (JIRA, GitHub, Confluence)

**Benefits**: Single configuration point for users, unified tool interface

---

## Current Project Status

**Completed** ✅:
- Phase 1: Foundation (MCP skeleton)
- Phase 2: External MCP Delegation (JIRA, GitHub, Confluence)
- Phase 3: Database Integration (guided access, query validation)
- Phase 4: Knowledge Base (DuckDB + S3 hybrid storage)
- Phase 5: Investigation Locks (prevent duplicate work)
- Phase 6: Write Queue (DuckDB concurrency)
- Phase 7: Rate Limiting (protect external APIs)
- Phase 8: Slack Bot (OpenCode HTTP integration)

**Current Focus** 🔨:
- Phase 9: Integration Testing & Validation

**Future Work** 📋 (Not Currently Planned):
- Production deployment and hardening
- Production security audit
- Production monitoring and alerting
- Production CI/CD pipeline
- Production launch activities

See `.opencode/work/planning/PROJECT_STATUS.md` for current project status and phase completion.

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

### 1. Every Mission Starts with Role Selection

Each development mission begins with the agent asking which role to assume and what persona to use. This creates consistency and accountability:

- Agent uses the same persona throughout the mission
- Commits include the persona: `[Persona: Azazel - Engineer]` or `[Persona: Seraphina - Designer]`
- Task artifacts document all work done
- Mission history tracks all work done

### 2. Start with the Administrator (or Pick Your Role)

If you're starting a new task and aren't sure which role is best, choose Administrator. It will coordinate and delegate. If you know what you need, pick the specific role.

### 3. Be Specific About Goals

✅ Good: "Add rate limiting to database queries with 50/minute limit"  
❌ Less good: "Make it faster"

### 4. Agents Read AGENTS.md

The agents are configured to read `.opencode/docs/guides/AGENTS.md` for patterns. Keep it updated with lessons learned.

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

**See**: `.opencode/docs/procedures/TROUBLESHOOTING.md` for comprehensive troubleshooting guide.

---

## Important Files

### For Development
- **`.opencode/docs/guides/AGENTS.md`** - Development patterns (READ THIS FIRST!)
- **`.opencode/site-nine-dev/development/SITE_NINE_DEV.md`** - Site-nine specific patterns
- **`.opencode/docs/MARKDOWN_STYLE_GUIDE.md`** - Markdown formatting standards (REQUIRED for all markdown files)
- **`s9`** - Unified project management CLI (tasks, missions, personas)
- **`.opencode/data/README.md`** - Complete s9 system reference
- **`.opencode/work/missions/README.md`** - Mission tracking format and guidelines
- **`.opencode/work/planning/build.md`** - Implementation phases
- **`.opencode/work/planning/PROJECT_STATUS.md`** - Current project status and progress (use this!)
- **`.opencode/docs/guides/commit-guidelines.md`** - Commit format reference
- **`.opencode/docs/procedures/TASK_WORKFLOW.md`** - Task-first documentation workflow
- **`Makefile`** - Development commands
- **`.env.example`** - Configuration template

### For Reference
- **`.opencode/docs/guides/architecture.md`** - Architecture overview
- **`.opencode/docs/guides/database.md`** - Database patterns
- **`.opencode/docs/guides/design-philosophy.md`** - Design philosophy
- **`.opencode/docs/guides/design-system.md`** - Design system documentation (if created)
- **`.opencode/design/*.md`** - Feature design documents

---

## Project Structure

```
site-nine/
├── src/
│   └── site_nine/           # Main package
│       ├── cli/             # CLI commands
│       ├── core/            # Core framework
│       └── templates/       # Project templates
├── tests/                   # Unit tests
├── .opencode/               # This directory
│   ├── docs/                # Static instructions
│   │   ├── roles/           # Agent role definitions
│   │   ├── commands/        # Slash command instructions
│   │   ├── guides/          # Development patterns
│   │   ├── procedures/      # Operational how-tos
│   │   └── skills/          # Reusable skill workflows
│   ├── work/                # Tracking documents
│   │   ├── sessions/        # Agent session logs
│   │   ├── tasks/           # Task artifacts
│   │   └── planning/        # Strategic planning docs
│   ├── data/                # Data storage
│   │   └── project.db       # SQLite database
│   ├── scripts/             # Utility scripts
│   └── README.md            # Minimal pointer file
├── .env.example             # Configuration template (if needed)
├── Makefile                 # Development tasks
└── pyproject.toml           # Project config
```

---

## Questions?

- **Development patterns**: See `.opencode/docs/guides/AGENTS.md` (this file)
- **Architecture**: See `.opencode/docs/guides/architecture.md`
- **Current status**: See `.opencode/work/planning/PROJECT_STATUS.md`
- **Session tracking**: See `.opencode/work/sessions/README.md`
- **Commands**: Run `make help`
- **Commit format**: See `.opencode/docs/guides/commit-guidelines.md`
- **Task workflow**: See `.opencode/docs/procedures/TASK_WORKFLOW.md`
- **Change history**: Run `s9 changelog`
- **Workflows**: See `.opencode/docs/procedures/WORKFLOWS.md`
- **Troubleshooting**: See `.opencode/docs/procedures/TROUBLESHOOTING.md`

---

**Remember**: This `.opencode/` configuration is for **developing** site-nine (building the codebase), not for using site-nine in your projects (end-user operation).

Happy building! 🚀
