"""This module is responsible for setting up the CLI."""

import click

from lean import __version__
from lean.commands import auth
from lean.commands import init
from lean.commands import create_project


@click.group()
@click.version_option(__version__)
def lean() -> None:
    """The Lean CLI by QuantConnect."""
    # This method is intentionally empty and is used as the root command group containing all subcommands
    pass


# Add all commands to the root command group
lean.add_command(auth.login)
lean.add_command(auth.logout)
lean.add_command(init.init)
lean.add_command(create_project.create_project)


def main() -> None:
    """This function is the entrypoint when running a Lean command in a terminal."""
    lean()
