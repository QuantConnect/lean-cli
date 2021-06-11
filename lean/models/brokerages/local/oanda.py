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


class OANDABrokerage(LocalBrokerage):
    """A LocalBrokerage implementation for the OANDA brokerage."""

    @classmethod
    def get_name(cls) -> str:
        return "OANDA"

    @classmethod
    def _configure_environment(cls, lean_config: Dict[str, Any], environment_name: str) -> None:
        lean_config["environments"][environment_name]["live-mode-brokerage"] = "OandaBrokerage"
        lean_config["environments"][environment_name]["transaction-handler"] = \
            "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler"

    @classmethod
    def _configure_credentials(cls, lean_config: Dict[str, Any], logger: Logger) -> None:
        logger.info("""
Your OANDA account id can be found on your OANDA Account Statement page (https://www.oanda.com/account/statement/).
It follows the following format: ###-###-######-###.
You can generate an API token from the Manage API Access page (https://www.oanda.com/account/tpa/personal_token).
        """.strip())

        lean_config["oanda-account-id"] = click.prompt("Account id", cls._get_default(lean_config, "oanda-account-id"))
        lean_config["oanda-access-token"] = logger.prompt_password("Access token",
                                                                   cls._get_default(lean_config, "oanda-access-token"))

        default_environment = cls._get_default(lean_config, "oanda-environment")
        environment = click.prompt("Environment",
                                   default_environment.lower() if default_environment is not None else None,
                                   type=click.Choice(["practice", "trade"], case_sensitive=False))
        lean_config["oanda-environment"] = environment.title()

        cls._save_properties(lean_config, ["oanda-account-id", "oanda-access-token", "oanda-environment"])


class OANDADataFeed(LeanConfigConfigurer):
    """A LeanConfigConfigurer implementation for the OANDA data feed."""

    @classmethod
    def get_name(cls) -> str:
        return OANDABrokerage.get_name()

    @classmethod
    def configure(cls, lean_config: Dict[str, Any], environment_name: str, logger: Logger) -> None:
        lean_config["environments"][environment_name]["data-queue-handler"] = "OandaBrokerage"
        lean_config["environments"][environment_name]["history-provider"] = "BrokerageHistoryProvider"

        OANDABrokerage.configure_credentials(lean_config, logger)
