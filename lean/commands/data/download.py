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
import webbrowser
from typing import Iterable, List, Optional

import click
from rich import box
from rich.table import Table

from lean.click import LeanCommand
from lean.container import container
from lean.models.api import QCDataInformation, QCDataVendor, QCFullOrganization
from lean.models.logger import Option
from lean.models.products.alternative.cboe import CBOEProduct
from lean.models.products.alternative.fred import FREDProduct
from lean.models.products.alternative.sec import SECProduct
from lean.models.products.alternative.usenergy import USEnergyProduct
from lean.models.products.alternative.ustreasury import USTreasuryProduct
from lean.models.products.base import DataFile, Product
from lean.models.products.security.cfd import CFDProduct
from lean.models.products.security.crypto import CryptoProduct
from lean.models.products.security.equity import EquityProduct
from lean.models.products.security.equity_option import EquityOptionProduct
from lean.models.products.security.forex import ForexProduct
from lean.models.products.security.future import FutureProduct

data_information: Optional[QCDataInformation] = None


def _map_files_to_vendors(organization: QCFullOrganization, data_files: Iterable[str]) -> List[DataFile]:
    """Maps a list of files to the available data vendors.

    Uses the API to get the latest price information.
    Raises an error if there is no vendor that sells the data of a file in the given list.

    :param organization: the organization to use the price information of
    :param data_files: the data files to map to the available vendors
    :return: the list of data files containing the file and vendor for each file
    """
    global data_information
    if data_information is None:
        data_information = container.api_client().data.get_info(organization.id)

    last_vendor: Optional[QCDataVendor] = None
    mapped_files = []

    for file in data_files:
        if last_vendor is not None and last_vendor.regex.search(file):
            mapped_files.append(DataFile(file=file, vendor=last_vendor))
            continue

        last_vendor = None

        for vendor in data_information.prices:
            if vendor.price is None:
                continue

            if vendor.regex.search(file):
                mapped_files.append(DataFile(file=file, vendor=vendor))
                last_vendor = vendor
                break

        if last_vendor is None:
            raise RuntimeError(f"There is no data vendor that sells '{file}'")

    return mapped_files


def _get_data_files(organization: QCFullOrganization, products: List[Product]) -> List[DataFile]:
    """Returns the unique data files of a list of products mapped to their vendor.

    :param organization: the organization to use the price information of
    :param products: the list of products to get the data files from
    :return: the list of unique data files containing the file and vendor for each file for each product
    """
    unique_data_files = sorted(list(set(itertools.chain(*[product.get_data_files() for product in products]))))
    return _map_files_to_vendors(organization, unique_data_files)


def _display_products(organization: QCFullOrganization, products: List[Product]) -> None:
    """Previews a list of products in pretty tables.

    :param organization: the organization the user selected
    :param products: the products to display
    """
    logger = container.logger()
    table = Table(box=box.SQUARE)

    for column in ["Data type", "Ticker", "Market", "Resolution", "Date range", "Vendor", "Price"]:
        table.add_column(column)

    summed_price = 0

    for product in products:
        details = product.get_details()

        mapped_files = _map_files_to_vendors(organization, product.get_data_files())
        vendor = mapped_files[0].vendor.vendorName
        price = sum(data_file.vendor.price for data_file in mapped_files)
        summed_price += price

        table.add_row(details.data_type,
                      details.ticker,
                      details.market,
                      details.resolution,
                      details.date_range,
                      vendor,
                      f"{price:,.0f} QCC")

    logger.info(table)

    all_data_files = _get_data_files(organization, products)
    total_price = sum(data_file.vendor.price for data_file in all_data_files)

    if total_price != summed_price:
        logger.warn("The total price is less than the sum of all separate prices because there is overlapping data")

    logger.info(f"Total price: {total_price:,.0f} QCC")
    logger.info(f"Organization balance: {organization.credit.balance:,.0f} QCC")


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

    security_product_classes = [
        CFDProduct,
        CryptoProduct,
        EquityProduct,
        EquityOptionProduct,
        ForexProduct,
        FutureProduct
    ]

    alternative_product_classes = [
        CBOEProduct,
        FREDProduct,
        SECProduct,
        USTreasuryProduct,
        USEnergyProduct
    ]

    while True:
        initial_type = logger.prompt_list("Select whether you want to download security data or alternative data", [
            Option(id="security", label="Security data"),
            Option(id="alternative", label="Alternative data")
        ])

        if initial_type == "security":
            product_classes = security_product_classes
            product_name_question = "Select the security type"
        else:
            product_classes = alternative_product_classes
            product_name_question = "Select the data type"

        product_class = logger.prompt_list(product_name_question,
                                           [Option(id=c, label=c.get_product_name()) for c in product_classes])

        new_products = product_class.build(organization)
        current_files = [data_file.file for data_file in _get_data_files(organization, products)]

        for new_product in new_products:
            new_files = new_product.get_data_files()
            if len(set(new_files) - set(current_files)) > 0:
                products.append(new_product)

        logger.info("Selected data:")
        _display_products(organization, products)

        if not click.confirm("Do you want to download more data?"):
            break

    return products


def _confirm_organization_balance(organization: QCFullOrganization, products: List[Product]) -> None:
    """Checks whether the selected organization has enough QCC to download all selected data.

    Raises an error if the organization does not have enough QCC.

    :param organization: the organization that the user selected
    :param products: the list of products selected by the user
    """
    all_data_files = _get_data_files(organization, products)
    total_price = sum(data_file.vendor.price for data_file in all_data_files)

    if total_price > organization.credit.balance:
        raise RuntimeError("\n".join([
            "The total price exceeds your organization's QCC balance",
            "You can purchase QCC by clicking \"Purchase Credit\" on your organization's home page:",
            f"https://www.quantconnect.com/organization/{organization.id}"
        ]))


def _accept_agreement(organization: QCFullOrganization) -> None:
    """Asks the user to accept the CLI API Access and Data Agreement.

    :param organization: the organization that the user selected
    """
    logger = container.logger()
    api_client = container.api_client()

    info = api_client.data.get_info(organization.id)

    webbrowser.open(info.agreement)

    logger.info(f"Go to the following url to accept the CLI API Access and Data Agreement:")
    logger.info(info.agreement)
    logger.info("Waiting until the CLI API Access and Data Agreement has been accepted...")

    container.task_manager().poll(
        make_request=lambda: api_client.organizations.get(organization.id),
        is_done=lambda data: data.data.signedTime != organization.data.signedTime
    )


def _confirm_payment(organization: QCFullOrganization, products: List[Product]) -> None:
    """Processes payment for the selected products.

    An abort error is raised if the user decides to cancel.

    :param organization: the organization that will be charged
    :param products: the list of products selected by the user
    """
    all_data_files = _get_data_files(organization, products)
    total_price = sum(data_file.vendor.price for data_file in all_data_files)

    organization_qcc = organization.credit.balance

    logger = container.logger()
    logger.info(f"You will be charged {total_price:,.0f} QCC from your organization's QCC balance")
    logger.info(
        f"After downloading all files your organization will have {organization_qcc - total_price:,.0f} QCC left")

    click.confirm("Continue?", abort=True)


@click.command(cls=LeanCommand, requires_lean_config=True)
@click.option("--overwrite", is_flag=True, default=False, help="Overwrite existing local data")
def download(overwrite: bool) -> None:
    """Purchase and download data from QuantConnect's Data Library.

    An interactive wizard will show to walk you through the process of selecting data,
    accepting the CLI API Access and Data Agreement and payment.
    After this wizard the selected data will be downloaded automatically.

    \b
    See the following url for the data that can be purchased and downloaded with this command:
    https://www.lean.io/docs/lean-cli/user-guides/local-data#03-QuantConnect-Data-Library
    """
    organization = _select_organization()

    products = _select_products(organization)
    _confirm_organization_balance(organization, products)

    _accept_agreement(organization)
    _confirm_payment(organization, products)

    all_data_files = _get_data_files(organization, products)
    container.data_downloader().download_files(all_data_files, overwrite, organization.id)
