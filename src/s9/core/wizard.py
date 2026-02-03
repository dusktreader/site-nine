"""Interactive configuration wizard"""

from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm, Prompt

from s9.core.config import HQueueConfig

console = Console()


def run_wizard() -> HQueueConfig:
    """Run interactive configuration wizard"""
    console.print("\n[bold cyan]site-nine Configuration Wizard[/bold cyan]\n")

    # Project info
    cwd_name = Path.cwd().name
    project_name = Prompt.ask("Project name", default=cwd_name)
    project_type = Prompt.ask("Project type", choices=["python", "typescript", "go", "rust", "other"], default="python")
    project_desc = Prompt.ask("Project description (optional)", default="")

    # Features
    console.print("\n[bold]Features[/bold]")
    pm_system = Confirm.ask("Include PM system (task management)?", default=True)
    session_tracking = Confirm.ask("Include session tracking?", default=True)
    commit_guidelines = Confirm.ask("Include commit guidelines?", default=True)

    # Agent roles
    console.print("\n[bold]Agent Roles[/bold]")
    console.print(
        "Default roles: Administrator, Architect, Builder, Tester, Documentarian, Designer, Inspector, Operator"
    )
    use_defaults = Confirm.ask("Use default agent roles?", default=True)

    config = HQueueConfig.default(project_name)
    config.project.type = project_type
    config.project.description = project_desc
    config.features.pm_system = pm_system
    config.features.session_tracking = session_tracking
    config.features.commit_guidelines = commit_guidelines

    if not use_defaults:
        # Allow customization (simplified for now)
        console.print("[yellow]Role customization not yet implemented - using defaults[/yellow]")

    console.print("\n[bold green]Configuration complete![/bold green]\n")
    return config
