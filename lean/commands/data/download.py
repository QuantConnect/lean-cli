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

import itertools
from typing import Iterable, List, Optional

import click
from rich import box
from rich.table import Table

from lean.click import LeanCommand
from lean.container import container
from lean.models.api import QCDataInformation, QCDataVendor, QCFullOrganization
from lean.models.errors import MoreInfoError
from lean.models.logger import Option
from lean.models.products.base import Product
from lean.models.products.cfd import CFDProduct
from lean.models.products.crypto import CryptoProduct
from lean.models.products.equity import EquityProduct
from lean.models.products.equity_option import EquityOptionProduct
from lean.models.products.forex import ForexProduct
from lean.models.products.future import FutureProduct

data_information: Optional[QCDataInformation] = None


def _calculate_price(organization: QCFullOrganization, data_files: Iterable[str]) -> float:
    """Calculates the price of a list of files.

    Uses the API to get the latest price information.

    :param organization: the organization to use the price information of
    :param data_files: the data files to calculate the price of
    :return: the price of the list of files in QCC
    """
    global data_information
    if data_information is None:
        data_information = container.api_client().data.get_info(organization.id)

    last_vendor: Optional[QCDataVendor] = None
    total_price = 0

    for file in data_files:
        if last_vendor is not None and last_vendor.regex.search(file):
            total_price += last_vendor.price
            continue

        last_vendor = None

        for vendor in data_information.prices:
            if vendor.price is None:
                continue

            if vendor.regex.search(file):
                total_price += vendor.price
                last_vendor = vendor
                break

        if last_vendor is None:
            raise RuntimeError(f"There is no data vendor that sells '{file}'")

    return total_price


def _display_products(organization: QCFullOrganization, products: List[Product]) -> None:
    """Previews a list of products in pretty tables.

    :param organization: the organization the user selected
    :param products: the products to display
    """
    logger = container.logger()
    table = Table(box=box.SQUARE)

    for column in ["Product type", "Ticker", "Market", "Resolution", "Date range", "Price"]:
        table.add_column(column)

    for product in products:
        details = product.get_details()
        price = _calculate_price(organization, product.get_data_files())

        table.add_row(details.product_type,
                      details.ticker,
                      details.market,
                      details.resolution,
                      details.date_range,
                      f"{price:,.0f} QCC")

    logger.info(table)

    all_data_files = list(itertools.chain(*[product.get_data_files() for product in products]))
    unique_data_files = set(all_data_files)

    if len(all_data_files) > len(unique_data_files):
        logger.warn("The total price is less than the sum of all product prices because there are overlapping products")

    total_price = _calculate_price(organization, unique_data_files)
    logger.info(f"Total price: {total_price:,.0f} QCC")


def _select_organization() -> QCFullOrganization:
    """Asks the user for the organization that should be used.

    :return: the selected organization
    """
    api_client = container.api_client()

    organizations = api_client.organizations.get_all()
    options = [Option(id=organization.id, label=organization.name) for organization in organizations]

    logger = container.logger()
    organization_id = logger.prompt_list("Select the organization to purchase and download data with", options)

    return api_client.organizations.get(organization_id)


def _select_products(organization: QCFullOrganization) -> List[Product]:
    """Asks the user for the products that should be purchased and downloaded.

    :return: the list of products selected by the user
    """
    products = []

    logger = container.logger()

    available_product_classes = [
        CFDProduct,
        CryptoProduct,
        EquityProduct,
        EquityOptionProduct,
        ForexProduct,
        FutureProduct
    ]

    while True:
        product_class = logger.prompt_list("Select the product type", [
            Option(id=c, label=c.get_product_type()) for c in available_product_classes
        ])

        products.extend(product_class.build(organization))

        logger.info("Selected products:")
        _display_products(organization, products)

        if not click.confirm("Do you want to add another product?"):
            break

    return products


def _accept_data_sales_agreement(organization: QCFullOrganization) -> None:
    """Asks the user to accept the data sales agreement.

    :param organization: the organization that the user selected
    """
    logger = container.logger()
    api_client = container.api_client()

    info = api_client.data.get_info(organization.id)

    logger.info(f"Go to the following url to accept the data sales agreement: {info.agreement}")
    logger.info("Waiting until the data sales agreement has been accepted...")

    container.task_manager().poll(
        make_request=lambda: api_client.organizations.get(organization.id),
        is_done=lambda data: data.data.signedTime != organization.data.signedTime
    )


def _confirm_payment(organization: QCFullOrganization, products: List[Product]) -> None:
    """Processes payment for the selected products.

    An abort error is raised if the user decides to cancel.

    :param organization: the organization that will be billed
    :param products: the list of products selected by the user
    """
    unique_data_files = set(itertools.chain(*[product.get_data_files() for product in products]))
    total_price = _calculate_price(organization, unique_data_files)

    organization_qcc = organization.credit.balance * 100

    if total_price > organization_qcc:
        raise MoreInfoError("The total price exceeds your organization's QCC balance",
                            "https://www.quantconnect.com/terminal/#organization/billing")

    logger = container.logger()
    logger.info(f"You will be billed {total_price:,.0f} QCC from your organization's QCC balance")
    logger.info(
        f"After downloading all files your organization will have {organization_qcc - total_price:,.0f} QCC left")

    click.confirm("Continue?", abort=True)


@click.command(cls=LeanCommand, requires_lean_config=True)
@click.option("--overwrite", is_flag=True, default=False, help="Overwrite existing local data")
def download(overwrite: bool) -> None:
    """Purchase and download data from QuantConnect's Data Library.

    An interactive wizard will show to walk you through the process of selecting data,
    agreeing to the distribution agreement and payment.
    After this wizard the selected data will be downloaded automatically.

    \b
    See the following url for the data that can be purchased and downloaded with this command:
    https://www.quantconnect.com/data/tree
    """
    organization = _select_organization()

    products = _select_products(organization)

    _accept_data_sales_agreement(organization)
    _confirm_payment(organization, products)

    all_data_files = list(itertools.chain(*[product.get_data_files() for product in products]))
    unique_data_files = sorted(list(set(all_data_files)))
    container.data_downloader().download_files(unique_data_files, overwrite, organization.id)
