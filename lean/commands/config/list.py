import click
from pathlib import Path
from rich import box
from rich.console import Console
from rich.table import Table

from lean.config.global_config import all_options
from lean.constants import GLOBAL_CONFIG_DIR


@click.command()
def list() -> None:
    """List the configurable options and their current values."""
    console = Console()

    table = Table(box=box.SQUARE)
    table.add_column("Key")
    table.add_column("Value")
    table.add_column("Location")
    table.add_column("Description")

    for option in all_options:
        table.add_row(option.key,
                      option.get_value(default="<not set>"),
                      str(Path.home() / GLOBAL_CONFIG_DIR / option.file_name),
                      option.description)

    console.print(table)
