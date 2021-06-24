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

import platform

from getmac import get_mac_address

from lean.components.api.api_client import *
from lean.models.api import QCPluginDetails


class PluginClient:
    """The PluginClient class contains methods to interact with plugins/* API endpoints."""

    def __init__(self, api_client: 'APIClient') -> None:
        """Creates a new PluginClient instance.

        :param api_client: the APIClient instance to use when making requests
        """
        self._api = api_client

    def get(self, plugin_id: str, organization_id: str) -> QCPluginDetails:
        """Returns the details of a plugin.

        :param plugin_id: the id of the plugin to retrieve the details of
        :param organization_id: the id of the organization that should have a subscription for the plugin
        :return: the details of the specified plugin
        """
        data = requests.post(f"http://localhost:3000/plugins/{plugin_id}", json={
            "organizationId": organization_id,
            "host": platform.node(),
            "mac": get_mac_address()
        }).json()

        # TODO: Switch to the production API after Gustavo added the endpoint
        # data = self._api.get(f"plugins/{plugin_id}", {
        #     "organizationId": organization_id,
        #     "host": platform.node(),
        #     "mac": get_mac_address()
        # })

        return QCPluginDetails(**data)
