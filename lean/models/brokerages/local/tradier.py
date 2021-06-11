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


class TradierBrokerage(LocalBrokerage):
    """A LocalBrokerage implementation for the Tradier brokerage."""

    @classmethod
    def get_name(cls) -> str:
        return "Tradier"

    @classmethod
    def _configure_environment(cls, lean_config: Dict[str, Any], environment_name: str) -> None:
        lean_config["environments"][environment_name]["live-mode-brokerage"] = "TradierBrokerage"
        lean_config["environments"][environment_name]["transaction-handler"] = \
            "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler"

    @classmethod
    def _configure_credentials(cls, lean_config: Dict[str, Any], logger: Logger) -> None:
        logger.info("""
Your Tradier account id and API token can be found on your Settings/API Access page (https://dash.tradier.com/settings/api).
The account id is the alpha-numeric code in a dropdown box on that page.
        """.strip())

        lean_config["tradier-account-id"] = click.prompt("Account id",
                                                         cls._get_default(lean_config, "tradier-account-id"))
        lean_config["tradier-access-token"] = logger.prompt_password(
            "Access token",
            cls._get_default(lean_config, "tradier-access-token")
        )
        lean_config["tradier-use-sandbox"] = click.confirm("Use the developer sandbox?",
                                                           cls._get_default(lean_config, "tradier-use-sandbox"))

        cls._save_properties(lean_config, ["tradier-account-id", "tradier-access-token", "tradier-use-sandbox"])


class TradierDataFeed(LeanConfigConfigurer):
    """A LeanConfigConfigurer implementation for the Tradier data feed."""

    @classmethod
    def get_name(cls) -> str:
        return TradierBrokerage.get_name()

    @classmethod
    def configure(cls, lean_config: Dict[str, Any], environment_name: str, logger: Logger) -> None:
        lean_config["environments"][environment_name]["data-queue-handler"] = "TradierBrokerage"

        TradierBrokerage.configure_credentials(lean_config, logger)
