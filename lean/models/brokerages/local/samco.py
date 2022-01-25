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
from lean.container import container
from lean.constants import SAMCO_PRODUCT_ID
from lean.models.brokerages.local.base import LocalBrokerage
from lean.models.config import LeanConfigConfigurer
from lean.models.logger import Option

class SamcoBrokerage(LocalBrokerage):
    """A LocalBrokerage implementation for the Samco brokerage."""

    _is_module_installed = False

    def __init__(self, organization_id: str, client_id: str, client_password: str, year_of_birth: str, product_type: str, trading_segment: str) -> None:
        self._organization_id = organization_id
        self._client_id = client_id
        self._client_password = client_password
        self._year_of_birth = year_of_birth
        self._product_type = product_type
        self._trading_segment = trading_segment

    @classmethod
    def get_name(cls) -> str:
        return "Samco"

    @classmethod
    def get_module_id(cls) -> int:
        return SAMCO_PRODUCT_ID

    @classmethod
    def _build(cls, lean_config: Dict[str, Any], logger: Logger) -> LocalBrokerage:

        api_client = container.api_client()

        organizations = api_client.organizations.get_all()
        options = [Option(id=organization.id, label=organization.name) for organization in organizations]

        organization_id = logger.prompt_list(
            "Select the organization with the Samco module subscription",
            options
        )

        client_id = click.prompt("Client ID", cls._get_default(lean_config, "samco-client-id"))
        client_password = logger.prompt_password("Client Password", cls._get_default(lean_config, "samco-client-password"))
        year_of_birth = click.prompt("Year of Birth", cls._get_default(lean_config, "samco-year-of-birth"))
        
        logger.info("""
The product type must be set to MIS if you are targeting intraday products, CNC if you are targeting delivery products or NRML if you are targeting carry forward products.
        """.strip())

        product_type = click.prompt(
            "Product type",
            cls._get_default(lean_config, "samco-product-type"),
            type=click.Choice(["MIS", "CNC", "NRML"], case_sensitive=False)
        )

        logger.info("""
The trading segment must be set to EQUITY if you are trading equities on NSE or BSE, or COMMODITY if you are trading commodities on MCX.
        """.strip())

        trading_segment = click.prompt(
            "Trading segment",
            cls._get_default(lean_config, "samco-trading-segment"),
            type=click.Choice(["EQUITY", "COMMODITY"], case_sensitive=False)
        )

        return SamcoBrokerage(organization_id, client_id, client_password, year_of_birth, product_type, trading_segment)

    def _configure_environment(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        self.ensure_module_installed()

        lean_config["environments"][environment_name]["live-mode-brokerage"] = "SamcoBrokerage"
        lean_config["environments"][environment_name]["transaction-handler"] = \
            "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler"

    def configure_credentials(self, lean_config: Dict[str, Any]) -> None:
        lean_config["job-organization-id"] = self._organization_id
        lean_config["samco-client-id"] = self._client_id
        lean_config["samco-client-password"] = self._client_password
        lean_config["samco-year-of-birth"] = self._year_of_birth
        lean_config["samco-product-type"] = self._product_type
        lean_config["samco-trading-segment"] = self._trading_segment
         
        self._save_properties(lean_config, ["job-organization-id",
                                            "samco-client-id",
                                            "samco-client-password",
                                            "samco-year-of-birth",
                                            "samco-product-type",
                                            "samco-trading-segment"])

    def ensure_module_installed(self) -> None:
        if not self._is_module_installed:
            container.module_manager().install_module(self.__class__.get_module_id(), self._organization_id)
            self._is_module_installed = True

class SamcoDataFeed(LeanConfigConfigurer):
    """A LeanConfigConfigurer implementation for the Samco data feed."""

    def __init__(self, brokerage: SamcoBrokerage) -> None:
        self._brokerage = brokerage

    @classmethod
    def get_name(cls) -> str:
        return SamcoBrokerage.get_name()

    @classmethod
    def build(cls, lean_config: Dict[str, Any], logger: Logger) -> LeanConfigConfigurer:
        brokerage = SamcoBrokerage.build(lean_config, logger)

        return SamcoDataFeed(brokerage)
        
    def configure(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        self._brokerage.ensure_module_installed()
        lean_config["environments"][environment_name]["data-queue-handler"] = "SamcoBrokerage"
        lean_config["environments"][environment_name]["history-provider"] = "BrokerageHistoryProvider"

        self._brokerage.configure_credentials(lean_config)
