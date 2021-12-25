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
from lean.constants import FTX_PRODUCT_ID
from lean.container import container
from lean.models.brokerages.local.base import LocalBrokerage
from lean.models.config import LeanConfigConfigurer
from lean.models.logger import Option


class FTXBrokerage(LocalBrokerage):
    """A LocalBrokerage implementation for the FTX brokerage."""

    _is_module_installed = False

    def __init__(self, organization_id: str, api_key: str, api_secret: str, account_tier: str) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._account_tier = account_tier
        self._organization_id = organization_id

    @classmethod
    def get_name(cls) -> str:
        return "FTX"

    @classmethod
    def _build(cls, lean_config: Dict[str, Any], logger: Logger) -> LocalBrokerage:
        api_client = container.api_client()

        organizations = api_client.organizations.get_all()
        options = [Option(id=organization.id, label=organization.name) for organization in organizations]

        organization_id = logger.prompt_list(
            "Select the organization with the FTX module subscription",
            options
        )

        logger.info("""
Create an API key by logging in and accessing the FTX Profile page (https://ftx.com/profile).
        """.strip())

        api_key = click.prompt("API key", cls._get_default(lean_config, "ftx-api-key"))
        api_secret = logger.prompt_password("API secret", cls._get_default(lean_config, "ftx-api-secret"))

        account_tier = logger.prompt_list(
            "Select the Account Tier",
            [Option(id="Tier1", label="Tier1"),
             Option(id="Tier2", label="Tier2"),
             Option(id="Tier3", label="Tier3"),
             Option(id="Tier4", label="Tier4"),
             Option(id="Tier5", label="Tier5"),
             Option(id="Tier6", label="Tier6"),
             Option(id="VIP1", label="VIP1"),
             Option(id="VIP2", label="VIP2"),
             Option(id="VIP3", label="VIP3"),
             Option(id="MM1", label="MM1"),
             Option(id="MM2", label="MM2"),
             Option(id="MM3", label="MM3")],
            cls._get_default(lean_config, "ftx-account-tier")
        )

        return FTXBrokerage(organization_id, api_key, api_secret, account_tier)

    def _configure_environment(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        self.ensure_module_installed()

        lean_config["environments"][environment_name]["live-mode-brokerage"] = "FTXBrokerage"
        lean_config["environments"][environment_name]["transaction-handler"] = \
            "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler"

    def configure_credentials(self, lean_config: Dict[str, Any]) -> None:
        lean_config["ftx-api-key"] = self._api_key
        lean_config["ftx-api-secret"] = self._api_secret
        lean_config["ftx-account-tier"] = self._account_tier
        lean_config["job-organization-id"] = self._organization_id

        self._save_properties(lean_config, ["job-organization-id", "ftx-api-key", "ftx-api-secret", "ftx-account-tier"])

    def ensure_module_installed(self) -> None:
        if not self._is_module_installed:
            container.module_manager().install_module(FTX_PRODUCT_ID, self._organization_id)
            self._is_module_installed = True

class FTXDataFeed(LeanConfigConfigurer):
    """A LeanConfigConfigurer implementation for the FTX data feed."""

    def __init__(self, brokerage: FTXBrokerage) -> None:
        self._brokerage = brokerage

    @classmethod
    def get_name(cls) -> str:
        return FTXBrokerage.get_name()

    @classmethod
    def build(cls, lean_config: Dict[str, Any], logger: Logger) -> LeanConfigConfigurer:
        return FTXDataFeed(FTXBrokerage.build(lean_config, logger))

    def configure(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        self._brokerage.ensure_module_installed()

        lean_config["environments"][environment_name]["data-queue-handler"] = "FTXBrokerage"
        lean_config["environments"][environment_name]["history-provider"] = "BrokerageHistoryProvider"

        self._brokerage.configure_credentials(lean_config)
