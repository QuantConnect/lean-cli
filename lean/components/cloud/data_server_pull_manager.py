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
from typing import List, Optional

from lean.components.api.data_server_client import DataServerClient, DataServerProject
from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.config.storage import safe_save
from lean.components.util.logger import Logger
from lean.components.util.project_manager import ProjectManager
from lean.models.api import QCLanguage


class DataServerPullManager:
    """The DataServerPullManager class is responsible for synchronizing data server projects to the local drive."""

    def __init__(self,
                 logger: Logger,
                 data_server_client: DataServerClient,
                 project_manager: ProjectManager,
                 project_config_manager: ProjectConfigManager) -> None:
        """Creates a new DataServerPullManager instance.

        :param logger: the logger to use when printing messages
        :param data_server_client: the DataServerClient instance to use when communicating with the data server
        :param project_manager: the ProjectManager instance to use when creating new projects
        :param project_config_manager: the ProjectConfigManager instance to use
        """
        self._logger = logger
        self._data_server_client = data_server_client
        self._project_manager = project_manager
        self._project_config_manager = project_config_manager
        self._last_file = None

    def pull_projects(self, projects_to_pull: List[DataServerProject]) -> None:
        """Pulls the given projects from the data server to the local drive.

        :param projects_to_pull: the data server projects that need to be pulled
        """
        projects_to_pull = sorted(projects_to_pull, key=lambda p: p.name)

        for index, project in enumerate(projects_to_pull, start=1):
            try:
                self._logger.info(f"[{index}/{len(projects_to_pull)}] Pulling '{project.name}'")
                self._pull_project(project)
            except Exception as ex:
                from traceback import format_exc
                self._logger.debug(format_exc().strip())
                if self._last_file is not None:
                    self._logger.warn(
                        f"Cannot pull '{project.name}' (id {project.id}, failed on {self._last_file}): {ex}")
                else:
                    self._logger.warn(f"Cannot pull '{project.name}' (id {project.id}): {ex}")

    def _pull_project(self, project: DataServerProject) -> Path:
        """Pulls a single project from the data server to the local drive.

        Raises an error with a descriptive message if the project cannot be pulled.

        :param project: the data server project to pull
        :return: the actual local path of the project
        """
        local_project_path = Path.cwd() / project.name

        # Pull the files to the local drive
        self._pull_files(project, local_project_path)

        # Update the local project config with the latest details
        project_config = self._project_config_manager.get_project_config(local_project_path)
        project_config.set("data-server-id", project.id)
        project_config.set("algorithm-language", project.algorithm_language)
        project_config.set("parameters", project.parameters)
        project_config.set("description", project.description)

        return local_project_path

    def _pull_files(self, project: DataServerProject, local_project_path: Path) -> None:
        """Pull the files of a single project.

        :param project: the data server project of which the files need to be pulled
        :param local_project_path: the path to the local project directory
        """
        if not local_project_path.exists():
            # Determine the language for project creation
            language = QCLanguage.Python
            if project.algorithm_language.lower() == "csharp":
                language = QCLanguage.CSharp
            self._project_manager.create_new_project(local_project_path, language)

        for cloud_file in project.files:
            self._last_file = cloud_file.file_name

            local_file_path = local_project_path / cloud_file.file_name

            # Skip if content is None (shouldn't happen with get_project, but be safe)
            if cloud_file.content is None:
                continue

            # Skip if the local file already exists with the correct content
            if local_file_path.exists():
                if local_file_path.read_text(encoding="utf-8").strip() == cloud_file.content.strip():
                    self._project_manager.update_last_modified_time(local_file_path, cloud_file.modified_at)
                    continue

            local_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Normalize line endings
            content = cloud_file.content.replace("\r\n", "\n")
            if content != "" and not content.endswith("\n"):
                content += "\n"
            safe_save(content, local_file_path)

            self._project_manager.update_last_modified_time(local_file_path, cloud_file.modified_at)
            self._logger.info(f"Successfully pulled '{project.name}/{cloud_file.file_name}'")

        self._last_file = None
        self._project_manager.update_last_modified_time(local_project_path, project.updated_at)
