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
from typing import Set, List, Dict

from lean.components.api.api_client import APIClient
from lean.components.util.http_client import HTTPClient
from lean.components.util.logger import Logger
from lean.constants import MODULES_DIRECTORY
from lean.models.modules import NuGetPackage


class ModuleManager:
    """The ModuleManager class is responsible for downloading and updating modules."""

    def __init__(self, logger: Logger, api_client: APIClient, http_client: HTTPClient) -> None:
        """Creates a new ModuleManager instance.

        :param logger: the logger to use
        :param api_client: the APIClient instance to use when communicating with the cloud
        :param http_client: the HTTPClient instance to use when downloading modules
        """
        self._logger = logger
        self._api_client = api_client
        self._http_client = http_client
        self._installed_product_ids: Set[int] = set()
        self._installed_packages: List[NuGetPackage] = []

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
        packages_to_download: Dict[str, NuGetPackage] = {}

        for file_name in module_files:
            package = NuGetPackage.parse(file_name)

            if package.name not in packages_to_download or package.version > packages_to_download[package.name].version:
                packages_to_download[package.name] = package

        for package in packages_to_download.values():
            self._download_file(product_id, organization_id, package)

        self._installed_product_ids.add(product_id)

    def get_installed_packages(self) -> List[NuGetPackage]:
        """Returns a list of NuGet packages that were installed by install_module() calls.

        :return: a list of NuGet packages in the modules directory that should be made available when running LEAN
        """
        return list(self._installed_packages)

    def _download_file(self, product_id: int, organization_id: str, package: NuGetPackage) -> None:
        """Downloads a file if it doesn't already exist locally.

        :param product_id: the product id of the module to download
        :param organization_id: the id of the organization that has a license for the module
        :param package: the NuGet package to download
        """
        package_file = Path(MODULES_DIRECTORY) / package.get_file_name()

        if package_file.is_file():
            self._installed_packages.append(package)
            return

        self._logger.info(f"Downloading '{package_file.name}'")

        package_file.parent.mkdir(parents=True, exist_ok=True)

        link = self._api_client.modules.get_link(product_id, organization_id, package_file.name)
        try:
            with self._http_client.get(link, stream=True) as response:
                with package_file.open("wb+") as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
        except Exception as exception:
            package_file.unlink(missing_ok=True)
            raise exception

        self._installed_packages.append(package)
