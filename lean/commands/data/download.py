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
from datetime import datetime
from typing import Iterable, List, Optional, Callable, TypeVar, Tuple

import click
from rich import box
from rich.table import Table

from lean.click import LeanCommand, ensure_options, DateParameter
from lean.container import container
from lean.models.api import QCDataInformation, QCDataVendor, QCFullOrganization, QCResolution
from lean.models.logger import Option
from lean.models.products.alternative import alternative_products
from lean.models.products.alternative.cboe import CBOEProduct
from lean.models.products.alternative.fred import FREDProduct
from lean.models.products.alternative.sec import SECProduct
from lean.models.products.alternative.usenergy import USEnergyProduct
from lean.models.products.alternative.ustreasury import USTreasuryProduct
from lean.models.products.base import DataFile, Product
from lean.models.products.security import security_products
from lean.models.products.security.base import DataType
from lean.models.products.security.cfd import CFDProduct
from lean.models.products.security.crypto import CryptoProduct
from lean.models.products.security.equity import EquityProduct
from lean.models.products.security.equity_option import EquityOptionProduct, OptionStyle
from lean.models.products.security.forex import ForexProduct
from lean.models.products.security.future import FutureProduct

_data_information: Optional[QCDataInformation] = None


def _map_files_to_vendors(organization: QCFullOrganization, data_files: Iterable[str]) -> List[DataFile]:
    """Maps a list of files to the available data vendors.

    Uses the API to get the latest price information.
    Raises an error if there is no vendor that sells the data of a file in the given list.

    :param organization: the organization to use the price information of
    :param data_files: the data files to map to the available vendors
    :return: the list of data files containing the file and vendor for each file
    """
    global _data_information
    if _data_information is None:
        _data_information = container.api_client().data.get_info(organization.id)

    last_vendor: Optional[QCDataVendor] = None
    mapped_files = []

    for file in data_files:
        if last_vendor is not None and last_vendor.regex.search(file):
            mapped_files.append(DataFile(file=file, vendor=last_vendor))
            continue

        last_vendor = None

        for vendor in _data_information.prices:
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

    while True:
        initial_type = logger.prompt_list("Select whether you want to download security data or alternative data", [
            Option(id="security", label="Security data"),
            Option(id="alternative", label="Alternative data")
        ])

        if initial_type == "security":
            product_classes = security_products
            product_name_question = "Select the security type"
        else:
            product_classes = alternative_products
            product_name_question = "Select the data type"

        product_class = logger.prompt_list(product_name_question,
                                           [Option(id=c, label=c.get_name()) for c in product_classes])

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


def _accept_agreement(organization: QCFullOrganization, open_browser: bool) -> None:
    """Asks the user to accept the CLI API Access and Data Agreement.

    :param organization: the organization that the user selected
    :param open_browser: whether the CLI should automatically open the agreement in the browser
    """
    logger = container.logger()
    api_client = container.api_client()

    info = api_client.data.get_info(organization.id)

    if open_browser:
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


T = TypeVar("T")


def _ensure_option(name: str, value: T, allowed_values: List[T], to_string: Callable[[T], str] = lambda v: v) -> T:
    """Ensures an option's value is valid, raising an error if that's not the case.

    :param name: the name of the option
    :param value: the value of the option
    :param allowed_values: the list of allowed values for the option
    :param to_string: the lambda that converts the possible values to strings that the user can provide to the option
    :return: the item from allowed_values matching the user's choice
    """
    for v in allowed_values:
        if to_string(value).lower() == to_string(v).lower():
            return v

    options = ", ".join(to_string(value) for value in allowed_values)
    raise RuntimeError(f"The --{name.replace('_', '-')} option must be one of the following: {options}")


def _get_start_end(ctx: click.Context) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Retrieves the start and end date of the data from the invocation context.

    :param ctx: the context of the current command invocation
    :return: a tuple containing the start and the end date of the data, or None if the resolution is hourly or daily
    """
    resolution = ctx.params["resolution"]
    if resolution == QCResolution.Hour or resolution == QCResolution.Daily:
        return None, None

    ensure_options(ctx, ["start", "end"])
    return ctx.params["start"], ctx.params["end"]


@click.command(cls=LeanCommand, requires_lean_config=True)
@click.option("--product",
              type=click.Choice([p.get_name() for p in security_products + alternative_products], case_sensitive=False),
              help="The product type to download")
@click.option("--organization", type=str, help="The name or id of the organization to purchase and download data with")
@click.option("--data-type",
              type=click.Choice(DataType.__members__.keys(), case_sensitive=False),
              callback=lambda ctx, value: DataType.by_name(value) if value is not None else None,
              help="The type of data that you want to download")
@click.option("--market", type=str, help="The market of the data that you want to download")
@click.option("--ticker", type=str, help="The ticker of the data that you want to download")
@click.option("--resolution",
              type=click.Choice(QCResolution.__members__.keys(), case_sensitive=False),
              callback=lambda ctx, value: QCResolution.by_name(value) if value is not None else None,
              help="The resolution of the data that you want to download")
@click.option("--option-style",
              type=click.Choice(OptionStyle.__members__.keys(), case_sensitive=False),
              callback=lambda ctx, value: OptionStyle.by_name(value) if value is not None else None,
              help="The option style of the data that you want to download")
@click.option("--start",
              type=DateParameter(),
              help="The start date of the data that you want to download (ignore for hourly and daily data)")
@click.option("--end",
              type=DateParameter(),
              help="The end date of the data that you want to download (ignore for hourly and daily data)")
@click.option("--report-type",
              type=click.Choice(["10K", "10Q", "8K"], case_sensitive=False),
              help="The type of SEC reports that you want to download")
@click.option("--overwrite", is_flag=True, default=False, help="Overwrite existing local data")
@click.pass_context
def download(ctx: click.Context,
             product: Optional[str],
             organization: Optional[str],
             data_type: Optional[DataType],
             market: Optional[str],
             ticker: Optional[str],
             resolution: Optional[QCResolution],
             option_style: Optional[OptionStyle],
             start: Optional[datetime],
             end: Optional[datetime],
             report_type: Optional[str],
             overwrite: bool) -> None:
    """Purchase and download data from QuantConnect's Data Library.

    An interactive wizard will show to walk you through the process of selecting data,
    accepting the CLI API Access and Data Agreement and payment.
    After this wizard the selected data will be downloaded automatically.

    If --product is given the command runs in non-interactive mode.
    In this mode the CLI does not prompt for input or confirmation but only halts when an agreement must be accepted.
    In non-interactive mode all options specific to the selected product as well as --organization are required.

    \b
    See the following url for the data that can be purchased and downloaded with this command:
    https://www.lean.io/docs/lean-cli/user-guides/local-data#03-QuantConnect-Data-Library
    """
    is_interactive = product is None and organization is None

    if not is_interactive:
        ensure_options(ctx, ["product", "organization"])

        api_client = container.api_client()

        all_organizations = api_client.organizations.get_all()
        selected_organization = next((o for o in all_organizations if o.id == organization or o.name == organization),
                                     None)

        if selected_organization is None:
            raise RuntimeError(f"You are not a member of an organization with name or id '{organization}'")

        selected_organization = api_client.organizations.get(selected_organization.id)
        products = []

        if product == CFDProduct.get_name():
            ensure_options(ctx, ["ticker", "resolution"])

            start, end = _get_start_end(ctx)

            products.append(CFDProduct(DataType.Quote, "Oanda", ticker, resolution, start, end))
        elif product == CryptoProduct.get_name():
            ensure_options(ctx, ["data_type", "market", "ticker", "resolution"])

            data_type = _ensure_option("data_type", data_type, [DataType.Trade, DataType.Quote], lambda d: d.name)
            market = _ensure_option("market", market, ["Bitfinex", "GDAX"])
            start, end = _get_start_end(ctx)

            products.append(CryptoProduct(data_type, market, ticker, resolution, start, end))
        elif product == EquityProduct.get_name():
            EquityProduct.ensure_security_master_subscription(selected_organization)

            ensure_options(ctx, ["data_type", "ticker", "resolution"])

            data_type = _ensure_option("data_type", data_type, [DataType.Trade, DataType.Quote], lambda d: d.name)
            if data_type == DataType.Quote:
                resolution = _ensure_option("resolution",
                                            resolution,
                                            [QCResolution.Tick, QCResolution.Second, QCResolution.Minute],
                                            lambda r: r.value)
            start, end = _get_start_end(ctx)

            products.append(EquityProduct(data_type, "USA", ticker, resolution, start, end))
        elif product == EquityOptionProduct.get_name():
            EquityOptionProduct.ensure_security_master_subscription(selected_organization)

            ensure_options(ctx, ["data_type", "option_style", "ticker"])
            data_type = _ensure_option("data_type",
                                       data_type,
                                       [DataType.Trade, DataType.Quote, DataType.OpenInterest],
                                       lambda d: d.name)
            start, end = _get_start_end(ctx)

            products.append(
                EquityOptionProduct(data_type, "USA", ticker, QCResolution.Minute, option_style, start, end))
        elif product == ForexProduct.get_name():
            ensure_options(ctx, ["ticker", "resolution"])

            start, end = _get_start_end(ctx)

            products.append(ForexProduct(DataType.Quote, "Oanda", ticker, resolution, start, end))
        elif product == FutureProduct.get_name():
            ensure_options(ctx, ["market", "ticker"])

            market = _ensure_option("market", market, ["CBOE", "CBOT", "CME", "COMEX", "HKFE", "ICE", "NYMEX", "SGX"])

            products.append(FutureProduct(DataType.Margins, market, ticker, QCResolution.Daily, None, None))
        elif product == CBOEProduct.get_name():
            ensure_options(ctx, ["ticker"])
            products.append(CBOEProduct(ticker))
        elif product == FREDProduct.get_name():
            ensure_options(ctx, ["ticker"])
            products.append(FREDProduct(FREDProduct.variables.get(ticker, ticker)))
        elif product == SECProduct.get_name():
            ensure_options(ctx, ["report_type", "ticker", "start", "end"])
            products.append(SECProduct(report_type, ticker, start, end))
        elif product == USTreasuryProduct.get_name():
            products.append(USTreasuryProduct())
        elif product == USEnergyProduct.get_name():
            ensure_options(ctx, ["ticker"])
            products.append(USEnergyProduct(USEnergyProduct.variables.get(ticker, ticker)))

        container.logger().info("Data that will be purchased and downloaded:")
        _display_products(selected_organization, products)
    else:
        selected_organization = _select_organization()
        products = _select_products(selected_organization)

    _confirm_organization_balance(selected_organization, products)
    _accept_agreement(selected_organization, product is None)

    if is_interactive:
        _confirm_payment(selected_organization, products)

    all_data_files = _get_data_files(selected_organization, products)
    container.data_downloader().download_files(all_data_files, overwrite, is_interactive, selected_organization.id)
