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

from typing import Optional, Tuple

from click import command, option, prompt

from lean.click import LeanCommand
from lean.container import container
from lean.models.errors import MoreInfoError


def get_lean_config_credentials() -> Tuple[str, str]:
    """Retrieve the QuantConnect credentials from the Lean CLI configuration.

    This function accesses the Lean CLI configuration manager to obtain the
    stored user ID and API token. The credentials are retrieved from the
    configuration settings managed by the Lean CLI.

    Returns:
        tuple[str, str]: A tuple containing the user ID and API token as strings.
    """
    cli_config_manager = container.cli_config_manager

    user_id = cli_config_manager.user_id.get_value()
    api_token = cli_config_manager.api_token.get_value()

    return user_id, api_token


def get_credentials(user_id: Optional[str], api_token: Optional[str], show_secrets: bool) -> Tuple[str, str]:
    """Fetch user credentials, prompting the user if necessary."""
    logger = container.logger
    credentials_storage = container.credentials_storage
    current_user_id, current_api_token = get_lean_config_credentials()

    if user_id is None or api_token is None:
        logger.info("Your user id and API token are needed to make authenticated requests to the QuantConnect API")
        logger.info("You can request these credentials on https://www.quantconnect.com/account")
        logger.info(f"Both will be saved in {credentials_storage.file}")

    if user_id is None:
        user_id = prompt("User id", current_user_id)

    if api_token is None:
        api_token = logger.prompt_password("API token", current_api_token, hide_input=not show_secrets)

    return user_id, api_token


def validate_credentials(user_id: str, api_token: str) -> None:
    """Validate the user credentials by attempting to authenticate with the QuantConnect API."""
    container.api_client.set_user_token(user_id=user_id, api_token=api_token)

    if not container.api_client.is_authenticated():
        raise MoreInfoError(
            "Credentials are invalid. Please ensure your computer clock is correct, or try using another terminal, or enter API token manually instead of copy-pasting.",
            "https://www.lean.io/docs/v2/lean-cli"
        )

    cli_config_manager = container.cli_config_manager
    cli_config_manager.user_id.set_value(user_id)
    cli_config_manager.api_token.set_value(api_token)

    container.logger.info("Successfully logged in")

@command(cls=LeanCommand)
@option("--user-id", "-u", type=str, help="QuantConnect user id")
@option("--api-token", "-t", type=str, help="QuantConnect API token")
@option("--show-secrets", is_flag=True, show_default=True, default=False, help="Show secrets as they are input")
def login(user_id: Optional[str], api_token: Optional[str], show_secrets: bool) -> None:
    """Log in with a QuantConnect account.

    If user id or API token is not provided an interactive prompt will show.

    Credentials are stored in ~/.lean/credentials and are removed upon running `lean logout`.
    """

    user_id, api_token = get_credentials(user_id, api_token, show_secrets)
    validate_credentials(user_id, api_token)
