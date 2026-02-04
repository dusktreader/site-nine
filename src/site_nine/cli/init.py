"""Initialize .opencode structure"""

from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from site_nine.core.config import SiteNineConfig
from site_nine.core.personas import load_personas
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
        site_nine_config = SiteNineConfig.from_yaml(config)
        console.print(f"[green]Loaded configuration from {config}[/green]")
    else:
        site_nine_config = run_wizard()

    # Create .opencode directory
    opencode_dir.mkdir(exist_ok=True)

    # Save configuration to .opencode/s9-config.yaml
    import yaml

    config_path = opencode_dir / "s9-config.yaml"
    with open(config_path, "w") as f:
        yaml.safe_dump(
            {
                "project": {
                    "name": site_nine_config.project.name,
                    "type": site_nine_config.project.type,
                    "description": site_nine_config.project.description,
                },
                "features": {
                    "pm_system": site_nine_config.features.pm_system,
                    "session_tracking": site_nine_config.features.session_tracking,
                    "commit_guidelines": site_nine_config.features.commit_guidelines,
                    "daemon_naming": site_nine_config.features.daemon_naming,
                },
                "customization": {
                    "personas_theme": site_nine_config.customization.personas_theme,
                    "variables": site_nine_config.customization.variables,
                },
            },
            f,
            default_flow_style=False,
            sort_keys=False,
        )
    console.print(f"[green]✓[/green] Saved configuration to {config_path}")

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

        # Populate personas
        task2 = progress.add_task("Populating personas...", total=None)
        populate_personas(db)
        progress.update(task2, description="✓ Personas populated")

        # Render templates
        task3 = progress.add_task("Rendering templates...", total=None)
        renderer = TemplateRenderer()
        context = site_nine_config.to_template_context()
        file_count = render_all_templates(renderer, opencode_dir, context)
        progress.update(task3, description=f"✓ Rendered {file_count} templates")

    console.print(f"\n[bold green]✓[/bold green] Successfully initialized .opencode at {opencode_dir}")
    console.print("\n[cyan]Next steps:[/cyan]")
    console.print("  1. Review .opencode/README.md")
    console.print("  2. Review configuration in .opencode/s9-config.yaml")
    console.print("  3. Customize agent roles in .opencode/docs/agents/")
    console.print("  4. Run: s9 dashboard")


def populate_personas(db: Database) -> None:
    """Populate personas from built-in list"""
    personas = load_personas()

    for persona_data in personas:
        db.execute_update(
            """
            INSERT INTO personas (name, role, mythology, description, mission_count, created_at)
            VALUES (:name, :role, :mythology, :description, 0, datetime('now'))
            """,
            persona_data,
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
        "base/docs/agents/engineer.md.jinja": "docs/agents/engineer.md",
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
        # Missions
        "base/work/missions/README.md.jinja": "work/missions/README.md",
        "base/work/missions/TEMPLATE.md.jinja": "work/missions/TEMPLATE.md",
        # Epics
        "base/work/epics/README.md.jinja": "work/epics/README.md",
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

    # Copy style guide from site-nine's .opencode/docs directory
    docs_src = PathLib(__file__).parent.parent.parent.parent / ".opencode" / "docs"
    docs_dest = output_dir / "docs"
    docs_dest.mkdir(exist_ok=True, parents=True)

    style_guide_src = docs_src / "MARKDOWN_STYLE_GUIDE.md"
    if style_guide_src.exists():
        try:
            (docs_dest / "MARKDOWN_STYLE_GUIDE.md").write_text(style_guide_src.read_text())
            count += 1
        except Exception as e:
            console.print(f"[yellow]Warning: Failed to copy MARKDOWN_STYLE_GUIDE.md: {e}[/yellow]")

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

    # Create empty directories for work/tasks, work/epics, scripts, etc.
    (output_dir / "work" / "tasks").mkdir(exist_ok=True, parents=True)
    (output_dir / "work" / "epics").mkdir(exist_ok=True, parents=True)
    (output_dir / "scripts").mkdir(exist_ok=True)

    return count
