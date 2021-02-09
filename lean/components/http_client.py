import shutil
from pathlib import Path
from typing import Any, Dict

import requests

from lean.components.logger import Logger
from lean.models.errors import RequestFailedError
from lean.models.response import Response


class HTTPClient:
    """The HTTPClient provides methods to make HTTP requests."""

    def __init__(self, logger: Logger) -> None:
        """Creates an HTTPClient instance.

        :param logger: the logger to use when printing debug messages
        """
        self._logger = logger

    def get(self, url: str, params: Dict[str, str] = {}, headers: Dict[str, str] = {}) -> Response:
        """Performs a GET request to the given url.

        Raises an error if the request fails or if the response code is not in the 200-299 range.

        :param url: the url to make a GET request to
        :param params: the parameters to attach to the url
        :param headers: the headers to attach to the request
        :return: a Response object containing the data of the response
        """
        self._logger.debug(f"GET {url} with parameters {params}")

        response = requests.get(url, params=params, headers=headers)
        self._raise_if_request_failed(response)

        return self._make_response(response)

    def post(self, url: str, data: Dict[str, Any] = {}, headers: Dict[str, str] = {}) -> Response:
        """Performs a POST request to the given url.

        Raises an error if the request fails or if the response code is not in the 200-299 range.

        :param url: the url to make a POST request to
        :param data: the data to add as JSON body to the request
        :param headers: the headers to attach to the request
        :return: a Response object containing the data of the response
        """
        self._logger.debug(f"GET {url} with data {data}")

        response = requests.post(url, json=data, headers=headers)
        self._raise_if_request_failed(response)

        return self._make_response(response)

    def download_file(self, url: str, destination: Path) -> None:
        """Downloads a file at a given url using a GET request.

        Raises an error if the request fails or if the response code is not in the 200-299 range.

        :param url: the url to download the file from
        :param destination: the path to save the file to
        """
        with requests.get(url, stream=True) as response:
            self._raise_if_request_failed(response)

            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("wb") as file:
                shutil.copyfileobj(response.raw, file)

    def _raise_if_request_failed(self, response: requests.Response) -> None:
        """Raises a RequestFailedError if the request has failed.

        :param response: the response to the request
        """
        # Don't do anything if the response is okay
        if response.ok and 200 <= response.status_code < 300:
            return

        # Raise a consistent error message
        raise RequestFailedError(
            f"{response.request.method} request to {response.url} failed with status code {response.status_code}",
            self._make_response(response))

    def _make_response(self, response: requests.Response) -> Response:
        """Converts a requests.Response object into a lean.models.Response object.

        This abstraction exists to make unit testing easier.

        :param response: the requests.Response object
        :return: a lean.models.Response object containing the data from the requests.response Object
        """
        return Response(response.text, response.status_code)
