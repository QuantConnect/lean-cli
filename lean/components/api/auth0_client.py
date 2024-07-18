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
from lean.components.util.logger import Logger
from lean.constants import API_BASE_URL
from lean.models.api import QCAuth0Authorization
from lean.models.errors import RequestFailedError


class Auth0Client:
    """The Auth0Client class contains methods to interact with live/auth0/* API endpoints."""

    def __init__(self, api_client: 'APIClient') -> None:
        """Creates a new Auth0Client instance.

        :param api_client: the APIClient instance to use when making requests
        """
        self._api = api_client

    def read(self, brokerage_id: str) -> QCAuth0Authorization:
        """Reads the authorization data for a brokerage.

        :param brokerage_id: the id of the brokerage to read the authorization data for
        :return: the authorization data for the specified brokerage
        """
        try:
            payload = {
                "brokerage": brokerage_id
            }

            data = self._api.post("live/auth0/read", payload)
            return QCAuth0Authorization(**data)
        except RequestFailedError as e:
            return QCAuth0Authorization(authorization=None)

    @staticmethod
    def authorize(brokerage_id: str, logger: Logger) -> None:
        """Starts the authorization process for a brokerage.

        :param brokerage_id: the id of the brokerage to start the authorization process for
        :param logger: the logger instance to use
        """
        from webbrowser import open

        full_url = f"{API_BASE_URL}live/auth0/authorize?brokerage={brokerage_id}"
        logger.info(f"Please open the following URL in your browser to authorize the LEAN CLI.")
        logger.info(full_url)
        open(full_url)


