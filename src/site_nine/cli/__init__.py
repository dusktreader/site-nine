"""site-nine CLI commands"""

from site_nine.cli.main import app

__all__ = ["app", "main"]


def main() -> None:
    """CLI entry point"""
    app()
