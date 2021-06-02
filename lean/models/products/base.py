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
from typing import Iterator, List

from lean.models.api import QCFullOrganization
from lean.models.pydantic import WrappedBaseModel


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
