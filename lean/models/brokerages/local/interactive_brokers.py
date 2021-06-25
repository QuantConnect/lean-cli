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
from lean.models.errors import MoreInfoError


class InteractiveBrokersBrokerage(LocalBrokerage):
    """A LocalBrokerage implementation for the Interactive Brokers brokerage."""

    def __init__(self, username: str, account_id: str, account_password: str) -> None:
        self._username = username
        self._account_id = account_id
        self._account_password = account_password
        self._agent_description = None
        self._trading_mode = None

        demo_slice = account_id.lower()[:2]
        live_slice = account_id.lower()[0]

        if live_slice == "d":
            if demo_slice == "df" or demo_slice == "du":
                self._agent_description = "Individual"
                self._trading_mode = "paper"
            elif demo_slice == "di":
                # TODO: Remove this once we know what ib-agent-description should be for Advisor accounts
                raise RuntimeError("Please use the --environment option for Advisor accounts")
                self._agent_description = "Advisor"
                self._trading_mode = "paper"
        else:
            if live_slice == "f" or live_slice == "i":
                # TODO: Remove this once we know what ib-agent-description should be for Advisor accounts
                raise RuntimeError("Please use the --environment option for Advisor accounts")
                self._agent_description = "Advisor"
                self._trading_mode = "live"
            elif live_slice == "u":
                self._agent_description = "Individual"
                self._trading_mode = "live"

        if self._trading_mode is None:
            raise MoreInfoError(
                f"Account id '{account_id}' does not look like a valid account id",
                "https://www.lean.io/docs/lean-cli/tutorials/live-trading/local-live-trading#03-Interactive-Brokers"
            )

    @classmethod
    def get_name(cls) -> str:
        return "Interactive Brokers"

    @classmethod
    def _build(cls, lean_config: Dict[str, Any], logger: Logger) -> LocalBrokerage:
        logger.info("""
To use IB with LEAN you must disable two-factor authentication or only use IBKR Mobile.
This is done from your IB Account Manage Account -> Settings -> User Settings -> Security -> Secure Login System.
In the Secure Login System, deselect all options or only select "IB Key Security via IBKR Mobile".
Interactive Brokers Lite accounts do not support API trading.
        """.strip())

        username = click.prompt("Username", cls._get_default(lean_config, "ib-user-name"))
        account_id = click.prompt("Account id", cls._get_default(lean_config, "ib-account"))
        account_password = logger.prompt_password("Account password", cls._get_default(lean_config, "ib-password"))

        return InteractiveBrokersBrokerage(username, account_id, account_password)

    def _configure_environment(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        lean_config["environments"][environment_name]["live-mode-brokerage"] = "InteractiveBrokersBrokerage"
        lean_config["environments"][environment_name]["transaction-handler"] = \
            "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler"

    def configure_credentials(self, lean_config: Dict[str, Any]) -> None:
        lean_config["ib-user-name"] = self._username
        lean_config["ib-account"] = self._account_id
        lean_config["ib-password"] = self._account_password
        lean_config["ib-agent-description"] = self._agent_description
        lean_config["ib-trading-mode"] = self._trading_mode

        self._save_properties(lean_config, ["ib-user-name",
                                            "ib-account",
                                            "ib-password",
                                            "ib-agent-description",
                                            "ib-trading-mode"])


class InteractiveBrokersDataFeed(LeanConfigConfigurer):
    """A LeanConfigConfigurer implementation for the Interactive Brokers data feed."""

    def __init__(self, brokerage: InteractiveBrokersBrokerage, enable_delayed_streaming_data: bool) -> None:
        self._brokerage = brokerage
        self._enable_delayed_streaming_data = enable_delayed_streaming_data

    @classmethod
    def get_name(cls) -> str:
        return InteractiveBrokersBrokerage.get_name()

    @classmethod
    def build(cls, lean_config: Dict[str, Any], logger: Logger) -> LeanConfigConfigurer:
        brokerage = InteractiveBrokersBrokerage.build(lean_config, logger)

        logger.info("""
Delayed market data is used when you subscribe to data for which you don't have a market data subscription on IB.
If delayed market data is disabled, live trading will stop and LEAN will shut down when this happens.
        """.strip())

        enable_delayed_streaming_data = click.confirm(
            "Enable delayed market data?",
            cls._get_default(lean_config, "ib-enable-delayed-streaming-data")
        )

        return InteractiveBrokersDataFeed(brokerage, enable_delayed_streaming_data)

    def configure(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        lean_config["environments"][environment_name]["data-queue-handler"] = \
            "QuantConnect.Brokerages.InteractiveBrokers.InteractiveBrokersBrokerage"
        lean_config["environments"][environment_name]["history-provider"] = "BrokerageHistoryProvider"

        self._brokerage.configure_credentials(lean_config)

        lean_config["ib-enable-delayed-streaming-data"] = self._enable_delayed_streaming_data

        self._save_properties(lean_config, ["ib-enable-delayed-streaming-data"])
