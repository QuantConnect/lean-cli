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


class BinanceBrokerage(CloudBrokerage):
    """A CloudBrokerage implementation for Binance."""

    def __init__(self, api_key: str, secret_key: str, environment: str) -> None:
        self._api_key = api_key
        self._secret_key = secret_key
        self._environment = environment

    @classmethod
    def get_id(cls) -> str:
        return "BinanceBrokerage"

    @classmethod
    def get_name(cls) -> str:
        return "Binance"

    @classmethod
    def build(cls, logger: Logger) -> CloudBrokerage:
        logger.info("""
Your Binance real account information can be found on your API Management Settings page (https://www.binance.com/en/my/settings/api-management).
Your account details are not save on QuantConnect.
Demo credentials can be generated on Binance Testnet (https://testnet.binance.vision/).
        """.strip())

        api_key = click.prompt("API key")
        secret_key = logger.prompt_password("Secret key")
        environment = click.prompt("Environment", type=click.Choice(["demo", "real"], case_sensitive=False))

        return BinanceBrokerage(api_key, secret_key, environment)

    def _get_settings(self) -> Dict[str, str]:
        return {
            "key": self._api_key,
            "secret": self._secret_key,
            "environment": "live" if self._environment == "real" else "paper"
        }
