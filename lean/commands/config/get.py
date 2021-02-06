import click

from lean.config.global_config import all_options
from lean.constants import CREDENTIALS_FILE


@click.command()
@click.argument("key")
def get(key: str) -> None:
    """Get the current value of a configurable option.

    Credentials cannot be retrieved this way for security reasons.
    Please open ~/.lean/credentials if you want to see your currently stored credentials.

    Run `lean config list` to show all available options.
    """
    option = next((x for x in all_options if x.key == key), None)
    if option is None:
        raise click.ClickException(f"There doesn't exist an option with key '{key}'")

    if option.file_name == CREDENTIALS_FILE:
        raise click.ClickException("Credentials cannot be retrieved using `lean config get` for security reasons")

    value = option.get_value()
    if value is None:
        raise click.ClickException(f"The option with key '{key}' doesn't have a value set")

    click.echo(value)
