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

from typing import List

from lean.components.api.api_client import *
from lean.models.api import QCDataset


class MarketClient:
    """The MarketClient class contains methods to interact with market/* API endpoints."""

    def __init__(self, api_client: 'APIClient') -> None:
        """Creates a new MarketClient instance.

        :param api_client: the APIClient instance to use when making requests
        """
        self._api = api_client

    def list_datasets(self) -> List[QCDataset]:
        """Get all available datasets.

        :return: all datasets on QuantConnect Datasets
        """
        data = self._api.post("market/data/list")

        return [QCDataset(**dataset) for dataset in data["list"]]
