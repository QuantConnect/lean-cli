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


from lean.components.util.logger import Logger


class HTTPClient:
    """The HTTPClient class is a lightweight wrapper around the requests library with additional logging."""

    def __init__(self, logger: Logger) -> None:
        """Creates a new HTTPClient instance.

        :param logger: the logger to log debug messages with
        """
        self._logger = logger

    def get(self, url: str, **kwargs):
        """A wrapper around requests.get().

        An error is raised if the response is unsuccessful unless kwargs["raise_for_status"] == False.

        :param url: the request url
        :param kwargs: any kwargs to pass on to requests.get()
        :return: the response of the request
        """
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs):
        """A wrapper around requests.post().

        An error is raised if the response is unsuccessful unless kwargs["raise_for_status"] == False.

        :param url: the request url
        :param kwargs: any kwargs to pass on to requests.post()
        :return: the response of the request
        """
        return self.request("POST", url, **kwargs)

    def request(self, method: str, url: str, **kwargs):
        """A wrapper around requests.request().

        An error is raised if the response is unsuccessful unless kwargs["raise_for_status"] == False.

        :param method: the request method
        :param url: the request url
        :param kwargs: any kwargs to pass on to requests.request()
        :return: the response of the request
        """
        from requests import request, exceptions

        self._log_request(method, url, **kwargs)

        raise_for_status = kwargs.pop("raise_for_status", True)
        try:
            response = request(method, url, **kwargs)
        except exceptions.SSLError as e:
            raise Exception(f"""
Detected SSL error, this might be due to custom certificates in your environment or system trust store.
A known limitation of the python requests implementation.
Please consider installing library https://pypi.org/project/python-certifi-win32/.
Related issue https://github.com/psf/requests/issues/2966
    """.strip())

        self._check_response(response, raise_for_status)
        return response

    def log_unsuccessful_response(self, response) -> None:
        """Logs an unsuccessful response's status code and body.

        :param response: the response to log
        """
        body = f"body:\n{response.text}" if response.text != "" else "empty body"
        self._logger.debug(f"Request was not successful, status code {response.status_code}, {body}")

    def _log_request(self, method: str, url: str, **kwargs) -> None:
        """Logs a request.

        :param method: the request method
        :param url: the request url
        :param kwargs: any kwargs passed to a request.* method
        """
        from json import dumps
        message = f"--> {method.upper()} {url}"

        data = next((kwargs.get(key) for key in ["json", "data", "params"] if key in kwargs), None)
        if data is not None and data != {}:
            message += f" with data:\n{dumps(data, indent=4)}"

        self._logger.debug(message)

    def _check_response(self, response, raise_for_status: bool) -> None:
        """Checks a response, logging a debug message if it wasn't successful.

        :param response: the response to check
        :param raise_for_status: True if an error needs to be raised if the request wasn't successful, False if not
        """
        if response.status_code < 200 or response.status_code >= 300:
            self.log_unsuccessful_response(response)

        if raise_for_status:
            response.raise_for_status()
