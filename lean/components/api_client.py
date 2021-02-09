import json
from base64 import b64encode
from hashlib import sha256
from time import time
from typing import Any, Dict

from lean.components.http_client import HTTPClient
from lean.models.errors import AuthenticationError, RequestFailedError
from lean.models.response import Response


class APIClient:
    """The APIClient class manages communication with the QuantConnect API."""

    def __init__(self, http_client: HTTPClient, base_url: str, user_id: str, api_token: str) -> None:
        """Creates a new APIClient instance.

        :param http_client: the HTTPClient instance to make HTTP requests with
        :param base_url: the base url of the QuantConnect API
        :param user_id: the QuantConnect user id to use for authentication
        :param api_token: the QuantConnect API token to use for authentication
        """
        self._http_client = http_client
        self._base_url = base_url
        self._user_id = user_id
        self._api_token = api_token

    def get(self, endpoint: str, params: Dict[str, Any] = {}) -> Any:
        """Makes an authenticated GET request to the given endpoint with the given parameters.

        Raises an error if the request fails or if the current credentials are invalid.

        :param endpoint: the API endpoint to send the request to
        :param params: the parameters to send
        :return: the parsed response of the request
        """
        url = self._endpoint_to_url(endpoint)
        headers = self._create_headers()

        try:
            response = self._http_client.get(url, params=params, headers=headers)
        except RequestFailedError as error:
            # An HTTP 500 response may also indicate that the user is not logged in
            if error.response.status_code == 500:
                raise AuthenticationError()
            else:
                raise error

        return self._parse_response(response)

    def post(self, endpoint: str, data: Dict[str, Any] = {}) -> Any:
        """Makes an authenticated POST request to the given endpoint with the given data.

        Raises an error if the request fails or if the current credentials are invalid.

        :param endpoint: the API endpoint to send the request to
        :param data: the data to send in the body of the request
        :return: the parsed response of the request
        """
        url = self._endpoint_to_url(endpoint)
        headers = self._create_headers()

        try:
            response = self._http_client.post(url, data=data, headers=headers)
        except RequestFailedError as error:
            # An HTTP 500 response may also indicate that the user is not logged in
            if error.response.status_code == 500:
                raise AuthenticationError()
            else:
                raise error

        return self._parse_response(response)

    def is_authenticated(self) -> bool:
        """Checks whether the current credentials are valid.

        :return: True if the current credentials are valid, False if not
        """
        try:
            self.get("projects/read")
            return True
        except:
            return False

    def _endpoint_to_url(self, endpoint: str) -> str:
        """Converts an endpoint into a full url.

        :param endpoint: the endpoint to create the full url for
        :return: the full url combining the base url of the API with the requested endpoint
        """
        url = self._base_url
        if not url.endswith("/"):
            url += "/"

        if endpoint.startswith("/"):
            url += endpoint[1:]
        else:
            url += endpoint

        return url

    def _create_headers(self) -> Dict[str, str]:
        """Returns the headers needed to authenticate requests.

        :return: a dict containing all headers which need to be set on a request to authenticate the user
        """
        timestamp = str(int(time()))
        password = sha256(f"{self._api_token}:{timestamp}".encode("utf-8")).hexdigest()
        authorization = b64encode(bytes(f"{self._user_id}:{password}", "utf-8")).decode("ascii")

        return {
            "Timestamp": timestamp,
            "Authorization": f"Basic {authorization}"
        }

    def _parse_response(self, response: Response) -> Any:
        """Parses the data in a response.

        Raises an error if the response indicates something went wrong.

        :param response: the response to parse
        :return: the parsed content of the response
        """
        data = json.loads(response.text)

        if data["success"]:
            return data

        if "errors" in data and len(data["errors"]) > 0:
            if data["errors"][0].startswith("Hash doesn't match."):
                raise AuthenticationError()

            raise RequestFailedError("\n".join(data["errors"]), response)

        if "messages" in data and len(data["messages"]) > 0:
            raise RequestFailedError("\n".join(data["messages"]), response)

        raise RequestFailedError("Request failed", response)
