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


class ZerodhaBrokerage(LocalBrokerage):
    """A LocalBrokerage implementation for the Zerodha brokerage."""

    def __init__(self, api_key: str, access_token: str, product_type: str, trading_segment: str) -> None:
        self._api_key = api_key
        self._access_token = access_token
        self._product_type = product_type
        self._trading_segment = trading_segment

    @classmethod
    def get_name(cls) -> str:
        return "Zerodha"

    @classmethod
    def _build(cls, lean_config: Dict[str, Any], logger: Logger) -> LocalBrokerage:
        logger.info("You need API credentials for Kite Connect (https://kite.trade/) to use the Zerodha brokerage.")

        api_key = click.prompt("API key", cls._get_default(lean_config, "zerodha-api-key"))
        access_token = logger.prompt_password("Access token", cls._get_default(lean_config, "zerodha-access-token"))

        logger.info("""
The product type must be set to MIS if you are targeting intraday products, CNC if you are targeting delivery products or NRML if you are targeting carry forward products.
        """.strip())

        product_type = click.prompt(
            "Product type",
            cls._get_default(lean_config, "zerodha-product-type"),
            type=click.Choice(["MIS", "CNC", "NRML"], case_sensitive=False)
        )

        logger.info("""
The trading segment must be set to EQUITY if you are trading equities on NSE or BSE, or COMMODITY if you are trading commodities on MCX.
        """.strip())

        trading_segment = click.prompt(
            "Trading segment",
            cls._get_default(lean_config, "zerodha-trading-segment"),
            type=click.Choice(["EQUITY", "COMMODITY"], case_sensitive=False)
        )

        return ZerodhaBrokerage(api_key, access_token, product_type, trading_segment)

    def _configure_environment(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        lean_config["environments"][environment_name]["live-mode-brokerage"] = "ZerodhaBrokerage"
        lean_config["environments"][environment_name]["transaction-handler"] = \
            "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler"

    def configure_credentials(self, lean_config: Dict[str, Any]) -> None:
        lean_config["zerodha-api-key"] = self._api_key
        lean_config["zerodha-access-token"] = self._access_token
        lean_config["zerodha-product-type"] = self._product_type
        lean_config["zerodha-trading-segment"] = self._trading_segment

        self._save_properties(lean_config, ["zerodha-api-key",
                                            "zerodha-access-token",
                                            "zerodha-product-type",
                                            "zerodha-trading-segment"])


class ZerodhaDataFeed(LeanConfigConfigurer):
    """A LeanConfigConfigurer implementation for the Zerodha data feed."""

    def __init__(self, brokerage: ZerodhaBrokerage, history_subscription: bool) -> None:
        self._brokerage = brokerage
        self._history_subscription = history_subscription

    @classmethod
    def get_name(cls) -> str:
        return ZerodhaBrokerage.get_name()

    @classmethod
    def build(cls, lean_config: Dict[str, Any], logger: Logger) -> LeanConfigConfigurer:
        brokerage = ZerodhaBrokerage.build(lean_config, logger)

        history_subscription = click.confirm(
            "Do you have a history API subscription?",
            cls._get_default(lean_config, "zerodha-history-subscription")
        )

        return ZerodhaDataFeed(brokerage, history_subscription)

    def configure(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        lean_config["environments"][environment_name]["data-queue-handler"] = "ZerodhaBrokerage"
        lean_config["environments"][environment_name]["history-provider"] = "BrokerageHistoryProvider"

        self._brokerage.configure_credentials(lean_config)

        lean_config["zerodha-history-subscription"] = self._history_subscription

        self._save_properties(lean_config, ["zerodha-history-subscription"])
