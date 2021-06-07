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

import abc
from datetime import datetime
from enum import Enum
from typing import Callable, List, Optional, Tuple, Union

import click

from lean.container import container
from lean.models.api import QCFullOrganization, QCResolution
from lean.models.logger import Option
from lean.models.map_file import MapFile, MapFileRange
from lean.models.products.base import Product, ProductDetails


class SecurityType(str, Enum):
    CFD = "CFD"
    Crypto = "Crypto"
    Equity = "Equity"
    EquityOption = "Equity Option"
    Forex = "Forex"
    Future = "Future"
    FutureOption = "Future Option"
    Index = "Index"
    IndexOption = "Index Option"

    def get_internal_name(self) -> str:
        """Returns the internal name of the security type.

        :return: the name of the security type in LEAN
        """
        return {
            SecurityType.CFD: "Cfd",
            SecurityType.Crypto: "Crypto",
            SecurityType.Equity: "Equity",
            SecurityType.EquityOption: "Option",
            SecurityType.Forex: "Forex",
            SecurityType.Future: "Future",
            SecurityType.FutureOption: "FutureOption",
            SecurityType.Index: "Index",
            SecurityType.IndexOption: "IndexOption"
        }[self]


class DataType(str, Enum):
    Trade = "Trade data"
    Quote = "Quote data"
    OpenInterest = "Open interest data"
    Margins = "Margins data"


class SecurityProduct(Product, abc.ABC):
    """The SecurityProduct class provides a common base for all security data Product implementations."""

    def __init__(self,
                 security_type: SecurityType,
                 data_type: DataType,
                 market: str,
                 ticker: str,
                 resolution: QCResolution,
                 start_date: Optional[datetime],
                 end_date: Optional[datetime]) -> None:
        super().__init__()

        self._security_type = security_type
        self._data_type = data_type
        self._market = market
        self._ticker = ticker
        self._resolution = resolution
        self._start_date = start_date
        self._end_date = end_date

    def get_details(self) -> ProductDetails:
        data_type = f"{self.get_product_name()} {self._data_type.value.lower()}"
        ticker = self._ticker.upper()
        market = self._market
        resolution = self._resolution

        if self._start_date is None:
            date_range = "All available data"
        else:
            date_range = f"{self._start_date.strftime('%Y-%m-%d')} - {self._end_date.strftime('%Y-%m-%d')}"

        return ProductDetails(data_type=data_type,
                              ticker=ticker,
                              market=market,
                              resolution=resolution,
                              date_range=date_range)

    @classmethod
    def _ask_data_type(cls, available_data_types: List[DataType]) -> DataType:
        """Asks the user to give the data type of the data.

        :param available_data_types: the data types the user can pick from
        :return: the selected data type
        """
        return container.logger().prompt_list("Select the data type", [
            Option(id=t, label=t.value) for t in available_data_types
        ])

    @classmethod
    def _ask_market(cls, available_markets: List[str]) -> str:
        """Asks the user to give the market of the data.

        :param available_markets: the markets the user can pick from
        :return: the selected market
        """
        return container.logger().prompt_list("Select the market of the data", [
            Option(id=m, label=m) for m in available_markets
        ])

    @classmethod
    def _ask_resolution(cls, available_resolutions: List[QCResolution]) -> QCResolution:
        """Asks the user to give the resolution of the data.

        :param available_resolutions: the resolutions the user can pick from
        :return: the selected resolution
        """
        return container.logger().prompt_list("Select the resolution of the data", [
            Option(id=r, label=r.value) for r in available_resolutions
        ])

    @classmethod
    def _ask_ticker(cls,
                    security_type: SecurityType,
                    market: str,
                    resolution: Union[QCResolution, str],
                    validate_ticker: Callable[[str], bool]) -> str:
        """Asks the user to give the ticker of the data.

        :param security_type: the security type of the data
        :param market: the market of the data
        :param resolution: the resolution of the data
        :param validate_ticker: the lambda which is called when verifying whether the ticker the user gives is valid
        :return: the given ticker
        """
        security_type = security_type.get_internal_name().lower()
        market = market.lower()
        resolution = resolution.value.lower() if isinstance(resolution, QCResolution) else resolution

        url = f"https://www.quantconnect.com/data/tree/{security_type}/{market}/{resolution}"

        logger = container.logger()
        logger.info(f"Browse the available data at {url}")

        while True:
            ticker = click.prompt("Enter the ticker of the data")

            if validate_ticker(ticker):
                return ticker

            logger.info(f"Error: we have no data for {ticker.upper()}")


class MapFactorSecurityProduct(SecurityProduct, abc.ABC):
    """The MapFactorSecurityProduct class provides utilities for securities which require a map/factor subscription."""

    @classmethod
    def _ensure_map_factor_subscription(cls, organization: QCFullOrganization) -> None:
        """Checks whether the organization has a map/factor subscription, raises an error if not.

        This method should be called at the start of build().

        :param organization: the organization passed to build()
        """
        if organization.has_map_factor_files_subscription():
            return

        raise RuntimeError("\n".join([
            f"Your organization needs to have an active map & factor files subscription to download {cls.get_product_name()} data",
            f"You can add the subscription at https://www.quantconnect.com/pricing?organization={organization.id}"
        ]))

    @classmethod
    def _finalize_build(cls,
                        organization: QCFullOrganization,
                        ticker: str,
                        start_date: Optional[datetime],
                        end_date: Optional[datetime],
                        factory: Callable[[str, Optional[datetime], Optional[datetime]], Product]) -> List[Product]:
        """Turns a chosen ticker and start/end date into a list of products.

        Uses the map files to detect when the ticker is used by more than one company between the given start/end date.
        Also asks the user whether data for previous tickers of the company should be downloaded, if any.

        :param organization: the organization the user selected
        :param ticker: the ticker given by the user
        :param start_date: the start date given by the user, may be None for hour and daily data
        :param end_date: the end date given by the user, may be None for hour and daily data
        :param factory: a lambda which is called with ticker, start date and end date when creating a new product
        :return: the list of products to add to the cart
        """
        if start_date is None:
            return [factory(ticker, start_date, end_date)]

        logger = container.logger()

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

        products = [factory(ticker, start_date, end_date)]

        historic_ranges = selected_map_file.get_historic_ranges(start_date)
        for index, r in enumerate(historic_ranges):
            next_ticker = ticker if index == 0 else historic_ranges[index - 1].ticker
            logger.info(f"Before trading as {next_ticker}, the selected company traded as {r.ticker}")

            if not click.confirm(
                    f"Do you also want to download {r.ticker} data from {r.start_date.strftime('%Y-%m-%d')} to {r.end_date.strftime('%Y-%m-%d')}?"):
                break

            products.append(factory(r.ticker, r.start_date, r.end_date))

        return products

    def _get_map_factor_data_files(self) -> List[str]:
        """Returns the map/factor files which should be downloaded if this product is downloaded.

        :return: a list of the relative paths of the recent map/factor files the user is missing
        """
        files = []

        data_directory = container.lean_config_manager().get_data_directory()
        for meta_type in ["map", "factor"]:
            zip_path = self._list_files(f"equity/{self._market.lower()}/{meta_type}_files/{meta_type}_files_", "")[-1]
            if not (data_directory / zip_path).is_file():
                files.append(zip_path)

        return files
