import click

from lean.click import LeanCommand
from lean.container import container


@click.command(cls=LeanCommand)
def logout() -> None:
    """Log out and remove stored credentials."""
    container.credentials_storage().clear()
