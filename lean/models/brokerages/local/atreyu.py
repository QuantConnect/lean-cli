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
from lean.constants import ATREYU_PRODUCT_ID
from lean.container import container
from lean.models.brokerages.local.base import LocalBrokerage
from lean.models.logger import Option


class AtreyuBrokerage(LocalBrokerage):
    """A LocalBrokerage implementation for the Atreyu brokerage."""

    _is_module_installed = False

    def __init__(self,
                 organization_id: str,
                 host: str,
                 req_port: int,
                 sub_port: int,
                 username: str,
                 password: str,
                 client_id: str,
                 broker_mpid: str,
                 locate_rqd: str) -> None:
        self._organization_id = organization_id
        self._host = host
        self._req_port = req_port
        self._sub_port = sub_port
        self._username = username
        self._password = password
        self._client_id = client_id
        self._broker_mpid = broker_mpid
        self._locate_rqd = locate_rqd

    @classmethod
    def get_name(cls) -> str:
        return "Atreyu"

    @classmethod
    def _build(cls, lean_config: Dict[str, Any], logger: Logger) -> LocalBrokerage:
        api_client = container.api_client()

        organizations = api_client.organizations.get_all()
        options = [Option(id=organization.id, label=organization.name) for organization in organizations]

        organization_id = logger.prompt_list("Select the organization with the Atreyu module subscription", options)

        host = click.prompt("Host", cls._get_default(lean_config, "atreyu-host"))
        req_port = click.prompt("Request port", cls._get_default(lean_config, "atreyu-req-port"), type=int)
        sub_port = click.prompt("Subscribe port", cls._get_default(lean_config, "atreyu-sub-port"), type=int)

        username = click.prompt("Username", cls._get_default(lean_config, "atreyu-username"))
        password = logger.prompt_password("Password", cls._get_default(lean_config, "atreyu-password"))
        client_id = click.prompt("Client id", cls._get_default(lean_config, "atreyu-client-id"))
        broker_mpid = click.prompt("Broker MPID", cls._get_default(lean_config, "atreyu-broker-mpid"))
        locate_rqd = click.prompt("Locate rqd", cls._get_default(lean_config, "atreyu-locate-rqd"))

        return AtreyuBrokerage(organization_id,
                               host,
                               req_port,
                               sub_port,
                               username,
                               password,
                               client_id,
                               broker_mpid,
                               locate_rqd)

    def _configure_environment(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        self.ensure_module_installed()

        lean_config["environments"][environment_name]["live-mode-brokerage"] = "AtreyuBrokerage"
        lean_config["environments"][environment_name]["transaction-handler"] = \
            "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler"

    def configure_credentials(self, lean_config: Dict[str, Any]) -> None:
        lean_config["job-organization-id"] = self._organization_id
        lean_config["atreyu-host"] = self._host
        lean_config["atreyu-req-port"] = self._req_port
        lean_config["atreyu-sub-port"] = self._sub_port
        lean_config["atreyu-username"] = self._username
        lean_config["atreyu-password"] = self._password
        lean_config["atreyu-client-id"] = self._client_id
        lean_config["atreyu-broker-mpid"] = self._broker_mpid
        lean_config["atreyu-locate-rqd"] = self._locate_rqd

        self._save_properties(lean_config, ["job-organization-id",
                                            "atreyu-host",
                                            "atreyu-req-port",
                                            "atreyu-sub-port",
                                            "atreyu-username",
                                            "atreyu-password",
                                            "atreyu-client-id",
                                            "atreyu-broker-mpid",
                                            "atreyu-locate-rqd"])

    def ensure_module_installed(self) -> None:
        if not self._is_module_installed:
            container.module_manager().install_module(ATREYU_PRODUCT_ID, self._organization_id)
            self._is_module_installed = True
