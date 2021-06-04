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
from typing import List, Optional, Tuple

import click

from lean.container import container
from lean.models.api import QCFullOrganization, QCResolution
from lean.models.logger import Option
from lean.models.map_file import MapFile, MapFileRange
from lean.models.products.base import Product
from lean.models.products.security.base import DataType, SecurityProduct, SecurityType


class EquityProduct(SecurityProduct):
    """The EquityProduct class supports downloading equity data with the `lean data download` command."""

    def __init__(self,
                 data_type: DataType,
                 market: str,
                 ticker: str,
                 resolution: QCResolution,
                 start_date: Optional[datetime],
                 end_date: Optional[datetime]) -> None:
        super().__init__(SecurityType.Equity, data_type, market, ticker, resolution, start_date, end_date)

    @classmethod
    def get_product_name(cls) -> str:
        return SecurityType.Equity.value

    @classmethod
    def build(cls, organization: QCFullOrganization) -> List[Product]:
        if not organization.has_map_factor_files_subscription():
            raise RuntimeError("\n".join([
                "Your organization needs to have an active map & factor files subscription to download equity data",
                f"You can add the subscription at https://www.quantconnect.com/pricing?organization={organization.id}"
            ]))

        data_type = cls._ask_data_type([DataType.Trade, DataType.Quote])
        market = "USA"

        if data_type is DataType.Trade:
            resolution = cls._ask_resolution([QCResolution.Tick,
                                              QCResolution.Second,
                                              QCResolution.Minute,
                                              QCResolution.Hour,
                                              QCResolution.Daily])
        else:
            resolution = cls._ask_resolution([QCResolution.Tick, QCResolution.Second, QCResolution.Minute])

        base_directory = f"equity/{market.lower()}/{resolution.value.lower()}"

        def validate_ticker(t: str) -> bool:
            if resolution == QCResolution.Hour or resolution == QCResolution.Daily:
                return t.lower() in cls._list_files(f"{base_directory}/{t[0].lower()}", r"/([^/.]+)\.zip")

            return len(cls._list_files(f"{base_directory}/{t.lower()}/", fr"/\d+_{data_type.name.lower()}\.zip")) > 0

        ticker = cls._ask_ticker(SecurityType.Equity, market, resolution, validate_ticker)

        if resolution != QCResolution.Hour and resolution != QCResolution.Daily:
            dates = cls._list_dates(f"{base_directory}/{ticker.lower()}/", fr"/(\d+)_{data_type.name.lower()}\.zip")
            start_date, end_date = cls._ask_start_end_date(dates)
        else:
            start_date, end_date = None, None

        logger = container.logger()

        if resolution != QCResolution.Hour and resolution != QCResolution.Daily:
            map_files = container.data_downloader().download_map_files(organization.id)
            map_file_ranges: List[Tuple[MapFile, MapFileRange]] = []

            for map_file in map_files:
                for r in map_file.get_ticker_ranges(ticker, start_date, end_date):
                    map_file_ranges.append((map_file, r))

            map_file_ranges = sorted(map_file_ranges, key=lambda r: r[1].start_date)

            if len(map_file_ranges) > 1:
                logger.info(f"Multiple companies have used the {ticker.upper()} ticker in the requested date range")
                selected_range = logger.prompt_list("Select the date range you are looking for", [
                    Option(id=r, label=r[1].get_label()) for r in map_file_ranges
                ])

                selected_map_file = selected_range[0]
                start_date = selected_range[1].start_date
                end_date = selected_range[1].end_date
            else:
                selected_map_file = map_file_ranges[0][0]
        else:
            selected_map_file = None

        products = [EquityProduct(data_type, market, ticker, resolution, start_date, end_date)]

        if selected_map_file is not None:
            historic_ranges = selected_map_file.get_historic_ranges(start_date)
            for index, r in enumerate(historic_ranges):
                next_ticker = ticker if index == 0 else historic_ranges[index - 1].ticker
                logger.info(f"Before trading as {next_ticker}, the selected company traded as {r.ticker}")

                if not click.confirm(
                        f"Do you also want to download {r.ticker} data from {r.start_date.strftime('%Y-%m-%d')} to {r.end_date.strftime('%Y-%m-%d')}?"):
                    break

                products.append(
                    EquityProduct(data_type, market, r.ticker, resolution, r.start_date, r.end_date))

        return products

    def _get_data_files(self) -> List[str]:
        files = []

        data_directory = container.lean_config_manager().get_data_directory()
        for meta_type in ["map", "factor"]:
            zip_path = self._list_files(f"equity/{self._market.lower()}/{meta_type}_files/{meta_type}_files_", "")[-1]
            if not (data_directory / zip_path).is_file():
                files.append(zip_path)

        base_directory = f"equity/{self._market.lower()}/{self._resolution.value.lower()}"

        if self._resolution == QCResolution.Hour or self._resolution == QCResolution.Daily:
            files.append(f"{base_directory}/{self._ticker.lower()}.zip")
        else:
            files.extend(self._get_data_files_in_range(f"{base_directory}/{self._ticker.lower()}/",
                                                       fr"/(\d+)_{self._data_type.name.lower()}\.zip",
                                                       self._start_date,
                                                       self._end_date))

        return files
