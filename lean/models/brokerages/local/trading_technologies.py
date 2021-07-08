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
from lean.constants import TRADING_TECHNOLOGIES_PRODUCT_ID
from lean.container import container
from lean.models.brokerages.local.base import LeanConfigConfigurer, LocalBrokerage
from lean.models.logger import Option


class TradingTechnologiesBrokerage(LocalBrokerage):
    """A LocalBrokerage implementation for the Trading Technologies brokerage."""

    _is_module_installed = False

    def __init__(self,
                 organization_id: str,
                 user_name: str,
                 session_password: str,
                 account_name: str,
                 rest_app_key: str,
                 rest_app_secret: str,
                 rest_environment: str,
                 market_data_sender_comp_id: str,
                 market_data_target_comp_id: str,
                 market_data_host: str,
                 market_data_port: str,
                 order_routing_sender_comp_id: str,
                 order_routing_target_comp_id: str,
                 order_routing_host: str,
                 order_routing_port: str,
                 log_fix_messages: bool) -> None:
        self._organization_id = organization_id
        self._user_name = user_name
        self._session_password = session_password
        self._account_name = account_name
        self._rest_app_key = rest_app_key
        self._rest_app_secret = rest_app_secret
        self._rest_environment = rest_environment
        self._market_data_sender_comp_id = market_data_sender_comp_id
        self._market_data_target_comp_id = market_data_target_comp_id
        self._market_data_host = market_data_host
        self._market_data_port = market_data_port
        self._order_routing_sender_comp_id = order_routing_sender_comp_id
        self._order_routing_target_comp_id = order_routing_target_comp_id
        self._order_routing_host = order_routing_host
        self._order_routing_port = order_routing_port
        self._log_fix_messages = log_fix_messages

    @classmethod
    def get_name(cls) -> str:
        return "Trading Technologies"

    @classmethod
    def _build(cls, lean_config: Dict[str, Any], logger: Logger) -> LocalBrokerage:
        api_client = container.api_client()

        organizations = api_client.organizations.get_all()
        options = [Option(id=organization.id, label=organization.name) for organization in organizations]

        organization_id = logger.prompt_list(
            "Select the organization with the Trading Technologies module subscription",
            options
        )

        user_name = click.prompt("User name", cls._get_default(lean_config, "tt-user-name"))
        session_password = logger.prompt_password("Session password",
                                                  cls._get_default(lean_config, "tt-session-password"))
        account_name = click.prompt("Account name", cls._get_default(lean_config, "tt-account-name"))

        rest_app_key = click.prompt("REST app key", cls._get_default(lean_config, "tt-rest-app-key"))
        rest_app_secret = logger.prompt_password("REST app secret", cls._get_default(lean_config, "tt-rest-app-secret"))
        rest_environment = click.prompt("REST environment", cls._get_default(lean_config, "tt-rest-environment"))

        market_data_sender_comp_id = click.prompt("Market data sender comp id",
                                                  cls._get_default(lean_config, "tt-market-data-sender-comp-id"))
        market_data_target_comp_id = click.prompt("Market data target comp id",
                                                  cls._get_default(lean_config, "tt-market-data-target-comp-id"))
        market_data_host = click.prompt("Market data host", cls._get_default(lean_config, "tt-market-data-host"))
        market_data_port = click.prompt("Market data port", cls._get_default(lean_config, "tt-market-data-port"))

        order_routing_sender_comp_id = click.prompt("Order routing sender comp id",
                                                    cls._get_default(lean_config, "tt-order-routing-sender-comp-id"))
        order_routing_target_comp_id = click.prompt("Order routing target comp id",
                                                    cls._get_default(lean_config, "tt-order-routing-target-comp-id"))
        order_routing_host = click.prompt("Order routing host", cls._get_default(lean_config, "tt-order-routing-host"))
        order_routing_port = click.prompt("Order routing port", cls._get_default(lean_config, "tt-order-routing-port"))

        log_fix_messages = click.prompt("Log FIX messages (yes/no)",
                                        cls._get_default(lean_config, "tt-log-fix-messages"),
                                        type=bool)

        return TradingTechnologiesBrokerage(organization_id,
                                            user_name,
                                            session_password,
                                            account_name,
                                            rest_app_key,
                                            rest_app_secret,
                                            rest_environment,
                                            market_data_sender_comp_id,
                                            market_data_target_comp_id,
                                            market_data_host,
                                            market_data_port,
                                            order_routing_sender_comp_id,
                                            order_routing_target_comp_id,
                                            order_routing_host,
                                            order_routing_port,
                                            log_fix_messages)

    def _configure_environment(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        self.ensure_module_installed()

        lean_config["environments"][environment_name]["live-mode-brokerage"] = "TradingTechnologiesBrokerage"
        lean_config["environments"][environment_name]["transaction-handler"] = \
            "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler"

    def configure_credentials(self, lean_config: Dict[str, Any]) -> None:
        lean_config["job-organization-id"] = self._organization_id
        lean_config["tt-user-name"] = self._user_name
        lean_config["tt-session-password"] = self._session_password
        lean_config["tt-account-name"] = self._account_name
        lean_config["tt-rest-app-key"] = self._rest_app_key
        lean_config["tt-rest-app-secret"] = self._rest_app_secret
        lean_config["tt-rest-environment"] = self._rest_environment
        lean_config["tt-market-data-sender-comp-id"] = self._market_data_sender_comp_id
        lean_config["tt-market-data-target-comp-id"] = self._market_data_target_comp_id
        lean_config["tt-market-data-host"] = self._market_data_host
        lean_config["tt-market-data-port"] = self._market_data_port
        lean_config["tt-order-routing-sender-comp-id"] = self._order_routing_sender_comp_id
        lean_config["tt-order-routing-target-comp-id"] = self._order_routing_target_comp_id
        lean_config["tt-order-routing-host"] = self._order_routing_host
        lean_config["tt-order-routing-port"] = self._order_routing_port
        lean_config["tt-log-fix-messages"] = self._log_fix_messages

        self._save_properties(lean_config, ["job-organization-id",
                                            "tt-user-name",
                                            "tt-session-password",
                                            "tt-account-name",
                                            "tt-rest-app-key",
                                            "tt-rest-app-secret",
                                            "tt-rest-environment",
                                            "tt-market-data-sender-comp-id",
                                            "tt-market-data-target-comp-id",
                                            "tt-market-data-host",
                                            "tt-market-data-port",
                                            "tt-order-routing-sender-comp-id",
                                            "tt-order-routing-target-comp-id",
                                            "tt-order-routing-host",
                                            "tt-order-routing-port",
                                            "tt-log-fix-messages"])

    def ensure_module_installed(self) -> None:
        if not self._is_module_installed:
            container.module_manager().install_module(TRADING_TECHNOLOGIES_PRODUCT_ID, self._organization_id)
            self._is_module_installed = True


class TradingTechnologiesDataFeed(LeanConfigConfigurer):
    """A LeanConfigConfigurer implementation for the Trading Technologies data feed."""

    def __init__(self, brokerage: TradingTechnologiesBrokerage) -> None:
        self._brokerage = brokerage

    @classmethod
    def get_name(cls) -> str:
        return TradingTechnologiesBrokerage.get_name()

    @classmethod
    def build(cls, lean_config: Dict[str, Any], logger: Logger) -> LeanConfigConfigurer:
        return TradingTechnologiesDataFeed(TradingTechnologiesBrokerage.build(lean_config, logger))

    def configure(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        self._brokerage.ensure_module_installed()

        lean_config["environments"][environment_name]["data-queue-handler"] = "TradingTechnologiesBrokerage"
        lean_config["environments"][environment_name]["history-provider"] = "BrokerageHistoryProvider"

        self._brokerage.configure_credentials(lean_config)
