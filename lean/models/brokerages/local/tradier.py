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


class TradierBrokerage(LocalBrokerage):
    """A LocalBrokerage implementation for the Tradier brokerage."""

    def __init__(self, account_id: str, access_token: str, use_sandbox: bool) -> None:
        self._account_id = account_id
        self._access_token = access_token
        self._use_sandbox = use_sandbox

    @classmethod
    def get_name(cls) -> str:
        return "Tradier"

    @classmethod
    def _build(cls, lean_config: Dict[str, Any], logger: Logger) -> LocalBrokerage:
        logger.info("""
Your Tradier account id and API token can be found on your Settings/API Access page (https://dash.tradier.com/settings/api).
The account id is the alpha-numeric code in a dropdown box on that page.
        """.strip())

        account_id = click.prompt("Account id", cls._get_default(lean_config, "tradier-account-id"))
        access_token = logger.prompt_password("Access token", cls._get_default(lean_config, "tradier-access-token"))
        use_sandbox = click.confirm("Use the developer sandbox?", cls._get_default(lean_config, "tradier-use-sandbox"))

        return TradierBrokerage(account_id, access_token, use_sandbox)

    def _configure_environment(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        lean_config["environments"][environment_name]["live-mode-brokerage"] = "TradierBrokerage"
        lean_config["environments"][environment_name]["transaction-handler"] = \
            "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler"

    def configure_credentials(self, lean_config: Dict[str, Any]) -> None:
        lean_config["tradier-account-id"] = self._account_id
        lean_config["tradier-access-token"] = self._access_token
        lean_config["tradier-use-sandbox"] = self._use_sandbox

        self._save_properties(lean_config, ["tradier-account-id", "tradier-access-token", "tradier-use-sandbox"])


class TradierDataFeed(LeanConfigConfigurer):
    """A LeanConfigConfigurer implementation for the Tradier data feed."""

    def __init__(self, brokerage: TradierBrokerage) -> None:
        self._brokerage = brokerage

    @classmethod
    def get_name(cls) -> str:
        return TradierBrokerage.get_name()

    @classmethod
    def build(cls, lean_config: Dict[str, Any], logger: Logger) -> LeanConfigConfigurer:
        return TradierDataFeed(TradierBrokerage.build(lean_config, logger))

    def configure(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        lean_config["environments"][environment_name]["data-queue-handler"] = "TradierBrokerage"

        self._brokerage.configure_credentials(lean_config)
