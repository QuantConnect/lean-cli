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

from pathlib import Path
from typing import Any, Dict, Optional

import click

from lean.click import PathParameter
from lean.components.util.logger import Logger
from lean.constants import BLOOMBERG_PRODUCT_ID
from lean.container import container
from lean.models.brokerages.local.base import LeanConfigConfigurer, LocalBrokerage
from lean.models.logger import Option


class BloombergBrokerage(LocalBrokerage):
    """A LocalBrokerage implementation for the Bloomberg brokerage."""

    _is_module_installed = False

    def __init__(self,
                 organization_id: str,
                 environment: str,
                 server_host: str,
                 server_port: int,
                 symbol_map_file: Optional[Path],
                 emsx_broker: str,
                 emsx_user_time_zone: Optional[str],
                 emsx_account: Optional[str],
                 emsx_strategy: Optional[str],
                 emsx_notes: Optional[str],
                 emsx_handling: Optional[str],
                 allow_modification: bool) -> None:
        self._organization_id = organization_id
        self._environment = environment
        self._server_host = server_host
        self._server_port = server_port
        self._symbol_map_file = symbol_map_file
        self._emsx_broker = emsx_broker
        self._emsx_user_time_zone = emsx_user_time_zone
        self._emsx_account = emsx_account
        self._emsx_strategy = emsx_strategy
        self._emsx_notes = emsx_notes
        self._emsx_handling = emsx_handling
        self._allow_modification = allow_modification

    @classmethod
    def get_name(cls) -> str:
        return "Bloomberg"

    @classmethod
    def _build(cls, lean_config: Dict[str, Any], logger: Logger) -> LocalBrokerage:
        api_client = container.api_client()

        organizations = api_client.organizations.get_all()
        options = [Option(id=organization.id, label=organization.name) for organization in organizations]

        organization_id = logger.prompt_list("Select the organization with the Bloomberg module subscription", options)

        environment = click.prompt("Environment",
                                   cls._get_default(lean_config, "bloomberg-environment"),
                                   type=click.Choice(["Production", "Beta"], case_sensitive=False))

        server_host = click.prompt("Server host", cls._get_default(lean_config, "bloomberg-server-host"))
        server_port = click.prompt("Server port", cls._get_default(lean_config, "bloomberg-server-port"), type=int)

        symbol_map_file = click.prompt("Path to symbol map file",
                                       cls._get_default(lean_config, "bloomberg-symbol-map-file") or "",
                                       type=PathParameter(exists=True, file_okay=True, dir_okay=False))

        emsx_broker = click.prompt("EMSX broker", cls._get_default(lean_config, "bloomberg-emsx-broker"))
        emsx_user_time_zone = click.prompt("EMSX user timezone",
                                           cls._get_default(lean_config, "bloomberg-emsx-user-time-zone") or "UTC")
        emsx_account = click.prompt("EMSX account", cls._get_default(lean_config, "bloomberg-emsx-account") or "")
        emsx_strategy = click.prompt("EMSX strategy", cls._get_default(lean_config, "bloomberg-emsx-strategy") or "")
        emsx_notes = click.prompt("EMSX notes", cls._get_default(lean_config, "bloomberg-emsx-notes") or "")
        emsx_handling = click.prompt("EMSX handling", cls._get_default(lean_config, "bloomberg-emsx-handling") or "")

        allow_modification = click.prompt("Allow modification (yes/no)",
                                          cls._get_default(lean_config, "bloomberg-allow-modification"),
                                          type=bool)

        return BloombergBrokerage(organization_id,
                                  environment,
                                  server_host,
                                  server_port,
                                  symbol_map_file,
                                  emsx_broker,
                                  emsx_user_time_zone,
                                  emsx_account,
                                  emsx_strategy,
                                  emsx_notes,
                                  emsx_handling,
                                  allow_modification)

    def _configure_environment(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        self.ensure_module_installed()

        lean_config["environments"][environment_name]["live-mode-brokerage"] = "BloombergBrokerage"
        lean_config["environments"][environment_name]["transaction-handler"] = \
            "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler"

    def configure_credentials(self, lean_config: Dict[str, Any]) -> None:
        lean_config["job-organization-id"] = self._organization_id
        lean_config["bloomberg-api-type"] = "Desktop"
        lean_config["bloomberg-environment"] = self._environment
        lean_config["bloomberg-server-host"] = self._server_host
        lean_config["bloomberg-server-port"] = self._server_port

        if self._symbol_map_file is not None:
            lean_config["bloomberg-symbol-map-file"] = str(self._symbol_map_file).replace("\\", "/")
        else:
            lean_config["bloomberg-symbol-map-file"] = ""

        lean_config["bloomberg-emsx-broker"] = self._emsx_broker
        lean_config["bloomberg-emsx-user-time-zone"] = self._emsx_user_time_zone or ""
        lean_config["bloomberg-emsx-account"] = self._emsx_account or ""
        lean_config["bloomberg-emsx-strategy"] = self._emsx_strategy or ""
        lean_config["bloomberg-emsx-notes"] = self._emsx_notes or ""
        lean_config["bloomberg-emsx-handling"] = self._emsx_handling or ""
        lean_config["bloomberg-allow-modification"] = self._allow_modification

        self._save_properties(lean_config, ["job-organization-id",
                                            "bloomberg-api-type",
                                            "bloomberg-environment",
                                            "bloomberg-server-host",
                                            "bloomberg-server-port",
                                            "bloomberg-symbol-map-file",
                                            "bloomberg-emsx-broker",
                                            "bloomberg-emsx-user-time-zone",
                                            "bloomberg-emsx-account",
                                            "bloomberg-emsx-strategy",
                                            "bloomberg-emsx-notes",
                                            "bloomberg-emsx-handling",
                                            "bloomberg-allow-modification"])

    def ensure_module_installed(self) -> None:
        if not self._is_module_installed:
            container.module_manager().install_module(BLOOMBERG_PRODUCT_ID, self._organization_id)
            self._is_module_installed = True


class BloombergDataFeed(LeanConfigConfigurer):
    """A LeanConfigConfigurer implementation for the Bloomberg data feed."""

    def __init__(self, brokerage: BloombergBrokerage) -> None:
        self._brokerage = brokerage

    @classmethod
    def get_name(cls) -> str:
        return BloombergBrokerage.get_name()

    @classmethod
    def build(cls, lean_config: Dict[str, Any], logger: Logger) -> LeanConfigConfigurer:
        return BloombergDataFeed(BloombergBrokerage.build(lean_config, logger))

    def configure(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        self._brokerage.ensure_module_installed()

        lean_config["environments"][environment_name]["data-queue-handler"] = "BloombergBrokerage"
        lean_config["environments"][environment_name]["history-provider"] = "BrokerageHistoryProvider"

        self._brokerage.configure_credentials(lean_config)
