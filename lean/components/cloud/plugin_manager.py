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

import shutil
import zipfile
from io import BytesIO
from pathlib import Path

import requests

from lean.components.api.api_client import APIClient
from lean.components.config.storage import Storage
from lean.components.util.logger import Logger
from lean.constants import PLUGINS_DIRECTORY


class PluginManager:
    """The PluginManager class is responsible for downloading and updating plugins."""

    def __init__(self, logger: Logger, api_client: APIClient, cache_storage: Storage) -> None:
        """Creates a new PluginManager instance.

        :param logger: the logger to use
        :param api_client: the APIClient instance to use when communicating with the cloud
        :param cache_storage: the storage instance to store last updated times in
        """
        self._logger = logger
        self._api_client = api_client
        self._cache_storage = cache_storage

    def install_plugin(self, plugin_id: str, organization_id: str) -> None:
        """Installs a plugin into the global plugins directory.

        If an outdated version is already installed, it is automatically updated.
        If the organization does not have a subscription for the given plugin, an error is raised.

        :param plugin_id: the id of the plugin to download
        :param organization_id: the id of the organization to download the plugin from
        """
        plugin_info = self._api_client.plugins.get(plugin_id, organization_id)

        cache_key = f"last-plugin-update-{plugin_id}"
        if self._cache_storage.get(cache_key, None) == plugin_info.updated:
            return

        self._logger.info(f"Downloading latest version of the '{plugin_id}' plugin")

        plugin_directory = Path(PLUGINS_DIRECTORY) / plugin_id
        if plugin_directory.exists():
            shutil.rmtree(plugin_directory, ignore_errors=True)
        plugin_directory.mkdir(parents=True, exist_ok=True)

        response = requests.get(plugin_info.url)
        response.raise_for_status()

        with zipfile.ZipFile(BytesIO(response.content)) as zip_file:
            zip_file.extractall(plugin_directory)

        self._cache_storage.set(cache_key, plugin_info.updated)
