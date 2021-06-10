# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean CLI v1.0. Copyright 2021 QuantConnect Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import Optional

import click

from lean.click import LeanCommand
from lean.container import container
from lean.models.errors import MoreInfoError


@click.command(cls=LeanCommand)
@click.option("--user-id", "-u", type=str, help="QuantConnect user id")
@click.option("--api-token", "-t", type=str, help="QuantConnect API token")
def login(user_id: Optional[str], api_token: Optional[str]) -> None:
    """Log in with a QuantConnect account.

    If user id or API token is not provided an interactive prompt will show.

    Credentials are stored in ~/.lean/credentials and are removed upon running `lean logout`.
    """
    logger = container.logger()
    credentials_storage = container.credentials_storage()

    if user_id is None or api_token is None:
        logger.info("Your user id and API token are needed to make authenticated requests to the QuantConnect API")
        logger.info("You can request these credentials on https://www.quantconnect.com/account")
        logger.info(f"Both will be saved in {credentials_storage.file}")

    if user_id is None:
        user_id = click.prompt("User id")

    if api_token is None:
        api_token = logger.prompt_password("API token")

    api_client = container.api_client(user_id=user_id, api_token=api_token)
    if not api_client.is_authenticated():
        raise MoreInfoError("Credentials are invalid",
                            "https://www.lean.io/docs/lean-cli/tutorials/authentication#02-Logging-in")

    cli_config_manager = container.cli_config_manager()
    cli_config_manager.user_id.set_value(user_id)
    cli_config_manager.api_token.set_value(api_token)

    logger.info("Successfully logged in")
