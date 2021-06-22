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
from typing import List, Optional

from lean.models.api import QCFullOrganization, QCResolution
from lean.models.products.base import Product, ProductDetails
from lean.models.products.security.base import DataType, SecurityProduct, SecurityType


class FutureProduct(SecurityProduct):
    """The FutureProduct class supports downloading future data with the `lean data download` command."""

    def __init__(self,
                 data_type: DataType,
                 market: str,
                 ticker: str,
                 resolution: QCResolution,
                 start_date: Optional[datetime],
                 end_date: Optional[datetime]) -> None:
        super().__init__(SecurityType.Future, data_type, market, ticker, resolution, start_date, end_date)

    @classmethod
    def get_name(cls) -> str:
        return SecurityType.Future.value

    @classmethod
    def build(cls, organization: QCFullOrganization) -> List[Product]:
        data_type = DataType.Margins
        market = cls._ask_market(["CBOE", "CBOT", "CME", "COMEX", "HKFE", "ICE", "NYMEX", "SGX"])
        resolution = "margins"

        base_directory = f"future/{market.lower()}/{resolution}"

        def validate_ticker(t: str) -> bool:
            return t.upper() in cls._list_files(f"{base_directory}/", r"/([^/.]+)\.csv")

        ticker = cls._ask_ticker(SecurityType.Future, market, resolution, validate_ticker)

        return [FutureProduct(data_type, market, ticker, QCResolution.Daily, None, None)]

    def get_details(self) -> ProductDetails:
        details = super().get_details()
        details.resolution = "-"
        return details

    def _get_data_files(self) -> List[str]:
        return [f"future/{self._market.lower()}/margins/{self._ticker.upper()}.csv"]
