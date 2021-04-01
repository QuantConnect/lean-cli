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
from pathlib import Path


class PathValidator:
    """The PathValidator validates paths."""

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
        if platform.system() == "Windows":
            for component in path.as_posix().split("/"):
                if component.startswith(" ") or component.endswith(" ") or component.endswith("."):
                    return False

                for reserved_name in ["CON", "PRN", "AUX", "NUL",
                                      "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
                                      "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"]:
                    if component.upper() == reserved_name:
                        return False

        return True
