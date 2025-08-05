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
from datetime import datetime
from json import dump

from docker.types import Mount
from typing import Any, Dict, Iterable, List, Optional
from click import command, option, confirm, pass_context, Context, Choice, prompt
from lean.click import LeanCommand, ensure_options
from lean.components.util.json_modules_handler import config_build_for_name
from lean.constants import DEFAULT_ENGINE_IMAGE
from lean.container import container
from lean.models.api import QCDataInformation, QCDataVendor, QCFullOrganization, QCDatasetDelivery, QCResolution, QCSecurityType, QCDataType
from lean.models.click_options import get_configs_for_options, options_from_json
from lean.models.data import Dataset, DataFile, DatasetDateOption, DatasetTextOption, DatasetTextOptionTransform,OptionResult, Product
from lean.models.logger import Option
from lean.models.cli import cli_data_downloaders
from lean.constants import LIST_PENDING_DATASETS

_data_information: Optional[QCDataInformation] = None
_presigned_terms="""
Data Terms of Use has been signed previously.
Find full agreement at: {link}
==========================================================================
CLI API Access Agreement: On {signed_time} You Agreed:
- Display or distribution of data obtained through CLI API Access is not permitted.
- Data and Third Party Data obtained via CLI API Access can only be used for individual or internal employee's use.
- Data is provided in LEAN format can not be manipulated for transmission or use in other applications.
- QuantConnect is not liable for the quality of data received and is not responsible for trading losses.
==========================================================================
"""

def _get_data_information(organization: QCFullOrganization) -> QCDataInformation:
    """Retrieves the datasources and prices information.

    :param organization: the organization to get the information for
    :return: the datasources and prices information
    """
    global _data_information

    if _data_information is None:
        _data_information = container.api_client.data.get_info(organization.id)

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
    from itertools import chain
    unique_data_files = sorted(list(set(chain(*[product.get_data_files() for product in products]))))
    return _map_data_files_to_vendors(organization, unique_data_files)

def _display_products(organization: QCFullOrganization, products: List[Product]) -> None:
    """Previews a list of products in pretty tables.

    :param organization: the organization the user selected
    :param products: the products to display
    """
    from rich import box
    from rich.table import Table

    logger = container.logger
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


def _get_security_master_warn(url: str) -> str:
    return "\n".join([f"Your organization does not have an active Security Master subscription. Override the Security Master precautions will likely"
                      f" result in inaccurate and misleading backtest results. Use this override flag at your own risk.",
                      f"You can add the subscription at https://www.quantconnect.com/datasets/{url}/pricing"
                      ])

def _select_products_interactive(organization: QCFullOrganization, datasets: List[Dataset], force: bool,
                                 ask_for_more_data: bool) -> List[Product]:
    """Asks the user for the products that should be purchased and downloaded.

    :param organization: the organization that will be charged
    :param datasets: the available datasets
    :param force: whether to force when organization does not have an active Security Master subscription
    :param ask_for_more_data: whether to ask the user if they want to select more products
    :return: the list of products selected by the user
    """
    from collections import OrderedDict

    products = []
    logger = container.logger

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

        for id, url in dataset.requirements.items():
            if organization.has_security_master_subscription(id):
                continue
            if not force:
                logger.warn("\n".join([
                    f"Your organization needs to have an active Security Master subscription to download data from the '{dataset.name}' dataset",
                    f"You can add the subscription at https://www.quantconnect.com/datasets/{url}/pricing"
                ]))
            else:
                logger.warn(_get_security_master_warn(url))

        option_results = OrderedDict()
        for dataset_option in dataset.options:
            if dataset_option.condition is None or dataset_option.condition.check(option_results):
                option_results[dataset_option.id] = dataset_option.configure_interactive()
        products.append(Product(dataset=dataset, option_results=option_results))

        logger.info("Selected data:")
        _display_products(organization, products)

        if not ask_for_more_data or not confirm("Do you want to download more data?"):
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


def _verify_accept_agreement(organization: QCFullOrganization, open_browser: bool) -> None:
    """ Verifies that the user has accepted the agreement.
    If they haven't, asks the user to accept the CLI API Access and Data Agreement.
    If they have, reminds them of the agreement and moves on.

    The API will enforce signing the agreement at the end of the day but this is how we keep it in the process of the CLI

    :param organization: the organization that the user selected
    :param open_browser: whether the CLI should automatically open the agreement in the browser
    """
    from webbrowser import open
    from time import sleep
    from datetime import datetime

    logger = container.logger
    api_client = container.api_client

    info = api_client.data.get_info(organization.id)

    # Is signed
    if organization.data.current:
        logger.info(_presigned_terms.format(link=info.agreement, signed_time=datetime.fromtimestamp(organization.data.signedTime)))
        sleep(1)
    else:
        if open_browser:
            open(info.agreement)

        logger.info(f"Go to the following url to accept the CLI API Access and Data Agreement:")
        logger.info(info.agreement)
        logger.info("Waiting until the CLI API Access and Data Agreement has been accepted...")

        container.task_manager.poll(
            make_request=lambda: api_client.organizations.get(organization.id),
            is_done=lambda data: data.data.current != False
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

    logger = container.logger
    logger.info(f"You will be charged {total_price:,.0f} QCC from your organization's QCC balance")
    logger.info(
        f"After downloading all files your organization will have {organization_qcc - total_price:,.0f} QCC left")

    confirm("Continue?", abort=True)


def _get_organization() -> QCFullOrganization:
    """Gets the working organization

    :return: The working organization in the current Lean CLI folder
    """
    organization_manager = container.organization_manager
    organization_id = organization_manager.try_get_working_organization_id()

    api_client = container.api_client
    return api_client.organizations.get(organization_id)


def _select_products_non_interactive(organization: QCFullOrganization,
                                     datasets: List[Dataset],
                                     ctx: Context,
                                     force: bool) -> List[Product]:
    """Asks the user for the products that should be purchased and downloaded.

    :param organization: the organization that will be charged
    :param datasets: the available datasets
    :param ctx: the click context of the invocation
    :return: the list of products selected by the user
    """
    from collections import OrderedDict

    dataset = next((d for d in datasets if d.name.lower() == ctx.params["dataset"].lower()), None)
    if dataset is None:
        raise RuntimeError(f"There is no dataset named '{ctx.params['dataset']}'")

    for id, url in dataset.requirements.items():
        if organization.has_security_master_subscription(id):
            continue
        if not force:
            raise RuntimeError("\n".join([
                f"Your organization needs to have an active Security Master subscription to download data from the '{dataset.name}' dataset",
                f"You can add the subscription at https://www.quantconnect.com/datasets/{url}/pricing"
            ]))
        else:
            container.logger.warn(_get_security_master_warn(url))

    option_results = OrderedDict()
    invalid_options = []
    missing_options = []

    for option in dataset.options:
        if option.condition is not None and not option.condition.check(option_results):
            continue

        # if the option id has a '-' in its name, and it's a click option, in the click context it's available with '_'
        user_input = ctx.params.get(option.id.replace('-', '_'), ctx.params.get(option.id, None))

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

    container.logger.info("Data that will be purchased and downloaded:")
    _display_products(organization, products)

    return products


def _get_available_datasets(organization: QCFullOrganization) -> List[Dataset]:
    """Retrieves the available datasets.

    :param organization: the organization that will be charged
    :return: the datasets which data can be downloaded from
    """
    cloud_datasets = container.api_client.market.list_datasets()
    data_information = _get_data_information(organization)

    available_datasets = []
    for cloud_dataset in cloud_datasets:
        if cloud_dataset.delivery == QCDatasetDelivery.CloudOnly or (not LIST_PENDING_DATASETS and cloud_dataset.pending):
            continue

        datasource = data_information.datasources.get(str(cloud_dataset.id), None)
        if datasource is None or isinstance(datasource, list):
            if cloud_dataset.name != "Template Data Source Product":
                name = cloud_dataset.name.strip()
                vendor = cloud_dataset.vendorName.strip()
                container.logger.debug(
                    f"There is no datasources entry for {name} by {vendor} (id {cloud_dataset.id})")
            continue

        available_datasets.append(Dataset(name=cloud_dataset.name.strip(),
                                          vendor=cloud_dataset.vendorName.strip(),
                                          categories=[tag.name.strip() for tag in cloud_dataset.tags],
                                          options=datasource["options"],
                                          paths=datasource["paths"],
                                          requirements=datasource.get("requirements", {})))

    return available_datasets

def _get_historical_data_provider() -> str:
    return container.logger.prompt_list("Select a historical data provider", [Option(id=data_downloader.get_name(), label=data_downloader.get_name()) for data_downloader in cli_data_downloaders])


def _get_download_specification_from_config(data_provider_config_json: Dict[str, Any], default_param: List[str],
                                            key_config_data: str) -> List[str]:
    """
    Get parameter from data provider config JSON or return default parameters.

    Args:
    - data_provider_config_json (Dict[str, Any]): Configuration JSON.
    - default_param (List[str]): Default parameters.
    - key_config_data (str): Key to look for in the config JSON.

    Returns:
    - List[str]: List of parameters.
    """

    if data_provider_config_json and "module-specification" in data_provider_config_json:
        if "download" in data_provider_config_json["module-specification"]:
            return data_provider_config_json["module-specification"]["download"].get(key_config_data, default_param)

    return default_param


def _get_user_input_or_prompt(user_input_data: str, available_input_data: List[str], data_provider_name: str,
                              prompt_message_helper: str, skip_validation: Optional[bool] = False) -> str:
    """
    Get user input or prompt for selection based on data types.

    Args:
    - user_input_data (str): User input data.
    - available_input_data (List[str]): List of available input data options.
    - data_provider_name (str): Name of the data provider.
    - skip_validation (Optional[bool]): Whether to skip validation of user input data. Default is False.

    Returns:
    - str: Selected data type or prompted choice.

    Raises:
    - ValueError: If user input data is not in supported data types.
    """

    if not user_input_data:
        if skip_validation:
            return prompt(prompt_message_helper, "")
        # Prompt user to select a ticker's security type
        options = [Option(id=data_type, label=data_type) for data_type in available_input_data]
        return container.logger.prompt_list(prompt_message_helper, options)

    elif user_input_data.lower() not in [available_data.lower() for available_data in available_input_data]:
        if skip_validation:
            return user_input_data
        # Raise ValueError for unsupported data type
        raise ValueError(
            f"The {data_provider_name} data provider does not support {user_input_data}. "
            f"Please choose a supported data from: {available_input_data}."
        )

    return user_input_data


def _configure_date_option(date_value: str, option_id: str, option_label: str) -> OptionResult:
    """
    Configure the date based on the provided date value, option ID, and option label.

    Args:
    - date_value (str): Existing date value.
    - option_id (str): Identifier for the date option.
    - option_label (str): Label for the date option.

    Returns:
    - str: Configured date.
    """

    date_option = DatasetDateOption(id=option_id, label=option_label,
                                    description=f"Enter the {option_label} "
                                                f"for the historical data request in the format YYYYMMDD.")

    if not date_value:
        if option_id == "end":
            return date_option.configure_interactive_with_default(datetime.today().strftime("%Y%m%d"))
        else:
            return date_option.configure_interactive()

    return date_option.configure_non_interactive(date_value)


class QCDataTypeCustomChoice(Choice):
    def get_metavar(self, param) -> str:
        choices_str = "|".join(QCDataType.get_all_members_except('Open Interest'))

        # Use square braces to indicate an option or optional argument.
        return f"[{choices_str}]"


def _replace_data_type(ctx, param, value):
    dataset = ctx.params.get('dataset')
    if dataset:
        if value == QCDataType.OpenInterest:
            return QCDataType.Open_Interest
        return value
    elif value == QCDataType.Open_Interest:
        return QCDataType.OpenInterest
    return value


@command(cls=LeanCommand, requires_lean_config=True, allow_unknown_options=True, name="download")
@option("--data-provider-historical",
        type=Choice([data_downloader.get_name() for data_downloader in cli_data_downloaders], case_sensitive=False),
        help="The name of the downloader data provider.")
@options_from_json(get_configs_for_options("download"))
@option("--dataset", type=str, help="The name of the dataset to download non-interactively")
@option("--overwrite", is_flag=True, default=False, help="Overwrite existing local data")
@option("--force", is_flag=True, default=False, hidden=True)
@option("--yes", "-y", "auto_confirm", is_flag=True, default=False,
        help="Automatically confirm payment confirmation prompts")
@option("--data-type", callback=_replace_data_type,
        type=QCDataTypeCustomChoice(QCDataType.get_all_members(), case_sensitive=False),
        help="Specify the type of historical data")
@option("--resolution", type=Choice(QCResolution.get_all_members(), case_sensitive=False),
        help="Specify the resolution of the historical data")
@option("--security-type", type=Choice(QCSecurityType.get_all_members(), case_sensitive=False),
    help="Specify the security type of the historical data")
@option("--market", type=str,
        help="Specify the market name for tickers (e.g., 'USA', 'NYMEX', 'Binance')"
             " (if not provided or empty the default market for the requested security type will be used)")
@option("--ticker",
        type=str,
        help="Specify comma separated list of tickers to use for historical data request.")
@option("--start",
        type=str,
        help="Specify the start date for the historical data request in the format yyyyMMdd.")
@option("--end",
        type=str,
        help="Specify the end date for the historical data request in the format yyyyMMdd. (defaults to today)")
@option("--image",
        type=str,
        help=f"The LEAN engine image to use (defaults to {DEFAULT_ENGINE_IMAGE})")
@option("--update",
        is_flag=True,
        default=False,
        help="Pull the LEAN engine image before running the Downloader Data Provider")
@option("--no-update",
        is_flag=True,
        default=False,
        help="Use the local LEAN engine image instead of pulling the latest version")
@pass_context
def download(ctx: Context,
             data_provider_historical: Optional[str],
             dataset: Optional[str],
             overwrite: bool,
             force: bool,
             auto_confirm: bool,
             data_type: Optional[str],
             resolution: Optional[str],
             security_type: Optional[str],
             market: Optional[str],
             ticker: Optional[str],
             start: Optional[str],
             end: Optional[str],
             image: Optional[str],
             update: bool,
             no_update: bool,
             **kwargs) -> None:
    """Purchase and download data directly from QuantConnect or download from supported data providers

    1. Acquire Data from QuantConnect Datasets: Purchase and seamlessly download data directly from QuantConnect.\n
    2. Streamlined Access from supported data providers:\n
        - Choose your preferred historical data provider.\n
        - Initiate hassle-free downloads from our supported providers.

    We have 2 options:\n
        - interactive (follow instruction in lean-cli)\n
        - no interactive (write arguments in command line)

    An interactive wizard will show to walk you through the process of selecting data,
    accepting the CLI API Access and Data Agreement and payment.
    After this wizard the selected data will be downloaded automatically.

    If --dataset is given the command runs in non-interactive mode.
    In this mode the CLI does not prompt for input or confirmation but only halts when the agreement must be accepted.
    In non-interactive mode all options specific to the selected dataset are required.

    \b
    See the following url for the data that can be purchased and downloaded with this command:
    https://www.quantconnect.com/datasets
    """
    organization = _get_organization()

    if dataset:
        data_provider_historical = 'QuantConnect'

    if data_provider_historical is None:
        data_provider_historical = _get_historical_data_provider()

    if data_provider_historical == 'QuantConnect':
        is_interactive = dataset is None
        if not is_interactive:
            ensure_options(["dataset"])
            datasets = _get_available_datasets(organization)
            products = _select_products_non_interactive(organization, datasets, ctx, force)
        else:
            datasets = _get_available_datasets(organization)
            products = _select_products_interactive(organization, datasets, force, ask_for_more_data=not auto_confirm)

        _confirm_organization_balance(organization, products)
        _verify_accept_agreement(organization, is_interactive)

        if is_interactive and not auto_confirm:
            _confirm_payment(organization, products)

        all_data_files = _get_data_files(organization, products)
        container.data_downloader.download_files(all_data_files, overwrite, organization.id)
    else:
        data_downloader_provider = next(data_downloader for data_downloader in cli_data_downloaders
                                        if data_downloader.get_name() == data_provider_historical)

        data_provider_config_json = None
        if data_downloader_provider.specifications_url is not None:
            data_provider_config_json = container.api_client.data.download_public_file_json(
                data_downloader_provider.specifications_url)

        data_provider_support_security_types = _get_download_specification_from_config(data_provider_config_json,
                                                                                       QCSecurityType.get_all_members(),
                                                                                       "security-types")
        data_provider_support_data_types = _get_download_specification_from_config(data_provider_config_json,
                                                                                   QCDataType.get_all_members(),
                                                                                   "data-types")
        data_provider_support_resolutions = _get_download_specification_from_config(data_provider_config_json,
                                                                                    QCResolution.get_all_members(),
                                                                                    "resolutions")
        data_provider_support_markets = _get_download_specification_from_config(data_provider_config_json,
                                                                                [""], "markets")

        security_type = _get_user_input_or_prompt(security_type, data_provider_support_security_types,
                                                  data_provider_historical, "Select a Ticker's security type")
        data_type = _get_user_input_or_prompt(data_type, data_provider_support_data_types,
                                              data_provider_historical, "Select a Data type")
        resolution = _get_user_input_or_prompt(resolution, data_provider_support_resolutions,
                                               data_provider_historical, "Select a Resolution")
        market = _get_user_input_or_prompt(market, data_provider_support_markets,
                                           data_provider_historical, "Select a Market", True)

        if not ticker:
            ticker = ','.join(DatasetTextOption(id="id",
                                                label="Enter comma separated list of tickers to use for historical data request.",
                                                description="description",
                                                transform=DatasetTextOptionTransform.Uppercase,
                                                multiple=True).configure_interactive().value)
        else:
            split_tickers = ticker.split(',')
            # don't trust user provider tickers without spaces in between
            ticker = ','.join([a_ticker.strip().upper() for a_ticker in split_tickers])

        start = _configure_date_option(start, "start", "Please enter a Start Date in the format")
        end = _configure_date_option(end, "end", "Please enter a End Date in the format")

        if start.value >= end.value:
            raise ValueError("Historical start date cannot be greater than or equal to historical end date.")

        logger = container.logger
        lean_config = container.lean_config_manager.get_complete_lean_config(None, None, None)

        engine_image, container_module_version, project_config = container.manage_docker_image(image, update, no_update)

        data_downloader_provider = config_build_for_name(lean_config, data_downloader_provider.get_name(),
                                                         cli_data_downloaders, kwargs, logger, interactive=True)
        data_downloader_provider.ensure_module_installed(organization.id, container_module_version)
        container.lean_config_manager.set_properties(data_downloader_provider.get_settings())
        # mounting additional data_downloader config files
        paths_to_mount = data_downloader_provider.get_paths_to_mount()

        downloader_data_provider_path_dll = "/Lean/DownloaderDataProvider/bin/Debug"

        run_options = container.lean_runner.get_basic_docker_config_without_algo(lean_config,
                                                                                 debugging_method=None,
                                                                                 detach=False,
                                                                                 image=engine_image,
                                                                                 target_path=downloader_data_provider_path_dll,
                                                                                 paths_to_mount=paths_to_mount)

        config_path = container.temp_manager.create_temporary_directory() / "config.json"
        with config_path.open("w+", encoding="utf-8") as file:
            dump(lean_config, file)

        run_options["working_dir"] = downloader_data_provider_path_dll

        dll_arguments = ["dotnet", "QuantConnect.DownloaderDataProvider.Launcher.dll",
                         "--data-type", data_type,
                         "--start-date", start.value.strftime("%Y%m%d"),
                         "--end-date", end.value.strftime("%Y%m%d"),
                         "--security-type", security_type,
                         "--resolution", resolution,
                         "--tickers", ticker]
        # If no market is specified, Lean will use a default market value based on the SecurityType
        if market != "":
            dll_arguments.extend(["--market", market])

        run_options["commands"].append(' '.join(dll_arguments))

        # mount our created above config with work directory
        run_options["mounts"].append(
            Mount(target=f"{downloader_data_provider_path_dll}/config.json",
                  source=str(config_path),
                  type="bind",
                  read_only=True)
        )

        success = container.docker_manager.run_image(engine_image, **run_options)

        if not success:
            raise RuntimeError(
                "Something went wrong while running the downloader data provider, see the logs above for more information")
