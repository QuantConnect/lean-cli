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
from lean.models.api import QCLanguage, QCProject


class ProjectClient:
    """The ProjectClient class contains methods to interact with projects/* API endpoints."""

    def __init__(self, api_client: 'APIClient') -> None:
        """Creates a new ProjectClient instance.

        :param api_client: the APIClient instance to use when making requests
        """
        self._api = api_client

    def get(self, project_id: int, organization_id: Optional[str]) -> QCProject:
        """Returns the details of a project.

        :param project_id: the id of the project to retrieve the details of
        :param organization_id: the id of the organization where the project is located
        :return: the details of the specified project
        """
        payload = {"projectId": project_id}
        if organization_id is not None:
            payload["organizationId"] = organization_id

        data = self._api.get("projects/read", payload)

        return self._process_project(QCProject(**data["projects"][0]))

    def get_all(self, organization_id: Optional[str]) -> List[QCProject]:
        """Returns all the projects the user has access to.

        :return: a list containing all the projects the user has access to
        :param organization_id: the id of the organization where the projects are located
        """
        payload = {}
        if organization_id is not None:
            payload["organizationId"] = organization_id

        data = self._api.get("projects/read", payload)

        return [self._process_project(QCProject(**project)) for project in data["projects"]]

    def create(self, name: str, language: QCLanguage, organization_id: Optional[str]) -> QCProject:
        """Creates a new project.

        :param name: the name of the project to create
        :param language: the language of the project to create
        :param organization_id: the id of the organization to create the project in
        :return: the created project
        """
        parameters = {
            "name": name,
            "language": language.value
        }
        if organization_id is not None:
            parameters["organizationId"] = organization_id
        data = self._api.post("projects/create", parameters)

        return self._process_project(QCProject(**data["projects"][0]))

    def update(self,
               project_id: int,
               name: Optional[str] = None,
               description: Optional[str] = None,
               parameters: Optional[Dict[str, str]] = None,
               lean_engine: Optional[int] = None,
               python_venv: Optional[int] = None,
               files: Optional[List[Dict[str, str]]] = None,
               libraries: Optional[List[int]] = None) -> None:
        """Updates an existing project.

        :param project_id: the id of the project to update
        :param name: the new name to assign to the project, or None if the name shouldn't be changed
        :param description: the new description to assign to the project, or None if the description shouldn't be changed
        :param parameters: the new parameters of the project, or None if the parameters shouldn't be changed
        :param lean_engine: the lean engine id for the project, or None if the lean engine shouldn't be changed
        :param python_venv: the python venv id for the project, or None if the python venv shouldn't be changed
        :param files: the list of files for the project
        :param libraries: the list of libraries referenced by the project
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
                for index, (key, value) in enumerate(parameters.items()):
                    request_parameters[f"parameters[{index}][key]"] = key
                    request_parameters[f"parameters[{index}][value]"] = value
            else:
                request_parameters["parameters"] = ""

        if lean_engine is not None:
            request_parameters["versionId"] = lean_engine

        if python_venv is not None:
            request_parameters["leanEnvironment"] = python_venv

        if files is not None:
            if len(files) > 0:
                for index, file in enumerate(files):
                    request_parameters[f"files[{index}][name]"] = file["name"]
                    request_parameters[f"files[{index}][content]"] = file["content"]
            else:
                request_parameters["files"] = []

        if libraries is not None:
            if len(libraries) > 0:
                for index, library in enumerate(libraries):
                    request_parameters[f"libraries[{index}]"] = library
            else:
                request_parameters["libraries"] = []

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
