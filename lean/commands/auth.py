"""This module contains commands used to authenticate with the QuantConnect.com API."""

from typing import Optional

import click


@click.command()
@click.option("--user-id", "-u", type=str, help="QuantConnect.com user id")
@click.option("--api-token", "-t", type=str, help="QuantConnect.com API token")
def login(user_id: Optional[str], api_token: Optional[str]) -> None:
    """Log in with a QuantConnect account.

    If user id or API token is not provided an interactive prompt will show.

    Credentials are stored in ~/.lean/credentials and are removed upon running `lean logout`.
    """
    pass


@click.command()
def logout() -> None:
    """Log out and remove stored credentials."""
    pass
