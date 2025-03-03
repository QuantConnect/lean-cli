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
        self._installed_packages: Dict[int, List[NuGetPackage]] = {}

    def install_module(self, product_id: int, organization_id: str, module_version: str) -> None:
        """
        Installs a module into the global modules' directory.

        If an outdated version is already installed, it is automatically updated. If a specific version
        is provided and is different from the installed version, it will be updated. If the organization
        does not have a subscription for the given module, an error is raised.

        Args:
        product_id (int): The product id of the module to download.
        organization_id (str): The id of the organization that has a license for the module.
        module_version (str): The specific version of the module to install. If None, installs the latest version.
        """
        if product_id in self._installed_product_ids:
            return

        # Retrieve the list of module files for the specified product and organization
        module_files = self._api_client.modules.list_files(product_id, organization_id)
        # Dictionaries to store the latest packages to download and specific version packages
        packages_to_download: Dict[str, NuGetPackage] = {}
        packages_to_download_specific_version: Dict[str, NuGetPackage] = {}

        # Parse the module files into NuGetPackage objects and sort them by version
        packages = [NuGetPackage.parse(file_name) for file_name in module_files]
        sorted_packages = sorted(packages, key=lambda p: p.version)

        for package in sorted_packages:
            # Store the latest version of each package
            if package.name not in packages_to_download or package.version > packages_to_download[package.name].version:
                packages_to_download[package.name] = package
                # If a specific version is requested, keep track of the highest version <= module_version
                if module_version and package.version.split('.')[-1] <= module_version:
                    packages_to_download_specific_version[package.name] = package

        # Replace version packages based on module_version if available
        for package_name, package_specific_version in packages_to_download_specific_version.items():
            packages_to_download[package_name] = package_specific_version

        for package in packages_to_download.values():
            if module_version and package.version.split('.')[-1] != module_version:
                self._logger.debug(f'Package "{package.name}" does not have the specified version {module_version}. '
                                   f'Using available version {package.version} instead.')
            self._download_file(product_id, organization_id, package)

        self._installed_product_ids.add(product_id)

    def get_installed_packages(self) -> List[NuGetPackage]:
        """Returns a list of NuGet packages that were installed by install_module() calls.

        :return: a list of NuGet packages in the modules directory that should be made available when running LEAN
        """
        packages = []
        for package_list in self._installed_packages.values():
            packages.extend(package_list)
        return packages

    def get_installed_packages_by_module(self, product_id: int) -> List[NuGetPackage]:
        """Returns a list of NuGet packages that were installed by install_module() for a given product id.

        :param product_id: the product id to get the installed packages of
        :return: a list of NuGet packages in are available for the given product id
        """
        return self._installed_packages.get(product_id, []).copy()

    def is_module_installed(self, product_id: int) -> bool:
        """Returns whether a module with a given producti d has been installed with install_module().

        :param product_id: the product id to check the install status of
        :return: True if the product id has been registered with install_module(), False if not
        """
        return product_id in self._installed_product_ids

    def _download_file(self, product_id: int, organization_id: str, package: NuGetPackage) -> None:
        """Downloads a file if it doesn't already exist locally.

        :param product_id: the product id of the module to download
        :param organization_id: the id of the organization that has a license for the module
        :param package: the NuGet package to download
        """

        package_file = Path(MODULES_DIRECTORY) / package.get_file_name()
        
        if package_file.is_file():
            from zipfile import ZipFile, BadZipFile
            from contextlib import suppress
            with suppress(BadZipFile, IOError):
                with ZipFile(package_file, 'r') as zip_ref:
                    # Verify the integrity of the file
                    if zip_ref.testzip() is None:
                        self._logger.debug(f"{package_file.name} exists and passed the integrity check.")
                        if product_id not in self._installed_packages:
                            self._installed_packages[product_id] = []
                        self._installed_packages[product_id].append(package)
                        self._logger.debug(f"ModuleManager._download_file(): {package_file} already exists locally")
                        return

            self._logger.info(f"{package_file.name} exists but is corrupted. Downloading again...")
            
            from os import remove
            remove(package_file)

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

        if product_id not in self._installed_packages:
            self._installed_packages[product_id] = []
        self._installed_packages[product_id].append(package)
        self._logger.debug(f"ModuleManager._download_file(): adding {package.name} to _installed_packages")
