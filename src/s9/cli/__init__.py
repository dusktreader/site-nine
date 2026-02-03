"""site-nine CLI commands"""

from s9.cli.main import app

__all__ = ["app", "main"]


def main() -> None:
    """CLI entry point"""
    app()
