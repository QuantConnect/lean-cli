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

from lean.components.api.file_client import FileClient
from lean.components.api.project_client import ProjectClient
from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.logger import Logger
from lean.components.project_manager import ProjectManager


class PushManager:
    """The PushManager class is responsible for synchronizing local projects to the cloud."""

    def __init__(self,
                 logger: Logger,
                 project_client: ProjectClient,
                 file_client: FileClient,
                 project_manager: ProjectManager,
                 project_config_manager: ProjectConfigManager) -> None:
        """Creates a new PushManager instance.

        :param logger: the logger to use when printing messages
        :param project_client: the ProjectClient to use interacting with the cloud
        :param file_client: the FileClient to use when interacting with the cloud
        :param project_manager: the ProjectManager to use when looking for certain projects
        :param project_config_manager: the ProjectConfigManager instance to use
        """
        self._logger = logger
        self._project_client = project_client
        self._file_client = file_client
        self._project_manager = project_manager
        self._project_config_manager = project_config_manager

    def push_projects(self, projects_to_push: List[Path]) -> None:
        """Pushes the given projects from the local drive to the cloud.

        The libraries the projects depend on will be added to the list of projects to be pushed.

        :param projects_to_push: a list of directories containing the local projects that need to be pushed
        """
        # Resolve the dependencies of all projects which need to be pushed
        projects_to_push = [self._project_manager.resolve_project_dependencies(p) for p in projects_to_push]
        projects_to_push = set(itertools.chain(*projects_to_push))

        for p in projects_to_push:
            self._logger.info(str(p))
