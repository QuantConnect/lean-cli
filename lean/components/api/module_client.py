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

from typing import List

from lean.components.api.api_client import *


class ModuleClient:
    """The ModuleClient class contains methods to interact with modules/* API endpoints."""

    def __init__(self, api_client: 'APIClient') -> None:
        """Creates a new ModuleClient instance.

        :param api_client: the APIClient instance to use when making requests
        """
        self._api = api_client

    def get_link(self, product_id: int, organization_id: str, file_name: str) -> str:
        """Returns the download link to a module's file.

        :param product_id: the product id of the module
        :param organization_id: the id of the organization holding a license for the module
        :param file_name: the name of the module's file to download
        :return: the download link to the file
        """
        data = self._api.post("modules/read", {
            "productId": product_id,
            "organizationId": organization_id,
            "fileName": file_name
        })

        return data["url"]

    def list_files(self, product_id: int, organization_id: str) -> List[str]:
        """Lists the most recent files of a module.

        :param product_id: the product id of the module
        :param organization_id: the id of the organization holding a license for the module
        :return: a list of file names of recent files belonging to the given module
        """
        data = self._api.post("modules/list", {
            "productId": product_id,
            "organizationId": organization_id
        })

        return data["files"]
