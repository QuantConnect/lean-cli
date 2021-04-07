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

from datetime import datetime, timedelta, timezone
from distutils.version import StrictVersion

import requests

import lean
from lean.components.config.storage import Storage
from lean.components.docker.docker_manager import DockerManager
from lean.components.util.logger import Logger
from lean.constants import UPDATE_CHECK_INTERVAL_CLI, UPDATE_CHECK_INTERVAL_DOCKER_IMAGE


class UpdateManager:
    """The UpdateManager class contains methods to check for and warn the user about available updates."""

    def __init__(self, logger: Logger, cache_storage: Storage, docker_manager: DockerManager) -> None:
        """Creates a new UpdateManager instance.

        :param logger: the logger to use when warning the user when something is outdated
        :param cache_storage: the Storage instance to use for getting/setting the last time a certain update check was performed
        :param docker_manager: the DockerManager instance to use to check for Docker updates
        """
        self._logger = logger
        self._cache_storage = cache_storage
        self._docker_manager = docker_manager

    def warn_if_cli_outdated(self) -> None:
        """Warns the user if the CLI is outdated.

        An update check is performed once every UPDATE_CHECK_INTERVAL_CLI hours.
        """
        current_version = lean.__version__

        # A development version is never considered outdated
        if current_version == "dev":
            return

        if not self._should_check_for_updates("cli", UPDATE_CHECK_INTERVAL_CLI):
            return

        try:
            response = requests.get("https://pypi.org/pypi/lean/json")
        except requests.exceptions.ConnectionError:
            # The user may be offline, do nothing
            return

        if not response.ok:
            return

        latest_version = response.json()["info"]["version"]

        if StrictVersion(latest_version) > StrictVersion(current_version):
            self._logger.warn(f"A new release of the Lean CLI is available ({current_version} -> {latest_version})")
            self._logger.warn("Run `pip install --upgrade lean` to update to the latest version")

    def warn_if_docker_image_outdated(self, image: str) -> None:
        """Warns the user if the latest installed version of a Docker image is outdated.

        An update check is performed once every UPDATE_CHECK_INTERVAL_DOCKER_IMAGE hours (the interval is per image).
        """
        # Don't consider checking for updates if the latest version of the image isn't installed yet
        if not self._docker_manager.tag_installed(image, "latest"):
            return

        if not self._should_check_for_updates(image, UPDATE_CHECK_INTERVAL_DOCKER_IMAGE):
            return

        current_digest = self._docker_manager.get_tag_digest(image, "latest")

        try:
            response = requests.get(f"https://registry.hub.docker.com/v2/repositories/{image}/tags/latest")
        except requests.exceptions.ConnectionError:
            # The user may be offline, do nothing
            return

        if not response.ok:
            return

        latest_digest = response.json()["images"][0]["digest"]

        if current_digest != latest_digest:
            self._logger.warn(f"You are currently using an outdated version of the '{image}' Docker image")
            self._logger.warn(f"Run this command with the --update flag to update it to the latest version")

    def _should_check_for_updates(self, key: str, interval_hours: int) -> bool:
        """Returns whether an update check should be performed.

        When this method returns True, for the next <interval_hours> hours it returns False for <key>.

        :param key: the key which is used to identify the current update check
        :param interval_hours: the amount of hours between update checks for the given key
        :return: True if an update check should be performed, False if not
        """
        storage_key = f"last-update-check-{key}"
        should_check = False

        if not self._cache_storage.has(storage_key):
            # Perform an update check if we haven't ran one yet
            should_check = True
        else:
            last_update_check = datetime.fromtimestamp(self._cache_storage.get(storage_key), tz=timezone.utc)
            time_since_last_update_check = datetime.now(tz=timezone.utc) - last_update_check

            if time_since_last_update_check >= timedelta(hours=interval_hours):
                # Perform an update check if the time since the last update check is greater than the given interval
                should_check = True

        if should_check:
            # Save the current timestamp so for the next <interval_hours> hours we can return False for <key>
            self._cache_storage.set(storage_key, datetime.now(tz=timezone.utc).timestamp())

        return should_check
