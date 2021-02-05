import click

from lean.commands.config.get import get
from lean.commands.config.list import list
from lean.commands.config.set import set


@click.group()
def config() -> None:
    """Configure Lean CLI options."""
    # This method is intentionally empty
    # It is used as the command group for all `lean config <command>` commands
    pass


config.add_command(get)
config.add_command(set)
config.add_command(list)
