import click

from lean.click import LeanCommand
from lean.container import container


@click.command(cls=LeanCommand)
@click.argument("key")
@click.argument("value")
def set(key: str, value: str) -> None:
    """Set a configurable option.

    Run `lean config list` to show all available options.
    """
    cli_config_manager = container.cli_config_manager()

    option = cli_config_manager.get_option_by_key(key)
    option.set_value(value)

    click.echo(f"Successfully updated the value of '{key}' to '{option.get_value()}'")
