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

from datetime import datetime
from typing import Optional

from lean.components.api.api_client import *
from lean.models.api import QCLink, QCResolution, QCSecurityType


class DataClient:
    """The DataClient class contains methods to interact with data/* API endpoints."""

    def __init__(self, api_client: 'APIClient') -> None:
        """Creates a new AccountClient instance.

        :param api_client: the APIClient instance to use when making requests
        """
        self._api = api_client

    def get_link(self,
                 security_type: QCSecurityType,
                 ticker: str,
                 market: str,
                 resolution: QCResolution,
                 date: Optional[datetime]) -> QCLink:
        """Returns the link to the downloadable data.

        :param security_type: the security type of the data
        :param ticker: the ticker of the data
        :param market: the market of the data
        :param resolution: the resolution of the data
        :param date: the date of the data, may be None
        :return: an object containing the download link for the data
        """
        parameters = {
            "format": "link",
            "type": security_type.value.lower(),
            "ticker": ticker,
            "market": market,
            "resolution": resolution.value.lower()
        }

        if date is not None:
            parameters["date"] = date.strftime("%Y%m%d")

        data = self._api.post("data/read", parameters)
        return QCLink(**data)
