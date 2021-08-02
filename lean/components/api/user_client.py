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

from lean.components.api.api_client import *
from lean.models.api import QCUser


class UserClient:
    """The UserClient class contains methods to interact with user/* API endpoints."""

    def __init__(self, api_client: 'APIClient') -> None:
        """Creates a new UserClient instance.

        :param api_client: the APIClient instance to use when making requests
        """
        self._api = api_client

    def get_info(self, organization_id: Optional[str] = None) -> QCUser:
        """Returns the user's name, avatar url and organization badge.

        :param organization_id: the id of the organization to get the badge of or None to use the preferred one
        :return: the user's name, avatar url and organization badge
        """
        parameters = {}

        if organization_id is not None:
            parameters["organizationId"] = organization_id

        data = self._api.post("user/read", parameters)
        return QCUser(**data["user"])
