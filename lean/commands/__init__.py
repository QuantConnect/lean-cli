import click

from lean import __version__
from lean.commands.backtest import backtest
from lean.commands.config import config
from lean.commands.create_project import create_project
from lean.commands.init import init
from lean.commands.login import login
from lean.commands.logout import logout


@click.group()
@click.version_option(__version__)
def lean() -> None:
    """The Lean CLI by QuantConnect."""
    # This method is intentionally empty
    # It is used as the command group for all `lean <command>` commands
    pass


lean.add_command(login)
lean.add_command(logout)
lean.add_command(config)
lean.add_command(init)
lean.add_command(create_project)
lean.add_command(backtest)
