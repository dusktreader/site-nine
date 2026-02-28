from importlib.metadata import version as get_version
from typing import Annotated

import typer
from typerdrive import (
    add_cache_subcommand,
    add_settings_subcommand,
    set_typerdrive_config,
    terminal_message,
)
from typerdrive.logging.commands import add_logs_subcommand

from site_nine.cli import adr, block, comms, epic, guide, mission, persona, review, role, task
from site_nine.cli.dashboard import dashboard_command
from site_nine.cli.doctor import doctor_command
from site_nine.cli.init import init_command
from site_nine.cli.reset import reset_command
from site_nine.cli.summon import summon_command
from site_nine.core.settings import SiteNineSettings

app = typer.Typer(
    name="site-nine",
    help="The headquarters for AI agent orchestration",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

set_typerdrive_config(app_name="site-nine")
add_settings_subcommand(app, SiteNineSettings)
add_cache_subcommand(app)
add_logs_subcommand(app)

app.command(name="init")(init_command)
app.command(name="dashboard")(dashboard_command)
app.command(name="doctor")(doctor_command)
app.command(name="reset")(reset_command)
app.command(name="summon")(summon_command)
app.add_typer(mission.app, name="mission")
app.add_typer(task.app, name="task")
app.add_typer(epic.app, name="epic")
app.add_typer(persona.app, name="persona")
app.add_typer(guide.app, name="guide")
app.add_typer(review.app, name="review")
app.add_typer(role.app, name="role")
app.add_typer(block.app, name="block")
app.add_typer(adr.app, name="adr")
app.add_typer(comms.app, name="comms")


@app.command()
def version(
    plain: Annotated[bool, typer.Option("--plain", "-p", help="Output only the version number")] = False,
) -> None:
    """Show site-nine version"""
    ver = get_version("site-nine")
    if plain:
        print(ver)
    else:
        terminal_message(f"site-nine version {ver}", subject="Version")


if __name__ == "__main__":
    app()
