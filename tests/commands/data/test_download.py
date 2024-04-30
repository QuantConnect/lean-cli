import json
from unittest import mock
from unittest.mock import MagicMock

import pytest
import os
import re
from pathlib import Path

from lean.commands.data.download import *
from lean.container import container
from lean.models.api import QCDataset, QCOrganizationCredit, QCOrganizationData
from tests.test_helpers import create_api_organization
from click.testing import CliRunner
from lean.commands import lean
from tests.test_helpers import create_fake_lean_cli_directory
from tests.conftest import initialize_container

test_files = Path(os.path.join(os.path.dirname(os.path.realpath(__file__)), "testFiles"))


# Load in our test files into fake filesystem
@pytest.fixture
def setup(fs):
    fs.add_real_directory(test_files, read_only=False)
    yield fs


def test_bulk_extraction(setup):
    fake_tar = Path(os.path.join(test_files, "20220222_coinapi_crypto_ftx_price_aggregation.tar"))
    out = Path("/tmp/out")

    container.data_downloader._process_bulk(fake_tar, out)
    assert not os.path.exists(out / fake_tar)

    # Empty file in fake tar
    file = os.path.join(out, "crypto/ftx/daily/imxusd_trade.zip")
    assert os.path.exists(file)


def _get_data_provider_config(is_crypto_configs: bool = False) -> Dict[str, Any]:
    """
    Retrieve the configuration settings for a financial data provider.

    This method encapsulates the configuration settings typically found in a data provider config JSON file,
    as referenced by a file named <provider_name>.json in an example from a GitHub repository.

    Returns:
        Dict[str, Any]: Configuration settings including supported data types, resolutions, and asset classes.
    """

    if is_crypto_configs:
        return {
            "module-specification": {
                "download": {
                    "data-types": ["Trade", "Quote"],
                    "resolutions": ["Minute", "Hour", "Daily"],
                    "security-types": ["Crypto", "CryptoFuture"],
                    "markets": ["Binance", "Kraken"]
                }
            }
        }

    data_provider_config_file_json: Dict[str, Any] = {
        "module-specification": {
            "download": {
                "data-types": ["Trade", "Quote"],
                "resolutions": ["Second", "Minute", "Hour", "Daily"],
                "security-types": ["Equity", "Option", "Index", "IndexOption"],
                "markets": ["NYSE", "USA"]
            }
        }
    }

    return data_provider_config_file_json


def _create_lean_data_download(data_provider_name: str,
                               data_type: str,
                               resolution: str,
                               security_type: str,
                               tickers: List[str],
                               start_date: str,
                               end_date: str,
                               data_provider_config_file_json: Dict[str, Any],
                               market: str = None,
                               extra_run_command: List[str] = None):
    """
    Create a data download command for the Lean algorithmic trading engine.

    This method constructs and invokes a Lean CLI command to download historical data from a specified data provider.
    It utilizes a mock data provider configuration JSON and may include extra run commands if provided.

    Args:
    data_provider_name (str): Name of the data provider.
    data_type (str): Type of data to download (e.g., Trade, Quote).
    resolution (str): Time resolution of the data (e.g., Second, Minute).
    security_type (str): Type of security (e.g., Equity, Equity Options).
    tickers (List[str]): List of tickers to download data for.
    start_date (str): Start date of the data download in YYYY-MM-DD format.
    end_date (str): End date of the data download in YYYY-MM-DD format.
    data_provider_config_file_json (Dict[str, Any]): Mock data provider configuration JSON.
    extra_run_command (List[str], optional): Extra run commands to be included in the Lean CLI command.

    Returns:
    CompletedProcess: Result of the Lean CLI command execution.
    """
    # add additional property in module config file
    for data_provider in cli_data_downloaders:
        data_provider.__setattr__("_specifications_url", "")

    create_fake_lean_cli_directory()
    container = initialize_container()

    with mock.patch.object(container.lean_runner, "get_basic_docker_config_without_algo",
                           return_value={"commands": [], "mounts": []}):
        with mock.patch.object(container.api_client.data, "download_public_file_json",
                               return_value=data_provider_config_file_json):
            with mock.patch.object(container.api_client.organizations, "get", return_value=create_api_organization()):
                run_parameters = [
                    "data", "download",
                    "--data-provider-historical", data_provider_name,
                    "--data-type", data_type,
                    "--resolution", resolution,
                    "--security-type", security_type,
                    "--tickers", ','.join(tickers),
                    "--start-date", start_date,
                    "--end-date", end_date,
                ]
                if market:
                    run_parameters.extend(["--market", market])
                if extra_run_command:
                    run_parameters += extra_run_command

                return CliRunner().invoke(lean, run_parameters)


@pytest.mark.parametrize("data_provider,market,is_crypto,security_type,tickers,data_provider_parameters",
                         [("Polygon", "NYSE", False, "Equity", ["AAPL"], ["--polygon-api-key", "123"]),
                          ("Binance", "Binance", True, "CryptoFuture", ["BTCUSDT"],
                           ["--binance-exchange-name", "BinanceUS", "--binanceus-api-key", "123",
                            "--binanceus-api-secret", "123"]),
                          ("CoinApi", "Kraken", True, "Crypto", ["BTCUSDC", "ETHUSD"],
                           ["--coinapi-api-key", "123", "--coinapi-product", "Free"]),
                          ("Interactive Brokers", "USA", False, "Index", ["INTL", "NVDA"],
                           ["--ib-user-name", "123", "--ib-account", "Individual", "--ib-password", "123"])])
def test_download_data_non_interactive(data_provider: str, market: str, is_crypto: bool, security_type: str,
                                       tickers: List[str], data_provider_parameters: List[str]):
    run_data_download = _create_lean_data_download(
        data_provider, "Trade", "Minute", security_type, tickers, "20240101", "20240202",
        _get_data_provider_config(is_crypto), market, data_provider_parameters)
    assert run_data_download.exit_code == 0


@pytest.mark.parametrize("data_type,resolution",
                         [("Trade", "Hour"), ("trade", "hour"), ("TRADE", "HOUR"), ("TrAdE", "HoUr")])
def test_download_data_non_interactive_insensitive_input_param(data_type: str, resolution: str):
    run_data_download = _create_lean_data_download(
        "Polygon", data_type, resolution, "Equity", ["AAPL"], "20240101", "20240202",
        _get_data_provider_config(False), "NYSE", ["--polygon-api-key", "123"])
    assert run_data_download.exit_code == 0


@pytest.mark.parametrize("data_provider,wrong_security_type",
                         [("Polygon", "Future"), ("Polygon", "Crypto"), ("Polygon", "Forex")])
def test_download_data_non_interactive_wrong_security_type(data_provider: str, wrong_security_type: str):
    run_data_download = _create_lean_data_download(data_provider, "Trade", "Hour", wrong_security_type, ["AAPL"],
                                                   "20240101", "20240202", _get_data_provider_config(),
                                                   extra_run_command=["--polygon-api-key", "123"])
    assert run_data_download.exit_code == 1

    error_msg = str(run_data_download.exc_info[1])
    assert data_provider in error_msg
    assert wrong_security_type in error_msg


@pytest.mark.parametrize("data_provider,start_date,end_date",
                         [("Polygon", "20240101", "20230202"), ("Polygon", "2024-01-01", "2023-02-02")])
def test_download_data_non_interactive_wrong_start_end_date(data_provider: str, start_date: str, end_date: str):
    run_data_download = _create_lean_data_download(data_provider, "Trade", "Hour", "Equity", ["AAPL"], start_date,
                                                   end_date, _get_data_provider_config(), "USA",
                                                   extra_run_command=["--polygon-api-key", "123"])
    assert run_data_download.exit_code == 1

    error_msg = str(run_data_download.exc_info[1])
    assert f"Historical start date cannot be greater than or equal to historical end date." in error_msg


@pytest.mark.parametrize("wrong_data_type", ["OpenInterest"])
def test_download_data_non_interactive_wrong_data_type(wrong_data_type: str):
    run_data_download = _create_lean_data_download("Polygon", wrong_data_type, "Hour", "Equity", ["AAPL"], "20240101",
                                                   "20240202", _get_data_provider_config(),
                                                   extra_run_command=["--polygon-api-key", "123"])
    assert run_data_download.exit_code == 1

    error_msg = str(run_data_download.exc_info[1])
    assert wrong_data_type in error_msg


def test_non_interactive_bulk_select():
    # TODO
    pass


def test_interactive_bulk_select():
    pytest.skip("This test is interactive")

    organization = create_api_organization()
    datasource = json.loads(bulk_datasource)
    testSets = [Dataset(name="testSet",
                        vendor="testVendor",
                        categories=["testData"],
                        options=datasource["options"],
                        paths=datasource["paths"],
                        requirements=datasource.get("requirements", {}))]

    products = _select_products_interactive(organization, testSets)
    # No assertion, since interactive has multiple results


def test_dataset_requirements():
    organization = create_api_organization()
    datasource = json.loads(bulk_datasource)
    testSet = Dataset(name="testSet",
                      vendor="testVendor",
                      categories=["testData"],
                      options=datasource["options"],
                      paths=datasource["paths"],
                      requirements=datasource.get("requirements", {}))

    for id, name in testSet.requirements.items():
        assert not organization.has_security_master_subscription(id)
    assert id == 39


bulk_datasource = """
{
	"requirements": {
        "39": "quantconnect-us-equity-security-master"
    },
	"options": [
		{
			"type": "select",
			"id": "data-type",
			"label": "Data type",
			"default": "Trade",
			"description": "The type of data that you want to download",
			"choices": {
				"Trade": "trade",
				"Quote": "quote",
				"Bulk": "bulk"
			}
		},
		{
			"condition": {
				"type": "oneOf",
				"option": "data-type",
				"values": [
					"trade",
					"quote"
				]
			},
			"type": "text",
			"id": "ticker",
			"label": "Ticker(s)",
			"default": "AAPL, MSFT",
			"description": "The comma-separated tickers of the data that you want to download",
			"transform": "lowercase",
			"multiple": true
		},
		{
			"condition": {
				"type": "oneOf",
				"option": "data-type",
				"values": [
					"trade",
					"quote"
				]
			},
			"type": "select",
			"id": "resolution",
			"label": "Resolution",
			"default": "Second",
			"description": "The resolution of the data that you want to download",
			"choices": {
				"Tick": "tick",
				"Second": "second",
				"Minute": "minute",
				"Hour": "hour",
				"Daily": "daily"
			}
		},
		{
			"condition": {
				"type": "oneOf",
				"option": "data-type",
				"values": [
					"bulk"
				]
			},
			"type": "select",
			"id": "resolution",
			"label": "Resolution",
			"default": "Second",
			"description": "The resolution of the bulk data that you want to download",
			"choices": {
				"Daily/Hour": "daily/hour",
				"Minute/Second/Tick": "minute/second/tick"
			}
		},
		{
			"condition": {
				"type": "or",
				"options": [
					{
						"type": "oneOf",
						"option": "data-type",
						"values": [
							"trade",
							"quote"
						]
					},
					{
						"type": "oneOf",
						"option": "resolution",
						"values": [
							"minute/second/tick"
						]
					}
				]
			},
			"type": "start-end"
		}
	],
	"paths": [
		{
			"condition": {
				"type": "and",
				"options": [
					{
						"type": "oneOf",
						"option": "data-type",
						"values": [
							"bulk"
						]
					},
					{
						"type": "oneOf",
						"option": "resolution",
						"values": [
							"daily/hour"
						]
					}
				]
			},
			"templates": {
				"all": [
					"setup/usa/daily_hourly.tar"
				]
			}
		},
		{
			"condition": {
				"type": "and",
				"options": [
					{
						"type": "oneOf",
						"option": "data-type",
						"values": [
							"bulk"
						]
					},
					{
						"type": "oneOf",
						"option": "resolution",
						"values": [
							"minute/second/tick"
						]
					}
				]
			},
			"templates": {
				"all": [
					"setup/usa/d+.tar"
				]
			}
		},
		{
			"condition": {
				"type": "oneOf",
				"option": "resolution",
				"values": [
					"hour",
					"daily"
				]
			},
			"templates": {
				"all": [
					"equity/usa/{resolution}/{ticker}.zip"
				],
				"latest": [
					"equity/usa/map_files/map_files_/d+.zip",
					"equity/usa/factor_files/factor_files_/d+.zip"
				]
			}
		},
		{
			"templates": {
				"all": [
					"equity/usa/{resolution}/{ticker}/{date}_{data-type}.zip"
				],
				"latest": [
					"equity/usa/map_files/map_files_/d+.zip",
					"equity/usa/factor_files/factor_files_/d+.zip"
				]
			}
		}
	]
}
"""


def test_validate_datafile() -> None:
    try:
        value = "/^equity\\/usa\\/(factor_files|map_files)\\/[^\\/]+.zip$/m"
        target = re.compile(value[value.index("/") + 1:value.rindex("/")])
        vendor = QCDataVendor(vendorName="Algoseek", regex=target)
        DataFile(file='equity/usa/daily/aal.zip', vendor=vendor)
    except Exception as err:
        pytest.fail(f"{err}")


def test_filter_pending_datasets() -> None:
    from lean.commands.data.download import _get_available_datasets, _get_data_information

    market_api_client = mock.Mock()
    test_datasets = [
        QCDataset(id=1, name="Pending Dataset", delivery=QCDatasetDelivery.DownloadOnly, vendorName="Vendor", tags=[],
                  pending=True),
        QCDataset(id=2, name="Non-Pending Dataset", delivery=QCDatasetDelivery.DownloadOnly, vendorName="Vendor",
                  tags=[], pending=False)
    ]
    market_api_client.list_datasets = MagicMock(return_value=test_datasets)
    container.api_client.market = market_api_client

    datasources = {
        str(test_datasets[0].id): {
            'options': [],
            'paths': [],
            'requirements': {},
        },
        str(test_datasets[1].id): {
            'options': [],
            'paths': [],
            'requirements': {},
        }
    }
    container.api_client.data.get_info = MagicMock(return_value=QCDataInformation(datasources=datasources, prices=[],
                                                                                  agreement=""))

    datasets = _get_available_datasets(QCFullOrganization(id=1, name="Test Org", seats=1, type="",
                                                          credit=QCOrganizationCredit(movements=[], balance=1000),
                                                          products=[], data=QCOrganizationData(current=True),
                                                          members=[]))

    assert len(datasets) == 1
    assert datasets[0].name == test_datasets[1].name
