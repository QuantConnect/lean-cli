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
from typing import List

from lean.container import container
from lean.models.api import QCFullOrganization
from lean.models.pydantic import WrappedBaseModel


class ProductDetails(WrappedBaseModel):
    product_type: str
    ticker: str
    market: str
    resolution: str
    date_range: str


class Product(abc.ABC):
    """A Product represents data that can be purchased and downloaded with the `lean data download` command."""

    def __init__(self) -> None:
        """Creates a new Product instance."""
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
        """Returns the data files this product instance contains.

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
        files = container.api_client().data.list_objects(directory_path)
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
