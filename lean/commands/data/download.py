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
import re
import webbrowser
from collections import OrderedDict
from typing import Iterable, List, Optional

import click
from rich import box
from rich.table import Table

from lean.click import LeanCommand, ensure_options
from lean.container import container
from lean.models.api import QCDataInformation, QCDataVendor, QCFullOrganization, QCDatasetDelivery
from lean.models.data import Dataset, DataFile, Product
from lean.models.logger import Option

_data_information: Optional[QCDataInformation] = None


def _get_data_information(organization: QCFullOrganization) -> QCDataInformation:
    """Retrieves the datasources and prices information.

    :param organization: the organization to get the information for
    :return: the datasources and prices information
    """
    global _data_information

    if _data_information is None:
        _data_information = container.api_client().data.get_info(organization.id)

    return _data_information


def _map_data_files_to_vendors(organization: QCFullOrganization, data_files: Iterable[str]) -> List[DataFile]:
    """Maps a list of data files to the available data vendors.

    Uses the API to get the latest price information.
    Raises an error if there is no vendor that sells the data of a file in the given list.

    :param organization: the organization to use the price information of
    :param data_files: the data files to map to the available vendors
    :return: the list of data files containing the file and vendor for each file
    """
    data_information = _get_data_information(organization)

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
    return _map_data_files_to_vendors(organization, unique_data_files)


def _display_products(organization: QCFullOrganization, products: List[Product]) -> None:
    """Previews a list of products in pretty tables.

    :param organization: the organization the user selected
    :param products: the products to display
    """
    logger = container.logger()
    table = Table(box=box.SQUARE)

    for column in ["Dataset", "Vendor", "Details", "File count", "Price"]:
        table.add_column(column, overflow="fold")

    summed_price = 0

    for product in products:
        details = []
        for option_id, result in product.option_results.items():
            option = next(o for o in product.dataset.options if o.id == option_id)
            if result is not None:
                label = option.label

                if isinstance(result.value, list):
                    if len(result.value) > 1:
                        label = label.replace("(s)", "s")
                    else:
                        label = label.replace("(s)", "")

                details.append(f"{label}: {result.label}")

        if len(details) == 0:
            details.append("-")

        mapped_files = _map_data_files_to_vendors(organization, product.get_data_files())
        price = sum(data_file.vendor.price for data_file in mapped_files)
        summed_price += price

        table.add_row(product.dataset.name,
                      product.dataset.vendor,
                      "\n".join(details),
                      f"{len(mapped_files):,.0f}",
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


def _select_products_interactive(organization: QCFullOrganization, datasets: List[Dataset]) -> List[Product]:
    """Asks the user for the products that should be purchased and downloaded.

    :param organization: the organization that will be charged
    :param datasets: the available datasets
    :return: the list of products selected by the user
    """
    products = []
    logger = container.logger()

    category_options = {}
    for dataset in datasets:
        for category in dataset.categories:
            if category in category_options:
                continue

            dataset_count = len(list(dataset for dataset in datasets if category in dataset.categories))
            category_options[category] = Option(
                id=category,
                label=f"{category} ({dataset_count} dataset{'s' if dataset_count > 1 else ''})"
            )

    category_options = sorted(category_options.values(), key=lambda opt: opt.label)

    while True:
        category = logger.prompt_list("Select a category", category_options)

        available_datasets = sorted((d for d in datasets if category in d.categories), key=lambda d: d.name)
        dataset: Dataset = logger.prompt_list("Select a dataset",
                                              [Option(id=d, label=d.name) for d in available_datasets])

        if dataset.requires_security_master and not organization.has_security_master_subscription():
            logger.warn("\n".join([
                f"Your organization needs to have an active Security Master subscription to download data from the '{dataset.name}' dataset",
                f"You can add the subscription at https://www.quantconnect.com/datasets/quantconnect-security-master/pricing"
            ]))
            continue

        option_results = OrderedDict()
        for option in dataset.options:
            if option.condition is None or option.condition.check(option_results):
                option_results[option.id] = option.configure_interactive()

        products.append(Product(dataset=dataset, option_results=option_results))

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


def _get_organization_by_name_or_id(user_input: str) -> QCFullOrganization:
    """Finds an organization by name or id.

    Raises an error if no organization with a matching name or id can be found.

    :param user_input: the input given by the user
    :return: the first organization with the given name or id
    """
    api_client = container.api_client()

    if re.match("^[a-f0-9]{32}$", user_input) is not None:
        try:
            return api_client.organizations.get(user_input)
        except:
            pass

    all_organizations = api_client.organizations.get_all()
    selected_organization = next((o for o in all_organizations if o.id == user_input or o.name == user_input), None)

    if selected_organization is None:
        raise RuntimeError(f"You are not a member of an organization with name or id '{user_input}'")

    return api_client.organizations.get(selected_organization.id)


def _select_products_non_interactive(organization: QCFullOrganization,
                                     datasets: List[Dataset],
                                     ctx: click.Context) -> List[Product]:
    """Asks the user for the products that should be purchased and downloaded.

    :param organization: the organization that will be charged
    :param datasets: the available datasets
    :param ctx: the click context of the invocation
    :return: the list of products selected by the user
    """
    dataset = next((d for d in datasets if d.name.lower() == ctx.params["dataset"].lower()), None)
    if dataset is None:
        raise RuntimeError(f"There is no dataset named '{ctx.params['dataset']}'")

    if dataset.requires_security_master and not organization.has_security_master_subscription():
        raise RuntimeError("\n".join([
            f"Your organization needs to have an active Security Master subscription to download data from the '{dataset.name}' dataset",
            f"You can add the subscription at https://www.quantconnect.com/datasets/quantconnect-security-master/pricing"
        ]))

    option_results = OrderedDict()
    invalid_options = []
    missing_options = []

    for option in dataset.options:
        if option.condition is not None and not option.condition.check(option_results):
            continue

        user_input = ctx.params.get(option.id, None)

        if user_input is None:
            missing_options.append(f"--{option.id} <{option.get_placeholder()}>: {option.description}")
        else:
            try:
                option_results[option.id] = option.configure_non_interactive(user_input)
            except ValueError as error:
                invalid_options.append(f"--{option.id}: {error}")

    if len(invalid_options) > 0 or len(missing_options) > 0:
        blocks = []

        for label, lines in [["Invalid option", invalid_options], ["Missing option", missing_options]]:
            if len(lines) > 0:
                joined_lines = "\n".join(lines)
                blocks.append(f"{label}{'s' if len(lines) > 1 else ''}:\n{joined_lines}")

        raise RuntimeError("\n\n".join(blocks))

    products = [Product(dataset=dataset, option_results=option_results)]

    container.logger().info("Data that will be purchased and downloaded:")
    _display_products(organization, products)

    return products


def _get_available_datasets(organization: QCFullOrganization) -> List[Dataset]:
    """Retrieves the available datasets.

    :param organization: the organization that will be charged
    :return: the datasets which data can be downloaded from
    """
    cloud_datasets = container.api_client().market.list_datasets()
    data_information = _get_data_information(organization)

    available_datasets = []
    for cloud_dataset in cloud_datasets:
        if cloud_dataset.delivery == QCDatasetDelivery.CloudOnly:
            continue

        datasource = data_information.datasources.get(str(cloud_dataset.id), None)
        if datasource is None or isinstance(datasource, list):
            if cloud_dataset.name != "Template Data Source Product":
                name = cloud_dataset.name.strip()
                vendor = cloud_dataset.vendorName.strip()
                container.logger().debug(
                    f"There is no datasources entry for {name} by {vendor} (id {cloud_dataset.id})")
            continue

        available_datasets.append(Dataset(name=cloud_dataset.name.strip(),
                                          vendor=cloud_dataset.vendorName.strip(),
                                          categories=[tag.name.strip() for tag in cloud_dataset.tags],
                                          options=datasource["options"],
                                          paths=datasource["paths"],
                                          requires_security_master=datasource["requiresSecurityMaster"]))

    return available_datasets


@click.command(cls=LeanCommand, requires_lean_config=True, allow_unknown_options=True)
@click.option("--dataset", type=str, help="The name of the dataset to download non-interactively")
@click.option("--organization", type=str, help="The name or id of the organization to purchase and download data with")
@click.option("--overwrite", is_flag=True, default=False, help="Overwrite existing local data")
@click.pass_context
def download(ctx: click.Context,
             dataset: Optional[str],
             organization: Optional[str],
             overwrite: bool,
             **kwargs) -> None:
    """Purchase and download data from QuantConnect Datasets.

    An interactive wizard will show to walk you through the process of selecting data,
    accepting the CLI API Access and Data Agreement and payment.
    After this wizard the selected data will be downloaded automatically.

    If --dataset is given the command runs in non-interactive mode.
    In this mode the CLI does not prompt for input or confirmation but only halts when the agreement must be accepted.
    In non-interactive mode all options specific to the selected dataset as well as --organization are required.

    \b
    See the following url for the data that can be purchased and downloaded with this command:
    https://www.quantconnect.com/datasets
    """
    is_interactive = dataset is None and organization is None

    if not is_interactive:
        ensure_options(["dataset", "organization"])
        selected_organization = _get_organization_by_name_or_id(organization)
        datasets = _get_available_datasets(selected_organization)
        products = _select_products_non_interactive(selected_organization, datasets, ctx)
    else:
        selected_organization = _select_organization()
        datasets = _get_available_datasets(selected_organization)
        products = _select_products_interactive(selected_organization, datasets)

    _confirm_organization_balance(selected_organization, products)
    _accept_agreement(selected_organization, is_interactive)

    if is_interactive:
        _confirm_payment(selected_organization, products)

    all_data_files = _get_data_files(selected_organization, products)
    container.data_downloader().download_files(all_data_files, overwrite, selected_organization.id)
