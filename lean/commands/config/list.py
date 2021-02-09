import click
from rich import box
from rich.console import Console
from rich.table import Table

from lean.click import LeanCommand
from lean.container import container


@click.command(cls=LeanCommand)
def list() -> None:
    """List the configurable options and their current values."""
    console = Console()

    table = Table(box=box.SQUARE)
    table.add_column("Key")
    table.add_column("Value")
    table.add_column("Location")
    table.add_column("Description")

    for option in container.cli_config_manager().all_options:
        value = option.get_value(default="<not set>")

        # Mask values of sensitive options
        if value != "<not set>" and option.is_sensitive:
            value = "*" * 12 + value[-3:] if len(value) >= 5 else "*" * 15

        table.add_row(option.key,
                      value,
                      str(option.location),
                      option.description)

    console.print(table)
