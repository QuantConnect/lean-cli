"""This module is responsible for setting up the CLI."""

import click

from lean import __version__
from lean.commands.create_project import create_project
from lean.commands.init import init
from lean.commands.login import login
from lean.commands.logout import logout


@click.group()
@click.version_option(__version__)
def lean() -> None:
    """The Lean CLI by QuantConnect."""
    # This method is intentionally empty and is used as the root command group containing all subcommands
    pass


# Add all commands to the root command group
lean.add_command(login)
lean.add_command(logout)
lean.add_command(init)
lean.add_command(create_project)


def main() -> None:
    """This function is the entrypoint when running a Lean command in a terminal."""
    lean()
