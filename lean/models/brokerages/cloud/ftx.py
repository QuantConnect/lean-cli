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


class FTXBrokerage(CloudBrokerage):
    """A CloudBrokerage implementation for FTX."""

    def __init__(self, api_key: str, secret_key: str, account_tier: str, exchange_name: str) -> None:
        self._api_key = api_key
        self._secret_key = secret_key
        self._account_tier = account_tier
        self._exchange_name = exchange_name

    @classmethod
    def get_id(cls) -> str:
        return "FTXBrokerage"

    @classmethod
    def get_name(cls) -> str:
        return "FTX"

    @classmethod
    def build(cls, logger: Logger) -> CloudBrokerage:
        exchange_name = click.prompt("FTX Exchange [FTX|FTXUS]")
        exchange = FTXExchange() if exchange_name.casefold() == "FTX".casefold() else FTXUSExchange()

        logger.info("""
Create an API key by logging in and accessing the {} Profile page (https://{}/profile).
        """.format(exchange.get_name(), exchange.get_domain()).strip())

        api_key = click.prompt("API key")
        secret_key = logger.prompt_password("Secret key")
        account_tier = click.prompt("Account Tier")

        return FTXBrokerage(api_key, secret_key, account_tier, exchange_name)   

    def _get_settings(self) -> Dict[str, str]:
        return {
            "key": self._api_key,
            "secret": self._secret_key,
            "tier": self._account_tier,
            "exchange": self._exchange_name,
            "environment": "live"
        }

class FTXExchange:
    def get_name(self) -> str:
        return "FTX"

    def get_domain(self) -> str:
        return "ftx.com"

class FTXUSExchange(FTXExchange):
    def get_name(self) -> str:
        return "FTXUS"

    def get_domain(self) -> str:
        return "ftx.us"
