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
from typing import List, Optional, Tuple

import click

from lean.click import DateParameter
from lean.container import container
from lean.models.api import QCDataVendor, QCFullOrganization
from lean.models.pydantic import WrappedBaseModel


class DataFile(WrappedBaseModel):
    file: str
    vendor: QCDataVendor


class ProductDetails(WrappedBaseModel):
    data_type: str
    ticker: str
    market: str
    resolution: str
    date_range: str


class Product(abc.ABC):
    """A Product class contains all the logic for a certain product type in the `lean data download` command."""

    def __init__(self) -> None:
        """Creates a new Product instance."""
        self._data_files = None

    @classmethod
    @abc.abstractmethod
    def get_product_name(cls) -> str:
        """Returns the name of this product.

        :return: the name of the product that can be displayed to the user
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
        """Returns the details about this product in a way that it can be displayed to the user.

        :return: the pretty details of this product
        """
        raise NotImplementedError()

    def get_data_files(self) -> List[str]:
        """Returns the data files that must be downloaded when this product is purchased.

        :return: the data files for this product instance, relative to the data directory
        """
        if self._data_files is None:
            self._data_files = self._get_data_files()
        return self._data_files

    @abc.abstractmethod
    def _get_data_files(self) -> List[str]:
        """Returns the data files this product instance contains.

        :return: the data files for this product instance, relative to the data directory
        """
        raise NotImplementedError()

    @classmethod
    def _list_files(cls, directory_path: str, pattern: str) -> List[str]:
        """Lists remote files and allows extracting useful data.

        :param directory_path: the path to the remote directory to list the files of
        :param pattern: the pattern to match against
        :return: the list of all matching files, or the list of all captured values if the pattern has a capturing group
        """
        files = container.api_client().data.list_files(directory_path)
        compiled_pattern = re.compile(pattern)

        results = []
        for file in files:
            match = compiled_pattern.search(file)
            if match is None:
                continue

            if match.lastindex is not None:
                results.append(match.group(1))
            else:
                results.append(file)

        return results

    @classmethod
    def _list_dates(cls, directory_path: str, pattern: str) -> List[datetime]:
        """Lists the dates in the file names of remote files.

        :param directory_path: the path to the remote directory to get the files from
        :param pattern: the pattern to match against, must have a capturing group capturing a yyyyMMdd timestamp
        :return: the parsed dates
        """
        return [datetime.strptime(timestamp, "%Y%m%d") for timestamp in cls._list_files(directory_path, pattern)]

    @classmethod
    def _ask_start_end_date(cls, all_dates: Optional[List[datetime]]) -> Tuple[datetime, datetime]:
        """Asks the user to give the start and the end date of the data.

        If all_dates is not None or empty the min and max date are set to the min and max dates in all_dates.

        :param all_dates: all available dates
        :return: the chosen start and end date
        """
        logger = container.logger()

        if all_dates is not None and len(all_dates) > 0:
            start_constraint = min(all_dates)
            end_constraint = max(all_dates)

            start_constraint_str = start_constraint.strftime('%Y-%m-%d')
            end_constraint_str = end_constraint.strftime('%Y-%m-%d')

            logger.info(f"Data is available from {start_constraint_str} to {end_constraint_str}")
        else:
            start_constraint, end_constraint = None, None
            start_constraint_str, end_constraint_str = None, None

        while True:
            start_date = click.prompt("Inclusive start date of the data (yyyyMMdd)", type=DateParameter())

            if start_constraint is not None and start_date < start_constraint:
                logger.info(f"Error: start date must be at or after {start_constraint_str}")
            else:
                break

        while True:
            end_date = click.prompt("Inclusive end date of the data (yyyyMMdd)", type=DateParameter())

            if end_date <= start_date:
                logger.info("Error: end date must be later than start date")
            elif end_constraint is not None and end_date > end_constraint:
                logger.info(f"Error: end date must be at or before {end_constraint_str}")
            else:
                return start_date, end_date

    def _get_data_files_in_range(self,
                                 directory_path: str,
                                 date_pattern: str,
                                 start_date: datetime,
                                 end_date: datetime) -> List[str]:
        """Retrieves data files from the API and returns all those with dates between a start and end date.

        :param directory_path: the path to the remote directory to get the files from
        :param date_pattern: the pattern to match against, must have a capturing group capturing a yyyyMMdd timestamp
        :param start_date: the inclusive start date to look for
        :param end_date: the inclusive end date to look for
        :return: the data files in the given directory, matching the given pattern, between the start and end date
        """
        files = container.api_client().data.list_files(directory_path)
        compiled_date_pattern = re.compile(date_pattern)

        results = []

        for file in files:
            match = compiled_date_pattern.search(file)
            if match is None:
                continue

            date = datetime.strptime(match.group(1), "%Y%m%d")
            if date < start_date or date > end_date:
                continue

            results.append(file)

        return results
