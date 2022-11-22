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

from lean.components.api.api_client import APIClient
from lean.components.cloud.pull_manager import PullManager
from lean.components.cloud.push_manager import PushManager
from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.util.organization_manager import OrganizationManager
from lean.components.util.path_manager import PathManager
from lean.components.util.project_manager import ProjectManager
from lean.models.api import QCProject


class CloudProjectManager:
    """The CloudProjectManager class is responsible for finding the correct cloud project in cloud commands."""

    def __init__(self,
                 api_client: APIClient,
                 project_config_manager: ProjectConfigManager,
                 pull_manager: PullManager,
                 push_manager: PushManager,
                 path_manager: PathManager,
                 project_manager: ProjectManager,
                 organization_manager: OrganizationManager) -> None:
        """Creates a new PullManager instance.

        :param api_client: the APIClient instance to use when communicating with the cloud
        :param project_config_manager: the ProjectConfigManager instance to use
        :param pull_manager: the PullManager instance to use
        :param push_manager: the PushManager instance to use
        :param path_manager: the PathManager instance to use when validating paths
        :param organization_manager: the OrganizationManager instance to use to get the working organization id
        """
        self._api_client = api_client
        self._project_config_manager = project_config_manager
        self._pull_manager = pull_manager
        self._push_manager = push_manager
        self._path_manager = path_manager
        self._project_manager = project_manager
        self._organization_manager = organization_manager

    def get_cloud_project(self, input: str, push: bool) -> QCProject:
        """Retrieves the cloud project to use given a certain input and whether the local project needs to be pushed.

        Many cloud commands look like "lean cloud <command> <name or id> --push".
        This method handles parsing the "<name or id> --push" part.
        This method returns the cloud project we think the user wants to use with the given command.

        :param input: the input the user gave, either a local project name, a cloud project name or a cloud id
        :param push: True if the local counterpart of the cloud project needs to be pushed
        :return: the cloud project to use
        """
        organization_id = self._organization_manager.try_get_working_organization_id()

        # If the given input is a valid project directory, we try to use that project
        local_path = Path.cwd() / input
        if self._project_config_manager.try_get_project_config(local_path):
            if push:
                self._push_manager.push_projects([local_path])

                cloud_id = self._project_config_manager.get_project_config(local_path).get("cloud-id")
                if cloud_id is None:
                    raise RuntimeError("Something went wrong while pushing the project to the cloud")

                return self._api_client.projects.get(cloud_id, organization_id)
            else:
                cloud_id = self._project_config_manager.get_project_config(local_path).get("cloud-id")
                if cloud_id is not None:
                    return self._api_client.projects.get(cloud_id, organization_id)

        # If the given input is not a valid project directory, we look for a cloud project with a matching name or id
        # If there are multiple, we use the first one
        for cloud_project in self._api_client.projects.get_all(organization_id):
            if str(cloud_project.projectId) != input and cloud_project.name != input:
                continue

            # If the user wants to push and the input doesn't match a local project name, we attempt to push again
            # This may happen if the input is an id instead of a name
            # If the local directory exists, we push it and return the updated cloud project
            if push:
                local_path = self._project_manager.get_local_project_path(cloud_project.name, cloud_project.projectId)
                if local_path.exists():
                    self._push_manager.push_projects([local_path])
                    return self._api_client.projects.get(cloud_project.projectId, organization_id)

            return cloud_project

        raise RuntimeError("No project with the given name or id could be found")
