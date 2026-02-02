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

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from lean.components.util.http_client import HTTPClient
from lean.components.util.logger import Logger
from lean.models.errors import RequestFailedError


@dataclass
class DataServerFile:
    """Represents a file in a data server project."""
    id: str
    project_id: str
    file_name: str
    storage_path: str
    content_hash: Optional[str]
    modified_at: datetime
    content: Optional[str] = None


@dataclass
class DataServerProject:
    """Represents a project in the data server."""
    id: str
    name: str
    description: str
    algorithm_language: str
    parameters: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    files: List[DataServerFile] = None

    def __post_init__(self):
        if self.files is None:
            self.files = []


class DataServerClient:
    """Client for interacting with the CascadeLabs data server lean projects API."""

    def __init__(self, logger: Logger, http_client: HTTPClient, base_url: str, api_key: str) -> None:
        """Creates a new DataServerClient instance.

        :param logger: the logger to use for debug messages
        :param http_client: the HTTP client to make requests with
        :param base_url: the base URL of the data server
        :param api_key: the API key for authentication
        """
        self._logger = logger
        self._http_client = http_client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    def _get_headers(self) -> Dict[str, str]:
        """Returns headers for authenticated requests."""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }

    def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Any:
        """Makes an authenticated request to the data server.

        :param method: the HTTP method
        :param endpoint: the API endpoint
        :param data: optional JSON data for POST/PUT requests
        :return: the parsed response
        """
        url = f"{self._base_url}/api/v1/lean/projects{endpoint}"

        options = {"headers": self._get_headers()}
        if data is not None:
            options["json"] = data

        response = self._http_client.request(method, url, raise_for_status=False, **options)

        if self._logger.debug_logging_enabled:
            self._logger.debug(f"Data server response: {response.text}")

        if response.status_code < 200 or response.status_code >= 300:
            raise RequestFailedError(response)

        if response.status_code == 204:
            return None

        return response.json()

    def _parse_project(self, data: Dict[str, Any]) -> DataServerProject:
        """Parses a project response into a DataServerProject object."""
        files = []
        if "files" in data:
            for f in data["files"]:
                files.append(DataServerFile(
                    id=f["id"],
                    project_id=f["project_id"],
                    file_name=f["file_name"],
                    storage_path=f["storage_path"],
                    content_hash=f.get("content_hash"),
                    modified_at=datetime.fromisoformat(f["modified_at"].replace("Z", "+00:00")),
                    content=f.get("content")
                ))

        return DataServerProject(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            algorithm_language=data["algorithm_language"],
            parameters=data["parameters"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
            files=files
        )

    def create_project(self, name: str, files: List[Dict[str, str]],
                       description: str = "", algorithm_language: str = "Python",
                       parameters: Optional[Dict[str, Any]] = None) -> DataServerProject:
        """Creates a new project with files.

        :param name: the project name
        :param files: list of dicts with 'name' and 'content' keys
        :param description: optional project description
        :param algorithm_language: the algorithm language (default: Python)
        :param parameters: optional project parameters
        :return: the created project
        """
        data = {
            "name": name,
            "description": description,
            "algorithm_language": algorithm_language,
            "parameters": parameters or {},
            "files": [{"name": f["name"], "content": f["content"]} for f in files]
        }
        response = self._request("post", "", data)
        return self._parse_project(response)

    def get_project(self, project_id: str) -> DataServerProject:
        """Gets a project by ID with all files.

        :param project_id: the project UUID
        :return: the project with files
        """
        response = self._request("get", f"/{project_id}")
        return self._parse_project(response)

    def get_project_by_name(self, name: str) -> DataServerProject:
        """Gets a project by name with all files.

        :param name: the project name
        :return: the project with files
        """
        response = self._request("get", f"/by-name/{name}")
        return self._parse_project(response)

    def list_projects(self) -> List[DataServerProject]:
        """Lists all projects (metadata only).

        :return: list of projects
        """
        response = self._request("get", "")
        return [self._parse_project(p) for p in response]

    def update_project(self, project_id: str, files: List[Dict[str, str]],
                       description: Optional[str] = None,
                       algorithm_language: Optional[str] = None,
                       parameters: Optional[Dict[str, Any]] = None) -> DataServerProject:
        """Updates a project and syncs files.

        :param project_id: the project UUID
        :param files: list of dicts with 'name' and 'content' keys
        :param description: optional new description
        :param algorithm_language: optional new algorithm language
        :param parameters: optional new parameters
        :return: the updated project
        """
        data = {
            "files": [{"name": f["name"], "content": f["content"]} for f in files]
        }
        if description is not None:
            data["description"] = description
        if algorithm_language is not None:
            data["algorithm_language"] = algorithm_language
        if parameters is not None:
            data["parameters"] = parameters

        response = self._request("put", f"/{project_id}", data)
        return self._parse_project(response)

    def delete_project(self, project_id: str) -> None:
        """Deletes a project and all its files.

        :param project_id: the project UUID to delete
        """
        self._request("delete", f"/{project_id}")

    def is_authenticated(self) -> bool:
        """Checks whether the current credentials are valid.

        :return: True if credentials are valid
        """
        try:
            self.list_projects()
            return True
        except RequestFailedError:
            return False

    # Backtest API methods

    def _backtest_request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Any:
        """Makes an authenticated request to the backtests API.

        :param method: the HTTP method
        :param endpoint: the API endpoint
        :param data: optional JSON data for POST/PUT/PATCH requests
        :return: the parsed response
        """
        url = f"{self._base_url}/api/v1/backtests{endpoint}"

        options = {"headers": self._get_headers()}
        if data is not None:
            options["json"] = data

        response = self._http_client.request(method, url, raise_for_status=False, **options)

        if self._logger.debug_logging_enabled:
            self._logger.debug(f"Data server response: {response.text}")

        if response.status_code < 200 or response.status_code >= 300:
            raise RequestFailedError(response)

        if response.status_code == 204:
            return None

        return response.json()

    def create_backtest(
        self,
        project_id: str,
        name: str,
        parameters: Optional[Dict[str, Any]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        initial_capital: float = 100000,
        data_provider_historical: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a new backtest job.

        :param project_id: the project UUID
        :param name: the backtest name
        :param parameters: optional algorithm parameters
        :param start_date: optional start date (ISO format)
        :param end_date: optional end date (ISO format)
        :param initial_capital: initial capital (default 100000)
        :param data_provider_historical: optional historical data provider
        :return: the created backtest
        """
        data = {
            "project_id": project_id,
            "name": name,
            "parameters": parameters or {},
            "initial_capital": initial_capital
        }
        if start_date:
            data["start_date"] = start_date
        if end_date:
            data["end_date"] = end_date
        if data_provider_historical:
            data["data_provider_historical"] = data_provider_historical

        return self._backtest_request("post", "", data)

    def get_backtest(self, backtest_id: str) -> Dict[str, Any]:
        """Gets a backtest by ID.

        :param backtest_id: the backtest UUID
        :return: the backtest data
        """
        return self._backtest_request("get", f"/{backtest_id}")

    def list_backtests(
        self,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Lists backtests with optional filtering.

        :param project_id: optional filter by project
        :param status: optional filter by status
        :param limit: maximum results
        :return: list of backtests
        """
        params = []
        if project_id:
            params.append(f"project_id={project_id}")
        if status:
            params.append(f"status={status}")
        params.append(f"limit={limit}")

        endpoint = "?" + "&".join(params) if params else ""
        return self._backtest_request("get", endpoint)

    def cancel_backtest(self, backtest_id: str) -> Dict[str, Any]:
        """Cancels a pending or running backtest.

        :param backtest_id: the backtest UUID
        :return: the cancelled backtest
        """
        return self._backtest_request("post", f"/{backtest_id}/cancel")

    def get_backtest_report(self, backtest_id: str) -> bytes:
        """Gets the HTML report for a backtest.

        :param backtest_id: the backtest UUID
        :return: the HTML report content
        """
        url = f"{self._base_url}/api/v1/backtests/{backtest_id}/report"
        response = self._http_client.request("get", url, headers=self._get_headers(), raise_for_status=False)

        if response.status_code < 200 or response.status_code >= 300:
            raise RequestFailedError(response)

        return response.content

    def get_backtest_results(self, backtest_id: str) -> Dict[str, Any]:
        """Gets the JSON results for a backtest (for report generation).

        :param backtest_id: the backtest UUID
        :return: the backtest results JSON
        """
        return self._backtest_request("get", f"/{backtest_id}/results")

    def get_backtest_insights(self, backtest_id: str) -> List[Dict[str, Any]]:
        """Gets the alpha insights for a backtest.

        :param backtest_id: the backtest UUID
        :return: list of insights from the Alpha Framework
        """
        url = f"{self._base_url}/api/v1/backtests/{backtest_id}/insights"
        response = self._http_client.request("get", url, headers=self._get_headers(), raise_for_status=False)

        if response.status_code < 200 or response.status_code >= 300:
            raise RequestFailedError(response)

        return response.json()

    def get_latest_backtest(self, status: str = "completed") -> Optional[Dict[str, Any]]:
        """Gets the most recent backtest with the given status.

        :param status: filter by status (default: completed)
        :return: the latest backtest or None if none found
        """
        backtests = self.list_backtests(status=status, limit=1)
        return backtests[0] if backtests else None

    def get_backtest_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Gets a backtest by name.

        :param name: the backtest name
        :return: the backtest or None if not found
        """
        backtests = self.list_backtests(limit=100)
        for bt in backtests:
            if bt.get("name") == name:
                return bt
        return None
