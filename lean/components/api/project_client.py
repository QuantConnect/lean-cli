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

from typing import Any, List

from lean.components.api.api_client import APIClient
from lean.models.api import QCCreatedProject, QCLanguage, QCProject


class ProjectClient:
    """The ProjectClient class contains methods to interact with projects/* API endpoints."""

    def __init__(self, api_client: APIClient) -> None:
        """Creates a new ProjectClient instance.

        :param api_client: the APIClient instance to use when making requests
        """
        self._api = api_client

    def get(self, project_id: int) -> QCProject:
        """Returns the details of a project.

        :param project_id: the id of the project to retrieve the details of
        :return: the details of the specified project
        """
        data = self._api.get("projects/read", {
            "projectId": project_id
        })

        return self._process_project(QCProject(**data["projects"][0]))

    def get_all(self) -> List[QCProject]:
        """Returns all the projects the user has access to.

        :return: a list containing all the projects the user has access to
        """
        data = self._api.get("projects/read")
        return [self._process_project(QCProject(**project)) for project in data["projects"]]

    def create(self, name: str, language: QCLanguage) -> QCCreatedProject:
        """Creates a new project.

        :param name: the name of the project to create
        :param language: the language of the project to create
        :return: the created project
        """
        data = self._api.post("projects/create", {
            "name": name,
            "language": language.value
        })

        return self._process_project(QCCreatedProject(**data["projects"][0]))

    def delete(self, project_id: int) -> None:
        """Deletes an existing project.

        :param project_id: the id of the project to delete
        """
        self._api.post("projects/delete", {
            "projectId": project_id
        })

    def _process_project(self, project: Any) -> Any:
        """Patches a cloud project's name by ensuring the name doesn't start with a slash.

        :param project: the project to process
        :return: the project that is given after patching it
        """
        project.name = project.name.lstrip("/")
        return project
