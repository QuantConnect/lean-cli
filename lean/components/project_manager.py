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
from typing import Dict, List

from lean.components.config.project_config_manager import ProjectConfigManager
from lean.constants import PROJECT_CONFIG_FILE_NAME


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

    def resolve_project_libraries(self, project: Path) -> List[Path]:
        """Resolves the library dependencies for a given project.

        :param project: the project to resolve dependencies for
        :return: a list containing the project and all of its recursive library dependencies
        """
        # The library index is only created when it is needed
        library_index = None

        # The list of projects which will be returned
        resolved_projects = []

        # The list of projects of which the dependencies need to be processed
        projects_to_process = [project]

        # The list of project ids of which the dependencies have been processed
        processed_project_ids = []

        while len(projects_to_process) > 0:
            current_project = projects_to_process.pop(0)
            current_config = self._project_config_manager.get_project_config(current_project)

            # Don't process a project twice
            current_project_id = current_config.get("project-id")
            if current_project_id in processed_project_ids:
                continue

            # Find the ids of not-yet-processed libraries of the current project
            required_library_ids = current_config.get("libraries", [])
            missing_library_ids = [library_id for library_id in required_library_ids if
                                   library_id not in processed_project_ids]

            # For each missing library id, add the library project to the list of projects that need to be processed
            for library_id in missing_library_ids:
                if library_index is None:
                    library_index = self._get_library_index()

                if library_id in library_index:
                    projects_to_process.append(library_index[library_id])

            resolved_projects.append(current_project)
            processed_project_ids.append(current_project_id)

        return resolved_projects

    def _get_library_index(self) -> Dict[str, Path]:
        """Returns a dictionary containing all library projects.

        :return: a dictionary where the keys are project ids and the values are paths to library project directories
        """
        library_index = {}

        for p in Path.cwd().rglob(f"Library/**/{PROJECT_CONFIG_FILE_NAME}"):
            config = self._project_config_manager.get_project_config(p.parent)
            project_id = config.get("project-id")

            if project_id is not None:
                library_index[project_id] = p.parent

        return library_index
