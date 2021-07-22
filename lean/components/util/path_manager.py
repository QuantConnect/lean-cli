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

from lean.components.util.platform_manager import PlatformManager


class PathManager:
    """The PathManager class provides utilities for working with paths."""

    def __init__(self, platform_manager: PlatformManager) -> None:
        """Creates a new PathManager instance.

        :param platform_manager: the PlatformManager used when checking which operating system is in use
        """
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

    def is_path_valid(self, path: Path) -> bool:
        """Returns whether a path is valid on the current operating system.

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
        if self._platform_manager.is_system_windows():
            # Skip the first component, which contains the drive name
            for component in path.as_posix().split("/")[1:]:
                if component.startswith(" ") or component.endswith(" ") or component.endswith("."):
                    return False

                for reserved_name in ["CON", "PRN", "AUX", "NUL",
                                      "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
                                      "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"]:
                    if component.upper() == reserved_name or component.upper().startswith(reserved_name + "."):
                        return False

                for forbidden_character in [":", "*", "?", '"', "<", ">", "|"]:
                    if forbidden_character in component:
                        return False

        return True
