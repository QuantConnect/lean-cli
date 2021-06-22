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

from lean.models.api import QCFullOrganization
from lean.models.products.base import Product, ProductDetails


class USTreasuryProduct(Product):
    """The USTreasuryProduct class supports downloading US Treasury data with the `lean data download` command."""

    @classmethod
    def get_name(cls) -> str:
        return "US Treasury Yield Curve Rates"

    @classmethod
    def build(cls, organization: QCFullOrganization) -> List[Product]:
        return [USTreasuryProduct()]

    def get_details(self) -> ProductDetails:
        return ProductDetails(data_type=self.get_name(),
                              ticker="-",
                              market="-",
                              resolution="Daily",
                              date_range="All available data")

    def _get_data_files(self) -> List[str]:
        return ["alternative/ustreasury/yieldcurverates.csv"]
