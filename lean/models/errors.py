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

from typing import Optional

import requests


class RequestFailedError(Exception):
    """A RequestFailedError indicates that an HTTP request has failed."""

    def __init__(self, response: requests.Response, message: Optional[str] = None) -> None:
        """Creates a new RequestFailedError instance.

        :param response: the data of the failed response
        :param message: a display-friendly error message, defaults to a message based on the response
        """
        if message is None:
            request = response.request
            message = f"{request.method} request to {request.url} failed with status code {response.status_code}"

        super().__init__(message)

        self.response = response


class AuthenticationError(Exception):
    """An error indicating that a request has failed because the used credentials were invalid."""

    def __init__(self) -> None:
        super().__init__("Invalid credentials, please log in using `lean login`")
