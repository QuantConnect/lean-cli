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

from lean.components.storage import Storage


class ProjectConfigManager:
    """The ProjectConfigManager class manages the configuration of a single project."""

    def __init__(self, file_name: str) -> None:
        """Creates a new ProjectConfigManager instance.

        :param file_name: the name of the file containing the project's configuration
        """
        self._file_name = file_name

    def get_project_config(self, project_directory: Path) -> Storage:
        """Returns a Storage instance to get/set the configuration for a project.

        :param project_directory: the path to the project to retrieve the configuration of
        :return: the Storage instance containing the project-specific configuration of the given project
        """
        return Storage(str(project_directory / self._file_name))
