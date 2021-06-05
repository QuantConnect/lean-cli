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
from typing import List

import click

from lean.container import container
from lean.models.api import QCFullOrganization
from lean.models.logger import Option
from lean.models.products.base import Product, ProductDetails


class SECProduct(Product):
    """The SECProduct class supports downloading SEC report data with the `lean data download` command."""

    def __init__(self, report_type: str, ticker: str, start_date: datetime, end_date: datetime) -> None:
        super().__init__()

        self._report_type = report_type
        self._ticker = ticker
        self._start_date = start_date
        self._end_date = end_date

    @classmethod
    def get_product_name(cls) -> str:
        return "SEC Filings"

    @classmethod
    def build(cls, organization: QCFullOrganization) -> List[Product]:
        logger = container.logger()

        report_type = logger.prompt_list("Select the report type", [
            Option(id="10K", label="10K - Yearly reports"),
            Option(id="10Q", label="10Q - Quarterly reports"),
            Option(id="8K", label="8K - Investor notices")
        ])

        while True:
            ticker = click.prompt("Enter the ticker of the company")

            dates = cls._list_dates(f"alternative/sec/{ticker.lower()}/", fr"/(\d+)_{report_type}.zip")
            if len(dates) > 0:
                break

            logger.info(f"Error: we have no {report_type} reports for {ticker.upper()}")

        start_date, end_date = cls._ask_start_end_date(dates)

        return [SECProduct(report_type, ticker, start_date, end_date)]

    def get_details(self) -> ProductDetails:
        date_range = f"{self._start_date.strftime('%Y-%m-%d')} - {self._end_date.strftime('%Y-%m-%d')}"

        return ProductDetails(data_type=f"SEC {self._report_type} reports",
                              ticker=self._ticker.upper(),
                              market="-",
                              resolution="-",
                              date_range=date_range)

    def _get_data_files(self) -> List[str]:
        return self._get_data_files_in_range(f"alternative/sec/{self._ticker.lower()}/",
                                             fr"/(\d+)_{self._report_type}.zip",
                                             self._start_date,
                                             self._end_date)
