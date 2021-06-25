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

from typing import Any, Dict

import click

from lean.components.util.logger import Logger
from lean.models.brokerages.local.base import LocalBrokerage
from lean.models.config import LeanConfigConfigurer


class BitfinexBrokerage(LocalBrokerage):
    """A LocalBrokerage implementation for the Bitfinex brokerage."""

    def __init__(self, api_key: str, api_secret: str) -> None:
        self._api_key = api_key
        self._api_secret = api_secret

    @classmethod
    def get_name(cls) -> str:
        return "Bitfinex"

    @classmethod
    def _build(cls, lean_config: Dict[str, Any], logger: Logger) -> LocalBrokerage:
        logger.info("""
Create an API key by logging in and accessing the Bitfinex API Management page (https://www.bitfinex.com/api).
        """.strip())

        api_key = click.prompt("API key", cls._get_default(lean_config, "bitfinex-api-key"))
        api_secret = logger.prompt_password("API secret", cls._get_default(lean_config, "bitfinex-api-secret"))

        return BitfinexBrokerage(api_key, api_secret)

    def _configure_environment(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        lean_config["environments"][environment_name]["live-mode-brokerage"] = "BitfinexBrokerage"
        lean_config["environments"][environment_name]["transaction-handler"] = \
            "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler"

    def configure_credentials(self, lean_config: Dict[str, Any]) -> None:
        lean_config["bitfinex-api-key"] = self._api_key
        lean_config["bitfinex-api-secret"] = self._api_secret

        self._save_properties(lean_config, ["bitfinex-api-key", "bitfinex-api-secret"])


class BitfinexDataFeed(LeanConfigConfigurer):
    """A LeanConfigConfigurer implementation for the Bitfinex data feed."""

    def __init__(self, brokerage: BitfinexBrokerage) -> None:
        self._brokerage = brokerage

    @classmethod
    def get_name(cls) -> str:
        return BitfinexBrokerage.get_name()

    @classmethod
    def build(cls, lean_config: Dict[str, Any], logger: Logger) -> LeanConfigConfigurer:
        return BitfinexDataFeed(BitfinexBrokerage.build(lean_config, logger))

    def configure(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        lean_config["environments"][environment_name]["data-queue-handler"] = "BitfinexBrokerage"
        lean_config["environments"][environment_name]["history-provider"] = "BrokerageHistoryProvider"

        self._brokerage.configure_credentials(lean_config)
