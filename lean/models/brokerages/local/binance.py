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
from lean.constants import BINANCE_PRODUCT_ID
from lean.container import container
from lean.models.brokerages.local.base import LocalBrokerage
from lean.models.config import LeanConfigConfigurer
from lean.models.logger import Option

class BinanceExchange:
    def get_name(self) -> str:
        return "Binance"

    def get_label(self) -> str:
        return "Binance"

    def get_api_endpoint(self) -> str:
        return "https://api.binance.com"

    def get_ws_endpoint(self) -> str:
        return "wss://stream.binance.com:9443/ws"

    def get_domain(self) -> str:
        return "binance.com"

    def prefix(self) -> str:
        return "binance"
    
    def live_mode_brokerage(self) -> str:
        return "BinanceBrokerage"

    def data_queue_handler_name(self) -> str:
        return "BinanceBrokerage"

class BinanceUSExchange(BinanceExchange):
    def get_name(self) -> str:
        return "BinanceUS"

    def get_label(self) -> str:
        return "BinanceUS"

    def get_api_endpoint(self) -> str:
        return "https://api.binance.us"

    def get_ws_endpoint(self) -> str:
        return "wss://stream.binance.us:9443/ws"
    
    def get_domain(self) -> str:
        return "binance.us"
    
    def prefix(self) -> str:
        return "binanceus"

    def live_mode_brokerage(self) -> str:
        return "BinanceUSBrokerage"

    def data_queue_handler_name(self) -> str:
        return "BinanceUSBrokerage"

class BinanceTestnetExchange(BinanceExchange):
    def get_name(self) -> str:
        return "Binance"

    def get_label(self) -> str:
        return "Binance Testnet"

    def get_api_endpoint(self) -> str:
        return "https://testnet.binance.vision"

    def get_ws_endpoint(self) -> str:
        return "wss://testnet.binance.vision/ws"

    def get_domain(self) -> str:
        return "binance.com"

    def prefix(self) -> str:
        return "binance"

    def live_mode_brokerage(self) -> str:
        return "BinanceBrokerage"

    def data_queue_handler_name(self) -> str:
        return "BinanceBrokerage"

class BinanceBrokerage(LocalBrokerage):
    """A LocalBrokerage implementation for the Binance brokerage."""
    _is_module_installed = False
    _exchange: BinanceExchange

    def __init__(self, organization_id: str, api_key: str, api_secret: str, exchange_name: str, testnet: bool) -> None:
        self._organization_id = organization_id
        self._api_key = api_key
        self._api_secret = api_secret
        self._testnet = testnet
        self._exchange_name = exchange_name
        self._exchange = BinanceExchange()
        if(exchange_name.casefold() == "BinanceUS".casefold()):
            self._exchange = BinanceUSExchange()
        elif(testnet):
            self._exchange = BinanceTestnetExchange()

    @classmethod
    def get_name(cls) -> str:
        return "Binance"

    @classmethod
    def _build(cls, lean_config: Dict[str, Any], logger: Logger) -> LocalBrokerage:
        api_client = container.api_client()

        organizations = api_client.organizations.get_all()
        options = [Option(id=organization.id, label=organization.name) for organization in organizations]

        organization_id = logger.prompt_list(
            "Select the organization with the {} module subscription".format(cls.get_name()),
            options
        )

        exchange_name = logger.prompt_list(
            "Binance Exchange",
            [Option(id="Binance", label="Binance"), Option(id="BinanceUS", label="BinanceUS")],
            cls._get_default(lean_config, 'binance-exchange-name')
        )
        exchange: BinanceExchange
        testnet = False
        if(exchange_name.casefold() == "BinanceUS".casefold()):
            exchange = BinanceUSExchange()
        else:
            click.confirm("Use the testnet?")
            if(testnet):
                exchange = BinanceTestnetExchange()
            else:
                exchange = BinanceExchange() 


        logger.info("""
Create an API key by logging in and accessing the {} API Management page (https://www.{}/en/my/settings/api-management).
        """.format(exchange.get_label(), exchange.get_domain()).strip())

        prefix = exchange.prefix()

        api_key = click.prompt("API key", cls._get_default(lean_config, f'{prefix}-api-key'))
        api_secret = logger.prompt_password("API secret", cls._get_default(lean_config, f'{prefix}-api-secret'))

        return BinanceBrokerage(organization_id, api_key, api_secret, exchange_name, testnet)

    def _configure_environment(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        self.ensure_module_installed()

        lean_config["environments"][environment_name]["live-mode-brokerage"] = self._exchange.live_mode_brokerage()
        lean_config["environments"][environment_name]["transaction-handler"] = \
            "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler"

    def configure_credentials(self, lean_config: Dict[str, Any]) -> None:
        prefix = self._exchange.prefix()

        lean_config[f'{prefix}-api-key'] = self._api_key
        lean_config[f'{prefix}-api-secret'] = self._api_secret
        lean_config[f'{prefix}-api-url'] = self._exchange.get_api_endpoint()
        lean_config[f'{prefix}-websocket-url'] = self._exchange.get_ws_endpoint()
        
        lean_config["binance-use-testnet"] = self._testnet
        lean_config["binance-exchange-name"] = self._exchange_name
        lean_config["job-organization-id"] = self._organization_id

        self._save_properties(lean_config, ["job-organization-id", f'{prefix}-api-key', f'{prefix}-api-secret', "binance-use-testnet"])

    def ensure_module_installed(self) -> None:
        if not self._is_module_installed:
            container.module_manager().install_module(BINANCE_PRODUCT_ID, self._organization_id)
            self._is_module_installed = True

class BinanceDataFeed(LeanConfigConfigurer):
    """A LeanConfigConfigurer implementation for the Binance data feed."""

    def __init__(self, brokerage: BinanceBrokerage) -> None:
        self._brokerage = brokerage

    @classmethod
    def get_name(cls) -> str:
        return BinanceBrokerage.get_name()

    @classmethod
    def build(cls, lean_config: Dict[str, Any], logger: Logger) -> LeanConfigConfigurer:
        return BinanceDataFeed(BinanceBrokerage.build(lean_config, logger))

    def configure(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        self._brokerage.ensure_module_installed()

        lean_config["environments"][environment_name]["data-queue-handler"] = self._brokerage._exchange.data_queue_handler_name()
        lean_config["environments"][environment_name]["history-provider"] = "BrokerageHistoryProvider"

        self._brokerage.configure_credentials(lean_config)
