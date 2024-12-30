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
import sys
import json
from pathlib import Path
import traceback
from unittest import mock

import pytest
import responses
from click.testing import CliRunner

from lean.commands import lean
from lean.constants import DEFAULT_ENGINE_IMAGE
from lean.container import container
from lean.models.docker import DockerImage
from lean.models.json_module import JsonModule
from tests.test_helpers import create_fake_lean_cli_directory, reset_state_installed_modules, \
    setup_mock_api_client_and_responses
from tests.conftest import initialize_container
from click.testing import Result

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
    "ib-enable-delayed-streaming-data": "no",
    "ib-weekly-restart-utc-time": "21:00:00",
    "organization-id": "abc",

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


def create_fake_binance_environment(name: str, live_mode: bool) -> None:
    path = Path.cwd() / "lean.json"
    config = path.read_text(encoding="utf-8")
    config = config.replace("{", f"""
{{
    "binance-use-testnet": "live",
    "binance-exchange-name": "binance",
    "binance-api-secret": "abc",
    "binance-api-key": "abc",
    "organization-id": "abc",

    "environments": {{
        "{name}": {{
            "live-mode": {str(live_mode).lower()},

            "live-mode-brokerage": "BinanceCoinFuturesBrokerage",
            "data-queue-handler": [ "BinanceCoinFuturesBrokerage" ],
            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
            "history-provider": [ "BrokerageHistoryProvider", "SubscriptionDataReaderHistoryProvider" ]
        }}
    }},
    """)

    path.write_text(config, encoding="utf-8")

@pytest.mark.skipif(
    sys.platform == "darwin", reason="MacOS does not support IB tests."
)
def test_live_calls_lean_runner_with_correct_algorithm_file() -> None:
    # TODO: currently it is not using the live-paper envrionment
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    result = CliRunner().invoke(lean, ["live", "Python Project", "--environment", "live-paper"])

    traceback.print_exception(*result.exc_info)

    assert result.exception is None
    assert result.exit_code == 0

    container.lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                 "live-paper",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 ENGINE_IMAGE,
                                                 None,
                                                 False,
                                                 False,
                                                 {},
                                                 {})

@pytest.mark.skipif(
    sys.platform == "darwin", reason="MacOS does not support IB tests."
)
def test_live_calls_lean_runner_with_extra_docker_config() -> None:
    # TODO: currently it is not using the live-paper environment
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    result = CliRunner().invoke(lean, ["live", "Python Project",
                                       "--environment",
                                       "live-paper",
                                       "--extra-docker-config",
                                       '{"device_requests": [{"count": -1, "capabilities": [["compute"]]}],'
                                       '"volumes": {"extra/path": {"bind": "/extra/path", "mode": "rw"}}}'])

    traceback.print_exception(*result.exc_info)

    assert result.exit_code == 0

    container.lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                           "live-paper",
                                                           Path("Python Project/main.py").resolve(),
                                                           mock.ANY,
                                                           ENGINE_IMAGE,
                                                           None,
                                                           False,
                                                           False,
                                                           {
                                                               "device_requests": [
                                                                   {"count": -1, "capabilities": [["compute"]]}
                                                               ],
                                                               "volumes": {
                                                                   "extra/path": {"bind": "/extra/path", "mode": "rw"}
                                                               }
                                                           },
                                                           {})

@pytest.mark.skipif(
    sys.platform == "darwin", reason="MacOS does not support IB tests."
)
def test_live_calls_lean_runner_with_paths_to_mount() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    with mock.patch.object(JsonModule, "get_paths_to_mount", return_value={"some-config": "/path/to/file.json"}):
        result = CliRunner().invoke(lean, ["live", "Python Project",
                                           "--environment", "live-paper",
                                           "--data-provider-historical", "QuantConnect"])

    assert result.exit_code == 0

    container.lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                           "live-paper",
                                                           Path("Python Project/main.py").resolve(),
                                                           mock.ANY,
                                                           ENGINE_IMAGE,
                                                           None,
                                                           False,
                                                           False,
                                                           {},
                                                           {"some-config": "/path/to/file.json"})


def test_live_aborts_when_environment_does_not_exist() -> None:
    create_fake_lean_cli_directory()

    result = CliRunner().invoke(lean, ["live", "Python Project", "--environment", "fake-environment"])

    assert result.exit_code != 0

    container.lean_runner.run_lean.assert_not_called()


def test_live_aborts_when_environment_has_live_mode_set_to_false() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("backtesting", False)

    result = CliRunner().invoke(lean, ["live", "Python Project", "--environment", "backtesting"])

    assert result.exit_code != 0

    container.lean_runner.run_lean.assert_not_called()

@pytest.mark.skipif(
    sys.platform == "darwin", reason="MacOS does not support IB tests."
)
def test_live_calls_lean_runner_with_default_output_directory() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)
    lean_runner = container.lean_runner

    result = CliRunner().invoke(lean, ["live", "Python Project", "--environment", "live-paper"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once()
    args, _ = lean_runner.run_lean.call_args

    # This will raise an error if the output directory is not relative to Python Project/backtests
    args[3].relative_to(Path("Python Project/live").resolve())

@pytest.mark.skipif(
    sys.platform == "darwin", reason="MacOS does not support IB tests."
)
def test_live_calls_lean_runner_with_custom_output_directory() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)
    lean_runner = container.lean_runner

    result = CliRunner().invoke(lean, ["live",
                                       "Python Project",
                                       "--environment", "live-paper",
                                       "--output", "Python Project/custom"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once()
    args, _ = lean_runner.run_lean.call_args

    # This will raise an error if the output directory is not relative to Python Project/custom-backtests
    args[3].relative_to(Path("Python Project/custom").resolve())

@pytest.mark.skipif(
    sys.platform == "darwin", reason="MacOS does not support IB tests."
)
def test_live_calls_lean_runner_with_release_mode() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)
    lean_runner = container.lean_runner

    result = CliRunner().invoke(lean, ["live", "CSharp Project", "--environment", "live-paper", "--release"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                 "live-paper",
                                                 Path("CSharp Project/Main.cs").resolve(),
                                                 mock.ANY,
                                                 ENGINE_IMAGE,
                                                 None,
                                                 True,
                                                 False,
                                                 {},
                                                 {})

@pytest.mark.skipif(
    sys.platform == "darwin", reason="MacOS does not support IB tests."
)
def test_live_calls_lean_runner_with_detach() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)
    lean_runner = container.lean_runner

    result = CliRunner().invoke(lean, ["live", "Python Project", "--environment", "live-paper", "--detach"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                 "live-paper",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 ENGINE_IMAGE,
                                                 None,
                                                 False,
                                                 True,
                                                 {},
                                                 {})


def test_live_aborts_when_project_does_not_exist() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)
    lean_runner = container.lean_runner

    result = CliRunner().invoke(lean, ["live", "This Project Does Not Exist"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


def test_live_aborts_when_project_does_not_contain_algorithm_file() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)
    lean_runner = container.lean_runner

    result = CliRunner().invoke(lean, ["live", "data"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


@pytest.mark.parametrize("target,replacement", [("DU1234567", ""), ('"ib-account": "DU1234567",', "")])
def test_live_aborts_when_lean_config_is_missing_properties(target: str, replacement: str) -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)
    lean_runner = container.lean_runner

    config_path = Path.cwd() / "lean.json"
    config = config_path.read_text(encoding="utf-8")
    config_path.write_text(config.replace(target, replacement), encoding="utf-8")

    result = CliRunner().invoke(lean, ["live", "Python Project", "--environment", "live-paper"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()

def test_live_sets_dependent_configurations_from_modules_json_based_on_environment() -> None:
    create_fake_lean_cli_directory()
    create_fake_binance_environment("live-binance", True)
    lean_runner = container.lean_runner

    config_path = Path.cwd() / "lean.json"
    config = config_path.read_text(encoding="utf-8")
    config_path.write_text(config.replace("binance-exchange-name", "different-config"), encoding="utf-8")

    result = CliRunner().invoke(lean, ["live", "Python Project", "--environment", "live-binance"])

    # binance exchange should be set
    assert result.exit_code == 1

terminal_link_required_options = {
    "terminal-link-connection-type": "SAPI",
    "terminal-link-server-auth-id": "abc",
    "terminal-link-environment": "Beta",
    "terminal-link-server-host": "abc",
    "terminal-link-server-port": "123",
    "terminal-link-emsx-broker": "abc",
    "terminal-link-emsx-account": "abc",
    "terminal-link-openfigi-api-key": "test"
}

brokerage_required_options = {
    "Paper Trading": {},
    "Interactive Brokers": {
        "ib-user-name": "trader777",
        "ib-account": "DU1234567",
        "ib-password": "hunter2",
        "ib-enable-delayed-streaming-data": "no"
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
    "Coinbase Advanced Trade": {
        "coinbase-api-name": "123",
        "coinbase-api-private-key": "456",
    },
    "Binance": {
        "binance-exchange-name": "binance",
        "binance-api-key": "123",
        "binance-api-secret": "456",
        "binance-use-testnet": "paper",
    },
    "Zerodha": {
        "zerodha-api-key": "123",
        "zerodha-access-token": "456",
        "zerodha-product-type": "mis",
        "zerodha-trading-segment": "equity",
        "zerodha-history-subscription": "false",
    },
    "Samco": {
        "samco-client-id": "123",
        "samco-client-password": "456",
        "samco-year-of-birth": "2000",
        "samco-product-type": "mis",
        "samco-trading-segment": "equity",
    },
    "Terminal Link": {
        **terminal_link_required_options,
        "live-cash-balance": "USD:10000,EUR:10",
    },
    "Kraken": {
        "kraken-api-key": "abc",
        "kraken-api-secret": "abc",
        "kraken-verification-tier": "starter",
    },
    "Trading Technologies": {
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
    },
    "CharlesSchwab": {
        "charles-schwab-account-number": "123"
    },
    "Bybit": {
        "bybit-api-key": "abc",
        "bybit-api-secret": "abc",
        "bybit-vip-level": "VIP0",
        "bybit-use-testnet": "paper",
    }
}

data_feed_required_options = {
    "Interactive Brokers": brokerage_required_options["Interactive Brokers"],
    "Tradier": brokerage_required_options["Tradier"],
    "OANDA": brokerage_required_options["OANDA"],
    "Bitfinex": brokerage_required_options["Bitfinex"],
    "Coinbase Advanced Trade": brokerage_required_options["Coinbase Advanced Trade"],
    "Binance": brokerage_required_options["Binance"],
    "Zerodha": brokerage_required_options["Zerodha"],
    "Samco": brokerage_required_options["Samco"],
    "Terminal Link": terminal_link_required_options,
    "Kraken": brokerage_required_options["Kraken"],
    "CharlesSchwab": brokerage_required_options["CharlesSchwab"],
    "Bybit": brokerage_required_options["Bybit"],
}

data_provider_required_options = {
    "IEX": {
        "iex-cloud-api-key": "123",
        "iex-price-plan": "Launch",
    },
    "Polygon": {
        "polygon-api-key": "123",
    },
    "AlphaVantage": {
        "alpha-vantage-api-key": "111",
        "alpha-vantage-price-plan": "Free"
    }
}


data_providers_required_options = {
    "QuantConnect": {},
    "local": {},
    "Terminal Link": terminal_link_required_options
}


@pytest.mark.skipif(
    sys.platform == "darwin", reason="MacOS does not support IB tests."
)
@pytest.mark.parametrize("data_provider", data_providers_required_options.keys())
def test_live_calls_lean_runner_with_data_provider(data_provider: str) -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)
    lean_runner = container.lean_runner

    options = []
    for key, value in data_providers_required_options[data_provider].items():
        options.extend([f"--{key}", value])

    result = CliRunner().invoke(lean, ["live", "CSharp Project", "--environment", "live-paper",
                                "--data-provider-historical", data_provider,
                                *options])

    expected = 0
    # not a valid option
    if data_provider == 'Terminal Link':
        expected = 2
    assert result.exit_code == expected

    if expected == 0:
        lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                     "live-paper",
                                                     Path("CSharp Project/Main.cs").resolve(),
                                                     mock.ANY,
                                                     ENGINE_IMAGE,
                                                     None,
                                                     False,
                                                     False,
                                                     {},
                                                     {})


@pytest.mark.parametrize("brokerage", brokerage_required_options.keys() - ["Paper Trading"])
def test_live_non_interactive_aborts_when_missing_brokerage_options(brokerage: str) -> None:
    if (brokerage == "Interactive Brokers" and sys.platform == "darwin"):
        pytest.skip("MacOS does not support IB tests")

    create_fake_lean_cli_directory()

    required_options = brokerage_required_options[brokerage].items()
    for length in range(len(required_options)):
        comb = itertools.combinations(required_options, length)
        # TODO: investigate the reason of slow iterations
        if len(list(comb)) > 1000:
            continue
        for current_options in comb:
            lean_runner = container.lean_runner

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

            if brokerage == "Trading Technologies":
                options.extend(["--live-cash-balance", "USD:100"])

            result = CliRunner().invoke(lean, ["live", "Python Project",
                                            "--brokerage", brokerage,
                                            "---data-provider-live", data_feed,
                                            *options])
            assert result.exit_code != 0

            lean_runner.run_lean.assert_not_called()


@pytest.mark.parametrize("data_feed", data_feed_required_options.keys())
def test_live_non_interactive_aborts_when_missing_data_feed_options(data_feed: str) -> None:
    if (data_feed == "Interactive Brokers" and sys.platform == "darwin"):
        pytest.skip("MacOS does not support IB tests")
    create_fake_lean_cli_directory()

    container.initialize(docker_manager=mock.Mock(), lean_runner=mock.Mock())

    required_options = data_feed_required_options[data_feed].items()
    for length in range(len(required_options)):
        for current_options in itertools.combinations(required_options, length):
            options = []

            for key, value in current_options:
                options.extend([f"--{key}", value])

            result = CliRunner().invoke(lean, ["live", "Python Project",
                                               "--brokerage", "Paper Trading",
                                               "--data-provider-live", data_feed,
                                               "--live-cash-balance", "USD:100",
                                               *options])

            traceback.print_exception(*result.exc_info)

            assert result.exit_code != 0

            container.lean_runner.run_lean.assert_not_called()


@responses.activate
@pytest.mark.parametrize("brokerage,data_feed",
                         itertools.product(brokerage_required_options.keys(), data_feed_required_options.keys()))
def test_live_non_interactive_do_not_store_non_persistent_properties_in_lean_config(brokerage: str, data_feed: str) -> None:
    if ((brokerage == "Interactive Brokers" or data_feed == "Interactive Brokers") and sys.platform == "darwin"):
        pytest.skip("MacOS does not support IB tests")

    create_fake_lean_cli_directory()
    container.api_client = setup_mock_api_client_and_responses()

    lean_runner = container.lean_runner

    options = []

    for key, value in brokerage_required_options[brokerage].items():
        options.extend([f"--{key}", value])

    for key, value in data_feed_required_options[data_feed].items():
        options.extend([f"--{key}", value])

    if brokerage == "Trading Technologies" or brokerage == "Paper Trading":
        options.extend(["--live-cash-balance", "USD:100"])

    result = CliRunner().invoke(lean, ["live", "Python Project",
                                       "--brokerage", brokerage,
                                       "--data-provider-live", data_feed,
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
                                                 False,
                                                 {},
                                                 {})

    config = container.lean_config_manager.get_lean_config()


@responses.activate
@pytest.mark.parametrize("brokerage,data_feed",
                         itertools.product(brokerage_required_options.keys(), data_feed_required_options.keys()))
def test_live_non_interactive_calls_run_lean_when_all_options_given(brokerage: str, data_feed: str) -> None:
    if ((brokerage == "Interactive Brokers" or data_feed == "Interactive Brokers") and sys.platform == "darwin"):
        pytest.skip("MacOS does not support IB tests")

    create_fake_lean_cli_directory()
    container.api_client = setup_mock_api_client_and_responses()
    lean_runner = container.lean_runner

    options = []

    for key, value in brokerage_required_options[brokerage].items():
        options.extend([f"--{key}", value])

    for key, value in data_feed_required_options[data_feed].items():
        options.extend([f"--{key}", value])

    if brokerage == "Trading Technologies" or brokerage == "Paper Trading":
        options.extend(["--live-cash-balance", "USD:100"])

    result = CliRunner().invoke(lean, ["live", "Python Project",
                                       "--brokerage", brokerage,
                                       "--data-provider-live", data_feed,
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
                                                 False,
                                                 {},
                                                 {})

@responses.activate
@pytest.mark.parametrize("brokerage,data_feed1,data_feed2",[(brokerage, *data_feeds) for brokerage, data_feeds in
                         itertools.product(brokerage_required_options.keys(), itertools.combinations(data_feed_required_options.keys(), 2))])
def test_live_non_interactive_calls_run_lean_when_all_options_given_with_multiple_data_feeds(brokerage: str, data_feed1: str, data_feed2: str) -> None:
    if ((brokerage == "Interactive Brokers" or data_feed1 == "Interactive Brokers" or data_feed2 == "Interactive Brokers") and sys.platform == "darwin"):
        pytest.skip("MacOS does not support IB tests")

    create_fake_lean_cli_directory()
    container.api_client = setup_mock_api_client_and_responses()
    lean_runner = container.lean_runner

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
                                       "--data-provider-live", data_feed1,
                                       "--data-provider-live", data_feed2,
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
                                                 False,
                                                 {},
                                                 {})


@pytest.mark.parametrize("brokerage", brokerage_required_options.keys() - ["Paper Trading"])
def test_live_non_interactive_falls_back_to_lean_config_for_brokerage_settings(brokerage: str) -> None:
    if (brokerage == "Interactive Brokers" and sys.platform == "darwin"):
        pytest.skip("MacOS does not support IB tests")

    create_fake_lean_cli_directory()

    required_options = brokerage_required_options[brokerage].items()
    for length in range(len(required_options)):
        comb = itertools.combinations(required_options, length)
        # TODO: investigate the reason of slow iterations
        if len(list(comb)) > 1000:
            continue
        for current_options in comb:
            lean_runner = container.lean_runner

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
            else:
                data_feed = "Binance"
                options.extend(["--binance-exchange-name", "binance",
                                "--binance-api-key", "123",
                                "--binance-api-secret", "456",
                                "--binance-use-testnet", "live"])

            if brokerage == "Trading Technologies":
                options.extend(["--live-cash-balance", "USD:100"])

            result = CliRunner().invoke(lean, ["live", "Python Project",
                                               "--brokerage", brokerage,
                                               "--data-provider-live", data_feed,
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
                                                         False,
                                                         {})


@pytest.mark.parametrize("data_feed", data_feed_required_options.keys())
def test_live_non_interactive_falls_back_to_lean_config_for_data_feed_settings(data_feed: str) -> None:
    if (data_feed == "Interactive Brokers" and sys.platform == "darwin"):
        pytest.skip("MacOS does not support IB tests")

    create_fake_lean_cli_directory()

    required_options = data_feed_required_options[data_feed].items()
    for length in range(len(required_options)):
        comb = itertools.combinations(required_options, length)
        # TODO: investigate the reason of slow iterations
        if len(list(comb)) > 1000:
            continue
        for current_options in comb:
            lean_runner = container.lean_runner

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

            if data_feed == "Binance":
                options.extend(["--binance-exchange-name", "binance"])

            result = CliRunner().invoke(lean, ["live", "Python Project",
                                               "--brokerage", "Paper Trading",
                                               "--data-provider-live", data_feed,
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
                                                         False,
                                                         {})


@responses.activate
@pytest.mark.parametrize("data_feed1,data_feed2", itertools.combinations(data_feed_required_options.keys(), 2))
def test_live_non_interactive_falls_back_to_lean_config_for_multiple_data_feed_settings(data_feed1: str, data_feed2: str) -> None:
    if ((data_feed1 == "Interactive Brokers" or data_feed2 == "Interactive Brokers") and sys.platform == "darwin"):
        pytest.skip("MacOS does not support IB tests")

    create_fake_lean_cli_directory()
    mock_api_client = setup_mock_api_client_and_responses()

    required_options = list(data_feed_required_options[data_feed1].items()) + list(data_feed_required_options[data_feed2].items())
    if len(required_options) > 8:
        #Skip computationally expensive tests
        pytest.skip('computationally expensive test')
    for length in range(len(required_options)):
        for current_options in itertools.combinations(required_options, length):
            lean_runner = mock.Mock()
            # refresh so we assert we are called once
            initialize_container(None, lean_runner,api_client_to_use=mock_api_client)

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

            if data_feed1 == "Binance" or data_feed2 == "Binance":
                options.extend(["--binance-exchange-name", "binance"])

            result = CliRunner().invoke(lean, ["live", "Python Project",
                                               "--brokerage", "Paper Trading",
                                               "--data-provider-live", data_feed1,
                                               "--data-provider-live", data_feed2,
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
                                                         False,
                                                         {},
                                                         {})

@pytest.mark.skipif(
    sys.platform == "darwin", reason="MacOS does not support IB tests."
)
def test_live_forces_update_when_update_option_given() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    result = CliRunner().invoke(lean, ["live", "Python Project", "--environment", "live-paper", "--update"])

    assert result.exit_code == 0

    container.docker_manager.pull_image.assert_called_once_with(ENGINE_IMAGE)
    container.lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                 "live-paper",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 ENGINE_IMAGE,
                                                 None,
                                                 False,
                                                 False,
                                                 {},
                                                 {})

@pytest.mark.skipif(
    sys.platform == "darwin", reason="MacOS does not support IB tests."
)
def test_live_passes_custom_image_to_lean_runner_when_set_in_config() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    container.cli_config_manager.engine_image.set_value("custom/lean:123")

    result = CliRunner().invoke(lean, ["live", "Python Project", "--environment", "live-paper"])

    assert result.exit_code == 0

    container.lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                 "live-paper",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 DockerImage(name="custom/lean", tag="123"),
                                                 None,
                                                 False,
                                                 False,
                                                 {},
                                                 {})

@pytest.mark.skipif(
    sys.platform == "darwin", reason="MacOS does not support IB tests."
)
def test_live_passes_custom_image_to_lean_runner_when_given_as_option() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    container.cli_config_manager.engine_image.set_value("custom/lean:123")

    result = CliRunner().invoke(lean,
                                ["live", "Python Project", "--environment", "live-paper", "--image", "custom/lean:456"])

    assert result.exit_code == 0

    container.lean_runner.run_lean.assert_called_once_with(mock.ANY,
                                                 "live-paper",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 DockerImage(name="custom/lean", tag="456"),
                                                 None,
                                                 False,
                                                 False,
                                                 {},
                                                 {})

@pytest.mark.skipif(
    sys.platform =="darwin", reason="MacOS does not support IB tests."
)
@pytest.mark.parametrize("python_venv", ["Custom-venv",
                                        "/Custom-venv",
                                        None])
def test_live_passes_custom_python_venv_to_lean_runner_when_given_as_option(python_venv: str) -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)
    lean_runner= container.lean_runner

    result = CliRunner().invoke(lean,
                                ["live", "Python Project", "--environment", "live-paper", "--python-venv", python_venv])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once()
    args, _ = lean_runner.run_lean.call_args

    if python_venv:
        assert args[0]["python-venv"] == "/Custom-venv"
    else:
        assert "python-venv" not in args[0]


@responses.activate
@pytest.mark.parametrize("brokerage,cash", [("Paper Trading", ""),
                                            ("Paper Trading", "USD:100"),
                                            ("Paper Trading", "USD:100,EUR:200"),
                                            # ("Trading Technologies", "") not tested since this will prompt to interactive panel
                                            ("Trading Technologies", "USD:100"),
                                            ("Trading Technologies", "USD:100,EUR:200"),
                                            ("Binance", ""),
                                            ("Binance", "USD:100"),
                                            ("Bitfinex", ""),
                                            ("Bitfinex", "USD:100"),
                                            ("Coinbase Advanced Trade", ""),
                                            ("Coinbase Advanced Trade", "USD:100"),
                                            ("Interactive Brokers", ""),
                                            ("Interactive Brokers", "USD:100"),
                                            ("Kraken", ""),
                                            ("Kraken", "USD:100"),
                                            ("OANDA", ""),
                                            ("OANDA", "USD:100"),
                                            ("Samco", ""),
                                            ("Samco", "USD:100"),
                                            # ("Terminal Link", ""),  not tested since this will prompt to interactive panel
                                            ("Terminal Link", "USD:100"),
                                            ("Tradier", ""),
                                            ("Tradier", "USD:100"),
                                            ("Zerodha", ""),
                                            ("Zerodha", "USD:100"),
                                            ("CharlesSchwab", ""),
                                            ("CharlesSchwab", "USD:100")])
def test_live_passes_live_cash_balance_to_lean_runner_when_given_as_option(brokerage: str, cash: str) -> None:
    if (brokerage == "Interactive Brokers" and sys.platform == "darwin"):
        pytest.skip("MacOS does not support IB tests")

    create_fake_lean_cli_directory()
    container.api_client = setup_mock_api_client_and_responses()
    lean_runner = container.lean_runner

    options = []
    required_options = brokerage_required_options[brokerage].items()
    for key, value in required_options:
        if key == "live-cash-balance":
            continue
        options.extend([f"--{key}", value])

    result = CliRunner().invoke(lean, ["live", "Python Project", *options,
                                       "--brokerage", brokerage, "--live-cash-balance", cash,
                                       "--data-provider-live", "Custom data only"])

    if brokerage not in ["Paper Trading", "Trading Technologies", "Terminal Link"] and cash != "":
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


@responses.activate
@pytest.mark.parametrize("brokerage,holdings", [("Paper Trading", ""),
                                                ("Paper Trading", "A:A 2T:1:145.1"),
                                                ("Paper Trading", "A:A 2T:1:145.1,AA:AA 2T:2:20.35"),
                                                ("Trading Technologies", ""),
                                                ("Trading Technologies", "A:A 2T:1:145.1"),
                                                ("Binance", ""),
                                                ("Binance", "A:A 2T:1:145.1"),
                                                ("Bitfinex", ""),
                                                ("Bitfinex", "A:A 2T:1:145.1"),
                                                ("Coinbase Advanced Trade", ""),
                                                ("Coinbase Advanced Trade", "A:A 2T:1:145.1"),
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
                                                ("Zerodha", "A:A 2T:1:145.1"),
                                                ("CharlesSchwab", ""),
                                                ("CharlesSchwab", "A:A 2T:1:145.1")])
def test_live_passes_live_holdings_to_lean_runner_when_given_as_option(brokerage: str, holdings: str) -> None:
    if (brokerage == "Interactive Brokers" and sys.platform == "darwin"):
        pytest.skip("MacOS does not support IB tests")

    create_fake_lean_cli_directory()
    container.api_client = setup_mock_api_client_and_responses()
    lean_runner = container.lean_runner

    options = []
    required_options = brokerage_required_options[brokerage].items()
    for key, value in required_options:
        options.extend([f"--{key}", value])

    if brokerage == "Trading Technologies":
        options.extend(["--live-cash-balance", "USD:100"])

    result = CliRunner().invoke(lean, ["live", "Python Project", "--brokerage", brokerage, "--live-holdings", holdings,
                                       "--data-provider-live", "Custom data only", *options])

    if brokerage not in ["Paper Trading", "Terminal Link", "Binance"] and holdings != "":
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

def test_live_non_interactive_deploy_with_live_and_historical_provider_missed_historical_not_optional_config() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    container.initialize(docker_manager=mock.Mock(), lean_runner=mock.Mock(), api_client = mock.MagicMock())

    provider_live_option = ["--data-provider-live", "IEX",
                            "--iex-cloud-api-key", "123",
                            "--iex-price-plan", "Launch"]

    provider_history_option = ["--data-provider-historical", "Polygon"]
                               # "--polygon-api-key", "123"]

    result = CliRunner().invoke(lean, ["live", "deploy" , "--brokerage", "Paper Trading",
                                       *provider_live_option,
                                       *provider_history_option,
                                       "Python Project",
                                       ])
    error_msg = str(result.exc_info[1]).split()

    assert "--polygon-api-key" in error_msg
    assert "--iex-cloud-api-key" not in error_msg

    assert result.exit_code == 1

def test_live_non_interactive_deploy_with_live_and_historical_provider_missed_live_not_optional_config() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    container.initialize(docker_manager=mock.Mock(), lean_runner=mock.Mock(), api_client = mock.MagicMock())

    provider_live_option = ["--data-provider-live", "IEX",
                            "--iex-cloud-api-key", "123"]
                            #"--iex-price-plan", "Launch"]

    provider_history_option = ["--data-provider-historical", "Polygon", "--polygon-api-key", "123"]

    result = CliRunner().invoke(lean, ["live", "deploy", "--brokerage", "Paper Trading",
                                       *provider_live_option,
                                       *provider_history_option,
                                       "Python Project",
                                       ])

    error_msg = str(result.exc_info[1]).split()

    assert "--iex-price-plan" in error_msg
    assert "--polygon-api-key" not in error_msg

    assert result.exit_code == 1

def test_live_non_interactive_deploy_with_real_brokerage_without_credentials() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    container.initialize(docker_manager=mock.Mock(), lean_runner=mock.Mock(), api_client = mock.MagicMock())

    # create fake environment has IB configs already
    brokerage = ["--brokerage", "OANDA"]

    provider_live_option = ["--data-provider-live", "IEX",
                            "--iex-cloud-api-key", "123",
                            "--iex-price-plan", "Launch"]

    result = CliRunner().invoke(lean, ["live", "deploy",
                                       *brokerage,
                                       *provider_live_option,
                                       "Python Project",
                                       ])
    assert result.exit_code == 1

    error_msg = str(result.exc_info[1])

    assert "--oanda-account-id" in error_msg
    assert "--oanda-access-token" in error_msg
    assert "--oanda-environment" in error_msg
    assert "--iex-price-plan" not in error_msg


def create_lean_option(brokerage_name: str, data_provider_live_name: str, data_provider_historical_name: str,
                       api_client: any, environment_modifier=None) -> Result:
    reset_state_installed_modules()
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    if environment_modifier:
        environment_modifier()

    initialize_container(api_client_to_use=api_client)

    option = ["--brokerage", brokerage_name]
    for key, value in brokerage_required_options[brokerage_name].items():
        option.extend([f"--{key}", value])

    data_feed_required_options.update(data_provider_required_options)

    option.extend(["--data-provider-live", data_provider_live_name])
    for key, value in data_feed_required_options[data_provider_live_name].items():
        if f"--{key}" not in option:
            option.extend([f"--{key}", value])

    if data_provider_historical_name is not None:
        option.extend(["--data-provider-historical", data_provider_historical_name])
        if data_provider_historical_name is not "Local":
            for key, value in data_feed_required_options[data_provider_historical_name].items():
                if f"--{key}" not in option:
                    option.extend([f"--{key}", value])

    result = CliRunner().invoke(lean, ["live", "deploy",
                                       *option,
                                       "Python Project",
                                       ])
    assert result.exit_code == 0
    return result

@pytest.mark.parametrize("brokerage_name,data_provider_live_name,data_provider_historical_name,brokerage_product_id,data_provider_live_product_id,data_provider_historical_id",
                         [("Interactive Brokers", "IEX", "Polygon", "181", "333", "306"),
                          ("Paper Trading", "IEX", "Polygon", None, "333", "306"),
                          ("Tradier", "IEX", "AlphaVantage", "185", "333", "334"),
                          ("Paper Trading", "IEX", "Local", None, "333", "222")])
def test_live_deploy_with_different_brokerage_and_different_live_data_provider_and_historical_data_provider(brokerage_name: str, data_provider_live_name: str, data_provider_historical_name: str, brokerage_product_id: str, data_provider_live_product_id: str, data_provider_historical_id: str) -> None:
    if (brokerage_name == "Interactive Brokers" and sys.platform == "darwin"):
        pytest.skip("MacOS does not support IB tests")

    api_client = mock.MagicMock()
    create_lean_option(brokerage_name, data_provider_live_name, data_provider_historical_name, api_client)

    is_exists = []
    if brokerage_product_id is None and data_provider_historical_name != "Local":
        assert len(api_client.method_calls) == 2
        for m_c, id in zip(api_client.method_calls, [data_provider_live_product_id, data_provider_historical_id]):
            if id in m_c[1]:
                is_exists.append(True)
        assert is_exists
        assert len(is_exists) == 2
    elif brokerage_product_id is None and data_provider_historical_name == "Local":
        assert len(api_client.method_calls) == 1
        if data_provider_live_product_id in api_client.method_calls[0][1]:
            is_exists.append(True)
        assert is_exists
        assert len(is_exists) == 1
    else:
        assert len(api_client.method_calls) == 3
        for m_c, id in zip(api_client.method_calls, [data_provider_live_product_id, data_provider_historical_id, brokerage_product_id]):
            if id in f"{m_c[1]}":
                is_exists.append(True)
        assert is_exists
        assert len(is_exists) == 3

@pytest.mark.parametrize("brokerage_name,data_provider_live_name,brokerage_product_id,data_provider_live_product_id",
                         [("Interactive Brokers", "IEX", "181", "333"),
                          ("Tradier", "IEX", "185", "333")])
def test_live_non_interactive_deploy_with_different_brokerage_and_different_live_data_provider(brokerage_name: str, data_provider_live_name: str, brokerage_product_id: str, data_provider_live_product_id: str) -> None:
    if (brokerage_name == "Interactive Brokers" and sys.platform == "darwin"):
        pytest.skip("MacOS does not support IB tests")

    api_client = mock.MagicMock()
    create_lean_option(brokerage_name, data_provider_live_name, None, api_client)

    assert len(api_client.method_calls) == 2
    is_exists = []
    for m_c, id in zip(api_client.method_calls, [data_provider_live_product_id, brokerage_product_id]):
        if id in m_c[1]:
            is_exists.append(True)

    assert is_exists
    assert len(is_exists) == 2

@pytest.mark.parametrize("brokerage_name,data_provider_live_name,brokerage_product_id",
                         [("Bybit", "Bybit", "305"),
                          ("Coinbase Advanced Trade", "Coinbase Advanced Trade", "183"),
                          ("Interactive Brokers", "Interactive Brokers", "181"),
                          ("Tradier", "Tradier", "185")])
def test_live_non_interactive_deploy_with_different_brokerage_with_the_same_live_data_provider(brokerage_name: str, data_provider_live_name: str, brokerage_product_id: str) -> None:
    if (brokerage_name == "Interactive Brokers" and sys.platform == "darwin"):
        pytest.skip("MacOS does not support IB tests")

    api_client = mock.MagicMock()
    create_lean_option(brokerage_name, data_provider_live_name, None, api_client)

    print(api_client.call_args_list)
    print(api_client.call_args)

    for m_c in api_client.method_calls:
        if brokerage_product_id in m_c[1]:
            is_exist = True

    assert is_exist

@pytest.mark.parametrize("brokerage_name,data_provider_live_name,data_provider_live_product_id",
                         [("Paper Trading", "IEX", "333"),
                          ("Paper Trading", "Polygon", "306")])
def test_live_non_interactive_deploy_paper_brokerage_different_live_data_provider(brokerage_name: str, data_provider_live_name: str, data_provider_live_product_id: str) -> None:
    api_client = mock.MagicMock()
    create_lean_option(brokerage_name, data_provider_live_name, None, api_client)

    assert len(api_client.method_calls) == 1
    for m_c in api_client.method_calls:
        if data_provider_live_product_id in m_c[1]:
            is_exist = True

    assert is_exist


@pytest.mark.parametrize("brokerage_name,data_provider_live_name,existing_cash,existing_holdings",
                         [("Paper Trading", "Polygon", "True", "True"),
                          ("Paper Trading", "Polygon", "True", "False"),
                          ("Paper Trading", "Polygon", "False", "True"),
                          ("Paper Trading", "Polygon", "False", "False")])
def test_live_state_file(brokerage_name: str, data_provider_live_name: str,
                    existing_cash: bool, existing_holdings: bool) -> None:
    api_client = mock.MagicMock()

    def environment_modifier():
        result_directory = Path.cwd() / "Python Project" / "live" / "2024-09-26_17-25-28"
        result_file = result_directory / f"L-3875119070.json"
        result_file.parent.mkdir(parents=True, exist_ok=True)
        with open(result_file, "w+") as out_file:
            state = {}
            if existing_cash:
                state["cash"] = {"USD": {"symbol": "USD", "amount": 100000.0}}
            if existing_holdings:
                state["holdings"] = {"BTCUSD 2XR":{"symbol":{"value":"BTCUSD","id":"BTCUSD 2XR","permtick":"BTCUSD"},
                                                   "type":7,"currencySymbol":"$","averagePrice":64778.92,"quantity":0.3,
                                                   "marketPrice":63425.05,"conversionRate":1.0,"marketValue":19027.515,
                                                   "unrealizedPnl":-25.98,"unrealizedPnLPercent":-0.13}}
            json.dump(state, out_file)
        with open(result_directory / "config", "w+") as out_file:
            json.dump({"algorithm-language": "Python", "parameters": {}, "id": "3875119070"}, out_file)

    create_lean_option(brokerage_name, data_provider_live_name, None, api_client,
                       environment_modifier=environment_modifier)
