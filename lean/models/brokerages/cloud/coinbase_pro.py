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


class CoinbaseProBrokerage(CloudBrokerage):
    """A CloudBrokerage implementation for Coinbase Pro."""

    def __init__(self, api_key: str, api_secret: str, passphrase: str) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._passphrase = passphrase

    @classmethod
    def get_id(cls) -> str:
        return "GDAXBrokerage"

    @classmethod
    def get_name(cls) -> str:
        return "Coinbase Pro"

    @classmethod
    def build(cls, logger: Logger) -> CloudBrokerage:
        logger.info("""
You can generate Coinbase Pro API credentials on the API settings page (https://pro.coinbase.com/profile/api).
When creating the key, make sure you authorize it for View and Trading access.
        """.strip())

        api_key = click.prompt("API key")
        api_secret = logger.prompt_password("API secret")
        passphrase = logger.prompt_password("Passphrase")

        return CoinbaseProBrokerage(api_key, api_secret, passphrase)

    def _get_settings(self) -> Dict[str, str]:
        return {
            "key": self._api_key,
            "secret": self._api_secret,
            "passphrase": self._passphrase,
            "environment": "live"
        }
