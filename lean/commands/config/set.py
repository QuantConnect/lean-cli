import click

from lean.config.global_config import all_options


@click.command()
@click.argument("key")
@click.argument("value")
def set(key: str, value: str) -> None:
    """Set a configurable option.

    Run `lean config list` to show all available options.
    """
    option = next((x for x in all_options if x.key == key), None)

    if option is None:
        raise click.ClickException(f"There doesn't exist an option with key '{key}'")

    option.set_value(value)

    click.echo(f"Successfully updated the value of '{key}' to '{option.get_value()}'")
