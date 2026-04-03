"""Summon command to launch OpenCode with possession-start instruction message"""

import os
import sqlite3
import subprocess
from pathlib import Path
from typing import Annotated

import typer
from snick import conjoin
from typerdrive import handle_errors, terminal_message

from site_nine.cli.utils import CLIError
from site_nine.core.paths import get_db_path, get_opencode_dir
from site_nine.core.settings import SiteNineSettings
from site_nine.exceptions import SiteNineError


def _build_instruction_message(
    role: str,
    daemon: str | None,
    auto_assign: bool,
    task: str | None,
    desk: bool,
) -> str:
    """Construct the instruction message to inject into OpenCode on summon.

    Message format:
    - role + daemon: "Your role is {role}, your daemon is {daemon}. Initialize your possession with the possession-start skill."
    - role only:     "Your role is {role}. Initialize your possession with the possession-start skill."
    - neither:       "Initialize your possession with the possession-start skill."

    Additional flag instructions are appended as needed.
    """
    if role and daemon:
        base = (
            f"Your role is {role}, your daemon is {daemon}. Initialize your possession with the possession-start skill."
        )
    elif role:
        base = f"Your role is {role}. Initialize your possession with the possession-start skill."
    else:
        base = "Initialize your possession with the possession-start skill."

    parts = [base]

    if auto_assign:
        parts.append("Automatically claim and start work on the top priority task for your role (--auto-assign).")
    if task:
        parts.append(f"Claim and start work on task {task} (--task {task}).")
    if desk:
        parts.append("Mode: desk (headless background worker).")

    return " ".join(parts)


@handle_errors("Failed to summon agent", handle_exc_class=SiteNineError)
def summon_command(
    role: Annotated[str, typer.Argument(help="Agent role to summon (e.g., operator, architect)")],
    daemon: Annotated[str | None, typer.Option("--daemon", "-d", help="Specific daemon name to use")] = None,
    auto_assign: Annotated[
        bool, typer.Option("--auto-assign", "-a", help="Auto-assign top priority task for role")
    ] = False,
    task: Annotated[str | None, typer.Option("--task", "-t", help="Specific task ID to claim and start")] = None,
    model: Annotated[str | None, typer.Option("--model", "-m", help="Model to use (provider/model format)")] = None,
    desk: Annotated[
        bool, typer.Option("--desk", help="Spawn a background (headless) desk-mode worker via opencode run")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show command that would be run without executing")
    ] = False,
) -> None:
    """Launch OpenCode with a possession-start instruction message (typically used by: humans)

    Constructs an instruction message and either execs into OpenCode (interactive)
    or spawns a background headless worker (--desk mode).

    Examples:
        s9 summon operator
        s9 summon operator --daemon atlas
        s9 summon operator --auto-assign
        s9 summon operator --task OPR-H-0065
        s9 summon operator --model github-copilot/gpt-5
        s9 summon engineer --desk
    """
    CLIError.require_condition(
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

    CLIError.require_condition(
        not (desk and (auto_assign or task)),
        conjoin(
            "Cannot use --task or --auto-assign with --desk mode.",
            "",
            "Desk mode workers initialize and wait for messages.",
            "To assign work to a desk worker, send a message via 's9 comms send'",
            "or use an orchestrator pattern after the worker is initialized.",
        ),
    )

    # Get model from config if not specified
    if model is None:
        settings = SiteNineSettings()
        model = settings.default_model or "github-copilot/claude-sonnet-4.6"

    # Build the instruction message
    instruction = _build_instruction_message(
        role=role,
        daemon=daemon,
        auto_assign=auto_assign,
        task=task,
        desk=desk,
    )

    if desk:
        # Desk mode: spawn persistent polling worker via desk_worker.py module
        # Get repo root (parent of .opencode directory)
        opencode_dir = get_opencode_dir()
        repo_root = opencode_dir.parent
        desk_worker_script = repo_root / "src" / "site_nine" / "workers" / "desk_worker.py"

        # Build command for desk_worker.py with appropriate arguments
        cmd = ["uv", "run", "python", str(desk_worker_script), role]
        if daemon:
            cmd.extend(["--daemon", daemon])
        if model:
            cmd.extend(["--model", model])

        terminal_message(
            f"Spawning desk-mode worker for role '{role}'...\n"
            f"Worker will poll for messages and stay alive for continuous work.",
            subject="Summon",
        )
        if dry_run:
            terminal_message(
                f"Dry run - would execute: {' '.join(cmd)}",
                subject="Dry Run",
                subject_color="yellow",
            )
            return
        try:
            # Redirect stdout/stderr to a log file so desk worker output
            # doesn't pollute the terminal. The log lives alongside the
            # typerdrive app logs in ~/.local/state/site-nine/logs/.
            from typerdrive.config import get_typerdrive_config

            log_dir = get_typerdrive_config().log_dir
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / f"desk-worker-{role}.log"
            fh = open(log_file, "a")
            subprocess.Popen(cmd, cwd=str(repo_root), stdout=fh, stderr=fh)
            terminal_message(
                f"Worker output is being logged to: {log_file}",
                subject="Desk Log",
            )
        except FileNotFoundError:
            raise CLIError(f"desk_worker.py module not found at {desk_worker_script}")
    else:
        # Interactive mode: exec into OpenCode, replacing the s9 process
        cmd = ["opencode", "--model", model, "--prompt", instruction]
        terminal_message(
            f"Launching OpenCode for role '{role}'...\nInstruction: {instruction}",
            subject="Summon",
        )
        if dry_run:
            terminal_message(
                f"Dry run - would execute: {' '.join(cmd)}",
                subject="Dry Run",
                subject_color="yellow",
            )
            return
        # Flush any stale status_queue entries before launching to avoid flooding
        # the new session with toasts from previous sessions.
        try:
            db_path = get_db_path()
            conn = sqlite3.connect(str(db_path))
            conn.execute("DELETE FROM status_queue")
            conn.commit()
            conn.close()
        except Exception:
            pass  # Non-fatal — proceed even if flush fails
        try:
            os.execvp("opencode", cmd)
        except FileNotFoundError:
            raise CLIError("'opencode' command not found. Is OpenCode installed?")
