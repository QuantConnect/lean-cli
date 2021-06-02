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
from typing import Iterator, List, Optional, Tuple, Union

import click
from dateutil.rrule import DAILY, rrule, rruleset, weekday

from lean.click import DateParameter
from lean.container import container
from lean.models.api import QCFullOrganization, QCResolution
from lean.models.logger import Option
from lean.models.map_file import MapFile, MapFileRange
from lean.models.market_hours_database import SecurityType
from lean.models.pydantic import WrappedBaseModel


class DataType(str, Enum):
    Trade = "Trade data"
    Quote = "Quote data"
    OpenInterest = "Open interest data"
    Chains = "Chains"
    Margins = "Margins data"


class OptionStyle(str, Enum):
    American = "American"
    European = "European"


class ProductDetails(WrappedBaseModel):
    product_type: str
    ticker: str
    market: str
    resolution: str
    date_range: str


class Product(abc.ABC):
    def __init__(self) -> None:
        self._data_files = None

    @classmethod
    @abc.abstractmethod
    def get_product_type(cls) -> str:
        """Returns the type of this product.

        :return: the type of the product that can be displayed to the user
        """
        raise NotImplementedError()

    @classmethod
    @abc.abstractmethod
    def build(cls, organization: QCFullOrganization) -> List['Product']:
        """Asks the user the required questions about the product to add it to the cart.

        :param organization: the organization the user selected
        :return: the products to add to the cart
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_details(self) -> ProductDetails:
        """Returns the details about this product in a way that they can be displayed to the user.

        :return: the pretty details of this product
        """
        raise NotImplementedError()

    def get_data_files(self) -> List[str]:
        if self._data_files is None:
            self._data_files = list(self._get_data_files())
        return self._data_files

    @abc.abstractmethod
    def _get_data_files(self) -> Iterator[str]:
        """Returns the data files this product instance contains.

        :return: the data files for this product instance, relative to the data directory
        """
        raise NotImplementedError()


class SecurityProduct(Product, abc.ABC):
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
        product_type = f"{self.get_product_type()} {self._data_type.value.lower()}"
        ticker = self._ticker.upper()
        market = self._market
        resolution = self._resolution

        if self._start_date is None:
            date_range = "All available data"
        else:
            date_range = f"{self._start_date.strftime('%Y-%m-%d')} - {self._end_date.strftime('%Y-%m-%d')}"

        return ProductDetails(product_type=product_type,
                              ticker=ticker,
                              market=market,
                              resolution=resolution,
                              date_range=date_range)

    @classmethod
    def _ask_data_type(cls, available_data_types: List[DataType]) -> DataType:
        return container.logger().prompt_list("Select the data type", [
            Option(id=t, label=t.value) for t in available_data_types
        ])

    @classmethod
    def _ask_market(cls, available_markets: List[str]) -> str:
        return container.logger().prompt_list("Select the market of the data", [
            Option(id=m, label=m) for m in available_markets
        ])

    @classmethod
    def _ask_resolution(cls, available_resolutions: List[QCResolution]) -> QCResolution:
        return container.logger().prompt_list("Select the resolution of the data", [
            Option(id=r, label=r.value) for r in available_resolutions
        ])

    @classmethod
    def _ask_ticker(cls, security_type: SecurityType, market: str, resolution: Union[QCResolution, str]) -> str:
        security_type = security_type.get_internal_name().lower()
        market = market.lower()
        resolution = resolution.value.lower() if isinstance(resolution, QCResolution) else resolution.lower()

        url = f"https://www.quantconnect.com/data/tree/{security_type}/{market}/{resolution}"
        container.logger().info(f"Browse the available data at {url}")

        return click.prompt("Enter the ticker of the data")

    @classmethod
    def _ask_start_end_date(cls, resolution: QCResolution) -> Tuple[Optional[datetime], Optional[datetime]]:
        if resolution == QCResolution.Hour or resolution == QCResolution.Daily:
            return None, None

        start_date = click.prompt("Start date of the data (yyyyMMdd)", type=DateParameter())

        while True:
            end_date = click.prompt("End date of the data (yyyyMMdd)", type=DateParameter())
            if end_date <= start_date:
                container.logger().info("Error: end date must be later than start date")
            else:
                return start_date, end_date

    def _is_hour_or_daily(self) -> bool:
        return self._resolution is QCResolution.Hour or self._resolution is QCResolution.Daily

    def _get_dates_with_data(self) -> List[str]:
        """Returns the dates between two dates for which the QuantConnect Data Library has data.

        The QuantConnect Data Library has data for all tradable days.
        This method uses the market hours database to find the tradable weekdays and the holidays.

        :return: the dates for which there is data for the given product in yyyyMMdd format
        """
        entry = container.market_hours_database().get_entry(self._security_type, self._market, self._ticker)

        # Create the set of rules containing all date rules
        rules = rruleset()

        # There is data on all weekdays on which the security trades
        weekdays_with_data = []
        for index, day in enumerate(["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
            if len(getattr(entry, day)) > 0:
                weekdays_with_data.append(weekday(index))
        rules.rrule(rrule(DAILY, dtstart=self._start_date, until=self._end_date, byweekday=weekdays_with_data))

        # There is no data for holidays
        for holiday in entry.holidays:
            rules.exdate(holiday)

        # Retrieve the dates of all tradable weekdays between the start and end date excluding the holidays
        dates = rules.between(self._start_date, self._end_date, inc=True)

        # Return the formatted version of all dates
        return [date.strftime("%Y%m%d") for date in dates]


class CFDSecurityProduct(SecurityProduct):
    def __init__(self,
                 data_type: DataType,
                 market: str,
                 ticker: str,
                 resolution: QCResolution,
                 start_date: Optional[datetime],
                 end_date: Optional[datetime]) -> None:
        super().__init__(SecurityType.CFD, data_type, market, ticker, resolution, start_date, end_date)

    @classmethod
    def get_product_type(cls) -> str:
        return SecurityType.CFD.value

    @classmethod
    def build(cls, organization: QCFullOrganization) -> List[Product]:
        data_type = DataType.Quote
        market = "Oanda"
        resolution = cls._ask_resolution([QCResolution.Tick,
                                          QCResolution.Second,
                                          QCResolution.Minute,
                                          QCResolution.Hour,
                                          QCResolution.Daily])
        ticker = cls._ask_ticker(SecurityType.CFD, market, resolution)
        start_date, end_date = cls._ask_start_end_date(resolution)

        return [CFDSecurityProduct(data_type, market, ticker, resolution, start_date, end_date)]

    def _get_data_files(self) -> Iterator[str]:
        base_directory = f"cfd/{self._market.lower()}/{self._resolution.value.lower()}"

        if self._is_hour_or_daily():
            yield f"{base_directory}/{self._ticker.lower()}.zip"
            return

        for date in self._get_dates_with_data():
            yield f"{base_directory}/{self._ticker.lower()}/{date}_{self._data_type.name.lower()}.zip"


class CryptoSecurityProduct(SecurityProduct):
    def __init__(self,
                 data_type: DataType,
                 market: str,
                 ticker: str,
                 resolution: QCResolution,
                 start_date: Optional[datetime],
                 end_date: Optional[datetime]) -> None:
        super().__init__(SecurityType.Crypto, data_type, market, ticker, resolution, start_date, end_date)

    @classmethod
    def get_product_type(cls) -> str:
        return SecurityType.Crypto.value

    @classmethod
    def build(cls, organization: QCFullOrganization) -> List[Product]:
        data_type = cls._ask_data_type([DataType.Trade, DataType.Quote])
        market = cls._ask_market(["Bitfinex", "GDAX"])
        resolution = cls._ask_resolution([QCResolution.Tick,
                                          QCResolution.Second,
                                          QCResolution.Minute,
                                          QCResolution.Hour,
                                          QCResolution.Daily])
        ticker = cls._ask_ticker(SecurityType.Crypto, market, resolution)
        start_date, end_date = cls._ask_start_end_date(resolution)

        return [CryptoSecurityProduct(data_type, market, ticker, resolution, start_date, end_date)]

    def _get_data_files(self) -> Iterator[str]:
        base_directory = f"crypto/{self._market.lower()}/{self._resolution.value.lower()}"

        if self._is_hour_or_daily():
            yield f"{base_directory}/{self._ticker.lower()}_{self._data_type.name.lower()}.zip"
            return

        for date in self._get_dates_with_data():
            yield f"{base_directory}/{self._ticker.lower()}/{date}_{self._data_type.name.lower()}.zip"


class EquitySecurityProduct(SecurityProduct):
    def __init__(self,
                 data_type: DataType,
                 market: str,
                 ticker: str,
                 resolution: QCResolution,
                 start_date: Optional[datetime],
                 end_date: Optional[datetime]) -> None:
        super().__init__(SecurityType.Equity, data_type, market, ticker, resolution, start_date, end_date)

    @classmethod
    def get_product_type(cls) -> str:
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

        ticker = cls._ask_ticker(SecurityType.Equity, market, resolution)
        start_date, end_date = cls._ask_start_end_date(resolution)

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

        products = [EquitySecurityProduct(data_type, market, ticker, resolution, start_date, end_date)]

        if selected_map_file is not None:
            historic_ranges = selected_map_file.get_historic_ranges(start_date)
            for index, r in enumerate(historic_ranges):
                next_ticker = ticker if index == 0 else historic_ranges[index - 1].ticker
                logger.info(f"Before trading as {next_ticker}, the selected company traded as {r.ticker}")

                if not click.confirm(
                        f"Do you also want to download {r.ticker} data from {r.start_date.strftime('%Y-%m-%d')} to {r.end_date.strftime('%Y-%m-%d')}?"):
                    break

                products.append(
                    EquitySecurityProduct(data_type, market, r.ticker, resolution, r.start_date, r.end_date))

        return products

    def _get_data_files(self) -> Iterator[str]:
        base_directory = f"equity/{self._market.lower()}/{self._resolution.value.lower()}"

        if self._is_hour_or_daily():
            yield f"{base_directory}/{self._ticker.lower()}.zip"
            return

        for date in self._get_dates_with_data():
            yield f"{base_directory}/{self._ticker.lower()}/{date}_{self._data_type.name.lower()}.zip"


class EquityOptionSecurityProduct(SecurityProduct):
    def __init__(self,
                 data_type: DataType,
                 market: str,
                 ticker: str,
                 resolution: QCResolution,
                 option_style: Optional[OptionStyle],
                 start_date: Optional[datetime],
                 end_date: Optional[datetime]) -> None:
        super().__init__(SecurityType.EquityOption, data_type, market, ticker, resolution, start_date, end_date)

        self._option_style = option_style

    @classmethod
    def get_product_type(cls) -> str:
        return SecurityType.EquityOption.value

    @classmethod
    def build(cls, organization: QCFullOrganization) -> List[Product]:
        data_type = cls._ask_data_type([DataType.Trade, DataType.Quote, DataType.OpenInterest, DataType.Chains])
        market = "USA"
        resolution = "chains" if data_type is DataType.Chains else QCResolution.Minute
        ticker = cls._ask_ticker(SecurityType.EquityOption, market, resolution)

        if data_type is not DataType.Chains:
            option_style = container.logger().prompt_list("Select the option style of the data", [
                Option(id=s, label=s.value) for s in OptionStyle.__members__.values()
            ])
        else:
            option_style = None

        start_date, end_date = cls._ask_start_end_date(resolution)

        return [EquityOptionSecurityProduct(data_type, market, ticker, resolution, option_style, start_date, end_date)]

    def get_details(self) -> ProductDetails:
        details = super().get_details()

        if self._data_type is DataType.Chains:
            details.resolution = "-"

        return details

    def _get_data_files(self) -> Iterator[str]:
        base_directory = f"option/{self._market.lower()}/{'chains' if self._data_type is DataType.Chains else 'minute'}"

        for date in self._get_dates_with_data():
            if self._data_type is DataType.Chains:
                yield f"{base_directory}/{date}/{self._ticker.lower()}.csv"
            else:
                yield f"{base_directory}/{self._ticker.lower()}/{date}_{self._data_type.name.lower()}_{self._option_style.name.lower()}.zip"


class ForexSecurityProduct(SecurityProduct):
    def __init__(self,
                 data_type: DataType,
                 market: str,
                 ticker: str,
                 resolution: QCResolution,
                 start_date: Optional[datetime],
                 end_date: Optional[datetime]) -> None:
        super().__init__(SecurityType.Forex, data_type, market, ticker, resolution, start_date, end_date)

    @classmethod
    def get_product_type(cls) -> str:
        return SecurityType.Forex.value

    @classmethod
    def build(cls, organization: QCFullOrganization) -> List[Product]:
        data_type = DataType.Quote
        market = "Oanda"
        resolution = cls._ask_resolution([QCResolution.Tick,
                                          QCResolution.Second,
                                          QCResolution.Minute,
                                          QCResolution.Hour,
                                          QCResolution.Daily])
        ticker = cls._ask_ticker(SecurityType.Forex, market, resolution)
        start_date, end_date = cls._ask_start_end_date(resolution)

        return [ForexSecurityProduct(data_type, market, ticker, resolution, start_date, end_date)]

    def _get_data_files(self) -> Iterator[str]:
        base_directory = f"forex/{self._market.lower()}/{self._resolution.value.lower()}"

        if self._is_hour_or_daily():
            yield f"{base_directory}/{self._ticker.lower()}.zip"
            return

        for date in self._get_dates_with_data():
            yield f"{base_directory}/{self._ticker.lower()}/{date}_{self._data_type.name.lower()}.zip"


class FutureSecurityProduct(SecurityProduct):
    def __init__(self,
                 data_type: DataType,
                 market: str,
                 ticker: str,
                 resolution: QCResolution,
                 start_date: Optional[datetime],
                 end_date: Optional[datetime]) -> None:
        super().__init__(SecurityType.Future, data_type, market, ticker, resolution, start_date, end_date)

    @classmethod
    def get_product_type(cls) -> str:
        return SecurityType.Future.value

    @classmethod
    def build(cls, organization: QCFullOrganization) -> List[Product]:
        data_type = cls._ask_data_type([DataType.Trade, DataType.Quote, DataType.OpenInterest])
        market = cls._ask_market(["CBOE", "CBOT", "CME", "COMEX", "HKFE", "ICE", "NYMEX", "SGX"])
        resolution = cls._ask_resolution([QCResolution.Tick, QCResolution.Second, QCResolution.Minute])
        ticker = cls._ask_ticker(SecurityType.Future, market, resolution)
        start_date, end_date = cls._ask_start_end_date(resolution)

        return [FutureSecurityProduct(data_type, market, ticker, resolution, start_date, end_date),
                FutureSecurityProduct(DataType.Margins, market, ticker, resolution, None, None)]

    def get_details(self) -> ProductDetails:
        details = super().get_details()

        if self._data_type is DataType.Margins:
            details.resolution = "-"

        return details

    def _get_data_files(self) -> Iterator[str]:
        if self._data_type is DataType.Margins:
            yield f"future/{self._market.lower()}/margins/{self._ticker.upper()}.csv"
            return

        base_directory = f"future/{self._market.lower()}/{self._resolution.value.lower()}"

        for date in self._get_dates_with_data():
            yield f"{base_directory}/{self._ticker.lower()}/{date}_{self._data_type.name.lower()}.zip"
