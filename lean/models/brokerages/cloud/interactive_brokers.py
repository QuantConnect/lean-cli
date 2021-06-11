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

    def __init__(self) -> None:
        super().__init__("InteractiveBrokersBrokerage", "Interactive Brokers", """
To use IB with QuantConnect you must disable two-factor authentication or only use IBKR Mobile.
This is done from your IB Account Manage Account -> Settings -> User Settings -> Security -> Secure Login System.
In the Secure Login System, deselect all options or only select "IB Key Security via IBKR Mobile".
Your account details are not saved on QuantConnect.
Interactive Brokers Lite accounts do not support API trading.
        """.strip())

    def _get_settings(self, logger: Logger) -> Dict[str, str]:
        username = click.prompt("Username")
        account_id = click.prompt("Account id")
        account_password = logger.prompt_password("Account password")

        account_type = None
        environment = None

        demo_slice = account_id.lower()[:2]
        live_slice = account_id.lower()[0]

        if live_slice == "d":
            if demo_slice == "df" or demo_slice == "du":
                account_type = "individual"
                environment = "paper"
            elif demo_slice == "di":
                account_type = "advisor"
                environment = "paper"
        else:
            if live_slice == "f" or live_slice == "i":
                account_type = "advisor"
                environment = "live"
            elif live_slice == "u":
                account_type = "individual"
                environment = "live"

        if environment is None:
            raise MoreInfoError(f"Account id '{account_id}' does not look like a valid account name",
                                "https://www.lean.io/docs/lean-cli/tutorials/live-trading/cloud-live-trading#03-Interactive-Brokers")

        return {
            "user": username,
            "account": account_id,
            "password": account_password,
            "accountType": account_type,
            "environment": environment
        }

    def get_price_data_handler(self) -> str:
        message = "Do you want to use the Interactive Brokers price data feed instead of the QuantConnect price data feed?"
        return "InteractiveBrokersHandler" if click.confirm(message, default=False) else "QuantConnectHandler"
