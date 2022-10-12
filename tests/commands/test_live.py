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
import json
from pathlib import Path
import traceback
from unittest import mock

import pytest
from click.testing import CliRunner
from dependency_injector import providers

import lean.models.brokerages.local
from lean.commands import lean
from lean.constants import DEFAULT_ENGINE_IMAGE
from lean.container import container
from lean.models.docker import DockerImage
from lean.models.api import QCMinimalOrganization
from tests.test_helpers import create_fake_lean_cli_directory

ENGINE_IMAGE = DockerImage.parse(DEFAULT_ENGINE_IMAGE)


def create_fake_environment(name: str, live_mode: bool) -> None:
    path = Path.cwd() / "lean.json"
    config = path.read_text(encoding="utf-8")
    config = config.replace("{", f"""
{{
    "ib-account": "DU1234567",
    "ib-user-name": "trader777",
    "ib-password": "hunter2",
    "ib-agent-description": "Individual",
    "ib-trading-mode": "paper",
    "ib-enable-delayed-streaming-data": "no",
    "organization": "abc",

    "environments": {{
        "{name}": {{
            "live-mode": {str(live_mode).lower()},

            "live-mode-brokerage": "InteractiveBrokersBrokerage",
            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
            "data-queue-handler": "InteractiveBrokersBrokerage",
            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
            "history-provider": "BrokerageHistoryProvider"
        }}
    }},
    """)

    path.write_text(config, encoding="utf-8")


def _mock_docker_lean_runner():
    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))
    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))
    return lean_runner, docker_manager


def _mock_docker_lean_runner_api():
    lean_runner, docker_manager = _mock_docker_lean_runner()
    api_client = mock.MagicMock()
    api_client.organizations.get_all.return_value = [
        QCMinimalOrganization(id="abc", name="abc", type="type", ownerName="You", members=1, preferred=True)
    ]
    container.api_client.override(providers.Object(api_client))
    return lean_runner, api_client, docker_manager


def test_live_calls_lean_runner_with_correct_algorithm_file() -> None:
    # TODO: currently it is not using the live-paper envrionment
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)
    lean_runner, _, _ = _mock_docker_lean_runner_api()

    result = CliRunner().invoke(lean, ["live", "Python Project", "--environment", "live-paper"])

    traceback.print_exception(*result.exc_info)

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                 "live-paper",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 ENGINE_IMAGE,
                                                 None,
                                                 False,
                                                 False)


def test_live_aborts_when_environment_does_not_exist() -> None:
    create_fake_lean_cli_directory()
    lean_runner, _ = _mock_docker_lean_runner()

    result = CliRunner().invoke(lean, ["live", "Python Project", "--environment", "fake-environment"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


def test_live_aborts_when_environment_has_live_mode_set_to_false() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("backtesting", False)
    lean_runner, _ = _mock_docker_lean_runner()

    result = CliRunner().invoke(lean, ["live", "Python Project", "--environment", "backtesting"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


def test_live_calls_lean_runner_with_default_output_directory() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)
    lean_runner, _, _ = _mock_docker_lean_runner_api()

    result = CliRunner().invoke(lean, ["live", "Python Project", "--environment", "live-paper"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once()
    args, _ = lean_runner.run_lean.call_args

    # This will raise an error if the output directory is not relative to Python Project/backtests
    args[3].relative_to(Path("Python Project/live").resolve())


def test_live_calls_lean_runner_with_custom_output_directory() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)
    lean_runner, _, _ = _mock_docker_lean_runner_api()

    result = CliRunner().invoke(lean, ["live",
                                       "Python Project",
                                       "--environment", "live-paper",
                                       "--output", "Python Project/custom"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once()
    args, _ = lean_runner.run_lean.call_args

    # This will raise an error if the output directory is not relative to Python Project/custom-backtests
    args[3].relative_to(Path("Python Project/custom").resolve())


def test_live_calls_lean_runner_with_release_mode() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)
    lean_runner, _, _ = _mock_docker_lean_runner_api()

    result = CliRunner().invoke(lean, ["live", "CSharp Project", "--environment", "live-paper", "--release"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                 "live-paper",
                                                 Path("CSharp Project/Main.cs").resolve(),
                                                 mock.ANY,
                                                 ENGINE_IMAGE,
                                                 None,
                                                 True,
                                                 False)


def test_live_calls_lean_runner_with_detach() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)
    lean_runner, _, _ = _mock_docker_lean_runner_api()

    result = CliRunner().invoke(lean, ["live", "Python Project", "--environment", "live-paper", "--detach"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                 "live-paper",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 ENGINE_IMAGE,
                                                 None,
                                                 False,
                                                 True)


def test_live_aborts_when_project_does_not_exist() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)
    lean_runner, _ = _mock_docker_lean_runner()

    result = CliRunner().invoke(lean, ["live", "This Project Does Not Exist"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


def test_live_aborts_when_project_does_not_contain_algorithm_file() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)
    lean_runner, _ = _mock_docker_lean_runner()

    result = CliRunner().invoke(lean, ["live", "data"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


@pytest.mark.parametrize("target,replacement", [("DU1234567", ""), ('"ib-account": "DU1234567",', "")])
def test_live_aborts_when_lean_config_is_missing_properties(target: str, replacement: str) -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)
    lean_runner, _ = _mock_docker_lean_runner()

    config_path = Path.cwd() / "lean.json"
    config = config_path.read_text(encoding="utf-8")
    config_path.write_text(config.replace(target, replacement), encoding="utf-8")

    result = CliRunner().invoke(lean, ["live", "Python Project", "--environment", "live-paper"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


brokerage_required_options = {
    "Paper Trading": {},
    "Interactive Brokers": {
        "ib-user-name": "trader777",
        "ib-account": "DU1234567",
        "ib-password": "hunter2",
        "ib-enable-delayed-streaming-data": "no",
        "organization": "abc",
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
        "organization": "abc",
    },
    "Zerodha": {
        "zerodha-api-key": "123",
        "zerodha-access-token": "456",
        "zerodha-product-type": "mis",
        "zerodha-trading-segment": "equity",
        "zerodha-history-subscription": "false",
        "organization": "abc",
    },
    "Samco": {
        "samco-client-id": "123",
        "samco-client-password": "456",
        "samco-year-of-birth": "2000",
        "samco-product-type": "mis",
        "samco-trading-segment": "equity",
        "organization": "abc",
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
        "organization": "abc",
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
        "organization": "abc",
    },
    "Kraken": {
        "kraken-api-key": "abc",
        "kraken-api-secret": "abc",
        "kraken-verification-tier": "starter",
        "organization": "abc",
    },
    "FTX": {
        "ftxus-api-key": "abc",
        "ftxus-api-secret": "abc",
        "ftxus-account-tier": "tier1",
        "ftx-api-key": "abc",
        "ftx-api-secret": "abc",
        "ftx-account-tier": "tier1",
        "ftx-exchange-name": "FTX",
        "organization": "abc",
    },
    "Trading Technologies": {
        "organization": "abc",
        "tt-user-name": "abc",
        "tt-session-password": "abc",
        "tt-account-name": "abc",
        "tt-rest-app-key": "abc",
        "tt-rest-app-secret": "abc",
        "tt-rest-environment": "abc",
        "tt-market-data-sender-comp-id": "abc",
        "tt-market-data-target-comp-id": "abc",
        "tt-market-data-host": "abc",
        "tt-market-data-port": "abc",
        "tt-order-routing-sender-comp-id": "abc",
        "tt-order-routing-target-comp-id": "abc",
        "tt-order-routing-host": "abc",
        "tt-order-routing-port": "abc",
        "tt-log-fix-messages": "no"
    }
}

data_feed_required_options = {
    "Interactive Brokers": brokerage_required_options["Interactive Brokers"],
    "Tradier": brokerage_required_options["Tradier"],
    "OANDA": brokerage_required_options["OANDA"],
    "Bitfinex": brokerage_required_options["Bitfinex"],
    "Coinbase Pro": brokerage_required_options["Coinbase Pro"],
    "Binance": brokerage_required_options["Binance"],
    "Zerodha": brokerage_required_options["Zerodha"],
    "Samco": brokerage_required_options["Samco"],
    "Terminal Link": brokerage_required_options["Terminal Link"],
    "Kraken": brokerage_required_options["Kraken"],
    "FTX": brokerage_required_options["FTX"],
}


data_providers_required_options = {
    "QuantConnect": {},
    "local": {},
    "Terminal Link": brokerage_required_options["Terminal Link"]
}


@pytest.mark.parametrize("data_provider", data_providers_required_options.keys())
def test_live_calls_lean_runner_with_data_provider(data_provider: str) -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)
    lean_runner, _, _ = _mock_docker_lean_runner_api()

    options = []
    for key, value in data_providers_required_options[data_provider].items():
        options.extend([f"--{key}", value])

    result = CliRunner().invoke(lean, ["live", "CSharp Project", "--environment", "live-paper",
                                "--data-provider", data_provider,
                                *options])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                 "live-paper",
                                                 Path("CSharp Project/Main.cs").resolve(),
                                                 mock.ANY,
                                                 ENGINE_IMAGE,
                                                 None,
                                                 False,
                                                 False)


@pytest.mark.parametrize("brokerage", brokerage_required_options.keys() - ["Paper Trading"])
def test_live_non_interactive_aborts_when_missing_brokerage_options(brokerage: str) -> None:
    create_fake_lean_cli_directory()

    required_options = brokerage_required_options[brokerage].items()
    for length in range(len(required_options)):
        comb = itertools.combinations(required_options, length)
        # TODO: investigate the reason of slow iterations
        if len(list(comb)) > 1000:
            continue
        for current_options in comb:
            lean_runner, _ = _mock_docker_lean_runner()
            
            options = []

            for key, value in current_options:
                options.extend([f"--{key}", value])

            if brokerage == "Binance":
                data_feed = "Bitfinex"
                options.extend(["--bitfinex-api-key", "123", "--bitfinex-api-secret", "456"])
            else:
                data_feed = "Binance"
                options.extend(["--binance-api-key", "123",
                                "--binance-api-secret", "456",
                                "--binance-use-testnet", "live"])

            if brokerage == "Trading Technologies" or brokerage == "Atreyu":
                options.extend(["--live-cash-balance", "USD:100"])

            result = CliRunner().invoke(lean, ["live", "Python Project",
                                            "--brokerage", brokerage,
                                            "--data-feed", data_feed,
                                            *options])
            assert result.exit_code != 0

            lean_runner.run_lean.assert_not_called()


@pytest.mark.parametrize("data_feed", data_feed_required_options.keys())
def test_live_non_interactive_aborts_when_missing_data_feed_options(data_feed: str) -> None:
    create_fake_lean_cli_directory()

    required_options = data_feed_required_options[data_feed].items()
    for length in range(len(required_options)):
        for current_options in itertools.combinations(required_options, length):
            lean_runner, _ = _mock_docker_lean_runner()

            options = []

            for key, value in current_options:
                options.extend([f"--{key}", value])

            result = CliRunner().invoke(lean, ["live", "Python Project",
                                               "--brokerage", "Paper Trading",
                                               "--data-feed", data_feed,
                                               "--live-cash-balance", "USD:100",
                                               *options])

            traceback.print_exception(*result.exc_info)

            assert result.exit_code != 0

            lean_runner.run_lean.assert_not_called()



@pytest.mark.parametrize("brokerage,data_feed",
                         itertools.product(brokerage_required_options.keys(), data_feed_required_options.keys()))
def test_live_non_interactive_calls_run_lean_when_all_options_given(brokerage: str, data_feed: str) -> None:
    create_fake_lean_cli_directory()
    lean_runner, _, _ = _mock_docker_lean_runner_api()

    options = []

    for key, value in brokerage_required_options[brokerage].items():
        options.extend([f"--{key}", value])

    for key, value in data_feed_required_options[data_feed].items():
        options.extend([f"--{key}", value])

    if brokerage == "Trading Technologies" or brokerage == "Paper Trading":
        options.extend(["--live-cash-balance", "USD:100"])

    result = CliRunner().invoke(lean, ["live", "Python Project",
                                       "--brokerage", brokerage,
                                       "--data-feed", data_feed,
                                       *options])

    traceback.print_exception(*result.exc_info)

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                 "lean-cli",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 ENGINE_IMAGE,
                                                 None,
                                                 False,
                                                 False)

@pytest.mark.parametrize("brokerage,data_feed1,data_feed2",[(brokerage, *data_feeds) for brokerage, data_feeds in
                         itertools.product(brokerage_required_options.keys(), itertools.combinations(data_feed_required_options.keys(), 2))])
def test_live_non_interactive_calls_run_lean_when_all_options_given_with_multiple_data_feeds(brokerage: str, data_feed1: str, data_feed2: str) -> None:
    create_fake_lean_cli_directory()
    lean_runner, _, _ = _mock_docker_lean_runner_api()

    options = []

    for key, value in brokerage_required_options[brokerage].items():
        options.extend([f"--{key}", value])

    for key, value in data_feed_required_options[data_feed1].items():
        options.extend([f"--{key}", value])

    for key, value in data_feed_required_options[data_feed2].items():
        options.extend([f"--{key}", value])

    if brokerage == "Trading Technologies" or brokerage == "Paper Trading":
        options.extend(["--live-cash-balance", "USD:100"])

    result = CliRunner().invoke(lean, ["live", "Python Project",
                                       "--brokerage", brokerage,
                                       "--data-feed", data_feed1,
                                       "--data-feed", data_feed2,
                                       *options])

    traceback.print_exception(*result.exc_info)

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                 "lean-cli",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 ENGINE_IMAGE,
                                                 None,
                                                 False,
                                                 False)


@pytest.mark.parametrize("brokerage", brokerage_required_options.keys() - ["Paper Trading"])
def test_live_non_interactive_falls_back_to_lean_config_for_brokerage_settings(brokerage: str) -> None:
    create_fake_lean_cli_directory()

    required_options = brokerage_required_options[brokerage].items()
    for length in range(len(required_options)):
        comb = itertools.combinations(required_options, length)
        # TODO: investigate the reason of slow iterations
        if len(list(comb)) > 1000:
            continue
        for current_options in comb:
            lean_runner, _, _ = _mock_docker_lean_runner_api()

            options = []

            for key, value in current_options:
                options.extend([f"--{key}", value])

            missing_options_config = {key: value for key, value in set(required_options) - set(current_options)}
            with (Path.cwd() / "lean.json").open("w+", encoding="utf-8") as file:
                file.write(json.dumps({
                    **missing_options_config,
                    "data-folder": "data",
                    "job-organization-id": "abc"
                }))

            if brokerage == "Binance":
                data_feed = "Bitfinex"
                options.extend(["--bitfinex-api-key", "123", "--bitfinex-api-secret", "456"])
            elif brokerage == "FTX":
                data_feed = "Binance"
                options.extend(["--ftx-exchange-name", "FTXUS",
                                "--binance-exchange-name", "binance",
                                "--binance-api-key", "123",
                                "--binance-api-secret", "456",
                                "--binance-use-testnet", "live"])
            else:
                data_feed = "Binance"
                options.extend(["--binance-exchange-name", "binance",
                                "--binance-api-key", "123",
                                "--binance-api-secret", "456",
                                "--binance-use-testnet", "live"])

            if brokerage == "Trading Technologies" or brokerage == "Atreyu":
                options.extend(["--live-cash-balance", "USD:100"])

            result = CliRunner().invoke(lean, ["live", "Python Project",
                                               "--brokerage", brokerage,
                                               "--data-feed", data_feed,
                                               *options])

            traceback.print_exception(*result.exc_info)

            assert result.exit_code == 0

            lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                         "lean-cli",
                                                         Path("Python Project/main.py").resolve(),
                                                         mock.ANY,
                                                         ENGINE_IMAGE,
                                                         None,
                                                         False,
                                                         False)


@pytest.mark.parametrize("data_feed", data_feed_required_options.keys())
def test_live_non_interactive_falls_back_to_lean_config_for_data_feed_settings(data_feed: str) -> None:
    create_fake_lean_cli_directory()

    required_options = data_feed_required_options[data_feed].items()
    for length in range(len(required_options)):
        comb = itertools.combinations(required_options, length)
        # TODO: investigate the reason of slow iterations
        if len(list(comb)) > 1000:
            continue
        for current_options in comb:
            lean_runner, _, _ = _mock_docker_lean_runner_api()

            options = []

            for key, value in current_options:
                options.extend([f"--{key}", value])

            missing_options_config = {key: value for key, value in set(required_options) - set(current_options)}
            with (Path.cwd() / "lean.json").open("w+", encoding="utf-8") as file:
                file.write(json.dumps({
                    **missing_options_config,
                    "data-folder": "data",
                    "job-organization-id": "abc"
                }))

            if data_feed == "FTX":
                options.extend(["--ftx-exchange-name", "FTX"])
            elif data_feed == "Binance":
                options.extend(["--binance-exchange-name", "binance"])

            result = CliRunner().invoke(lean, ["live", "Python Project",
                                               "--brokerage", "Paper Trading",
                                               "--data-feed", data_feed,
                                               "--live-cash-balance", "USD:100",
                                               *options])

            assert result.exit_code == 0

            lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                         "lean-cli",
                                                         Path("Python Project/main.py").resolve(),
                                                         mock.ANY,
                                                         ENGINE_IMAGE,
                                                         None,
                                                         False,
                                                         False)


@pytest.mark.parametrize("data_feed1,data_feed2", itertools.combinations(data_feed_required_options.keys(), 2))
def test_live_non_interactive_falls_back_to_lean_config_for_multiple_data_feed_settings(data_feed1: str, data_feed2: str) -> None:
    create_fake_lean_cli_directory()

    required_options = list(data_feed_required_options[data_feed1].items()) + list(data_feed_required_options[data_feed2].items())
    if len(required_options) > 8:
        #Skip computationally expensive tests
        pytest.skip('computationally expensive test')
    for length in range(len(required_options)):
        for current_options in itertools.combinations(required_options, length):
            lean_runner, _, _ = _mock_docker_lean_runner_api()

            options = []

            for key, value in current_options:
                options.extend([f"--{key}", value])

            missing_options_config = {key: value for key, value in set(required_options) - set(current_options)}
            with (Path.cwd() / "lean.json").open("w+", encoding="utf-8") as file:
                file.write(json.dumps({
                    **missing_options_config,
                    "data-folder": "data",
                    "job-organization-id": "abc"
                }))

            if data_feed1 == "FTX" or data_feed2 == "FTX":
                options.extend(["--ftx-exchange-name", "FTX"])
            elif data_feed1 == "Binance" or data_feed2 == "Binance":
                options.extend(["--binance-exchange-name", "binance"])

            result = CliRunner().invoke(lean, ["live", "Python Project",
                                               "--brokerage", "Paper Trading",
                                               "--data-feed", data_feed1,
                                               "--data-feed", data_feed2,
                                               "--live-cash-balance", "USD:100",
                                               *options])

            assert result.exit_code == 0

            lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                         "lean-cli",
                                                         Path("Python Project/main.py").resolve(),
                                                         mock.ANY,
                                                         ENGINE_IMAGE,
                                                         None,
                                                         False,
                                                         False)


def test_live_forces_update_when_update_option_given() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)
    lean_runner, _, docker_manager = _mock_docker_lean_runner_api()

    result = CliRunner().invoke(lean, ["live", "Python Project", "--environment", "live-paper", "--update"])

    assert result.exit_code == 0

    docker_manager.pull_image.assert_called_once_with(ENGINE_IMAGE)
    lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                 "live-paper",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 ENGINE_IMAGE,
                                                 None,
                                                 False,
                                                 False)


def test_live_passes_custom_image_to_lean_runner_when_set_in_config() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)
    lean_runner, _, _ = _mock_docker_lean_runner_api()

    container.cli_config_manager().engine_image.set_value("custom/lean:123")

    result = CliRunner().invoke(lean, ["live", "Python Project", "--environment", "live-paper"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                 "live-paper",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 DockerImage(name="custom/lean", tag="123"),
                                                 None,
                                                 False,
                                                 False)


def test_live_passes_custom_image_to_lean_runner_when_given_as_option() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)
    lean_runner, _, _ = _mock_docker_lean_runner_api()

    container.cli_config_manager().engine_image.set_value("custom/lean:123")

    result = CliRunner().invoke(lean,
                                ["live", "Python Project", "--environment", "live-paper", "--image", "custom/lean:456"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                 "live-paper",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 DockerImage(name="custom/lean", tag="456"),
                                                 None,
                                                 False,
                                                 False)


@pytest.mark.parametrize("python_venv", ["Custom-venv",
                                        "/Custom-venv",
                                        None])
def test_live_passes_custom_python_venv_to_lean_runner_when_given_as_option(python_venv: str) -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)
    lean_runner, _, _ = _mock_docker_lean_runner_api()

    result = CliRunner().invoke(lean,
                                ["live", "Python Project", "--environment", "live-paper", "--python-venv", python_venv])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once()
    args, _ = lean_runner.run_lean.call_args

    if python_venv:
        assert args[0]["python-venv"] == "/Custom-venv"
    else:
        assert "python-venv" not in args[0]


@pytest.mark.parametrize("brokerage,cash", [("Paper Trading", ""),
                                            ("Paper Trading", "USD:100"),
                                            ("Paper Trading", "USD:100,EUR:200"),
                                            ("Atreyu", ""),
                                            ("Atreyu", "USD:100"),
                                            # ("Trading Technologies", "") not tested since this will prompt to interactive panel
                                            ("Trading Technologies", "USD:100"),
                                            ("Trading Technologies", "USD:100,EUR:200"),
                                            ("Binance", ""),
                                            ("Binance", "USD:100"),
                                            ("Bitfinex", ""),
                                            ("Bitfinex", "USD:100"),
                                            ("FTX", ""),
                                            ("FTX", "USD:100"),
                                            ("Coinbase Pro", ""),
                                            ("Coinbase Pro", "USD:100"),
                                            ("Interactive Brokers", ""),
                                            ("Interactive Brokers", "USD:100"),
                                            ("Kraken", ""),
                                            ("Kraken", "USD:100"),
                                            ("OANDA", ""),
                                            ("OANDA", "USD:100"),
                                            ("Samco", ""),
                                            ("Samco", "USD:100"),
                                            ("Terminal Link", ""),
                                            ("Terminal Link", "USD:100"),
                                            ("Tradier", ""),
                                            ("Tradier", "USD:100"),
                                            ("Zerodha", ""),
                                            ("Zerodha", "USD:100")])
def test_live_passes_live_cash_balance_to_lean_runner_when_given_as_option(brokerage: str, cash: str) -> None:
    create_fake_lean_cli_directory()
    lean_runner, _, _ = _mock_docker_lean_runner_api()

    options = []
    required_options = brokerage_required_options[brokerage].items()
    for key, value in required_options:
        options.extend([f"--{key}", value])

    result = CliRunner().invoke(lean, ["live", "Python Project", "--brokerage", brokerage, "--live-cash-balance", cash,
                                       "--data-feed", "Custom data only", *options])

    # TODO: remove Atreyu after the discontinuation of the brokerage support (when removed from module-*.json)
    if brokerage not in ["Paper Trading", "Atreyu", "Trading Technologies"] and cash != "":
        assert result.exit_code != 0
        lean_runner.run_lean.start.assert_not_called()
        return

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once()
    args, _ = lean_runner.run_lean.call_args

    cash_pairs = [x for x in cash.split(",") if x]
    if len(cash_pairs) == 2:
        cash_list = [{"currency": "USD", "amount": 100}, {"currency": "EUR", "amount": 200}]
    elif len(cash_pairs) == 1:
        cash_list = [{"currency": "USD", "amount": 100}]
    else:
        assert "live-cash-balance" not in args[0]
        return

    assert args[0]["live-cash-balance"] == cash_list


@pytest.mark.parametrize("brokerage,holdings", [("Paper Trading", ""),
                                                ("Paper Trading", "A:A 2T:1:145.1"),
                                                ("Paper Trading", "A:A 2T:1:145.1,AA:AA 2T:2:20.35"),
                                                ("Atreyu", ""),
                                                ("Atreyu", "A:A 2T:1:145.1"),
                                                ("Trading Technologies", ""),
                                                ("Trading Technologies", "A:A 2T:1:145.1"),
                                                ("Binance", ""),
                                                ("Binance", "A:A 2T:1:145.1"),
                                                ("Bitfinex", ""),
                                                ("Bitfinex", "A:A 2T:1:145.1"),
                                                ("FTX", ""),
                                                ("FTX", "A:A 2T:1:145.1"),
                                                ("Coinbase Pro", ""),
                                                ("Coinbase Pro", "A:A 2T:1:145.1"),
                                                ("Interactive Brokers", ""),
                                                ("Interactive Brokers", "A:A 2T:1:145.1"),
                                                ("Kraken", ""),
                                                ("Kraken", "A:A 2T:1:145.1"),
                                                ("OANDA", ""),
                                                ("OANDA", "A:A 2T:1:145.1"),
                                                ("Samco", ""),
                                                ("Samco", "A:A 2T:1:145.1"),
                                                ("Terminal Link", ""),
                                                ("Terminal Link", "A:A 2T:1:145.1"),
                                                ("Tradier", ""),
                                                ("Tradier", "A:A 2T:1:145.1"),
                                                ("Zerodha", ""),
                                                ("Zerodha", "A:A 2T:1:145.1")])
def test_live_passes_live_holdings_to_lean_runner_when_given_as_option(brokerage: str, holdings: str) -> None:
    create_fake_lean_cli_directory()
    lean_runner, _, _ = _mock_docker_lean_runner_api()

    options = []
    required_options = brokerage_required_options[brokerage].items()
    for key, value in required_options:
        options.extend([f"--{key}", value])
    
    if brokerage == "Trading Technologies":
        options.extend(["--live-cash-balance", "USD:100"])

    result = CliRunner().invoke(lean, ["live", "Python Project", "--brokerage", brokerage, "--live-holdings", holdings,
                                       "--data-feed", "Custom data only", *options])

    # TODO: remove Atreyu after the discontinuation of the brokerage support (when removed from module-*.json)
    if brokerage not in ["Paper Trading", "Atreyu"] and holdings != "":
        assert result.exit_code != 0
        lean_runner.run_lean.start.assert_not_called()
        return

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once()
    args, _ = lean_runner.run_lean.call_args

    holding = [x for x in holdings.split(",") if x]
    if len(holding) == 2:
        holding_list = [{"Symbol": {"Value": "A", "ID": "A 2T"}, "Quantity": 1, "AveragePrice": 145.1}, 
                        {"Symbol": {"Value": "AA", "ID": "AA 2T"}, "Quantity": 2, "AveragePrice": 20.35}]
    elif len(holding) == 1:
        holding_list = [{"Symbol": {"Value": "A", "ID": "A 2T"}, "Quantity": 1, "AveragePrice": 145.1}]
    else:
        assert "live-holdings" not in args[0]
        return

    assert args[0]["live-holdings"] == holding_list
