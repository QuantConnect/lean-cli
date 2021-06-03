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
import re
from datetime import datetime
from enum import Enum
from typing import Callable, List, Optional, Tuple, Union

import click
from dateutil.rrule import DAILY, rrule, rruleset, weekday

from lean.click import DateParameter
from lean.container import container
from lean.models.api import QCResolution
from lean.models.logger import Option
from lean.models.market_hours_database import SecurityType
from lean.models.products.base import Product, ProductDetails


class DataType(str, Enum):
    Trade = "Trade data"
    Quote = "Quote data"
    OpenInterest = "Open interest data"
    Chains = "Chains"
    Margins = "Margins data"


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
    def _ask_ticker(cls,
                    security_type: SecurityType,
                    market: str,
                    resolution: Union[QCResolution, str],
                    validate_ticker: Callable[[str], bool]) -> str:
        security_type = security_type.get_internal_name().lower()
        market = market.lower()
        resolution = resolution.value.lower() if isinstance(resolution, QCResolution) else resolution.lower()

        url = f"https://www.quantconnect.com/data/tree/{security_type}/{market}/{resolution}"

        logger = container.logger()
        logger.info(f"Browse the available data at {url}")

        while True:
            user_input = click.prompt("Enter the ticker of the data")

            if validate_ticker(user_input):
                return user_input

            logger.info("Error: Invalid ticker")

    @classmethod
    def _ask_start_end_date(cls, all_dates: Optional[List[datetime]]) -> Tuple[datetime, datetime]:
        logger = container.logger()

        if all_dates is not None and len(all_dates) > 0:
            start_constraint = all_dates[0]
            end_constraint = all_dates[-1]

            start_constraint_str = start_constraint.strftime('%Y-%m-%d')
            end_constraint_str = end_constraint.strftime('%Y-%m-%d')

            logger.info(f"Data is available from {start_constraint_str} to {end_constraint_str}")
        else:
            start_constraint, end_constraint = None, None
            start_constraint_str, end_constraint_str = None, None

        while True:
            start_date = click.prompt("Start date of the data (yyyyMMdd)", type=DateParameter())

            if start_constraint is not None and start_date < start_constraint:
                logger.info(f"Error: start date must be at or after {start_constraint_str}")
            else:
                break

        while True:
            end_date = click.prompt("End date of the data (yyyyMMdd)", type=DateParameter())

            if end_date <= start_date:
                logger.info("Error: end date must be later than start date")
            elif end_constraint is not None and end_date > end_constraint:
                logger.info(f"Error: end date must be at or before {end_constraint_str}")
            else:
                return start_date, end_date

    def _get_data_files_in_range(self, directory_path: str, pattern: str) -> List[str]:
        """Retrieves data files from the API and returns all those with dates between this product's start and end date.

        :param directory_path: the path to the remote directory to get the files from
        :param pattern: the pattern to match against, must have a capturing group capturing a yyyyMMdd timestamp
        :return: the data files in the given directory, matching the given pattern, between the start and end date
        """
        files = container.api_client().data.list_objects(directory_path)
        compiled_pattern = re.compile(pattern)

        results = []

        for file in files:
            match = compiled_pattern.search(file)
            if match is None:
                continue

            date = datetime.strptime(match.group(1), "%Y%m%d")
            if date < self._start_date or date > self._end_date:
                continue

            results.append(file)

        return results

    def _get_tradable_dates(self) -> List[str]:
        """Returns the dates for which the data in this product is tradable.

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
