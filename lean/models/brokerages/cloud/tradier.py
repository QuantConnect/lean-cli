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

    def __init__(self, account_id: str, access_token: str, environment: str) -> None:
        self._account_id = account_id
        self._access_token = access_token
        self._environment = environment

    @classmethod
    def get_id(cls) -> str:
        return "TradierBrokerage"

    @classmethod
    def get_name(cls) -> str:
        return "Tradier"

    @classmethod
    def build(cls, logger: Logger) -> CloudBrokerage:
        logger.info("""
Your Tradier account id and API token can be found on your Settings/API Access page (https://dash.tradier.com/settings/api).
The account id is the alpha-numeric code in a dropdown box on that page.
Your account details are not saved on QuantConnect.
        """.strip())

        account_id = click.prompt("Account id")
        access_token = logger.prompt_password("Access token")
        environment = click.prompt("Environment", type=click.Choice(["demo", "real"], case_sensitive=False))

        return TradierBrokerage(account_id, access_token, environment)

    def _get_settings(self) -> Dict[str, str]:
        return {
            "account": self._account_id,
            "token": self._access_token,
            "environment": "live" if self._environment == "real" else "paper"
        }
