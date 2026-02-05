"""site-nine CLI commands"""

from site_nine.cli.main import _register_subcommands, app

__all__ = ["app", "main"]

# Register subcommands after all imports are done
_register_subcommands()


def main() -> None:
    """CLI entry point"""
    app()
