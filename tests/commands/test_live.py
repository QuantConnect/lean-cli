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
from typing import Optional
from unittest import mock

import pytest
from click.testing import CliRunner
from dependency_injector import providers

import lean.models.brokerages.local
from lean.commands import lean
from lean.constants import DEFAULT_ENGINE_IMAGE
from lean.container import container
from lean.models.docker import DockerImage
from tests.test_helpers import create_fake_lean_cli_directory

ENGINE_IMAGE = DockerImage.parse(DEFAULT_ENGINE_IMAGE)


@pytest.fixture(autouse=True)
def update_manager_mock() -> mock.Mock:
    """A pytest fixture which mocks the update manager before every test."""
    update_manager = mock.Mock()
    container.update_manager.override(providers.Object(update_manager))
    return update_manager


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
    "ib-enable-delayed-streaming-data": false,

    "environments": {{
        "{name}": {{
            "live-mode": {str(live_mode).lower()},

            "live-mode-brokerage": "InteractiveBrokersBrokerage",
            "setup-handler": "QuantConnect.Lean.Engine.Setup.BrokerageSetupHandler",
            "result-handler": "QuantConnect.Lean.Engine.Results.LiveTradingResultHandler",
            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.LiveTradingDataFeed",
            "data-queue-handler": "QuantConnect.Brokerages.InteractiveBrokers.InteractiveBrokersBrokerage",
            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.LiveTradingRealTimeHandler",
            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BrokerageTransactionHandler",
            "history-provider": "BrokerageHistoryProvider"
        }}
    }},
    """)

    path.write_text(config, encoding="utf-8")


def test_live_calls_lean_runner_with_correct_algorithm_file() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["live", "Python Project", "--environment", "live-paper"])

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

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["live", "Python Project", "--environment", "fake-environment"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


def test_live_aborts_when_environment_has_live_mode_set_to_false() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("backtesting", False)

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["live", "Python Project", "--environment", "backtesting"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


def test_live_calls_lean_runner_with_default_output_directory() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["live", "Python Project", "--environment", "live-paper"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once()
    args, _ = lean_runner.run_lean.call_args

    # This will raise an error if the output directory is not relative to Python Project/backtests
    args[3].relative_to(Path("Python Project/live").resolve())


def test_live_calls_lean_runner_with_custom_output_directory() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["live",
                                       "Python Project",
                                       "--environment", "live-paper",
                                       "--output", "Python Project/custom"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once()
    args, _ = lean_runner.run_lean.call_args

    # This will raise an error if the output directory is not relative to Python Project/custom-backtests
    args[3].relative_to(Path("Python Project/custom").resolve())


def test_live_copies_code_to_output_directory() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    project_manager = mock.Mock()
    project_manager.find_algorithm_file.return_value = Path.cwd() / "Python Project" / "main.py"
    container.project_manager.override(providers.Object(project_manager))

    result = CliRunner().invoke(lean, ["live",
                                       "Python Project",
                                       "--environment", "live-paper",
                                       "--output", "Python Project/custom"])

    assert result.exit_code == 0

    project_manager.copy_code.assert_called_once_with(Path.cwd() / "Python Project",
                                                      Path.cwd() / "Python Project" / "custom" / "code")


def test_live_calls_lean_runner_with_release_mode() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

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

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

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

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["live", "This Project Does Not Exist"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


def test_live_aborts_when_project_does_not_contain_algorithm_file() -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["live", "data"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


@pytest.mark.parametrize("target,replacement", [("DU1234567", ""), ('"ib-account": "DU1234567",', "")])
def test_live_aborts_when_lean_config_is_missing_properties(target: str, replacement: str) -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    config_path = Path.cwd() / "lean.json"
    config = config_path.read_text(encoding="utf-8")
    config_path.write_text(config.replace(target, replacement), encoding="utf-8")

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["live", "Python Project", "--environment", "live-paper"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


brokerage_required_options = {
    "Paper Trading": {},
    "Interactive Brokers": {
        "ib-user-name": "trader777",
        "ib-account": "DU1234567",
        "ib-password": "hunter2"
    },
    "Tradier": {
        "tradier-account-id": "123",
        "tradier-access-token": "456",
        "tradier-use-sandbox": "yes"
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
        "gdax-passphrase": "789"
    },
    "Binance": {
        "binance-api-key": "123",
        "binance-api-secret": "456"
    },
    "Zerodha": {
        "zerodha-api-key": "123",
        "zerodha-access-token": "456",
        "zerodha-product-type": "MIS",
        "zerodha-trading-segment": "EQUITY"
    }
}

data_feed_required_options = {
    "Interactive Brokers": {
        **brokerage_required_options["Interactive Brokers"],
        "ib-enable-delayed-streaming-data": "yes"
    },
    "Tradier": brokerage_required_options["Tradier"],
    "OANDA": brokerage_required_options["OANDA"],
    "Bitfinex": brokerage_required_options["Bitfinex"],
    "Coinbase Pro": brokerage_required_options["Coinbase Pro"],
    "Binance": brokerage_required_options["Binance"],
    "Zerodha": {
        **brokerage_required_options["Zerodha"],
        "zerodha-history-subscription": "yes"
    }
}


@pytest.mark.parametrize("brokerage", brokerage_required_options.keys() - ["Paper Trading"])
def test_live_non_interactive_aborts_when_missing_brokerage_options(brokerage: str) -> None:
    create_fake_lean_cli_directory()

    required_options = brokerage_required_options[brokerage].items()
    for length in range(len(required_options)):
        for current_options in itertools.combinations(required_options, length):
            docker_manager = mock.Mock()
            container.docker_manager.override(providers.Object(docker_manager))

            lean_runner = mock.Mock()
            container.lean_runner.override(providers.Object(lean_runner))

            options = []

            for key, value in current_options:
                options.extend([f"--{key}", value])

            if brokerage == "Binance":
                data_feed = "Bitfinex"
                options.extend(["--bitfinex-api-key", "123", "--bitfinex-api-secret", "456"])
            else:
                data_feed = "Binance"
                options.extend(["--binance-api-key", "123", "--binance-api-secret", "456"])

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
            docker_manager = mock.Mock()
            container.docker_manager.override(providers.Object(docker_manager))

            lean_runner = mock.Mock()
            container.lean_runner.override(providers.Object(lean_runner))

            options = []

            for key, value in current_options:
                options.extend([f"--{key}", value])

            result = CliRunner().invoke(lean, ["live", "Python Project",
                                               "--brokerage", "Paper Trading",
                                               "--data-feed", data_feed,
                                               *options])

            assert result.exit_code != 0

            lean_runner.run_lean.assert_not_called()


@pytest.mark.parametrize("brokerage,data_feed",
                         itertools.product(brokerage_required_options.keys(), data_feed_required_options.keys()))
def test_live_non_interactive_calls_run_lean_when_all_options_given(brokerage: str, data_feed: str) -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    options = []

    for key, value in brokerage_required_options[brokerage].items():
        options.extend([f"--{key}", value])

    for key, value in data_feed_required_options[data_feed].items():
        options.extend([f"--{key}", value])

    result = CliRunner().invoke(lean, ["live", "Python Project",
                                       "--brokerage", brokerage,
                                       "--data-feed", data_feed,
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


@pytest.mark.parametrize("brokerage", brokerage_required_options.keys() - ["Paper Trading"])
def test_live_non_interactive_falls_back_to_lean_config_for_brokerage_settings(brokerage: str) -> None:
    create_fake_lean_cli_directory()

    required_options = brokerage_required_options[brokerage].items()
    for length in range(len(required_options)):
        for current_options in itertools.combinations(required_options, length):
            docker_manager = mock.Mock()
            container.docker_manager.override(providers.Object(docker_manager))

            lean_runner = mock.Mock()
            container.lean_runner.override(providers.Object(lean_runner))

            options = []

            for key, value in current_options:
                options.extend([f"--{key}", value])

            missing_options_config = {key: value for key, value in set(required_options) - set(current_options)}
            with (Path.cwd() / "lean.json").open("w+", encoding="utf-8") as file:
                file.write(json.dumps({
                    **missing_options_config,
                    "data-folder": "data"
                }))

            if brokerage == "Binance":
                data_feed = "Bitfinex"
                options.extend(["--bitfinex-api-key", "123", "--bitfinex-api-secret", "456"])
            else:
                data_feed = "Binance"
                options.extend(["--binance-api-key", "123", "--binance-api-secret", "456"])

            result = CliRunner().invoke(lean, ["live", "Python Project",
                                               "--brokerage", brokerage,
                                               "--data-feed", data_feed,
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


@pytest.mark.parametrize("data_feed", data_feed_required_options.keys())
def test_live_non_interactive_falls_back_to_lean_config_for_data_feed_settings(data_feed: str) -> None:
    create_fake_lean_cli_directory()

    required_options = data_feed_required_options[data_feed].items()
    for length in range(len(required_options)):
        for current_options in itertools.combinations(required_options, length):
            docker_manager = mock.Mock()
            container.docker_manager.override(providers.Object(docker_manager))

            lean_runner = mock.Mock()
            container.lean_runner.override(providers.Object(lean_runner))

            options = []

            for key, value in current_options:
                options.extend([f"--{key}", value])

            missing_options_config = {key: value for key, value in set(required_options) - set(current_options)}
            with (Path.cwd() / "lean.json").open("w+", encoding="utf-8") as file:
                file.write(json.dumps({
                    **missing_options_config,
                    "data-folder": "data"
                }))

            result = CliRunner().invoke(lean, ["live", "Python Project",
                                               "--brokerage", "Paper Trading",
                                               "--data-feed", data_feed,
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

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

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

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

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

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

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


@pytest.mark.parametrize("image_option,update_flag,update_check_expected", [(None, True, False),
                                                                            (None, False, True),
                                                                            ("custom/lean:3", True, False),
                                                                            ("custom/lean:3", False, False),
                                                                            (DEFAULT_ENGINE_IMAGE, True, False),
                                                                            (DEFAULT_ENGINE_IMAGE, False, True)])
def test_live_checks_for_updates(update_manager_mock: mock.Mock,
                                 image_option: Optional[str],
                                 update_flag: bool,
                                 update_check_expected: bool) -> None:
    create_fake_lean_cli_directory()
    create_fake_environment("live-paper", True)

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    options = []
    if image_option is not None:
        options.extend(["--image", image_option])
    if update_flag:
        options.extend(["--update"])

    result = CliRunner().invoke(lean, ["live", "Python Project", "--environment", "live-paper", *options])

    assert result.exit_code == 0

    if update_check_expected:
        update_manager_mock.warn_if_docker_image_outdated.assert_called_once_with(ENGINE_IMAGE)
    else:
        update_manager_mock.warn_if_docker_image_outdated.assert_not_called()
