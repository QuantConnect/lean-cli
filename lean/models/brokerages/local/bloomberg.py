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
from typing import Any, Dict

import click

from lean.click import PathParameter
from lean.components.util.logger import Logger
from lean.container import container
from lean.models.brokerages.local.base import LeanConfigConfigurer, LocalBrokerage
from lean.models.logger import Option


class BloombergBrokerage(LocalBrokerage):
    """A LocalBrokerage implementation for the Bloomberg brokerage."""

    _is_plugin_installed = False

    def __init__(self,
                 organization_id: str,
                 api_type: str,
                 environment: str,
                 server_host: str,
                 server_port: int,
                 symbol_map_file: Path) -> None:
        self._organization_id = organization_id
        self._api_type = api_type
        self._environment = environment
        self._server_host = server_host
        self._server_port = server_port
        self._symbol_map_file = symbol_map_file

    @classmethod
    def get_name(cls) -> str:
        return "Bloomberg"

    @classmethod
    def _build(cls, lean_config: Dict[str, Any], logger: Logger) -> LocalBrokerage:
        api_client = container.api_client()

        organizations = api_client.organizations.get_all()
        options = [Option(id=organization.id, label=organization.name) for organization in organizations]

        organization_id = logger.prompt_list("Select the organization with the Bloomberg plugin subscription", options)

        api_type = click.prompt("API type",
                                cls._get_default(lean_config, "bloomberg-api-type"),
                                type=click.Choice(["Desktop", "Server", "Bpipe"], case_sensitive=False))

        environment = click.prompt("Environment",
                                   cls._get_default(lean_config, "bloomberg-environment"),
                                   type=click.Choice(["Production", "Beta"], case_sensitive=False))

        server_host = click.prompt("Server host", cls._get_default(lean_config, "bloomberg-server-host"))
        server_port = click.prompt("Server port", cls._get_default(lean_config, "bloomberg-server-port"), type=int)
        symbol_map_file = click.prompt("Path to symbol map file",
                                       cls._get_default(lean_config, "bloomberg-symbol-map-file"),
                                       type=PathParameter(exists=True, file_okay=True, dir_okay=False))

        return BloombergBrokerage(organization_id, api_type, environment, server_host, server_port, symbol_map_file)

    def _configure_environment(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        self.ensure_plugin_installed()

        lean_config["environments"][environment_name]["live-mode-brokerage"] = "BloombergBrokerage"
        lean_config["environments"][environment_name]["transaction-handler"] = \
            "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler"

    def configure_credentials(self, lean_config: Dict[str, Any]) -> None:
        lean_config["bloomberg-organization-id"] = self._organization_id
        lean_config["bloomberg-api-type"] = self._api_type
        lean_config["bloomberg-environment"] = self._environment
        lean_config["bloomberg-server-host"] = self._server_host
        lean_config["bloomberg-server-port"] = self._server_port
        lean_config["bloomberg-symbol-map-file"] = str(self._symbol_map_file).replace("\\", "/")

        self._save_properties(lean_config, ["bloomberg-organization-id",
                                            "bloomberg-api-type",
                                            "bloomberg-environment",
                                            "bloomberg-server-host",
                                            "bloomberg-server-port",
                                            "bloomberg-symbol-map-file"])

    def ensure_plugin_installed(self) -> None:
        if not self._is_plugin_installed:
            container.plugin_manager().install_plugin("bloomberg", self._organization_id)
            self._is_plugin_installed = True


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
        self._brokerage.ensure_plugin_installed()

        lean_config["environments"][environment_name]["data-queue-handler"] = "BloombergBrokerage"
        lean_config["environments"][environment_name]["history-provider"] = "BrokerageHistoryProvider"

        self._brokerage.configure_credentials(lean_config)
