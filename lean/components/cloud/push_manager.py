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
from typing import List

from lean.components.api.api_client import APIClient
from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.util.logger import Logger
from lean.components.util.project_manager import ProjectManager
from lean.models.api import QCLanguage, QCProject


class PushManager:
    """The PushManager class is responsible for synchronizing local projects to the cloud."""

    def __init__(self,
                 logger: Logger,
                 api_client: APIClient,
                 project_manager: ProjectManager,
                 project_config_manager: ProjectConfigManager) -> None:
        """Creates a new PushManager instance.

        :param logger: the logger to use when printing messages
        :param api_client: the APIClient instance to use when communicating with the cloud
        :param project_manager: the ProjectManager to use when looking for certain projects
        :param project_config_manager: the ProjectConfigManager instance to use
        """
        self._logger = logger
        self._api_client = api_client
        self._project_manager = project_manager
        self._project_config_manager = project_config_manager

    def push_projects(self, projects_to_push: List[Path]) -> None:
        """Pushes the given projects from the local drive to the cloud.

        The libraries the projects depend on will be added to the list of projects to be pushed.

        :param projects_to_push: a list of directories containing the local projects that need to be pushed
        """
        # Resolve the library dependencies of all projects which need to be pushed
        projects_to_push = sorted(projects_to_push)

        cloud_projects = self._api_client.projects.get_all()

        for index, project in enumerate(projects_to_push, start=1):
            relative_path = project.relative_to(Path.cwd())
            try:
                self._logger.info(f"[{index}/{len(projects_to_push)}] Pushing '{relative_path}'")
                self._push_project(project, cloud_projects)
            except Exception as ex:
                self._logger.warn(f"Could not push '{relative_path}': {ex}")

    def _push_project(self, project: Path, cloud_projects: List[QCProject]) -> None:
        """Pushes a single local project to the cloud.

        Raises an error with a descriptive message if the project cannot be pushed.

        :param project: the local project to push
        :param cloud_projects: a list containing all of the user's cloud projects
        """
        project_name = project.relative_to(Path.cwd()).as_posix()

        project_config = self._project_config_manager.get_project_config(project)
        project_id = project_config.get("cloud-id")

        cloud_project_by_id = next(iter([p for p in cloud_projects if p.projectId == project_id]), None)
        cloud_project_by_name = next(iter([p for p in cloud_projects if p.name == project_name]), None)

        # Find the cloud project to push the files to
        if cloud_project_by_id is not None:
            # Project has id which matches cloud project, update cloud project
            cloud_project = cloud_project_by_id
        elif cloud_project_by_name is None:
            # Project has invalid id or no id at all and no cloud project has same name, create cloud project
            new_project = self._api_client.projects.create(project_name,
                                                           QCLanguage[project_config.get("algorithm-language")])
            self._logger.info(f"Successfully created cloud project '{project_name}'")

            project_config.set("cloud-id", new_project.projectId)

            # We need to retrieve the created project again to get all project details
            cloud_project = self._api_client.projects.get(new_project.projectId)
        else:
            raise RuntimeError("There already exists a project with the same name in the cloud")

        # Push local files to cloud
        self._push_files(project, cloud_project)

        # Finalize pushing by updating locally modified metadata
        self._push_parameters(project, cloud_project)

    def _push_files(self, project: Path, cloud_project: QCProject) -> None:
        """Push the files of a local project to the cloud.

        :param project: the local project to push the files of
        :param cloud_project: the cloud project to push the files to
        """
        local_files = list(project.rglob("*.py")) + list(project.rglob("*.cs")) + list(project.rglob("*.ipynb"))
        cloud_files = self._api_client.files.get_all(cloud_project.projectId)

        for local_file in local_files:
            file_name = local_file.relative_to(project).as_posix()
            file_content = local_file.read_text()

            cloud_file = next(iter([f for f in cloud_files if f.name == file_name]), None)

            if cloud_file is None:
                self._api_client.files.create(cloud_project.projectId, file_name, file_content)
                self._logger.info(f"Successfully created cloud file '{cloud_project.name}/{file_name}'")
            elif cloud_file.content.strip() != file_content.strip():
                self._api_client.files.update(cloud_project.projectId, file_name, file_content)
                self._logger.info(f"Successfully updated cloud file '{cloud_project.name}/{file_name}'")

    def _push_parameters(self, project: Path, cloud_project: QCProject) -> None:
        """Push local parameters to the cloud. Does nothing if the cloud is already up-to-date.

        :param project: the local project to push the parameters of
        :param cloud_project: the cloud project to push the parameters to
        """
        local_parameters = self._project_config_manager.get_project_config(project).get("parameters", {})
        cloud_parameters = {parameter.key: parameter.value for parameter in cloud_project.parameters}

        if local_parameters != cloud_parameters and local_parameters != {}:
            self._api_client.projects.update(cloud_project.projectId, parameters=local_parameters)
            self._logger.info(f"Successfully updated cloud parameters for '{cloud_project.name}'")
