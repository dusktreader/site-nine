# Guide for AI Agents Working on site-nine

This guide is for AI agents (like Claude, ChatGPT, Copilot, etc.) that are NOT using the OpenCode agent system.

**If you are an OpenCode agent:** This file is not for you. Follow instructions in `.opencode/opencode.json`.

---

## For Non-OpenCode Agents

Before starting work on site-nine, **thoroughly review the `.opencode/` directory**. It contains all the information you need:

### 📚 Essential Reading (In Order)

1. **`.opencode/README.md`**
   - Start here for project overview
   - Quick start guide
   - Key principles and technology stack

2. **`.opencode/work/planning/PROJECT_STATUS.md`**
   - Current project status and phase completion
   - What's complete, what's in progress, what's planned
   - Key metrics and milestones
   - Known blockers and risks

3. **`.opencode/planning/build.md`**
   - Complete implementation phases
   - Phase dependencies and order
   - Technical requirements for each phase

4. **`.opencode/guides/architecture.md`**
   - System architecture and design decisions
   - Hybrid MCP pattern (server + client)
   - Component interactions

5. **`.opencode/guides/database.md`**
   - Database access patterns (CRITICAL for security)
   - Query validation requirements
   - Guided vs. blind access strategy

6. **`.opencode/guides/design-philosophy.md`**
   - Core design principles
   - Trade-offs and rationale
   - Safety and security requirements

### 🔍 Additional Resources

**Procedures** (`.opencode/procedures/`):
- `COMMIT_GUIDELINES.md` - How to format commits
- `WORKFLOWS.md` - Development workflow patterns
- `TROUBLESHOOTING.md` - Common issues and solutions

**Design Documents** (`.opencode/design/`):
- `slack-bot.md` - Slack bot architecture
- `deployment.md` - Deployment strategy
- `concurrency.md` - Concurrency patterns

**Planning** (`.opencode/planning/`):
- `ideas.md` - Future enhancements and ideas

### ⚠️ Critical Requirements

Before writing any code, ensure you understand:

1. **Testing Requirements**
   - All features MUST have tests
   - Unit tests required for all CLI commands
   - See existing tests in `tests/` directory

2. **Template System**
   - All generated files use Jinja2 templates
   - Templates located in `src/s9/templates/`
   - Test template rendering thoroughly

3. **Database Schema**
   - SQLite database for tasks, agents, daemon names
   - Use SQLAlchemy models (see `src/s9/core/models.py`)
   - Run migrations carefully with Alembic

4. **CLI Design**
   - Use Typer for all commands
   - Follow existing command patterns
   - Provide helpful error messages
   - Use Rich for formatted output

### 📝 Documentation Updates

When you make changes:

1. Update task artifact (`.opencode/data/tasks/TASK_ID.md`) with implementation details
2. Update task status in database when completing tasks: `s9 task close TASK_ID`
3. Update `.opencode/work/planning/PROJECT_STATUS.md` when completing major milestones
4. Add patterns learned to this guide if valuable
5. Follow commit format from `.opencode/procedures/COMMIT_GUIDELINES.md` with `[Task: ID]` reference

### 🚀 Getting Started

1. **Read the essential documents above** (30-60 minutes of reading)
2. **Check current status** in `.opencode/work/planning/PROJECT_STATUS.md`
3. **Set up development environment**: `uv sync`
4. **Run tests** to verify setup: `make qa/test`
5. **Try the CLI**: `s9 --help`
6. **Start with a small task** to familiarize yourself with the codebase
7. **Ask questions** if anything is unclear

---

## Code Patterns & Conventions

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

**Migration Guide:**

When converting existing f-string logs to structured logging:

1. **Extract the event name** from the message
   - `f"Rendering template: {template_name}"` → `"rendering_template"`
   
2. **Move variables to parameters**
   - `f"Created task with {count} dependencies"` → `logger.info("task_created", dependency_count=count)`
   
3. **Use descriptive parameter names**
   - `task_id=`, `agent_name=`, `template_name=` (not just `id=`, `name=`, `template=`)

4. **Keep context together**
   - If the log message had multiple variables, include them all as parameters
   - `logger.info("session_started", agent_name=agent.name, role=agent.role, task_id=task.id)`

---

## Key Takeaways

- **Read `.opencode/` thoroughly before coding** - it has everything you need
- **Testing is critical** - all CLI commands need tests
- **Templates matter** - use Jinja2 for all generated files
- **Database schema** - understand SQLAlchemy models before making changes
- **Documentation is important** - update as you work

---

**Remember:** The `.opencode/` directory is your source of truth. When in doubt, refer to the documentation there.
