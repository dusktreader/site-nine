"""Manage guide documents in .opencode/docs/guides/"""

from typing import Annotated

import typer
from typerdrive import handle_errors, terminal_message

from site_nine.cli.utils import CLIError, open_in_editor, require_opencode_dir
from site_nine.exceptions import SiteNineError

app = typer.Typer(help="List and edit guide documents")


def _guides_dir():
    return require_opencode_dir() / "docs" / "guides"


def _available_guides(guides_dir):
    if not guides_dir.exists():
        return []
    return sorted(f.stem for f in guides_dir.iterdir() if f.suffix == ".md" and f.stem.lower() != "readme")


@app.command(name="list")
@handle_errors("Failed to list guides", handle_exc_class=SiteNineError)
def list_guides() -> None:
    """List available guide documents"""
    guides_dir = _guides_dir()
    available = _available_guides(guides_dir)

    CLIError.require_condition(bool(available), "No guides found. Run 's9 init' to create guide documents.")

    terminal_message(
        "\n".join(f"  {name}" for name in available),
        subject="Available Guides",
    )


@app.command(name="edit")
@handle_errors("Failed to edit guide", handle_exc_class=SiteNineError)
def edit_guide(
    name: Annotated[str, typer.Argument(help="Guide name (e.g. 'testing', 'code-review')")],
) -> None:
    """Edit a guide document from .opencode/docs/guides/"""
    guides_dir = _guides_dir()
    guide_file = guides_dir / f"{name}.md"

    if not guide_file.exists():
        available = _available_guides(guides_dir)
        hint = f"Available guides: {', '.join(available)}" if available else f"No guides found in {guides_dir}."
        raise CLIError(f"Guide '{name}' not found.\n{hint}")

    open_in_editor(f"{name}.md", guide_file)
