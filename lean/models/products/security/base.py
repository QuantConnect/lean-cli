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
from typing import Callable, List, Optional, Union

import click

from lean.container import container
from lean.models.api import QCResolution
from lean.models.logger import Option
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
