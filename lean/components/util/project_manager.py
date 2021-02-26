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

from lean.components.config.project_config_manager import ProjectConfigManager


class ProjectManager:
    """The ProjectManager class provides utilities for finding specific files in projects."""

    def __init__(self, project_config_manager: ProjectConfigManager) -> None:
        """Creates a new ProjectManager instance.

        :param project_config_manager: the ProjectConfigManager instance to use when retrieving project configuration
        """
        self._project_config_manager = project_config_manager

    def find_algorithm_file(self, input: Path) -> Path:
        """Returns the path to the file containing the algorithm.

        Raises an error if the algorithm file cannot be found.

        :param input: the path to the algorithm or the path to the project
        :return: the path to the file containing the algorithm
        """
        if input.is_file():
            return input

        for file_name in ["main.py", "Main.cs"]:
            target_file = input / file_name
            if target_file.exists():
                return target_file

        raise ValueError("The specified project does not contain a main.py or Main.cs file")
