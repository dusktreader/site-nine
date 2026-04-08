"""Manage role definition documents in .opencode/docs/roles/"""

from typing import Annotated

import typer
from typerdrive import handle_errors, terminal_message

from site_nine.cli.utils import CLIError, open_in_editor, require_opencode_dir
from site_nine.exceptions import SiteNineError

app = typer.Typer(help="List and edit role definition documents", invoke_without_command=True)


@app.callback()
def _callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())


def _roles_dir():
    return require_opencode_dir() / "docs" / "roles"


def _available_roles(roles_dir):
    if not roles_dir.exists():
        return []
    return sorted(f.stem for f in roles_dir.iterdir() if f.suffix == ".md" and f.stem.lower() != "readme")


@app.command(name="list")
@handle_errors("Failed to list roles", handle_exc_class=SiteNineError)
def list_roles() -> None:
    """List available role definition documents"""
    roles_dir = _roles_dir()
    available = _available_roles(roles_dir)

    CLIError.require_condition(bool(available), "No role definitions found. Run 's9 init' to create role documents.")

    terminal_message(
        "\n".join(f"  {name}" for name in available),
        subject="Available Roles",
    )


@app.command(name="edit")
@handle_errors("Failed to edit role", handle_exc_class=SiteNineError)
def edit_role(
    name: Annotated[str, typer.Argument(help="Role name (e.g. 'engineer', 'architect', 'tester')")],
) -> None:
    """Edit a role definition document from .opencode/docs/roles/"""
    roles_dir = _roles_dir()
    role_file = roles_dir / f"{name}.md"

    if not role_file.exists():
        available = _available_roles(roles_dir)
        hint = f"Available roles: {', '.join(available)}" if available else f"No role definitions found in {roles_dir}."
        raise CLIError(f"Role '{name}' not found.\n{hint}")

    open_in_editor(f"{name}.md", role_file)
