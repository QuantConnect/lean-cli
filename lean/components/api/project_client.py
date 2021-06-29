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

from typing import List, Optional

from lean.components.api.api_client import *
from lean.models.api import QCCreatedProject, QCLanguage, QCProject


class ProjectClient:
    """The ProjectClient class contains methods to interact with projects/* API endpoints."""

    def __init__(self, api_client: 'APIClient') -> None:
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

    def update(self,
               project_id: int,
               name: Optional[str] = None,
               description: Optional[str] = None,
               parameters: Optional[Dict[str, str]] = None) -> None:
        """Updates an existing project.

        :param project_id: the id of the project to update
        :param name: the new name to assign to the project, or None if the name shouldn't be changed
        :param description: the new description to assign to the project, or None if the description shouldn't be changed
        :param parameters: the new parameters of the project, or None if the parameters shouldn't be changed
        """
        request_parameters = {
            "projectId": project_id
        }

        if name is not None:
            request_parameters["name"] = name

        if description is not None:
            request_parameters["description"] = description

        if parameters is not None:
            if len(parameters) > 0:
                index = 0
                for key, value in parameters.items():
                    request_parameters[f"parameters[{index}][key]"] = key
                    request_parameters[f"parameters[{index}][value]"] = value
                    index += 1
            else:
                request_parameters["parameters"] = ""

        self._api.post("projects/update", request_parameters, data_as_json=False)

    def delete(self, project_id: int) -> None:
        """Deletes an existing project.

        :param project_id: the id of the project to delete
        """
        self._api.post("projects/delete", {
            "projectId": project_id
        })

    def add_library(self, project_id: int, library_project_id: int) -> None:
        """Links a library to a project.

        :param project_id: the id of the project to add the library to
        :param library_project_id: the id of the library project to add as library
        """
        self._api.post("projects/library/create", {
            "projectId": project_id,
            "libraryId": library_project_id
        })

    def delete_library(self, project_id: int, library_project_id: int) -> None:
        """Removes a library from a project.

        :param project_id: the id of the project the library is added to
        :param library_project_id: the id of the library project to remove
        """
        self._api.post("projects/library/delete", {
            "projectId": project_id,
            "libraryId": library_project_id
        })

    def _process_project(self, project: Any) -> Any:
        """Patches a cloud project's name by ensuring the name doesn't start with a slash.

        :param project: the project to process
        :return: the project that is given after patching it
        """
        project.name = project.name.lstrip("/")
        return project
