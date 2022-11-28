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

from lean.components import reserved_names, forbidden_characters
from lean.components.config.lean_config_manager import LeanConfigManager
from lean.components.util.platform_manager import PlatformManager


class PathManager:
    """The PathManager class provides utilities for working with paths."""

    def __init__(self, lean_config_manager: LeanConfigManager, platform_manager: PlatformManager) -> None:
        """Creates a new PathManager instance.

        :param platform_manager: the PlatformManager used when checking which operating system is in use
        """
        self._lean_config_manager = lean_config_manager
        self._platform_manager = platform_manager

    def get_relative_path(self, destination: Path, source: Path = Path.cwd()) -> Path:
        """Returns a path relative to another one.

        :param destination: the path to point to
        :param source: the root where the relative path is relative to
        :return: the destination path relative to the source path, or destination path if it is not relative
        """
        try:
            return destination.relative_to(source)
        except ValueError:
            return destination

    def is_name_valid(self, name: str) -> bool:
        """Returns whether a name is valid on Windows operating system.

        :param name: the name to validate
        :return: True if the name is valid on Windows operating system, False if not
        """
        import re
        return re.match(r'^[-_a-zA-Z0-9/\s]*$', name) is not None

    def is_path_valid(self, path: Path) -> bool:
        """Returns whether the given path is a valid project path in the current operating system.

        This method should only be used to check paths relative to the current lean init folder.
        Passing an absolute path might result in false being returned since especial cases for root directories
        for each operating system (like devices in Windows) are not validated.

        :param path: the path to validate
        :return: True if the path is valid on the current operating system, False if not
        """
        try:
            # This call fails if the path contains invalid characters
            path.exists()
        except OSError:
            return False

        # On Windows path.exists() doesn't throw for paths like CON/file.txt
        # Trying to create them does raise errors, so we manually validate path components
        # We follow the rules of windows for every OS
        components = path.as_posix().split("/")
        for component in components:
            if component.startswith(" ") or component.endswith(" ") or component.endswith("."):
                return False

            for reserved_name in reserved_names:
                if component.upper() == reserved_name or component.upper().startswith(reserved_name + "."):
                    return False

            for forbidden_character in forbidden_characters:
                if forbidden_character in component:
                    return False
        return True

    def is_cli_path_valid(self, path: Path) -> bool:
        """Returns whether the given path is a valid project path in the current operating system.

        :param path: the path to validate
        :return: True if the path is valid on the current operating system, False if not
        """
        from lean.models.errors import MoreInfoError

        relative_path = path

        try:
            cli_root_dir = self._lean_config_manager.get_cli_root_directory()
            relative_path = path.relative_to(cli_root_dir)
        except (MoreInfoError, ValueError):
            from platform import system
            if system() == "Windows":
                # Skip the first component, which contains the drive name
                posix_path = path.as_posix()
                first_separator_index = posix_path.find('/')
                relative_path = Path(posix_path[first_separator_index:] if first_separator_index != -1 else path)

        return relative_path == Path(".") or self.is_path_valid(relative_path)
