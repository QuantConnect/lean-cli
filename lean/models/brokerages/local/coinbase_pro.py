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


class CoinbaseProBrokerage(LocalBrokerage):
    """A LocalBrokerage implementation for the Coinbase Pro brokerage."""

    def __init__(self, api_key: str, api_secret: str, passphrase: str, sandbox: bool) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._passphrase = passphrase
        self._sandbox = sandbox

    @classmethod
    def get_name(cls) -> str:
        return "Coinbase Pro"

    @classmethod
    def _build(cls, lean_config: Dict[str, Any], logger: Logger) -> LocalBrokerage:
        logger.info("""
You can generate Coinbase Pro API credentials on the API settings page (https://pro.coinbase.com/profile/api).
When creating the key, make sure you authorize it for View and Trading access.
        """.strip())

        api_key = click.prompt("API key", cls._get_default(lean_config, "gdax-api-key"))
        api_secret = logger.prompt_password("API secret", cls._get_default(lean_config, "gdax-api-secret"))
        passphrase = logger.prompt_password("Passphrase", cls._get_default(lean_config, "gdax-passphrase"))
        sandbox = click.confirm("Use the sandbox?")

        return CoinbaseProBrokerage(api_key, api_secret, passphrase, sandbox)

    def _configure_environment(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        lean_config["environments"][environment_name]["live-mode-brokerage"] = "GDAXBrokerage"
        lean_config["environments"][environment_name]["transaction-handler"] = \
            "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler"

    def configure_credentials(self, lean_config: Dict[str, Any]) -> None:
        lean_config["gdax-api-key"] = self._api_key
        lean_config["gdax-api-secret"] = self._api_secret
        lean_config["gdax-passphrase"] = self._passphrase
        lean_config["gdax-use-sandbox"] = self._sandbox

        if self._sandbox:
            lean_config["gdax-url"] = "wss://ws-feed-public.sandbox.pro.coinbase.com"
            lean_config["gdax-rest-api"] = "https://api-public.sandbox.pro.coinbase.com"
        else:
            lean_config["gdax-url"] = "wss://ws-feed.pro.coinbase.com"
            lean_config["gdax-rest-api"] = "https://api.pro.coinbase.com"

        self._save_properties(lean_config, ["gdax-api-key", "gdax-api-secret", "gdax-passphrase", "gdax-use-sandbox"])


class CoinbaseProDataFeed(LeanConfigConfigurer):
    """A LeanConfigConfigurer implementation for the Coinbase Pro data feed."""

    def __init__(self, brokerage: CoinbaseProBrokerage) -> None:
        self._brokerage = brokerage

    @classmethod
    def get_name(cls) -> str:
        return CoinbaseProBrokerage.get_name()

    @classmethod
    def build(cls, lean_config: Dict[str, Any], logger: Logger) -> LeanConfigConfigurer:
        return CoinbaseProDataFeed(CoinbaseProBrokerage.build(lean_config, logger))

    def configure(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        lean_config["environments"][environment_name]["data-queue-handler"] = "GDAXDataQueueHandler"
        lean_config["environments"][environment_name]["history-provider"] = "BrokerageHistoryProvider"

        self._brokerage.configure_credentials(lean_config)
