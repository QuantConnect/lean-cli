import click

from lean.config.global_config import all_options


@click.command()
@click.argument("key")
def get(key: str) -> None:
    """Get the current value of a configurable option.

    Run `lean config list` to show all available options.
    """
    option = next((x for x in all_options if x.key == key), None)
    if option is None:
        raise click.ClickException(f"There doesn't exist an option with key '{key}'")

    value = option.get_value()
    if value is None:
        raise click.ClickException(f"The option with key '{key}' doesn't have a value set")

    click.echo(value)
