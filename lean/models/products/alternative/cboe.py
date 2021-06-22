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

import click

from lean.container import container
from lean.models.api import QCFullOrganization
from lean.models.products.base import Product, ProductDetails


class CBOEProduct(Product):
    """The CBOEProduct class supports downloading CBOE data with the `lean data download` command."""

    def __init__(self, ticker: str) -> None:
        super().__init__()

        self._ticker = ticker

    @classmethod
    def get_name(cls) -> str:
        return "CBOE Volatility Index Pricing"

    @classmethod
    def build(cls, organization: QCFullOrganization) -> List[Product]:
        logger = container.logger()
        api_client = container.api_client()

        while True:
            ticker = click.prompt("Enter the ticker of the index")

            if len(api_client.data.list_files(f"alternative/cboe/{ticker.lower()}.csv")) > 0:
                return [CBOEProduct(ticker)]

            logger.info(f"Error: we have no volatility index pricing for {ticker.upper()}")

    def get_details(self) -> ProductDetails:
        return ProductDetails(data_type=self.get_name(),
                              ticker=self._ticker.upper(),
                              market="-",
                              resolution="Daily",
                              date_range="All available data")

    def _get_data_files(self) -> List[str]:
        return [f"alternative/cboe/{self._ticker.lower()}.csv"]
