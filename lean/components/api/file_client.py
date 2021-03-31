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

from typing import List

from lean.components.api.api_client import *
from lean.models.api import QCFullFile, QCMinimalFile


class FileClient:
    """The FileClient class contains methods to interact with files/* API endpoints."""

    def __init__(self, api_client: 'APIClient') -> None:
        """Creates a new FileClient instance.

        :param api_client: the APIClient instance to use when making requests
        """
        self._api = api_client

    def get(self, project_id: int, file_name: str) -> QCMinimalFile:
        """Returns the details of a file.

        :param project_id: the id of the project the file belongs to
        :param file_name: the name of the file to retrieve the details of
        :return: the details of the specified file
        """
        data = self._api.get("files/read", {
            "projectId": project_id,
            "name": file_name
        })

        return QCMinimalFile(**data["files"][0])

    def get_all(self, project_id: int) -> List[QCFullFile]:
        """Returns all files in a project.

        :param project_id: the id of the project to retrieve the files of
        :return: the files in the specified project
        """
        data = self._api.get("files/read", {
            "projectId": project_id
        })

        return [QCFullFile(**file) for file in data["files"]]

    def create(self, project_id: int, file_name: str, content: str) -> QCMinimalFile:
        """Creates a new file.

        :param project_id: the id of the project to create a file for
        :param file_name: the name of the file to create
        :param content: the content of the file to create
        :return: the created file
        """
        data = self._api.post("files/create", {
            "projectId": project_id,
            "name": file_name,
            "content": content
        })

        return QCMinimalFile(**data["files"][0])

    def update(self, project_id: int, file_name: str, content: str) -> QCMinimalFile:
        """Updates an existing file.

        :param project_id: the id of the project to update a file in
        :param file_name: the name of the file to update
        :param content: the new content of the file
        """
        data = self._api.post("files/update", {
            "projectId": project_id,
            "name": file_name,
            "content": content
        })

        return QCMinimalFile(**data["files"][0])

    def delete(self, project_id: int, file_name: str) -> None:
        """Deletes an existing file.

        :param project_id: the id of the project the file belongs to
        :param file_name: the name of the file to delete
        """
        self._api.post("files/delete", {
            "projectId": project_id,
            "name": file_name
        })
