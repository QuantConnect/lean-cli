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


class OANDABrokerage(CloudBrokerage):
    """A CloudBrokerage implementation for OANDA."""

    def __init__(self, account_id: str, access_token: str, environment: str) -> None:
        self._account_id = account_id
        self._access_token = access_token
        self._environment = environment

    @classmethod
    def get_id(cls) -> str:
        return "OandaBrokerage"

    @classmethod
    def get_name(cls) -> str:
        return "OANDA"

    @classmethod
    def build(cls, logger: Logger) -> CloudBrokerage:
        logger.info("""
Your OANDA account number can be found on your OANDA Account Statement page (https://www.oanda.com/account/statement/).
It follows the following format: ###-###-######-###.
You can generate an API token from the Manage API Access page (https://www.oanda.com/account/tpa/personal_token).
Your account details are not saved on QuantConnect.
        """.strip())

        account_id = click.prompt("Account id")
        access_token = logger.prompt_password("Access token")
        environment = click.prompt("Environment", type=click.Choice(["demo", "real"], case_sensitive=False))

        return OANDABrokerage(account_id, access_token, environment)

    def _get_settings(self) -> Dict[str, str]:
        return {
            "account": self._account_id,
            "key": self._access_token,
            "environment": "live" if self._environment == "real" else "paper"
        }
