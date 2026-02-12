"""Summon command to launch OpenCode with /summon slash command"""

import subprocess
from typing import Annotated

import typer
from snick import conjoin
from typerdrive import attach_settings, terminal_message

from site_nine.cli.utils import abort, abort_unless
from site_nine.core.settings import SiteNineSettings


@attach_settings(SiteNineSettings)
def summon_command(
    ctx: typer.Context,
    settings: SiteNineSettings,
    role: Annotated[str, typer.Argument(help="Agent role to summon (e.g., operator, architect)")],
    persona: Annotated[str | None, typer.Option("--persona", "-p", help="Specific persona name to use")] = None,
    auto_assign: Annotated[
        bool, typer.Option("--auto-assign", "-a", help="Auto-assign top priority task for role")
    ] = False,
    task: Annotated[str | None, typer.Option("--task", "-t", help="Specific task ID to claim and start")] = None,
    model: Annotated[str | None, typer.Option("--model", "-m", help="Model to use (provider/model format)")] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-d", help="Show command that would be run without executing")
    ] = False,
) -> None:
    """Launch OpenCode and automatically run /summon with specified role and flags (typically used by: humans)

    Examples:
        s9 summon operator
        s9 summon operator --persona atlas
        s9 summon operator --auto-assign
        s9 summon operator --task OPR-H-0065
        s9 summon operator --model github-copilot/gpt-5
    """
    abort_unless(
        not (auto_assign and task),
        conjoin(
            "Cannot use both --auto-assign and --task flags together.",
            "",
            "- Use --auto-assign to claim the top priority task for the role",
            "- Use --task TASK-ID to claim a specific task",
            "",
            "Please use one or the other.",
        ),
    )

    # Get model from config if not specified
    if model is None:
        model = settings.default_model

    # Build the /summon command
    summon_cmd = f"/summon {role}"

    if persona:
        summon_cmd += f" --persona {persona}"

    if auto_assign:
        summon_cmd += " --auto-assign"

    if task:
        summon_cmd += f" --task {task}"

    # Show what would be executed
    terminal_message(f"Launching OpenCode TUI with: {summon_cmd}", subject="Summon")

    if dry_run:
        terminal_message(
            f'Dry run - would execute: opencode --model {model} --prompt "{summon_cmd}"',
            subject="Dry Run",
            subject_color="yellow",
        )
        return

    # Launch OpenCode TUI with the /summon command
    try:
        subprocess.run(["opencode", "--model", model, "--prompt", summon_cmd], check=True)
    except subprocess.CalledProcessError as e:
        abort(f"Error launching OpenCode: {e}")
    except FileNotFoundError:
        abort("'opencode' command not found. Is OpenCode installed?")
