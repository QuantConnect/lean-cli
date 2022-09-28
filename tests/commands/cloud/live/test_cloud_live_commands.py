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
from tests.commands.test_live import brokerage_required_options

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
    api_client.get.return_value = {'portfolio': {"cash": {}}}
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
                                                  mock.ANY)

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
    api_client.get.return_value = {'portfolio': {"cash": {}}}
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
                                                  mock.ANY)


@pytest.mark.parametrize("brokerage,cash", [("Paper Trading", None),
                                            ("Paper Trading", ""),
                                            ("Paper Trading", "USD:100"),
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
def test_cloud_live_deploy_with_live_cash_balance(brokerage: str, cash: str) -> None:
    create_fake_lean_cli_directory()

    api_client = mock.Mock()
    api_client.nodes.get_all.return_value = create_qc_nodes()
    api_client.get.return_value = {
            'portfolio': {
                'cash': {
                    'USD': {
                        'SecuritySymbols': [],
                        'Symbol': 'USD',
                        'Amount': 500,
                        'ConversionRate': 1,
                        'CurrencySymbol': '$',
                        'ValueInAccountCurrency': 500
                    }
                }
            },
            'success': True
        }
    container.api_client.override(providers.Object(api_client))

    cloud_project_manager = mock.Mock()
    container.cloud_project_manager.override(providers.Object(cloud_project_manager))

    cloud_runner = mock.Mock()
    container.cloud_runner.override(providers.Object(cloud_runner))
    
    options = []
    for key, value in brokerage_required_options[brokerage].items():
        if "organization" not in key:
            options.extend([f"--{key}", value])

    result = CliRunner().invoke(lean, ["cloud", "live", "Python Project", "--brokerage", brokerage, "--live-cash-balance", cash, 
                                       "--node", "live", "--auto-restart", "yes", "--notify-order-events", "no", 
                                       "--notify-insights", "no", *options])

    if brokerage not in ["Paper Trading", "Trading Technologies"]:
        assert result.exit_code != 0
        api_client.live.start.assert_not_called()
        return

    assert result.exit_code == 0
    
    if cash:
        cash_pairs = cash.split(",")
        if len(cash_pairs) == 2:
            cash_list = [{"currency": "USD", "amount": 100}, {"currency": "EUR", "amount": 200}]
        else:
            cash_list = [{"currency": "USD", "amount": 100}]
    else:
        cash_list = [{"currency": "USD", "amount": 500}]
        
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
