import click

from lean.click import LeanCommand
from lean.container import container


@click.command(cls=LeanCommand)
@click.argument("key")
def get(key: str) -> None:
    """Get the current value of a configurable option.

    Sensitive options like credentials cannot be retrieved this way for security reasons.
    Please open ~/.lean/credentials if you want to see your currently stored credentials.

    Run `lean config list` to show all available options.
    """
    cli_config_manager = container.cli_config_manager()

    option = cli_config_manager.get_option_by_key(key)
    if option.is_sensitive:
        raise RuntimeError(
            "Sensitive options like credentials cannot be retrieved using `lean config get` for security reasons")

    value = option.get_value()
    if value is None:
        raise RuntimeError(f"The option with key '{key}' doesn't have a value set")

    click.echo(value)
