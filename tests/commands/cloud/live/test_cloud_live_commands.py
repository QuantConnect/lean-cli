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


from unittest import mock
from click.testing import CliRunner
from dependency_injector import providers
import pytest
import lean.models.brokerages.local
from lean.commands import lean
from lean.container import container
from lean.models.api import QCEmailNotificationMethod, QCWebhookNotificationMethod, QCSMSNotificationMethod, QCTelegramNotificationMethod
from tests.test_helpers import create_fake_lean_cli_directory, create_qc_nodes

def test_cloud_live_stop() -> None:
    create_fake_lean_cli_directory()

    api_client = mock.Mock()
    container.api_client.override(providers.Object(api_client))

    cloud_project_manager = mock.Mock()
    container.cloud_project_manager.override(providers.Object(cloud_project_manager))

    result = CliRunner().invoke(lean, ["cloud", "live", "stop", "Python Project"])

    assert result.exit_code == 0

def test_cloud_live_liquidate() -> None:
    create_fake_lean_cli_directory()

    api_client = mock.Mock()
    container.api_client.override(providers.Object(api_client))

    cloud_project_manager = mock.Mock()
    container.cloud_project_manager.override(providers.Object(cloud_project_manager))

    result = CliRunner().invoke(lean, ["cloud", "live", "liquidate", "Python Project"])

    assert result.exit_code == 0

def test_cloud_live_deploy() -> None:
    create_fake_lean_cli_directory()

    api_client = mock.Mock()
    api_client.nodes.get_all.return_value = create_qc_nodes()
    container.api_client.override(providers.Object(api_client))

    cloud_project_manager = mock.Mock()
    container.cloud_project_manager.override(providers.Object(cloud_project_manager))

    cloud_runner = mock.Mock()
    container.cloud_runner.override(providers.Object(cloud_runner))
        
    result = CliRunner().invoke(lean, ["cloud", "live", "Python Project", "--brokerage", "Paper Trading", "--node", "live", 
                                       "--auto-restart", "yes", "--notify-order-events", "no", "--notify-insights", "no"])
    
    assert result.exit_code == 0
    
    api_client.live.start.assert_called_once_with(mock.ANY,
                                                  mock.ANY,
                                                  "3",
                                                  mock.ANY,
                                                  mock.ANY,
                                                  True,
                                                  mock.ANY,
                                                  False,
                                                  False,
                                                  [],
                                                  None)

@pytest.mark.parametrize("notice_method,configs", [("emails", "customAddress:customSubject"),
                                             ("emails", "customAddress1:customSubject1,customAddress2:customSubject2"),
                                             ("webhooks", "customAddress:header1=value1"),
                                             ("webhooks", "customAddress:header1=value1:header2=value2"),
                                             ("webhooks", "customAddress1:header1=value1:header2=value2,customAddress2:header3=value3"),
                                             ("sms", "customNumber"),
                                             ("sms", "customNumber1,customNumber2,customNumber3"),
                                             ("telegram", "customId"),
                                             ("telegram", "customId1,customNumber2"),
                                             ("telegram", "customId:"),
                                             ("telegram", "customId1:,customNumber2:"),
                                             ("telegram", "customId:custom:token"),
                                             ("telegram", "customId1:custom:token1,customId2"),
                                             ("telegram", "customId1:custom:token1,customId2:custom:token2")])
def test_cloud_live_deploy_with_notifications(notice_method: str, configs: str) -> None:
    create_fake_lean_cli_directory()

    api_client = mock.Mock()
    api_client.nodes.get_all.return_value = create_qc_nodes()
    container.api_client.override(providers.Object(api_client))

    cloud_project_manager = mock.Mock()
    container.cloud_project_manager.override(providers.Object(cloud_project_manager))

    cloud_runner = mock.Mock()
    container.cloud_runner.override(providers.Object(cloud_runner))
        
    result = CliRunner().invoke(lean, ["cloud", "live", "Python Project", "--brokerage", "Paper Trading", "--node", "live", 
                                       "--auto-restart", "yes", "--notify-order-events", "yes", "--notify-insights", "yes",
                                       f"--notify-{notice_method}", configs])
    
    assert result.exit_code == 0
    
    notification = []
    
    for config in configs.split(","):
        if notice_method == "emails":
            address, subject = config.split(":")
            notification.append(QCEmailNotificationMethod(address=address, subject=subject))
            
        elif notice_method == "webhooks":
            address, headers = config.split(":", 1)
            headers_dict = {}
            
            for header in headers.split(":"):
                key, value = header.split("=")
                headers_dict[key] = value
                    
            notification.append(QCWebhookNotificationMethod(address=address, headers=headers_dict))
            
        elif notice_method == "sms":
            notification.append(QCSMSNotificationMethod(phoneNumber=config))
            
        else:
            id_token_pair = config.split(":", 1)
            
            if len(id_token_pair) == 2:
                chat_id, token = id_token_pair
                if not token:
                    notification.append(QCTelegramNotificationMethod(id=chat_id))
                else:
                    notification.append(QCTelegramNotificationMethod(id=chat_id, token=token))
            else:
                notification.append(QCTelegramNotificationMethod(id=id_token_pair[0]))
    
    api_client.live.start.assert_called_once_with(mock.ANY,
                                                  mock.ANY,
                                                  "3",
                                                  mock.ANY,
                                                  mock.ANY,
                                                  True,
                                                  mock.ANY,
                                                  True,
                                                  True,
                                                  notification,
                                                  None)

brokerage_required_options = {
    "Paper Trading": {},
    "Interactive Brokers": {
        "ib-user-name": "trader777",
        "ib-account": "DU1234567",
        "ib-password": "hunter2",
        "ib-enable-delayed-streaming-data": "no",
        "ib-organization": "abc",
    },
    "Tradier": {
        "tradier-account-id": "123",
        "tradier-access-token": "456",
        "tradier-environment": "paper"
    },
    "OANDA": {
        "oanda-account-id": "123",
        "oanda-access-token": "456",
        "oanda-environment": "Practice"
    },
    "Bitfinex": {
        "bitfinex-api-key": "123",
        "bitfinex-api-secret": "456",
    },
    "Coinbase Pro": {
        "gdax-api-key": "123",
        "gdax-api-secret": "456",
        "gdax-passphrase": "789",
        "gdax-use-sandbox": "paper"
    },
    "Binance": {
        "binance-exchange-name": "binance",
        "binance-api-key": "123",
        "binance-api-secret": "456",
        "binance-use-testnet": "paper",
        "binance-organization": "abc",
    },
    "Zerodha": {
        "zerodha-api-key": "123",
        "zerodha-access-token": "456",
        "zerodha-product-type": "mis",
        "zerodha-trading-segment": "equity",
        "zerodha-history-subscription": "false",
        "zerodha-organization": "abc",
    },
    "Samco": {
        "samco-client-id": "123",
        "samco-client-password": "456",
        "samco-year-of-birth": "2000",
        "samco-product-type": "mis",
        "samco-trading-segment": "equity",
        "samco-organization": "abc",
    },
    "Atreyu": {
        "atreyu-host": "abc",
        "atreyu-req-port": "123",
        "atreyu-sub-port": "456",
        "atreyu-username": "abc",
        "atreyu-password": "abc",
        "atreyu-client-id": "abc",
        "atreyu-broker-mpid": "abc",
        "atreyu-locate-rqd": "abc",
        "atreyu-organization": "abc",
    },
    "Terminal Link": {
        "terminal-link-environment": "Beta",
        "terminal-link-server-host": "abc",
        "terminal-link-server-port": "123",
        "terminal-link-emsx-broker": "abc",
        "terminal-link-allow-modification": "no",
        "terminal-link-emsx-account": "abc",
        "terminal-link-emsx-strategy": "abc",
        "terminal-link-emsx-notes": "abc",
        "terminal-link-emsx-handling": "abc",
        "terminal-link-emsx-user-time-zone": "abc",
        "terminal-link-organization": "abc",
    },
    "Kraken": {
        "kraken-api-key": "abc",
        "kraken-api-secret": "abc",
        "kraken-verification-tier": "starter",
        "kraken-organization": "abc",
    },
    "FTX": {
        "ftxus-api-key": "abc",
        "ftxus-api-secret": "abc",
        "ftxus-account-tier": "tier1",
        "ftx-api-key": "abc",
        "ftx-api-secret": "abc",
        "ftx-account-tier": "tier1",
        "ftx-exchange-name": "FTX",
        "ftx-organization": "abc",
    },
    "Trading Technologies": {
        "tt-organization": "abc",
        "tt-user-name": "abc",
        "tt-session-password": "abc",
        "tt-account-name": "abc",
        "tt-rest-app-key": "abc",
        "tt-rest-app-secret": "abc",
        "tt-rest-environment": "abc",
        "tt-market-data-sender-comp-id": "123",
        "tt-market-data-target-comp-id": "123",
        "tt-market-data-host": "abc",
        "tt-market-data-port": "123",
        "tt-order-routing-sender-comp-id": "123",
        "tt-order-routing-target-comp-id": "123",
        "tt-order-routing-host": "abc",
        "tt-order-routing-port": "123",
        "tt-log-fix-messages": "abc"
    }
}

@pytest.mark.parametrize("brokerage,cash", [("Paper Trading", "USD:100"),
                                            ("Paper Trading", "USD:100,EUR:200"),
                                            ("Atreyu", "USD:100"),
                                            ("Trading Technologies", "USD:100"),
                                            ("Binance", "USD:100"),
                                            ("Bitfinex", "USD:100"),
                                            ("FTX", "USD:100"),
                                            ("Coinbase Pro", "USD:100"),
                                            ("Interactive Brokers", "USD:100"),
                                            ("Kraken", "USD:100"),
                                            ("OANDA", "USD:100"),
                                            ("Samco", "USD:100"),
                                            ("Terminal Link", "USD:100"),
                                            ("Tradier", "USD:100"),
                                            ("Zerodha", "USD:100")])
def test_cloud_live_deploy_with_initial_cash_balance(brokerage: str, cash: str) -> None:
    create_fake_lean_cli_directory()

    api_client = mock.Mock()
    api_client.nodes.get_all.return_value = create_qc_nodes()
    container.api_client.override(providers.Object(api_client))

    cloud_project_manager = mock.Mock()
    container.cloud_project_manager.override(providers.Object(cloud_project_manager))

    cloud_runner = mock.Mock()
    container.cloud_runner.override(providers.Object(cloud_runner))
    
    options = []
    for key, value in brokerage_required_options[brokerage].items():
        options.extend([f"--{key}", value])

    result = CliRunner().invoke(lean, ["cloud", "live", "Python Project", "--brokerage", brokerage, "--live-cash-balance", cash, 
                                       "--node", "live", "--auto-restart", "yes", "--notify-order-events", "no", 
                                       "--notify-insights", "no", *options])

    if brokerage not in ["Paper Trading", "Atreyu", "Trading Technologies"]:
        assert result.exit_code != 0
        api_client.live.start.assert_not_called()
        return

    assert result.exit_code == 0
    
    cash_pairs = cash.split(",")
    if len(cash_pairs) == 2:
        cash_list = [{"currency": "USD", "amount": 100}, {"currency": "EUR", "amount": 200}]
    else:
        cash_list = [{"currency": "USD", "amount": 100}]
    
    api_client.live.start.assert_called_once_with(mock.ANY,
                                                  mock.ANY,
                                                  "3",
                                                  mock.ANY,
                                                  mock.ANY,
                                                  True,
                                                  mock.ANY,
                                                  False,
                                                  False,
                                                  [],
                                                  cash_list)
