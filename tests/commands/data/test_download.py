import json
import pytest
import os
from pathlib import Path

from lean.commands.data.download import *
from lean.container import container
from tests.test_helpers import create_api_organization

test_files = Path(os.path.join(os.path.dirname(os.path.realpath(__file__)), "testFiles"))

# Load in our test files into fake filesystem
@pytest.fixture
def setup(fs):
    fs.add_real_directory(test_files)
    yield fs

def test_bulk_extraction(setup):
    fakeTar = Path(os.path.join(test_files, "20220222_coinapi_crypto_ftx_price_aggregation.tar"))
    out = Path("/tmp/out")

    container.data_downloader()._process_bulk(fakeTar, out)
    assert os.path.exists(out)

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