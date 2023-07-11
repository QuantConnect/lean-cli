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
                        requires_security_master=datasource["requiresSecurityMaster"])]

    products = _select_products_interactive(organization, testSets)
    # No assertion, since interactive has multiple results

bulk_datasource="""
{
	"requiresSecurityMaster": true,
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
            'requiresSecurityMaster': True,
        },
        str(test_datasets[1].id): {
            'options': [],
            'paths': [],
            'requiresSecurityMaster': True,
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
