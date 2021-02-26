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

import itertools
from pathlib import Path
from typing import List

from lean.components.api.api_client import APIClient
from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.util.logger import Logger
from lean.models.api import QCLanguage, QCProject


class PullManager:
    """The PullManager class is responsible for synchronizing cloud projects to the local drive."""

    def __init__(self, logger: Logger, api_client: APIClient, project_config_manager: ProjectConfigManager) -> None:
        """Creates a new PullManager instance.

        :param logger: the logger to use when printing messages
        :param api_client: the APIClient instance to use when communicating with the cloud
        :param project_config_manager: the ProjectConfigManager instance to use
        """
        self._logger = logger
        self._api_client = api_client
        self._project_config_manager = project_config_manager

    def pull_projects(self, projects_to_pull: List[QCProject]) -> None:
        """Pulls the given projects from the cloud to the local drive.

        The libraries the projects depend on will be added to the list of projects to be pulled.

        :param projects_to_pull: the cloud projects that need to be pulled
        """
        projects_to_pull = self._resolve_projects_to_pull(projects_to_pull, self._api_client.projects.get_all())
        projects_to_pull = sorted(projects_to_pull, key=lambda p: p.name)

        for index, project in enumerate(projects_to_pull, start=1):
            try:
                self._logger.info(f"[{index}/{len(projects_to_pull)}] Pulling '{project.name}'")
                self._pull_project(project)
            except Exception as ex:
                self._logger.warn(f"Cannot pull '{project.name}' ({project.projectId}): {ex}")

    def _resolve_projects_to_pull(self,
                                  projects_to_pull: List[QCProject],
                                  all_projects: List[QCProject]) -> List[QCProject]:
        """Resolves all library dependencies in projects_to_pull.

         :param projects_to_pull: the projects that need to be pulled
         :param all_projects: all cloud projects accessible by the user
         :return: a list containing all projects in projects_to_pull where no project has a dependency on a project not in the list
         """
        required_library_ids = set(itertools.chain(*[p.libraries for p in projects_to_pull]))
        missing_library_ids = [library_id for library_id in required_library_ids if
                               not any([p.projectId == library_id for p in projects_to_pull])]

        # If all required libraries are already in projects_to_pull we're done
        if len(missing_library_ids) == 0:
            return projects_to_pull

        # Add all not-yet-added libraries which are depended upon by projects in projects_to_pull
        for library_id in missing_library_ids:
            projects_to_pull.append([p for p in all_projects if p.projectId == library_id][0])

        # Resolve the dependencies of dependencies recursively
        return self._resolve_projects_to_pull(projects_to_pull, all_projects)

    def _pull_project(self, project: QCProject) -> None:
        """Pulls a single project from the cloud to the local drive.

        Raises an error with a descriptive message if the project cannot be pulled.

        :param project: the cloud project to pull
        """
        local_path = Path.cwd() / project.name
        if local_path.exists():
            project_config = self._project_config_manager.get_project_config(local_path)

            if project_config.has("cloud-id"):
                if project_config.get("cloud-id") == project.projectId:
                    # There is a local project which is linked to this cloud project
                    self._pull_files(project)
                else:
                    # There is a local project but the project config's cloud id doesn't match this cloud project's id
                    raise RuntimeError(
                        f"The local directory matching the project's name is configured to synchronize with cloud project {project_config.get('cloud-id')}")
            elif project_config.file.exists():
                # There is a local project but the project config does not contain a cloud id
                raise RuntimeError(
                    f"The local directory matching the project's name already contains a Lean project which is not linked to a cloud project")
            else:
                # There is a local directory but it doesn't have a project config
                raise RuntimeError(
                    f"The local directory matching the project's name is not a Lean project")
        else:
            # There is no local directory with the same path as the cloud project
            self._pull_files(project)

        # Finalize pulling by updating the project config with the latest details
        project_config = self._project_config_manager.get_project_config(local_path)
        project_config.set("cloud-id", project.projectId)
        project_config.set("algorithm-language", "Python" if project.language == QCLanguage.Python else "CSharp")
        project_config.set("parameters", {parameter.key: parameter.value for parameter in project.parameters})

    def _pull_files(self, project: QCProject) -> None:
        """Pull the files of a single project.

        :param project: the cloud project of which the files need to be pulled
        """
        for cloud_file in self._api_client.files.get_all(project.projectId):
            if cloud_file.isLibrary:
                continue

            local_file_path = Path.cwd() / project.name / cloud_file.name

            # Skip if the local file already exists with the correct content
            if local_file_path.exists() and local_file_path.read_text() == cloud_file.content:
                continue

            local_file_path.parent.mkdir(parents=True, exist_ok=True)
            with local_file_path.open("w+") as local_file:
                local_file.write(cloud_file.content)

            self._logger.info(f"Successfully pulled '{project.name}/{cloud_file.name}'")
