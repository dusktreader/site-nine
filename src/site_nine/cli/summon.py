"""Summon command to launch OpenCode with /summon slash command"""

import subprocess
import typer
from rich.console import Console

from site_nine.core.settings import get_default_model

console = Console()


def summon_command(
    role: str = typer.Argument(..., help="Agent role to summon (e.g., operator, architect)"),
    persona: str | None = typer.Option(None, "--persona", "-p", help="Specific persona name to use"),
    auto_assign: bool = typer.Option(False, "--auto-assign", "-a", help="Auto-assign top priority task for role"),
    task: str | None = typer.Option(None, "--task", "-t", help="Specific task ID to claim and start"),
    model: str | None = typer.Option(None, "--model", "-m", help="Model to use (provider/model format)"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Show command that would be run without executing"),
) -> None:
    """Launch OpenCode and automatically run /summon with specified role and flags (typically used by: humans)

    Examples:
        s9 summon operator
        s9 summon operator --persona atlas
        s9 summon operator --auto-assign
        s9 summon operator --task OPR-H-0065
        s9 summon operator --model github-copilot/gpt-5
    """
    # Validate flag conflicts
    if auto_assign and task:
        console.print("[red]❌ Error: Cannot use both --auto-assign and --task flags together.[/red]")
        console.print("\n- Use --auto-assign to claim the top priority task for the role")
        console.print("- Use --task TASK-ID to claim a specific task")
        console.print("\nPlease use one or the other.")
        raise typer.Exit(1)

    # Get model from config if not specified
    if model is None:
        model = get_default_model()

    # Build the /summon command
    summon_cmd = f"/summon {role}"

    if persona:
        summon_cmd += f" --persona {persona}"

    if auto_assign:
        summon_cmd += " --auto-assign"

    if task:
        summon_cmd += f" --task {task}"

    # Show what would be executed
    console.print(f"[cyan]🚀 Launching OpenCode TUI with:[/cyan] {summon_cmd}")

    if dry_run:
        console.print(f'[yellow]Dry run - would execute:[/yellow] opencode --model {model} --prompt "{summon_cmd}"')
        return

    # Launch OpenCode TUI with the /summon command
    try:
        subprocess.run(["opencode", "--model", model, "--prompt", summon_cmd], check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error launching OpenCode: {e}[/red]")
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print("[red]Error: 'opencode' command not found. Is OpenCode installed?[/red]")
        raise typer.Exit(1)
