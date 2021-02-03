from hashlib import sha256
from time import time
from typing import Dict, Any

import requests

from lean.api.errors import FailedRequestException, AuthenticationException

BASE_URL = "https://www.quantconnect.com/api/v2"


class APIClient:
    def __init__(self, user_id: str, api_token: str) -> None:
        """Create a new APIClient instance.

        :param user_id: the QuantConnect user id to use for authentication
        :param api_token: the QuantConnect API token to use for authentication
        """
        self.__user_id = user_id
        self.__api_token = api_token

    def get(self, endpoint: str, parameters: Dict[str, Any] = {}) -> Any:
        """Make an authenticated GET request to the given endpoint with the given parameters.

        :param endpoint: the API endpoint to send the request to
        :param parameters: the parameters to send
        :return: the parsed response of the request
        """
        return self.__request("GET", endpoint, {"params": parameters})

    def post(self, endpoint: str, data: Dict[str, Any] = {}) -> Any:
        """Make an authenticated POST request to the given endpoint with the given data.

        :param endpoint: the API endpoint to send the request to
        :param parameters: the data to send in the body of the request
        :return: the parsed response of the request
        """
        return self.__request("POST", endpoint, {"json": data})

    def is_authenticated(self) -> bool:
        try:
            self.get("projects/read")
            return True
        except:
            return False

    def __request(self, method: str, endpoint: str, options: Dict[str, Any] = {}) -> Any:
        """Make an authenticated request to the given endpoint and parse the response.

        :param method: the HTTP method to use for the request
        :param endpoint: the API endpoint to send the request to
        :param options: additional options to pass on to requests.request()
        :return: the parsed response of the request
        """
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"

        url = BASE_URL + endpoint

        # Create the hash which is used to authenticate the user to the API
        timestamp = str(int(time()))
        hash = sha256(f"{self.__api_token}:{timestamp}".encode("utf-8")).hexdigest()

        response = requests.request(method,
                                    url,
                                    headers={"Timestamp": timestamp},
                                    auth=(self.__user_id, hash),
                                    **options)

        if response.status_code == 500:
            raise AuthenticationException()

        if not response.ok or response.status_code < 200 or response.status_code >= 300:
            raise FailedRequestException(f"{method} request to {url} failed with status code {response.status_code}")

        data = response.json()

        if data["success"]:
            return data

        if "errors" in data and len(data["errors"]) > 0:
            if data["errors"][0].startswith("Hash doesn't match."):
                raise AuthenticationException()

            raise FailedRequestException("\n".join(data["errors"]))

        if "messages" in data and len(data["messages"]) > 0:
            raise FailedRequestException("\n".join(data["messages"]))

        raise FailedRequestException(f"{method} request to {url} failed with status code {response.status_code}")
