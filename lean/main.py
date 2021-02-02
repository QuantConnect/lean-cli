"""This module is responsible for setting up the CLI."""

import click

from lean import __version__
from lean.commands import auth


@click.group()
@click.version_option(__version__)
def lean() -> None:
    """The Lean CLI by QuantConnect."""
    # This method is intentionally empty and is used as the root command group containing all subcommands
    pass


# Authentication commands
lean.add_command(auth.login)
lean.add_command(auth.logout)


def main() -> None:
    """This function is the entrypoint when running a Lean command in a terminal."""
    lean()
