# Coding Patterns and Conventions

This guide documents the coding patterns, conventions, and best practices for the site-nine codebase. Agents should follow these patterns when implementing features or making changes.


## Logging Patterns

### Standard: Structured Logging

Site-nine uses **structured logging** with `loguru` for consistent log aggregation and monitoring.

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


### Why Structured Logging?

- **Queryable:** Log aggregation systems (Datadog, Splunk, CloudWatch) can filter by specific fields
- **Consistent:** Event names follow `snake_case` convention
- **Type-safe:** Values are properly serialized (no f-string escaping issues)
- **Parseable:** Structured data is easier to analyze programmatically


### Event Naming Convention

- Use `snake_case` for event names: `cli_command_executed`, `database_initialized`
- Use action verbs: `rendering_template`, `creating_task`, `validating_input`
- Be specific but concise: `task_claimed_by_agent` (not just `claimed`)


### Examples by Log Level

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


## CLI Commands (Typer)

Site-nine uses [Typer](https://typer.tiangolo.com/) for CLI commands, enhanced with
[TyperDrive](https://github.com/dusktreader/typer-drive) for command organization, and
[Rich](https://rich.readthedocs.io/) for output formatting.

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


## Database Operations (SQLAlchemy)

Use the Database context manager for all database operations.

```python
from site_nine.core.database import Database

db = Database()
with db.get_session() as session:
    result = session.execute(
        "SELECT * FROM tasks WHERE status = :status",
        {"status": "TODO"}
    )
```


## Template Rendering (Jinja2)

Use the TemplateRenderer for rendering Jinja2 templates.

```python
from site_nine.core.renderer import TemplateRenderer

renderer = TemplateRenderer()
output = renderer.render("template.j2", {
    "project_name": "my-project",
    "features": ["task_management"]
})
```
