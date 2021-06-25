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


class OANDABrokerage(LocalBrokerage):
    """A LocalBrokerage implementation for the OANDA brokerage."""

    def __init__(self, account_id: str, access_token: str, environment: str) -> None:
        self._account_id = account_id
        self._access_token = access_token
        self._environment = environment

    @classmethod
    def get_name(cls) -> str:
        return "OANDA"

    @classmethod
    def _build(cls, lean_config: Dict[str, Any], logger: Logger) -> LocalBrokerage:
        logger.info("""
Your OANDA account id can be found on your OANDA Account Statement page (https://www.oanda.com/account/statement/).
It follows the following format: ###-###-######-###.
You can generate an API token from the Manage API Access page (https://www.oanda.com/account/tpa/personal_token).
        """.strip())

        account_id = click.prompt("Account id", cls._get_default(lean_config, "oanda-account-id"))
        access_token = logger.prompt_password("Access token", cls._get_default(lean_config, "oanda-access-token"))
        environment = click.prompt("Environment",
                                   cls._get_default(lean_config, "oanda-environment"),
                                   type=click.Choice(["Practice", "Trade"], case_sensitive=False))

        return OANDABrokerage(account_id, access_token, environment)

    def _configure_environment(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        lean_config["environments"][environment_name]["live-mode-brokerage"] = "OandaBrokerage"
        lean_config["environments"][environment_name]["transaction-handler"] = \
            "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler"

    def configure_credentials(self, lean_config: Dict[str, Any]) -> None:
        lean_config["oanda-account-id"] = self._account_id
        lean_config["oanda-access-token"] = self._access_token
        lean_config["oanda-environment"] = self._environment

        self._save_properties(lean_config, ["oanda-account-id", "oanda-access-token", "oanda-environment"])


class OANDADataFeed(LeanConfigConfigurer):
    """A LeanConfigConfigurer implementation for the OANDA data feed."""

    def __init__(self, brokerage: OANDABrokerage) -> None:
        self._brokerage = brokerage

    @classmethod
    def get_name(cls) -> str:
        return OANDABrokerage.get_name()

    @classmethod
    def build(cls, lean_config: Dict[str, Any], logger: Logger) -> LeanConfigConfigurer:
        return OANDADataFeed(OANDABrokerage.build(lean_config, logger))

    def configure(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        lean_config["environments"][environment_name]["data-queue-handler"] = "OandaBrokerage"
        lean_config["environments"][environment_name]["history-provider"] = "BrokerageHistoryProvider"

        self._brokerage.configure_credentials(lean_config)
