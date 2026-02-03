"""Template management commands"""

import typer
from rich.console import Console

app = typer.Typer(help="Manage templates")
console = Console()


@app.command()
def list() -> None:
    """List available templates"""
    console.print("[yellow]TODO: Implement template list[/yellow]")


@app.command()
def show(
    template_id: str = typer.Argument(..., help="Template ID"),
) -> None:
    """Show template details"""
    console.print("[yellow]TODO: Implement template show[/yellow]")
