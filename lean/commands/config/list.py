from pathlib import Path

import click
from rich import box
from rich.console import Console
from rich.table import Table

from lean.config.global_config import all_options
from lean.constants import CREDENTIALS_FILE, GLOBAL_CONFIG_DIR


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
        value = option.get_value(default="<not set>")

        # Don't print complete credentials
        if value != "<not set>" and option.file_name == CREDENTIALS_FILE:
            value = "*" * 12 + value[-3:] if len(value) >= 5 else "*" * 15

        table.add_row(option.key,
                      value,
                      str(Path.home() / GLOBAL_CONFIG_DIR / option.file_name),
                      option.description)

    console.print(table)
