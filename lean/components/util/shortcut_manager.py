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

import sys
from datetime import datetime, timezone
from pathlib import Path

import click
import pkg_resources
import pyshortcuts

from lean.components.config.lean_config_manager import LeanConfigManager
from lean.components.config.storage import Storage
from lean.components.util.logger import Logger
from lean.components.util.platform_manager import PlatformManager


class ShortcutManager:
    """The ShortcutManager contains the logic to create the local GUI desktop shortcut."""

    def __init__(self,
                 logger: Logger,
                 lean_config_manager: LeanConfigManager,
                 platform_manager: PlatformManager,
                 cache_storage: Storage) -> None:
        """Creates a new ShortcutManager instance.

        :param logger: the logger to use
        :param lean_config_manager: the LeanConfigManager to get the path to the Lean config from
        :param platform_manager: the PlatformManager to use
        :param cache_storage: the Storage instance to use for checking whether the user was asked to create a shortcut
        """
        self._logger = logger
        self._lean_config_manager = lean_config_manager
        self._platform_manager = platform_manager
        self._cache_storage = cache_storage

    def create_shortcut(self, organization_id: str) -> None:
        """Creates a desktop shortcut which launches the local GUI.

        :param organization_id: the id of the organization with the local GUI module subscription
        """
        required_icon = "icon.icns" if self._platform_manager.is_system_macos() else "icon.ico"
        icons_path = Path("~/.lean/icons").expanduser() / required_icon
        if not icons_path.is_file():
            icons_path.parent.mkdir(parents=True, exist_ok=True)
            with icons_path.open("wb+") as file:
                file.write(pkg_resources.resource_string("lean", f"icons/{required_icon}"))

        command = " ".join([
            sys.argv[0],
            "gui", "start",
            "--organization", f'"{organization_id}"',
            "--lean-config", f'"{self._lean_config_manager.get_lean_config_path().as_posix()}"',
            "--shortcut-launch"
        ])

        pyshortcuts.make_shortcut(command,
                                  name="Lean CLI GUI",
                                  description="The local GUI for the Lean CLI",
                                  icon=icons_path.as_posix())

        self._logger.info("Successfully created a desktop shortcut for launching the local GUI")
        self._cache_storage.set("last-shortcut-prompt", datetime.now(tz=timezone.utc).timestamp())

    def prompt_if_necessary(self, organization_id: str) -> None:
        """Prompts the user to confirm the creation of a desktop shortcut if the user hasn't been prompted before.

        :param organization_id: the id of the organization with the local GUI module subscription
        """
        if self._cache_storage.has("last-shortcut-prompt"):
            return

        if click.confirm("Do you want to create a desktop shortcut to launch the local GUI?", default=True):
            self.create_shortcut(organization_id)
        else:
            self._logger.info(
                "You can use `lean gui start --shortcut` to create a desktop shortcut at a later time if you change your mind")
