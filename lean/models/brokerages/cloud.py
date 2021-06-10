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

import abc
from typing import Dict, Optional

import click

from lean.components.util.logger import Logger
from lean.models.errors import MoreInfoError


class CloudBrokerage(abc.ABC):
    """The CloudBrokerage class is the base class extended for all brokerages supported in the cloud."""

    def __init__(self, id: str, name: str, notes: Optional[str] = None) -> None:
        """Creates a new BaseBrokerage instance.

        :param id: the id of the brokerage
        :param name: the display-friendly name of the brokerage
        :param notes: notes which need to be shown before prompting for settings
        """
        self.id = id
        self.name = name
        self._notes = notes

    def get_settings(self, logger: Logger) -> Dict[str, str]:
        """Returns all settings for this brokerage, prompting the user for input when necessary.

        :param logger: the logger to use for printing instructions
        """
        if self._notes is not None:
            logger.info(self._notes)

        settings = self._get_settings(logger)
        settings["id"] = self.id

        return settings

    def get_price_data_handler(self) -> str:
        """Returns the price data feed handler to use."""
        return "QuantConnectHandler"

    @abc.abstractmethod
    def _get_settings(self, logger: Logger) -> Dict[str, str]:
        """Returns the brokerage-specific settings, prompting the user for input when necessary.

        :param logger: the logger to use when prompting for passwords
        :return: a dict containing the brokerage-specific settings (all settings except for "id")
        """
        pass


class PaperTradingBrokerage(CloudBrokerage):
    """A CloudBrokerage implementation for paper trading."""

    def __init__(self) -> None:
        super().__init__("QuantConnectBrokerage", "Paper Trading")

    def _get_settings(self, logger: Logger) -> Dict[str, str]:
        return {
            "environment": "paper"
        }


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


class TradierBrokerage(CloudBrokerage):
    """A CloudBrokerage implementation for Tradier."""

    def __init__(self) -> None:
        super().__init__("TradierBrokerage", "Tradier (beta)", """
Your Tradier account id and API token can be found on your Settings/API Access page (https://dash.tradier.com/settings/api).
The account id is the alpha-numeric code in a dropdown box on that page.
Your account details are not saved on QuantConnect.
        """.strip())

    def _get_settings(self, logger: Logger) -> Dict[str, str]:
        account_id = click.prompt("Account id")
        access_token = logger.prompt_password("Access token")

        environment = click.prompt("Environment", type=click.Choice(["demo", "real"], case_sensitive=False))

        return {
            "account": account_id,
            "token": access_token,
            "environment": "live" if environment == "real" else "paper"
        }


class OANDABrokerage(CloudBrokerage):
    """A CloudBrokerage implementation for OANDA."""

    def __init__(self) -> None:
        super().__init__("OandaBrokerage", "OANDA", """
Your OANDA account number can be found on your OANDA Account Statement page (https://www.oanda.com/account/statement/).
It follows the following format: ###-###-######-###.
You can generate an API token from the Manage API Access page (https://www.oanda.com/account/tpa/personal_token).
Your account details are not saved on QuantConnect.
        """.strip())

    def _get_settings(self, logger: Logger) -> Dict[str, str]:
        account_id = click.prompt("Account id")
        access_token = logger.prompt_password("Access token")

        environment = click.prompt("Environment", type=click.Choice(["demo", "real"], case_sensitive=False))

        return {
            "account": account_id,
            "key": access_token,
            "environment": "live" if environment == "real" else "paper"
        }


class BitfinexBrokerage(CloudBrokerage):
    """A CloudBrokerage implementation for Bitfinex."""

    def __init__(self) -> None:
        super().__init__("BitfinexBrokerage", "Bitfinex (beta)", """
Create an API key by logging in and accessing the Bitfinex API Management page (https://www.bitfinex.com/api).
        """.strip())

    def _get_settings(self, logger: Logger) -> Dict[str, str]:
        api_key = click.prompt("API key")
        secret_key = logger.prompt_password("Secret key")

        return {
            "key": api_key,
            "secret": secret_key,
            "environment": "live"
        }


class CoinbaseProBrokerage(CloudBrokerage):
    """A CloudBrokerage implementation for Coinbase Pro."""

    def __init__(self) -> None:
        super().__init__("GDAXBrokerage", "Coinbase Pro", """
You can generate Coinbase Pro API credentials on the API settings page (https://pro.coinbase.com/profile/api).
When creating the key, make sure you authorize it for View and Trading access.
        """.strip())

    def _get_settings(self, logger: Logger) -> Dict[str, str]:
        api_key = click.prompt("API key")
        api_secret = logger.prompt_password("API secret")
        passphrase = logger.prompt_password("Passphrase")

        return {
            "key": api_key,
            "secret": api_secret,
            "passphrase": passphrase,
            "environment": "live"
        }


all_cloud_brokerages = [
    PaperTradingBrokerage(),
    InteractiveBrokersBrokerage(),
    TradierBrokerage(),
    OANDABrokerage(),
    BitfinexBrokerage(),
    CoinbaseProBrokerage()
]
