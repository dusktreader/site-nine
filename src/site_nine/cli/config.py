"""Configuration management commands"""

import typer
from rich.console import Console

app = typer.Typer(help="Manage configuration")
console = Console()


@app.command()
def show() -> None:
    """Show current configuration"""
    console.print("[yellow]TODO: Implement config show[/yellow]")


@app.command()
def validate(
    config_file: str = typer.Argument(..., help="Config file to validate"),
) -> None:
    """Validate configuration file"""
    console.print("[yellow]TODO: Implement config validate[/yellow]")
