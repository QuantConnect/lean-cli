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

import json
from typing import Dict, Any
from unittest import mock

from lean.models.brokerages.local import DataFeed
from lean.models.data_providers import DataProvider
from lean.models.lean_config_configurer import LeanConfigConfigurer

JSON_MODULE = json.loads("""
{
    "type": [
        "data-queue-handler",
        "data-provider"
    ],
    "product-id": "305",
    "id": "PolygonDataFeed",
    "display-id": "Polygon",
    "installs": true,
    "configurations": [
        {
            "id": "polygon-api-key",
            "cloud-id": "apiKey",
            "type": "input",
            "value": "",
            "input-method": "prompt",
            "prompt-info": "Your Polygon.io API Key",
            "help": "Your Polygon.io API Key"
        },
        {
            "id": "environments",
            "type": "configurations-env",
            "value": [
                {
                    "name": "lean-cli",
                    "value": [
                        {
                            "name": "data-queue-handler",
                            "value": "QuantConnect.Polygon.PolygonDataQueueHandler"
                        },
                        {
                            "name": "history-provider",
                            "value": [
                                "QuantConnect.Polygon.PolygonDataQueueHandler",
                                "SubscriptionDataReaderHistoryProvider"
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "id": "data-provider",
            "type": "info",
            "value": "QuantConnect.Lean.Engine.DataFeeds.DownloaderDataProvider"
        },
        {
            "id": "data-downloader",
            "type": "info",
            "value": "QuantConnect.Polygon.PolygonDataDownloader"
        }
    ]
}
""")


def test_gets_environment_from_configuration() -> None:
    module = LeanConfigConfigurer(JSON_MODULE)
    environment_values = module.get_configurations_env_values()

    assert environment_values == JSON_MODULE["configurations"][1]["value"][0]["value"]


def get_lean_config() -> Dict[str, Any]:
    return {
        "environments": {
            "live-ib-polygon": {
                "live-mode": True,
                "live-mode-brokerage": "InteractiveBrokersBrokerage",
                "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
                "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
                "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
                "data-queue-handler": ["QuantConnect.Brokerages.InteractiveBrokers.InteractiveBrokersBrokerage"],
                "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
                "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
                "history-provider": [
                    "BrokerageHistoryProvider",
                    "SubscriptionDataReaderHistoryProvider"
                ]
            }
        }
    }


def test_configures_environment_with_module() -> None:
    with mock.patch.object(DataFeed, "configure_credentials"):
        lean_config = get_lean_config()
        module = DataFeed(JSON_MODULE)
        module.configure(lean_config, "live-ib-polygon")

        assert lean_config != get_lean_config()
        assert "QuantConnect.Polygon.PolygonDataQueueHandler" in lean_config["environments"]["live-ib-polygon"]["data-queue-handler"]


def test_invalid_environment_configuration_is_ignored() -> None:
    with mock.patch.object(DataProvider, "configure_credentials"):
        lean_config = get_lean_config()
        module = DataProvider(JSON_MODULE)
        module.configure(lean_config, "live-ib-polygon")

        assert lean_config == get_lean_config()
