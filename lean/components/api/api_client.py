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

from typing import Any, Dict

from lean.components.api.account_client import AccountClient
from lean.components.api.backtest_client import BacktestClient
from lean.components.api.compile_client import CompileClient
from lean.components.api.data_client import DataClient
from lean.components.api.file_client import FileClient
from lean.components.api.lean_client import LeanClient
from lean.components.api.live_client import LiveClient
from lean.components.api.market_client import MarketClient
from lean.components.api.module_client import ModuleClient
from lean.components.api.node_client import NodeClient
from lean.components.api.optimization_client import OptimizationClient
from lean.components.api.organization_client import OrganizationClient
from lean.components.api.project_client import ProjectClient
from lean.components.api.service_client import ServiceClient
from lean.components.api.user_client import UserClient
from lean.components.util.http_client import HTTPClient
from lean.components.util.logger import Logger
from lean.constants import API_BASE_URL
from lean.models.errors import AuthenticationError, RequestFailedError


class APIClient:
    """The APIClient class manages communication with the QuantConnect API."""

    def __init__(self, logger: Logger, http_client: HTTPClient, user_id: str, api_token: str) -> None:
        """Creates a new APIClient instance.

        :param logger: the logger to use to print debug messages to
        :param http_client: the HTTP client to make HTTP requests with
        :param user_id: the QuantConnect user id to use when sending authenticated requests
        :param api_token: the QuantConnect API token to use when sending authenticated requests
        """
        self._logger = logger
        self._http_client = http_client
        self.set_user_token(user_id, api_token)

        # Create the clients containing the methods to send requests to the various API endpoints
        self.accounts = AccountClient(self)
        self.backtests = BacktestClient(self)
        self.compiles = CompileClient(self)
        self.data = DataClient(self, http_client)
        self.files = FileClient(self)
        self.live = LiveClient(self)
        self.market = MarketClient(self)
        self.modules = ModuleClient(self)
        self.nodes = NodeClient(self)
        self.optimizations = OptimizationClient(self)
        self.organizations = OrganizationClient(self)
        self.projects = ProjectClient(self)
        self.services = ServiceClient(self)
        self.users = UserClient(self)
        self.lean = LeanClient(self)

    def set_user_token(self, user_id: str, api_token: str):
        self._user_id = user_id
        self._api_token = api_token

    def get(self, endpoint: str, parameters: Dict[str, Any] = {}) -> Any:
        """Makes an authenticated GET request to the given endpoint with the given parameters.

        Raises an error if the request fails or if the current credentials are invalid.

        :param endpoint: the API endpoint to send the request to
        :param parameters: the parameters to attach to the url
        :return: the parsed response of the request
        """
        return self._request("get", endpoint, {"params": parameters})

    def post(self, endpoint: str, data: Dict[str, Any] = {}, data_as_json: bool = True) -> Any:
        """Makes an authenticated POST request to the given endpoint with the given data.

        Raises an error if the request fails or if the current credentials are invalid.

        :param endpoint: the API endpoint to send the request to
        :param data: the data to send in the body of the request
        :param data_as_json: True if data needs to be sent as JSON, False if data needs to be sent as form data
        :return: the parsed response of the request
        """
        options = {"json": data} if data_as_json else {"data": data}
        return self._request("post", endpoint, options)

    def is_authenticated(self) -> bool:
        """Checks whether the current credentials are valid.

        :return: True if the current credentials are valid, False if not
        """
        try:
            self.get("authenticate")
            return True
        except (RequestFailedError, AuthenticationError):
            from traceback import format_exc
            self._logger.debug(format_exc().strip())
            return False

    def _request(self, method: str, endpoint: str, options: Dict[str, Any] = {}, retry_http_5xx: bool = True) -> Any:
        """Makes an authenticated request to the given endpoint.

        :param method: the HTTP method to use for the request
        :param endpoint: the API endpoint to send the request to
        :param options: additional options to pass on to requests.request()
        :param retry_http_5xx: True if the request should be retried on an HTTP 5xx response, False if not
        :return: the parsed response of the request
        """
        from hashlib import sha256
        from urllib.parse import urljoin
        from lean import __version__
        from time import time

        full_url = urljoin(API_BASE_URL, endpoint)

        # Create the hash which is used to authenticate the user to the API
        timestamp = str(int(time()))
        password = sha256(f"{self._api_token}:{timestamp}".encode("utf-8")).hexdigest()

        headers = {
            "Timestamp": timestamp
        }

        version = __version__
        if __version__ == 'dev':
            version = 99999999
        headers["User-Agent"] = f"Lean CLI {version}"

        response = self._http_client.request(method,
                                             full_url,
                                             headers=headers,
                                             auth=(self._user_id, password),
                                             raise_for_status=False,
                                             **options)

        if self._logger.debug_logging_enabled:
            self._logger.debug(f"Request response: {response.text}")

        if 500 <= response.status_code < 600 and retry_http_5xx:
            return self._request(method, endpoint, options, False)

        if response.status_code == 500:
            raise AuthenticationError()

        if response.status_code < 200 or response.status_code >= 300:
            raise RequestFailedError(response)

        return self._parse_response(response)

    def _parse_response(self, response) -> Any:
        """Parses the data in a response.

        Raises an error if the data in the response indicates something went wrong.

        :param response: the response of the request
        :return: the data in the response
        """
        data = response.json()

        if data["success"]:
            return data

        self._http_client.log_unsuccessful_response(response)

        if "errors" in data and len(data["errors"]) > 0:
            if data["errors"][0].startswith("Hash doesn't match."):
                raise AuthenticationError()
            if data["errors"][0].startswith('UserID not valid'):
                data["errors"].append('Please login to your account with "lean login". '
                                      'https://www.quantconnect.com/docs/v2/lean-cli/api-reference/lean-login')
            raise RequestFailedError(response, "\n".join(data["errors"]))

        if "messages" in data and len(data["messages"]) > 0:
            raise RequestFailedError(response, "\n".join(data["messages"]))

        if "Message" in data:
            raise RequestFailedError(response, data["Message"])

        raise RequestFailedError(response)
