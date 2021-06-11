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
from lean.models.brokerages.local.base import LeanConfigConfigurer, LocalBrokerage


class BitfinexBrokerage(LocalBrokerage):
    """A LocalBrokerage implementation for the Bitfinex brokerage."""

    @classmethod
    def get_name(cls) -> str:
        return "Bitfinex"

    @classmethod
    def _configure_environment(cls, lean_config: Dict[str, Any], environment_name: str) -> None:
        lean_config["environments"][environment_name]["live-mode-brokerage"] = "BitfinexBrokerage"
        lean_config["environments"][environment_name]["transaction-handler"] = \
            "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler"

    @classmethod
    def _configure_credentials(cls, lean_config: Dict[str, Any], logger: Logger) -> None:
        logger.info("""
Create an API key by logging in and accessing the Bitfinex API Management page (https://www.bitfinex.com/api).
        """.strip())

        lean_config["bitfinex-api-key"] = click.prompt("API key", cls._get_default(lean_config, "bitfinex-api-key"))
        lean_config["bitfinex-api-secret"] = logger.prompt_password(
            "API secret",
            cls._get_default(lean_config, "bitfinex-api-secret")
        )

        cls._save_properties(lean_config, ["bitfinex-api-key", "bitfinex-api-secret"])


class BitfinexDataFeed(LeanConfigConfigurer):
    """A LeanConfigConfigurer implementation for the Bitfinex data feed."""

    @classmethod
    def get_name(cls) -> str:
        return BitfinexBrokerage.get_name()

    @classmethod
    def configure(cls, lean_config: Dict[str, Any], environment_name: str, logger: Logger) -> None:
        lean_config["environments"][environment_name]["data-queue-handler"] = "BitfinexBrokerage"
        lean_config["environments"][environment_name]["history-provider"] = "BrokerageHistoryProvider"

        BitfinexBrokerage.configure_credentials(lean_config, logger)
