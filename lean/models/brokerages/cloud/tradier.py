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

from typing import Dict

import click

from lean.components.util.logger import Logger
from lean.models.brokerages.cloud.base import CloudBrokerage


class TradierBrokerage(CloudBrokerage):
    """A CloudBrokerage implementation for Tradier."""

    def __init__(self) -> None:
        super().__init__("TradierBrokerage", "Tradier (beta)", """
Your Tradier account id and API token can be found on your Settings/API Access page (https://dash.tradier.com/settings/api).
The account id is the alpha-numeric code in a dropdown box on that page.
Your account details are not saved on QuantConnect.
        """.strip())

    def _get_settings(self, logger: Logger) -> Dict[str, str]:
        account_id = click.prompt("Account id")
        access_token = logger.prompt_password("Access token")

        environment = click.prompt("Environment", type=click.Choice(["demo", "real"], case_sensitive=False))

        return {
            "account": account_id,
            "token": access_token,
            "environment": "live" if environment == "real" else "paper"
        }
