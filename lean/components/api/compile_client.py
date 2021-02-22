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

from lean.components.api.api_client import *
from lean.models.api import QCCompileWithLogs, QCCompileWithParameters


class CompileClient:
    """The CompileClient class contains methods to interact with compile/* API endpoints."""

    def __init__(self, api_client: 'APIClient') -> None:
        """Creates a new CompileClient instance.

        :param api_client: the APIClient instance to use when making requests
        """
        self._api = api_client

    def get(self, project_id: int, compile_id: str) -> QCCompileWithLogs:
        """Returns the details of a compile.

        :param project_id: the id of the project the compile belongs to
        :param compile_id: the id of the compile to retrieve the details of
        :return: the details of the specified compile
        """
        data = self._api.get("compile/read", {
            "projectId": project_id,
            "compileId": compile_id
        })

        return QCCompileWithLogs(**data)

    def create(self, project_id: int) -> QCCompileWithParameters:
        """Creates a new compile.

        :param project_id: the id of the project to create a compile for
        :return: the created compile
        """
        data = self._api.post("compile/create", {
            "projectId": project_id
        })

        return QCCompileWithParameters(**data)
