"""Main CLI application for site-nine"""

import typer
from loguru import logger
from rich.console import Console
from typerdrive import add_cache_subcommand, add_settings_subcommand, handle_errors, set_typerdrive_config
from typerdrive.logging.commands import add_logs_subcommand

from site_nine.core.settings import SiteNineSettings

# Configure typerdrive
set_typerdrive_config(app_name="site-nine")

app = typer.Typer(
    name="site-nine",
    help="The headquarters for AI agent orchestration",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

console = Console()

# Add typerdrive subcommands for settings, cache, and logs
add_settings_subcommand(app, SiteNineSettings)
add_cache_subcommand(app)
add_logs_subcommand(app)


@app.command()
@handle_errors("Failed to get version")
def version() -> None:
    """Show site-nine version"""
    from importlib.metadata import version as get_version

    try:
        ver = get_version("site-nine")
        console.print(f"site-nine version {ver}")
        logger.info(f"Version check: {ver}")
    except Exception:
        console.print("site-nine version unknown (development)")
        logger.warning("Version check failed - development mode")


# Import subcommands (will create these next)
# Imports are at the end to avoid circular imports
def _register_subcommands() -> None:
    """Register CLI subcommands"""
    from site_nine.cli import adr, config, edit, epic, handoff, mission, persona, review, task, template
    from site_nine.cli.changelog import changelog_command
    from site_nine.cli.check import check_command
    from site_nine.cli.dashboard import dashboard_command
    from site_nine.cli.doctor import doctor_command
    from site_nine.cli.init import init_command
    from site_nine.cli.reset import reset_command
    from site_nine.cli.summon import summon_command

    app.command(name="init")(init_command)
    app.command(name="dashboard")(dashboard_command)
    app.command(name="changelog")(changelog_command)
    app.command(name="check")(check_command)
    app.command(name="doctor")(doctor_command)
    app.command(name="reset")(reset_command)
    app.command(name="summon")(summon_command)
    app.add_typer(mission.app, name="mission")
    app.add_typer(task.app, name="task")
    app.add_typer(epic.app, name="epic")
    app.add_typer(template.app, name="template")
    app.add_typer(config.app, name="config")
    app.add_typer(persona.app, name="persona")
    app.add_typer(edit.app, name="edit")
    app.add_typer(review.app, name="review")
    app.add_typer(handoff.app, name="handoff")
    app.add_typer(adr.app, name="adr")


# Register subcommands when module is imported
_register_subcommands()


if __name__ == "__main__":
    app()
