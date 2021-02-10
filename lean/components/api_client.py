from hashlib import sha256
from time import time
from typing import Any, Dict
from urllib.parse import urljoin

import requests

from lean.components.logger import Logger
from lean.models.errors import AuthenticationError, RequestFailedError


class APIClient:
    """The APIClient class manages communication with the QuantConnect API."""

    def __init__(self, logger: Logger, base_url: str, user_id: str, api_token: str) -> None:
        """Creates a new APIClient instance.

        :param logger: the logger to use to print debug messages to
        :param base_url: the base url of the QuantConnect API
        :param user_id: the QuantConnect user id to use when sending authenticated requests
        :param api_token: the QuantConnect API token to use when sending authenticated requests
        """
        self._logger = logger
        self._base_url = base_url
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

    def post(self, endpoint: str, data: Dict[str, Any] = {}) -> Any:
        """Makes an authenticated POST request to the given endpoint with the given data.

        Raises an error if the request fails or if the current credentials are invalid.

        :param endpoint: the API endpoint to send the request to
        :param data: the data to send in the body of the request
        :return: the parsed response of the request
        """
        return self._request("post", endpoint, {"json": data})

    def is_authenticated(self) -> bool:
        """Checks whether the current credentials are valid.

        :return: True if the current credentials are valid, False if not
        """
        try:
            requests.get("https://github.com/QuantConnect/Lean/archive/master.zip")
            self.get("projects/read")
            return True
        except:
            return False

    def _request(self, method: str, endpoint: str, options: Dict[str, Any] = {}) -> Any:
        """Makes an authenticated request to the given endpoint.

        :param method: the HTTP method to use for the request
        :param endpoint: the API endpoint to send the request to
        :param options: additional options to pass on to requests.request()
        :return: the parsed response of the request
        """
        base_url = self._base_url if self._base_url.endswith("/") else self._base_url + "/"
        full_url = urljoin(base_url, endpoint)

        # Create the hash which is used to authenticate the user to the API
        timestamp = str(int(time()))
        password = sha256(f"{self._api_token}:{timestamp}".encode("utf-8")).hexdigest()

        self._logger.debug(f"{method.upper()} {full_url} with data {list(options.values())[0]}")

        response = requests.request(method,
                                    full_url,
                                    headers={"Timestamp": timestamp},
                                    auth=(self._user_id, password),
                                    **options)

        if response.status_code == 500:
            raise AuthenticationError()

        if not response.ok or response.status_code < 200 or response.status_code >= 300:
            raise RequestFailedError(response)

        return self._parse_response(response)

    def _parse_response(self, response: requests.Response) -> Any:
        """Parses the data in a response.

        Raises an error if the data in the response indicates something went wrong.

        :param response: the response of the request
        :return: the data in the response
        """
        data = response.json()

        if data["success"]:
            return data

        if "errors" in data and len(data["errors"]) > 0:
            if data["errors"][0].startswith("Hash doesn't match."):
                raise AuthenticationError()

            raise RequestFailedError(response, "\n".join(data["errors"]))

        if "messages" in data and len(data["messages"]) > 0:
            raise RequestFailedError(response, "\n".join(data["messages"]))

        raise RequestFailedError(response)
