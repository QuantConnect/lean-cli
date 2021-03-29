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


class PathValidator:
    """The PathValidator validates paths."""

    def is_path_valid(self, path: Path) -> bool:
        """Returns whether a path is valid on the current operating system.

        :param path: the path to validate
        :return: True if the path is valid on the current operating system, False if not
        """
        try:
            # This call fails if the path is invalid
            path.exists()
            return True
        except OSError:
            return False
