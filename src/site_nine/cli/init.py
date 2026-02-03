"""Initialize .opencode structure"""

from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from site_nine.core.config import HQueueConfig
from site_nine.core.daemon_names import load_daemon_names
from site_nine.core.database import Database
from site_nine.core.templates import TemplateRenderer
from site_nine.core.wizard import run_wizard

console = Console()


def init_command(
    config: Path | None = typer.Option(None, "--config", "-c", help="Config file path"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing .opencode"),
) -> None:
    """Initialize .opencode structure in current directory"""

    opencode_dir = Path.cwd() / ".opencode"

    # Check if already exists
    if opencode_dir.exists() and not force:
        console.print(f"[red]Error:[/red] .opencode already exists at {opencode_dir}")
        console.print("Use --force to overwrite")
        raise typer.Exit(1)

    # Get configuration
    if config:
        hq_config = HQueueConfig.from_yaml(config)
        console.print(f"[green]Loaded configuration from {config}[/green]")
    else:
        hq_config = run_wizard()

    # Create .opencode directory
    opencode_dir.mkdir(exist_ok=True)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Initialize database
        task = progress.add_task("Initializing database...", total=None)
        db_path = opencode_dir / "data" / "project.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db = Database(db_path)
        db.initialize_schema()
        progress.update(task, description="✓ Database initialized")

        # Populate daemon names
        task2 = progress.add_task("Populating daemon names...", total=None)
        populate_daemon_names(db)
        progress.update(task2, description="✓ Daemon names populated")

        # Render templates
        task3 = progress.add_task("Rendering templates...", total=None)
        renderer = TemplateRenderer()
        context = hq_config.to_template_context()
        file_count = render_all_templates(renderer, opencode_dir, context)
        progress.update(task3, description=f"✓ Rendered {file_count} templates")

    console.print(f"\n[bold green]✓[/bold green] Successfully initialized .opencode at {opencode_dir}")
    console.print("\n[cyan]Next steps:[/cyan]")
    console.print("  1. Review .opencode/README.md")
    console.print("  2. Customize agent roles in .opencode/docs/agents/")
    console.print("  3. Run: s9 dashboard")


def populate_daemon_names(db: Database) -> None:
    """Populate daemon names from built-in list"""
    names = load_daemon_names()

    for name_data in names:
        db.execute_update(
            """
            INSERT INTO daemon_names (name, role, mythology, description, usage_count, created_at)
            VALUES (:name, :role, :mythology, :description, 0, datetime('now'))
            """,
            name_data,
        )


def render_all_templates(renderer: TemplateRenderer, output_dir: Path, context: dict) -> int:
    """Render all templates to output directory"""

    # Map template names to output paths
    template_mappings = {
        "base/project-README.md.jinja": "../README.md",  # Project root README
        "base/README.md.jinja": "README.md",  # .opencode internal README
        "base/opencode.json.jinja": "opencode.json",
        # Agents
        "base/docs/agents/administrator.md.jinja": "docs/agents/administrator.md",
        "base/docs/agents/architect.md.jinja": "docs/agents/architect.md",
        "base/docs/agents/builder.md.jinja": "docs/agents/builder.md",
        "base/docs/agents/tester.md.jinja": "docs/agents/tester.md",
        "base/docs/agents/documentarian.md.jinja": "docs/agents/documentarian.md",
        "base/docs/agents/designer.md.jinja": "docs/agents/designer.md",
        "base/docs/agents/inspector.md.jinja": "docs/agents/inspector.md",
        "base/docs/agents/operator.md.jinja": "docs/agents/operator.md",
        # Guides
        "base/docs/guides/AGENTS.md.jinja": "docs/guides/AGENTS.md",
        "base/docs/guides/architecture.md.jinja": "docs/guides/architecture.md",
        "base/docs/guides/design-philosophy.md.jinja": "docs/guides/design-philosophy.md",
        "base/docs/guides/README.md.jinja": "docs/guides/README.md",
        # Procedures
        "base/docs/procedures/COMMIT_GUIDELINES.md.jinja": "docs/procedures/COMMIT_GUIDELINES.md",
        "base/docs/procedures/WORKFLOWS.md.jinja": "docs/procedures/WORKFLOWS.md",
        "base/docs/procedures/TROUBLESHOOTING.md.jinja": "docs/procedures/TROUBLESHOOTING.md",
        "base/docs/procedures/TASK_WORKFLOW.md.jinja": "docs/procedures/TASK_WORKFLOW.md",
        "base/docs/procedures/README.md.jinja": "docs/procedures/README.md",
        # Planning
        "base/work/planning/PROJECT_STATUS.md.jinja": "work/planning/PROJECT_STATUS.md",
        # Commands
        "base/commands/README.md.jinja": "commands/README.md",
        # Sessions
        "base/work/sessions/README.md.jinja": "work/sessions/README.md",
        "base/work/sessions/TEMPLATE.md.jinja": "work/sessions/TEMPLATE.md",
    }

    count = 0
    for template_name, output_path in template_mappings.items():
        try:
            renderer.render_to_file(template_name, output_dir / output_path, context)
            count += 1
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to render {template_name}: {e}[/yellow]")

    # Copy non-templated command files (simple markdown files that don't need rendering)
    commands_dir = output_dir / "commands"
    commands_dir.mkdir(exist_ok=True, parents=True)

    simple_commands = [
        "summon.md",
        "dismiss.md",
        "handoff.md",
        "commit.md",
        "tasks.md",
        "claim-task.md",
        "close-task.md",
        "create-task.md",
        "update-task.md",
    ]

    from pathlib import Path as PathLib

    template_base = PathLib(__file__).parent.parent / "templates" / "base" / "commands"

    for cmd_file in simple_commands:
        src_file = template_base / cmd_file
        if src_file.exists():
            try:
                (commands_dir / cmd_file).write_text(src_file.read_text())
                count += 1
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to copy {cmd_file}: {e}[/yellow]")

    # Copy skill files directly from site-nine's .opencode directory
    # Skills should be exact copies, not templates
    skills_src = PathLib(__file__).parent.parent.parent.parent / ".opencode" / "skills"
    skills_dest = output_dir / "skills"

    if skills_src.exists():
        import shutil

        for skill_dir in skills_src.iterdir():
            if skill_dir.is_dir():
                dest_skill_dir = skills_dest / skill_dir.name
                try:
                    shutil.copytree(skill_dir, dest_skill_dir, dirs_exist_ok=True)
                    # Count files copied
                    count += sum(1 for _ in dest_skill_dir.rglob("*") if _.is_file())
                except Exception as e:
                    console.print(f"[yellow]Warning: Failed to copy skill {skill_dir.name}: {e}[/yellow]")
    else:
        console.print(f"[yellow]Warning: Skills source directory not found at {skills_src}[/yellow]")

    # Create empty directories for work/tasks, scripts, etc.
    (output_dir / "work" / "tasks").mkdir(exist_ok=True, parents=True)
    (output_dir / "scripts").mkdir(exist_ok=True)

    return count
