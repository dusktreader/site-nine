from __future__ import annotations

from typing import Annotated

import typer
from rich.table import Table
from snick import conjoin
from typerdrive import handle_errors, terminal_message

from site_nine.blocks import BlockManager
from site_nine.cli.json_utils import format_json_response, output_json
from site_nine.cli.utils import CLIError, require_db_path
from site_nine.core.database import Database
from site_nine.exceptions import SiteNineError

app = typer.Typer(help="Manage external blockers for tasks", invoke_without_command=True)


@app.callback()
def _callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())


@app.command()
@handle_errors("Failed to create block", handle_exc_class=SiteNineError)
def create(
    task_id: Annotated[str, typer.Option("--task", "-t", help="Task ID to block")],
    block_type: Annotated[
        str, typer.Option("--type", help="Type of blocker (e.g., external-dependency, waiting-for-access)")
    ],
    description: Annotated[str, typer.Option("--description", "-d", help="Description of what's blocking the task")],
) -> None:
    """Create an external blocker for a task (typically used by: agents)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = BlockManager(db)

        block_id = manager.create_block(
            task_id=task_id,
            block_type=block_type,
            description=description,
        )

        terminal_message(
            conjoin(
                f"Task: {task_id}",
                f"Type: {block_type}",
                f"Description: {description}",
            ),
            subject=f"Created block #{block_id}",
        )


@app.command()
@handle_errors("Failed to list blocks", handle_exc_class=SiteNineError)
def list(
    task_id: Annotated[str | None, typer.Option("--task", "-t", help="Filter by task ID")] = None,
    resolved: Annotated[bool | None, typer.Option("--resolved", help="Show only resolved blocks")] = None,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """List blocks (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = BlockManager(db)

        blocks = manager.list_blocks(task_id=task_id, resolved=resolved)

        if not blocks:
            if json_output:
                output_json(format_json_response([]))
                return

            filter_msg = ""
            if task_id or resolved is not None:
                filter_parts = []
                if task_id:
                    filter_parts.append(f"task={task_id}")
                if resolved is not None:
                    filter_parts.append(f"resolved={resolved}")
                filter_msg = f" ({', '.join(filter_parts)})"
            terminal_message(f"No blocks found{filter_msg}.")
            return

        if json_output:
            data = []
            for block in blocks:
                block_dict = {
                    "id": block.id,
                    "task_id": block.task_id,
                    "block_type": block.block_type,
                    "description": block.description,
                    "status": "resolved" if block.resolved_at else "active",
                    "created_at": block.created_at,
                    "resolved_at": block.resolved_at,
                }
                data.append(block_dict)

            output_json(format_json_response(data))
            return

        table = Table(title="Blocks")
        table.add_column("ID", style="cyan", justify="right", width=4)
        table.add_column("Task", style="magenta", width=12)
        table.add_column("Type", style="blue", width=20)
        table.add_column("Description", style="white", width=40)
        table.add_column("Status", style="yellow", width=10)

        for block in blocks:
            status = "[green]resolved[/green]" if block.resolved_at else "[red]active[/red]"

            table.add_row(
                str(block.id),
                block.task_id,
                block.block_type,
                block.description[:60] + "..." if len(block.description) > 60 else block.description,
                status,
            )

        terminal_message(table, indent=False)


@app.command()
@handle_errors("Failed to show block", handle_exc_class=SiteNineError)
def show(
    block_id: Annotated[int, typer.Argument(help="Block ID")],
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output in JSON format")] = False,
) -> None:
    """Show block details (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = BlockManager(db)

        block = CLIError.enforce_defined(manager.get_block(block_id), f"Block #{block_id} not found")

        if json_output:
            block_dict = {
                "id": block.id,
                "task_id": block.task_id,
                "block_type": block.block_type,
                "description": block.description,
                "status": "resolved" if block.resolved_at else "active",
                "created_at": block.created_at,
                "resolved_at": block.resolved_at,
            }

            output_json(format_json_response(block_dict))
            return

        status_display = "Resolved" if block.resolved_at else "Active"

        details = [
            f"Status:      {status_display}",
            f"Task:        {block.task_id}",
            f"Type:        {block.block_type}",
            f"Description: {block.description}",
            f"Created:     {block.created_at}",
        ]

        if block.resolved_at:
            details.append(f"Resolved:    {block.resolved_at}")

        terminal_message(conjoin(*details), subject=f"Block #{block.id}")


@app.command()
@handle_errors("Failed to resolve block", handle_exc_class=SiteNineError)
def resolve(
    block_id: Annotated[int, typer.Argument(help="Block ID")],
) -> None:
    """Resolve a block (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = BlockManager(db)

        block = CLIError.enforce_defined(manager.get_block(block_id), f"Block #{block_id} not found")

        if block.resolved_at:
            terminal_message(f"Block #{block_id} is already resolved.", subject="Warning", subject_color="yellow")
            return

        manager.resolve_block(block_id)

        terminal_message(f"Task: {block.task_id}", subject=f"Resolved block #{block_id}")


@app.command()
@handle_errors("Failed to delete block", handle_exc_class=SiteNineError)
def delete(
    block_id: Annotated[int, typer.Argument(help="Block ID")],
) -> None:
    """Delete a block (typically used by: both)"""
    db_path = require_db_path()

    with Database(db_path) as db:
        manager = BlockManager(db)

        block = CLIError.enforce_defined(manager.get_block(block_id), f"Block #{block_id} not found")

        manager.delete_block(block_id)

        terminal_message(f"Task: {block.task_id}", subject=f"Deleted block #{block_id}")
