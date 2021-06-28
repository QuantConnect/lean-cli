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

import re
from pathlib import Path
from typing import Dict

import requests

from lean.components.api.api_client import APIClient
from lean.components.util.logger import Logger
from lean.constants import MODULES_DIRECTORY


class ModuleManager:
    """The ModuleManager class is responsible for downloading and updating modules."""

    def __init__(self, logger: Logger, api_client: APIClient) -> None:
        """Creates a new ModuleManager instance.

        :param logger: the logger to use
        :param api_client: the APIClient instance to use when communicating with the cloud
        """
        self._logger = logger
        self._api_client = api_client
        self._installed_product_ids = set()
        self._installed_modules = {}

    def install_module(self, product_id: int, organization_id: str) -> None:
        """Installs a module into the global modules directory.

        If an outdated version is already installed, it is automatically updated.
        If the organization does not have a subscription for the given module, an error is raised.

        :param product_id: the product id of the module to download
        :param organization_id: the id of the organization that has a license for the module
        """
        if product_id in self._installed_product_ids:
            return

        module_files = self._api_client.modules.list_files(product_id, organization_id)
        if len(module_files) == 0:
            raise RuntimeError(f"The module with product id '{product_id}' does not have any files")

        file_name = sorted(module_files)[-1]
        nupkg_name = re.search(r"([^\d]+)\.\d", file_name).group(1)
        nupkg_version = file_name.replace(f"{nupkg_name}.", "").replace(".nupkg", "")

        module_file = Path(MODULES_DIRECTORY) / file_name

        if module_file.is_file():
            self._installed_product_ids.add(product_id)
            self._installed_modules[nupkg_name] = nupkg_version
            return

        self._logger.info(f"Downloading '{file_name}'")

        module_file.parent.mkdir(parents=True, exist_ok=True)

        link = self._api_client.modules.get_link(product_id, organization_id, file_name)
        try:
            with requests.get(link, stream=True) as response:
                response.raise_for_status()

                with module_file.open("wb+") as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
        except Exception as exception:
            module_file.unlink(missing_ok=True)
            raise exception

        self._installed_product_ids.add(product_id)
        self._installed_modules[nupkg_name] = nupkg_version

    def get_installed_modules(self) -> Dict[str, str]:
        """Returns a dict containing name -> version pairs of all modules that install_module() was called for.

        :return: a dict containing name -> version pairs for which there are .nupkg files in the modules directory
        """
        return dict(self._installed_modules)
