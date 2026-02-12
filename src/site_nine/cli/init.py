"""Initialize .opencode structure"""

from pathlib import Path
from typing import Annotated

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from snick import conjoin
from typerdrive import handle_errors, terminal_message

from site_nine.core.models import ProjectConfig
from site_nine.exceptions import SiteNineError
from site_nine.init import PROJECT_TYPES, InitManager


def _prompt_for_project_info(default_name: str) -> ProjectConfig:
    """Prompt user for basic project information."""
    terminal_message("Welcome to site-nine", subject="Initialization")

    project_name = Prompt.ask("Project name", default=default_name)
    project_type = Prompt.ask("Project type", choices=PROJECT_TYPES, default="python")
    project_desc = Prompt.ask("Project description (optional)", default="")

    return ProjectConfig(name=project_name, type=project_type, description=project_desc)


@handle_errors("Failed to initialize project", handle_exc_class=SiteNineError)
def init_command(
    directory: Annotated[
        Path | None,
        typer.Option("--directory", "-D", help="Target directory to initialize (defaults to current directory)"),
    ] = None,
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite existing .opencode")] = False,
    name: Annotated[str | None, typer.Option("--name", "-n", help="Project name")] = None,
    type: Annotated[str | None, typer.Option("--type", "-t", help="Project type")] = None,
    description: Annotated[str, typer.Option("--description", "-d", help="Project description")] = "",
) -> None:
    """Initialize .opencode structure in a directory (typically used by: humans)"""
    target_dir = directory or Path.cwd()
    manager = InitManager(target_dir)

    manager.validate_target()
    was_forced = manager.check_existing(force)

    if was_forced:
        terminal_message(
            conjoin(
                f"Removing existing .opencode at {manager.opencode_dir}",
                "All existing contents will be deleted and recreated from scratch.",
            ),
            subject="Warning",
            subject_color="yellow",
        )

    if name and type:
        config = ProjectConfig(name=name, type=type, description=description)
    else:
        config = _prompt_for_project_info(manager.target_dir.name)

    manager.create_opencode_dir()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ) as progress:
        task = progress.add_task("Initializing database...", total=None)
        persona_count = manager.initialize_database()
        progress.update(task, description=f"Database initialized ({persona_count} personas)")

        task2 = progress.add_task("Copying static files...", total=None)
        static_count = manager.copy_static_files()
        progress.update(task2, description=f"Copied {static_count} static files")

        task3 = progress.add_task("Rendering templates...", total=None)
        template_count = manager.render_templates(config)
        progress.update(task3, description=f"Rendered {template_count} templates")

    manager.create_work_directories()

    next_step = "Next, run: s9 summon"
    if manager.target_dir != Path.cwd().resolve():
        next_step = f"Next, navigate to {manager.target_dir} and run: s9 summon"

    terminal_message(
        conjoin(
            f"Successfully initialized .opencode at {manager.opencode_dir}",
            f"  {static_count} static files, {template_count} rendered templates",
            "",
            next_step,
        ),
        subject="Success",
        subject_color="green",
    )
