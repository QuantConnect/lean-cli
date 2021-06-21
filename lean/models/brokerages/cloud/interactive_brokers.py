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
from lean.models.errors import MoreInfoError


class InteractiveBrokersBrokerage(CloudBrokerage):
    """A CloudBrokerage implementation for Interactive Brokers."""

    def __init__(self, username: str, account_id: str, account_password: str, use_ib_feed: bool) -> None:
        self._username = username
        self._account_id = account_id
        self._account_password = account_password
        self._account_type = None
        self._environment = None

        self._use_ib_feed = use_ib_feed

        demo_slice = account_id.lower()[:2]
        live_slice = account_id.lower()[0]

        if live_slice == "d":
            if demo_slice == "df" or demo_slice == "du":
                self._account_type = "individual"
                self._environment = "paper"
            elif demo_slice == "di":
                self._account_type = "advisor"
                self._environment = "paper"
        else:
            if live_slice == "f" or live_slice == "i":
                self._account_type = "advisor"
                self._environment = "live"
            elif live_slice == "u":
                self._account_type = "individual"
                self._environment = "live"

        if self._environment is None:
            raise MoreInfoError(f"Account id '{account_id}' does not look like a valid account name",
                                "https://www.lean.io/docs/lean-cli/tutorials/live-trading/cloud-live-trading#03-Interactive-Brokers")

    @classmethod
    def get_id(cls) -> str:
        return "InteractiveBrokersBrokerage"

    @classmethod
    def get_name(cls) -> str:
        return "Interactive Brokers"

    @classmethod
    def build(cls, logger: Logger) -> CloudBrokerage:
        logger.info("""
To use IB with QuantConnect you must disable two-factor authentication or only use IBKR Mobile.
This is done from your IB Account Manage Account -> Settings -> User Settings -> Security -> Secure Login System.
In the Secure Login System, deselect all options or only select "IB Key Security via IBKR Mobile".
Your account details are not saved on QuantConnect.
Interactive Brokers Lite accounts do not support API trading.
        """.strip())

        username = click.prompt("Username")
        account_id = click.prompt("Account id")
        account_password = logger.prompt_password("Account password")

        use_ib_feed = click.confirm(
            "Do you want to use the Interactive Brokers price data feed instead of the QuantConnect price data feed?",
            default=False
        )

        return InteractiveBrokersBrokerage(username, account_id, account_password, use_ib_feed)

    def _get_settings(self) -> Dict[str, str]:
        return {
            "user": self._username,
            "account": self._account_id,
            "password": self._account_password,
            "accountType": self._account_type,
            "environment": self._environment
        }

    def get_price_data_handler(self) -> str:
        return "InteractiveBrokersHandler" if self._use_ib_feed else "QuantConnectHandler"
