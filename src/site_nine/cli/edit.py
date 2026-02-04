"""Edit bootstrapped configuration and documentation files"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from typerdrive import handle_errors

from site_nine.core.paths import get_opencode_dir

app = typer.Typer(help="Edit bootstrapped configuration and documentation files")
console = Console()


def _get_editor() -> str:
    """Get the system editor from environment variables"""
    return os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vim"


def _open_editor(file_path: Path) -> None:
    """Open a file in the system editor"""
    editor = _get_editor()

    try:
        # Use subprocess to open the editor
        subprocess.run([editor, str(file_path)], check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error: Failed to open editor: {e}[/red]")
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print(f"[red]Error: Editor '{editor}' not found[/red]")
        console.print("[cyan]💡 Set the EDITOR or VISUAL environment variable to your preferred editor[/cyan]")
        raise typer.Exit(1)


@app.command(name="agents")
@handle_errors("Failed to edit AGENTS.md")
def edit_agents() -> None:
    """Edit the AGENTS.md file with development patterns and guidelines (typically used by: humans)"""
    try:
        opencode_dir = get_opencode_dir()
    except FileNotFoundError:
        console.print("[red]Error: .opencode directory not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    agents_file = opencode_dir / "docs" / "guides" / "AGENTS.md"

    if not agents_file.exists():
        console.print(f"[red]Error: AGENTS.md not found at {agents_file}[/red]")
        console.print("[cyan]💡 This file should be created during 's9 init'[/cyan]")
        raise typer.Exit(1)

    console.print(f"[cyan]Opening AGENTS.md in {_get_editor()}...[/cyan]")
    _open_editor(agents_file)
    console.print("[green]✓[/green] Done editing AGENTS.md")


@app.command(name="commits")
@handle_errors("Failed to edit COMMIT_GUIDELINES.md")
def edit_commits() -> None:
    """Edit the COMMIT_GUIDELINES.md file with git commit conventions (typically used by: humans)"""
    try:
        opencode_dir = get_opencode_dir()
    except FileNotFoundError:
        console.print("[red]Error: .opencode directory not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    commits_file = opencode_dir / "docs" / "procedures" / "COMMIT_GUIDELINES.md"

    if not commits_file.exists():
        console.print(f"[red]Error: COMMIT_GUIDELINES.md not found at {commits_file}[/red]")
        console.print("[cyan]💡 This file should be created during 's9 init'[/cyan]")
        raise typer.Exit(1)

    console.print(f"[cyan]Opening COMMIT_GUIDELINES.md in {_get_editor()}...[/cyan]")
    _open_editor(commits_file)
    console.print("[green]✓[/green] Done editing COMMIT_GUIDELINES.md")


@app.command(name="workflows")
@handle_errors("Failed to edit WORKFLOWS.md")
def edit_workflows() -> None:
    """Edit the WORKFLOWS.md file with development workflows (typically used by: humans)"""
    try:
        opencode_dir = get_opencode_dir()
    except FileNotFoundError:
        console.print("[red]Error: .opencode directory not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    workflows_file = opencode_dir / "docs" / "procedures" / "WORKFLOWS.md"

    if not workflows_file.exists():
        console.print(f"[red]Error: WORKFLOWS.md not found at {workflows_file}[/red]")
        console.print("[cyan]💡 This file should be created during 's9 init'[/cyan]")
        raise typer.Exit(1)

    console.print(f"[cyan]Opening WORKFLOWS.md in {_get_editor()}...[/cyan]")
    _open_editor(workflows_file)
    console.print("[green]✓[/green] Done editing WORKFLOWS.md")


@app.command(name="troubleshooting")
@handle_errors("Failed to edit TROUBLESHOOTING.md")
def edit_troubleshooting() -> None:
    """Edit the TROUBLESHOOTING.md file (typically used by: humans)"""
    try:
        opencode_dir = get_opencode_dir()
    except FileNotFoundError:
        console.print("[red]Error: .opencode directory not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    troubleshooting_file = opencode_dir / "docs" / "procedures" / "TROUBLESHOOTING.md"

    if not troubleshooting_file.exists():
        console.print(f"[red]Error: TROUBLESHOOTING.md not found at {troubleshooting_file}[/red]")
        console.print("[cyan]💡 This file should be created during 's9 init'[/cyan]")
        raise typer.Exit(1)

    console.print(f"[cyan]Opening TROUBLESHOOTING.md in {_get_editor()}...[/cyan]")
    _open_editor(troubleshooting_file)
    console.print("[green]✓[/green] Done editing TROUBLESHOOTING.md")


@app.command(name="task-workflow")
@handle_errors("Failed to edit TASK_WORKFLOW.md")
def edit_task_workflow() -> None:
    """Edit the TASK_WORKFLOW.md file (typically used by: humans)"""
    try:
        opencode_dir = get_opencode_dir()
    except FileNotFoundError:
        console.print("[red]Error: .opencode directory not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    task_workflow_file = opencode_dir / "docs" / "procedures" / "TASK_WORKFLOW.md"

    if not task_workflow_file.exists():
        console.print(f"[red]Error: TASK_WORKFLOW.md not found at {task_workflow_file}[/red]")
        console.print("[cyan]💡 This file should be created during 's9 init'[/cyan]")
        raise typer.Exit(1)

    console.print(f"[cyan]Opening TASK_WORKFLOW.md in {_get_editor()}...[/cyan]")
    _open_editor(task_workflow_file)
    console.print("[green]✓[/green] Done editing TASK_WORKFLOW.md")


@app.command(name="project-status")
@handle_errors("Failed to edit PROJECT_STATUS.md")
def edit_project_status() -> None:
    """Edit the PROJECT_STATUS.md file with project goals and status (typically used by: humans)"""
    try:
        opencode_dir = get_opencode_dir()
    except FileNotFoundError:
        console.print("[red]Error: .opencode directory not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    project_status_file = opencode_dir / "work" / "planning" / "PROJECT_STATUS.md"

    if not project_status_file.exists():
        console.print(f"[red]Error: PROJECT_STATUS.md not found at {project_status_file}[/red]")
        console.print("[cyan]💡 This file should be created during 's9 init'[/cyan]")
        raise typer.Exit(1)

    console.print(f"[cyan]Opening PROJECT_STATUS.md in {_get_editor()}...[/cyan]")
    _open_editor(project_status_file)
    console.print("[green]✓[/green] Done editing PROJECT_STATUS.md")


@app.command(name="architecture")
@handle_errors("Failed to edit architecture.md")
def edit_architecture() -> None:
    """Edit the architecture.md file with system design documentation (typically used by: humans)"""
    try:
        opencode_dir = get_opencode_dir()
    except FileNotFoundError:
        console.print("[red]Error: .opencode directory not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    architecture_file = opencode_dir / "docs" / "guides" / "architecture.md"

    if not architecture_file.exists():
        console.print(f"[red]Error: architecture.md not found at {architecture_file}[/red]")
        console.print("[cyan]💡 This file should be created during 's9 init'[/cyan]")
        raise typer.Exit(1)

    console.print(f"[cyan]Opening architecture.md in {_get_editor()}...[/cyan]")
    _open_editor(architecture_file)
    console.print("[green]✓[/green] Done editing architecture.md")


@app.command(name="design-philosophy")
@handle_errors("Failed to edit design-philosophy.md")
def edit_design_philosophy() -> None:
    """Edit the design-philosophy.md file (typically used by: humans)"""
    try:
        opencode_dir = get_opencode_dir()
    except FileNotFoundError:
        console.print("[red]Error: .opencode directory not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    philosophy_file = opencode_dir / "docs" / "guides" / "design-philosophy.md"

    if not philosophy_file.exists():
        console.print(f"[red]Error: design-philosophy.md not found at {philosophy_file}[/red]")
        console.print("[cyan]💡 This file should be created during 's9 init'[/cyan]")
        raise typer.Exit(1)

    console.print(f"[cyan]Opening design-philosophy.md in {_get_editor()}...[/cyan]")
    _open_editor(philosophy_file)
    console.print("[green]✓[/green] Done editing design-philosophy.md")


@app.command(name="opencode-config")
@handle_errors("Failed to edit opencode.json")
def edit_opencode_config() -> None:
    """Edit the opencode.json configuration file (typically used by: humans)"""
    try:
        opencode_dir = get_opencode_dir()
    except FileNotFoundError:
        console.print("[red]Error: .opencode directory not found. Run 's9 init' first.[/red]")
        raise typer.Exit(1)

    config_file = opencode_dir / "opencode.json"

    if not config_file.exists():
        console.print(f"[red]Error: opencode.json not found at {config_file}[/red]")
        console.print("[cyan]💡 This file should be created during 's9 init'[/cyan]")
        raise typer.Exit(1)

    console.print(f"[cyan]Opening opencode.json in {_get_editor()}...[/cyan]")
    _open_editor(config_file)
    console.print("[green]✓[/green] Done editing opencode.json")
