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
from pathlib import Path
from unittest import mock

import pytest
from click.testing import CliRunner

from lean.commands import lean
from lean.components.cloud.module_manager import ModuleManager
from lean.components.config.storage import Storage
from lean.constants import DEFAULT_ENGINE_IMAGE, LEAN_ROOT_PATH
from lean.container import container
from lean.models.docker import DockerImage
from lean.models.optimizer import (OptimizationConstraint, OptimizationExtremum, OptimizationParameter,
                                   OptimizationTarget)
from tests.test_helpers import create_fake_lean_cli_directory

ENGINE_IMAGE = DockerImage.parse(DEFAULT_ENGINE_IMAGE)


def _get_optimizer_config_manager_mock() -> mock.Mock:
    """A pytest fixture which mocks the optimizer config manager before every test."""
    optimizer_config_manager = mock.Mock()
    optimizer_config_manager.configure_strategy.return_value = "QuantConnect.Optimizer.Strategies.GridSearchOptimizationStrategy"
    optimizer_config_manager.configure_target.return_value = OptimizationTarget(
        target="TotalPerformance.PortfolioStatistics.SharpeRatio",
        extremum=OptimizationExtremum.Maximum)

    optimizer_config_manager.configure_parameters.return_value = [
        OptimizationParameter(name="param1", min=1.0, max=10.0, step=0.5)
    ]

    optimizer_config_manager.configure_constraints.return_value = [
        OptimizationConstraint(**{
            "target": "TotalPerformance.PortfolioStatistics.Drawdown",
            "operator": "less",
            "target-value": "0.25"
        })
    ]

    return optimizer_config_manager


def run_image(image: DockerImage, **kwargs) -> bool:
    results_path = next(key for key in kwargs["volumes"].keys() if kwargs["volumes"][key]["bind"] == "/Results")
    (Path(results_path) / "log.txt").touch()
    return True


def test_optimize_runs_lean_container() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    docker_manager.run_image.side_effect = run_image
    container.initialize(docker_manager=docker_manager)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == ENGINE_IMAGE


def test_optimize_runs_optimizer() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    docker_manager.run_image.side_effect = run_image
    container.initialize(docker_manager=docker_manager)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert kwargs["working_dir"] == "/Lean/Optimizer.Launcher/bin/Debug"
    assert "dotnet QuantConnect.Optimizer.Launcher.dll" in kwargs["commands"]


def test_optimize_mounts_optimizer_config() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    docker_manager.run_image.side_effect = run_image
    container.initialize(docker_manager=docker_manager)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert any([mount["Target"] == "/Lean/Optimizer.Launcher/bin/Debug/config.json" for mount in kwargs["mounts"]])


def test_optimize_mounts_lean_config() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    docker_manager.run_image.side_effect = run_image
    container.initialize(docker_manager=docker_manager)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert any([mount["Target"] == f"{LEAN_ROOT_PATH}/config.json" for mount in kwargs["mounts"]])


def test_optimize_mounts_data_directory() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    docker_manager.run_image.side_effect = run_image
    container.initialize(docker_manager=docker_manager)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert any([volume["bind"] == "/Lean/Data" for volume in kwargs["volumes"].values()])

    key = next(key for key in kwargs["volumes"].keys() if kwargs["volumes"][key]["bind"] == "/Lean/Data")
    assert key == str(Path.cwd() / "data")


def test_optimize_mounts_output_directory() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    docker_manager.run_image.side_effect = run_image
    container.initialize(docker_manager=docker_manager)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project", "--output", "output"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert any([volume["bind"] == "/Results" for volume in kwargs["volumes"].values()])

    key = next(key for key in kwargs["volumes"].keys() if kwargs["volumes"][key]["bind"] == "/Results")
    assert key == str(Path.cwd() / "output")


def test_optimize_creates_output_directory_when_not_existing_yet() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.initialize(docker_manager=docker_manager)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project", "--output", "output"])

    assert result.exit_code == 0

    assert (Path.cwd() / "output").is_dir()


def test_optimize_copies_code_to_output_directory() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    docker_manager.run_image.side_effect = run_image
    container.initialize(docker_manager=docker_manager)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    project_manager = mock.MagicMock()
    project_manager.find_algorithm_file.return_value = Path.cwd() / "Python Project" / "main.py"
    project_manager.get_source_files.return_value = [Path.cwd() / "Python Project" / "main.py"]
    container.project_manager = project_manager

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project", "--output", "output"])

    assert result.exit_code == 0

    project_manager.copy_code.assert_called_once_with(Path.cwd() / "Python Project",
                                                      Path.cwd() / "output" / "code")


def test_optimize_creates_correct_config_from_optimizer_config_manager_output() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    docker_manager.run_image.side_effect = run_image
    container.initialize(docker_manager=docker_manager)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    mount = next(m for m in kwargs["mounts"] if m["Target"] == "/Lean/Optimizer.Launcher/bin/Debug/config.json")
    config = json.loads(Path(mount["Source"]).read_text(encoding="utf-8"))

    assert config["results-destination-folder"] == "/Results"

    assert config["optimization-strategy"] == "QuantConnect.Optimizer.Strategies.GridSearchOptimizationStrategy"
    assert config["optimization-criterion"] == {
        "target": "TotalPerformance.PortfolioStatistics.SharpeRatio",
        "extremum": "max"
    }

    assert config["parameters"] == [
        {
            "name": "param1",
            "min": 1.0,
            "max": 10.0,
            "step": 0.5
        }
    ]

    assert config["constraints"] == [
        {
            "target": "TotalPerformance.PortfolioStatistics.Drawdown",
            "operator": "less",
            "target-value": 0.25
        }
    ]


def test_optimize_creates_correct_config_from_given_optimizer_config() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    docker_manager.run_image.side_effect = run_image
    container.initialize(docker_manager=docker_manager)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    with (Path.cwd() / "optimizer-config.json").open("w+", encoding="utf-8") as file:
        file.write("""
{
  // optional: algorithm class selector
  "algorithm-type-name": "ParameterizedAlgorithm",

  // optional: Algorithm language selector - options CSharp, Python
  "algorithm-language": "CSharp",

  // optional: Physical DLL location
  "algorithm-location": "QuantConnect.Algorithm.CSharp.dll",

  "optimizer-close-automatically": true,

  // How we manage solutions and make decision to continue or stop
  "optimization-strategy": "QuantConnect.Optimizer.Strategies.GridSearchOptimizationStrategy",

  // on-demand settings required for different optimization strategies
  "optimization-strategy-settings": {
    "$type": "QuantConnect.Optimizer.Strategies.StepBaseOptimizationStrategySettings, QuantConnect.Optimizer",
    "default-segment-amount": 10
  },

  // optimization problem
  "optimization-criterion": {
    // path in algorithm output json
    "target": "TotalPerformance.PortfolioStatistics.SharpeRatio",

    // optimization: available options max, min
    "extremum": "max",

    // optional, if defined and backtest complies with the targets then trigger ended event
    "target-value": 3.0
  },

  // if it doesn't comply just drop the backtest
  "constraints": [
    {
      "target": "TotalPerformance.PortfolioStatistics.Drawdown",
      "operator": "less", // less, greaterOrEqual, greater, notEqual, equals
      "target-value": 0.25
    }
  ],

  // optional: default is process count / 2
  //"maximum-concurrent-backtests": 10,

  // optimization parameters
  "parameters": [
    {
      "name": "param1",
      "min": 1.0,
      "max": 10.0,
      "step": 0.5
    }
  ]
}
        """)

    result = CliRunner().invoke(lean, ["optimize", "Python Project", "--optimizer-config", "optimizer-config.json"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    mount = next(m for m in kwargs["mounts"] if m["Target"] == "/Lean/Optimizer.Launcher/bin/Debug/config.json")
    config = json.loads(Path(mount["Source"]).read_text(encoding="utf-8"))

    assert not any([key.startswith("algorithm-") for key in config.keys()])

    assert config["results-destination-folder"] == "/Results"

    assert config["optimization-strategy"] == "QuantConnect.Optimizer.Strategies.GridSearchOptimizationStrategy"
    assert config["optimization-criterion"] == {
        "target": "TotalPerformance.PortfolioStatistics.SharpeRatio",
        "extremum": "max",
        "target-value": 3.0
    }

    assert config["parameters"] == [
        {
            "name": "param1",
            "min": 1.0,
            "max": 10.0,
            "step": 0.5
        }
    ]

    assert config["constraints"] == [
        {
            "target": "TotalPerformance.PortfolioStatistics.Drawdown",
            "operator": "less",
            "target-value": 0.25
        }
    ]


def test_optimize_writes_config_to_output_directory() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    docker_manager.run_image.side_effect = run_image
    container.initialize(docker_manager=docker_manager)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project", "--output", "output"])

    assert result.exit_code == 0

    assert (Path.cwd() / "output" / "optimizer-config.json").exists()
    config = json.loads((Path.cwd() / "output" / "optimizer-config.json").read_text(encoding="utf-8"))

    assert config["results-destination-folder"] == "/Results"

    assert config["optimization-strategy"] == "QuantConnect.Optimizer.Strategies.GridSearchOptimizationStrategy"
    assert config["optimization-criterion"] == {
        "target": "TotalPerformance.PortfolioStatistics.SharpeRatio",
        "extremum": "max"
    }

    assert config["parameters"] == [
        {
            "name": "param1",
            "min": 1.0,
            "max": 10.0,
            "step": 0.5
        }
    ]

    assert config["constraints"] == [
        {
            "target": "TotalPerformance.PortfolioStatistics.Drawdown",
            "operator": "less",
            "target-value": 0.25
        }
    ]


def test_optimize_aborts_when_project_has_no_parameters() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    docker_manager.run_image.side_effect = run_image
    container.initialize(docker_manager=docker_manager)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {})

    result = CliRunner().invoke(lean, ["optimize", "Python Project"])

    assert result.exit_code != 0

    docker_manager.run_image.assert_not_called()


def test_optimize_aborts_when_run_image_fails() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = False
    container.initialize(docker_manager=docker_manager)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project"])

    assert result.exit_code != 0

    docker_manager.run_image.assert_called_once()


def test_optimize_forces_update_when_update_option_given() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.initialize(docker_manager=docker_manager)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project", "--update"])

    assert result.exit_code == 0

    docker_manager.pull_image.assert_called_once_with(ENGINE_IMAGE)
    docker_manager.run_image.assert_called_once()


def test_optimize_runs_custom_image_when_set_in_config() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    docker_manager.run_image.side_effect = run_image
    container.initialize(docker_manager=docker_manager)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    container.cli_config_manager.engine_image.set_value("custom/lean:123")

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == DockerImage(name="custom/lean", tag="123")


def test_optimize_runs_custom_image_when_given_as_option() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.initialize(docker_manager=docker_manager)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    container.cli_config_manager.engine_image.set_value("custom/lean:123")

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project", "--image", "custom/lean:456"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == DockerImage(name="custom/lean", tag="456")


@pytest.mark.parametrize("max_concurrent_backtests", range(1, 4))
def test_optimize_uses_the_given_max_concurrent_backtests(max_concurrent_backtests: int) -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image
    container.initialize(docker_manager=docker_manager)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project",
                                       "--max-concurrent-backtests", max_concurrent_backtests])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    mount = next(m for m in kwargs["mounts"] if m["Target"] == "/Lean/Optimizer.Launcher/bin/Debug/config.json")
    config = json.loads(Path(mount["Source"]).read_text(encoding="utf-8"))

    assert config["maximum-concurrent-backtests"] == max_concurrent_backtests


def test_optimize_estimate_fails_if_no_backtests_have_been_run() -> None:
    create_fake_lean_cli_directory()

    result = CliRunner().invoke(lean, ["optimize", "Python Project", "--estimate"])

    assert result.exit_code != 0

    expected_message = "Please run at least one backtest for this project in order to run an optimization estimate"
    assert expected_message in result.exception.args[0]


@pytest.mark.parametrize("max_concurrent_backtests, expected_runtime", [(2, "0:01:10.568375"),
                                                                        (3, "0:00:47.045583"),
                                                                        (4, "0:00:35.284188")])
def test_optimize_estimate_properly_calculates_runtime(max_concurrent_backtests: int, expected_runtime: str) -> None:
    create_fake_lean_cli_directory()

    backtest_log_file = Path.cwd() / "Python Project" / "backtests" / "2020-01-01_00-00-00" / "log.txt"
    backtest_log_file.parent.mkdir(parents=True, exist_ok=True)

    with backtest_log_file.open("w+", encoding="utf-8") as logs:
        logs.write("""
2022-11-25T15:04:37.6556705Z TRACE:: Config.Get(): Configuration key not found. Key: data-directory - Using default value: ../../../Data/
2022-11-25T15:04:37.6623325Z TRACE:: Config.Get(): Configuration key not found. Key: version-id - Using default value:
2022-11-25T15:04:37.6669692Z TRACE:: Config.Get(): Configuration key not found. Key: cache-location - Using default value: /Lean/Data
2022-11-25T15:04:37.6683605Z TRACE:: Engine.Main(): LEAN ALGORITHMIC TRADING ENGINE v2.5.0.0 Mode: DEBUG (64bit) Host: abreu
2022-11-25T15:04:37.6809416Z TRACE:: Engine.Main(): Started 3:04 PM
2022-11-25T15:04:37.6910935Z TRACE:: Config.Get(): Configuration key not found. Key: lean-manager-type - Using default value: LocalLeanManager
2022-11-25T15:04:37.7399317Z TRACE:: JobQueue.NextJob(): Selected ParametrizedAlgorithm.dll
2022-11-25T15:04:37.8757698Z TRACE:: Config.GetValue(): scheduled-event-leaky-bucket-capacity - Using default value: 120
2022-11-25T15:04:37.8764057Z TRACE:: Config.GetValue(): scheduled-event-leaky-bucket-time-interval-minutes - Using default value: 1440
2022-11-25T15:04:37.8768633Z TRACE:: Config.GetValue(): scheduled-event-leaky-bucket-refill-amount - Using default value: 18
2022-11-25T15:04:37.8804663Z TRACE:: Config.GetValue(): storage-limit - Using default value: 10737418240
2022-11-25T15:04:37.8811283Z TRACE:: Config.GetValue(): storage-permissions - Using default value: 3
2022-11-25T15:04:37.8819123Z TRACE:: Config.Get(): Configuration key not found. Key: backtest-name - Using default value: local
2022-11-25T15:04:37.8853002Z TRACE:: Config.Get(): Configuration key not found. Key: job-organization-id - Using default value:
2022-11-25T15:04:37.8859221Z TRACE:: Config.Get(): Configuration key not found. Key: python-venv - Using default value:
2022-11-25T15:04:37.8882173Z TRACE:: Config.Get(): Configuration key not found. Key: data-permission-manager - Using default value: DataPermissionManager
2022-11-25T15:04:37.9367442Z TRACE:: AlgorithmManager.CreateTokenBucket(): Initializing LeakyBucket: Capacity: 120 RefillAmount: 18 TimeInterval: 1440
2022-11-25T15:04:37.9400835Z TRACE:: Config.GetValue(): algorithm-manager-time-loop-maximum - Using default value: 20
2022-11-25T15:04:37.9534255Z TRACE:: Engine.Run(): Resource limits '0' CPUs. 2147483647 MB RAM.
2022-11-25T15:04:37.9551149Z TRACE:: TextSubscriptionDataSourceReader.SetCacheSize(): Setting cache size to 71582788 items
2022-11-25T15:04:38.4999911Z TRACE:: Config.GetValue(): algorithm-creation-timeout - Using default value: 90
2022-11-25T15:04:38.5064153Z TRACE:: Loader.TryCreateILAlgorithm(): Loading only the algorithm assembly
2022-11-25T15:04:38.5110230Z TRACE:: Config.GetValue(): ema-fast - Using default value: 100
2022-11-25T15:04:38.5116188Z TRACE:: Config.GetValue(): ema-slow - Using default value: 200
2022-11-25T15:04:38.5249196Z TRACE:: Config.GetValue(): api-data-update-period - Using default value: 1
2022-11-25T15:04:38.6560232Z TRACE:: Loader.TryCreateILAlgorithm(): Loaded ParametrizedAlgorithm
2022-11-25T15:04:38.6858198Z TRACE:: LocalObjectStore.Initialize(): Storage Root: /Storage. StorageFileCount 9999999. StorageLimit 10240MB
2022-11-25T15:04:38.7197877Z TRACE:: HistoryProviderManager.Initialize(): history providers [SubscriptionDataReaderHistoryProvider]
2022-11-25T15:04:38.7259645Z TRACE:: BacktestingSetupHandler.Setup(): Setting up job: UID: 200374, PID: 912831163, Version: 2.5.0.0, Source: WebIDE
2022-11-25T15:04:38.7342927Z TRACE:: Config.Get(): Configuration key not found. Key: security-data-feeds - Using default value:
2022-11-25T15:04:39.0841083Z TRACE:: BaseSetupHandler.SetupCurrencyConversions():
Account Type: Margin

Symbol      Quantity    Conversion = Value in USD
USD: $      100000.00 @       1.00 = $100000.0
-------------------------------------------------
CashBook Total Value:                $100000.0

2022-11-25T15:04:39.0891304Z TRACE:: SetUp Backtesting: User: 200374 ProjectId: 912831163 AlgoId: 1347518945
2022-11-25T15:04:39.0912471Z TRACE:: Dates: Start: 10/07/2013 End: 10/08/2013 Cash: ¤100,000.00 MaximumRuntime: 100.00:00:00 MaxOrders: 2147483647
2022-11-25T15:04:39.0953964Z TRACE:: BacktestingResultHandler(): Sample Period Set: 04.00
2022-11-25T15:04:39.0981582Z TRACE:: Time.TradeableDates(): Security Count: 1
2022-11-25T15:04:39.1067040Z TRACE:: Config.GetValue(): forward-console-messages - Using default value: True
2022-11-25T15:04:39.1115510Z TRACE:: JOB HANDLERS:
         DataFeed:             QuantConnect.Lean.Engine.DataFeeds.FileSystemDataFeed
         Setup:                QuantConnect.Lean.Engine.Setup.BacktestingSetupHandler
         RealTime:             QuantConnect.Lean.Engine.RealTime.BacktestingRealTimeHandler
         Results:              QuantConnect.Lean.Engine.Results.BacktestingResultHandler
         Transactions:         QuantConnect.Lean.Engine.TransactionHandlers.BacktestingTransactionHandler
         Alpha:                QuantConnect.Lean.Engine.Alphas.DefaultAlphaHandler
         Object Store:         QuantConnect.Lean.Engine.Storage.LocalObjectStore
         History Provider:     QuantConnect.Lean.Engine.HistoricalData.HistoryProviderManager
         Brokerage:            QuantConnect.Brokerages.Backtesting.BacktestingBrokerage
         Data Provider:        QuantConnect.Lean.Engine.DataFeeds.DefaultDataProvider

2022-11-25T15:04:39.1704075Z TRACE:: Debug: Launching analysis for 1347518945 with LEAN Engine v2.5.0.0
2022-11-25T15:04:39.1950135Z TRACE:: Event Name "Daily Sampling", scheduled to run.
2022-11-25T15:04:39.1985939Z TRACE:: AlgorithmManager.Run(): Begin DataStream - Start: 10/7/2013 12:00:00 AM Stop: 10/8/2013 11:59:59 PM Time: 10/7/2013 12:00:00 AM Warmup: False
2022-11-25T15:04:39.2701271Z TRACE:: Config.GetValue(): data-feed-workers-count - Using default value: 8
2022-11-25T15:04:39.2715890Z TRACE:: Config.GetValue(): data-feed-max-work-weight - Using default value: 400
2022-11-25T15:04:39.2722741Z TRACE:: WeightedWorkScheduler(): will use 8 workers and MaxWorkWeight is 400
2022-11-25T15:04:39.4354501Z TRACE:: UniverseSelection.AddPendingInternalDataFeeds(): Adding internal benchmark data feed SPY,#0,SPY,Hour,TradeBar,Trade,Adjusted,OpenInterest,Internal
2022-11-25T15:04:39.8316645Z TRACE:: Synchronizer.GetEnumerator(): Exited thread.
2022-11-25T15:04:39.8360508Z TRACE:: AlgorithmManager.Run(): Firing On End Of Algorithm...
2022-11-25T15:04:39.8386196Z TRACE:: Engine.Run(): Exiting Algorithm Manager
2022-11-25T15:04:39.8444890Z TRACE:: StopSafely(): waiting for 'Isolator Thread' thread to stop...
2022-11-25T15:04:39.8456755Z TRACE:: FileSystemDataFeed.Exit(): Start. Setting cancellation token...
2022-11-25T15:04:39.8541874Z TRACE:: FileSystemDataFeed.Exit(): Exit Finished.
2022-11-25T15:04:39.8552627Z TRACE:: DefaultAlphaHandler.Exit(): Exiting...
2022-11-25T15:04:39.8707062Z TRACE:: DefaultAlphaHandler.Exit(): Ended
2022-11-25T15:04:39.8739784Z TRACE:: BacktestingResultHandler.Exit(): starting...
2022-11-25T15:04:39.8751163Z TRACE:: BacktestingResultHandler.Exit(): Saving logs...
2022-11-25T15:04:39.8764845Z TRACE:: Debug: Algorithm Id:(1347518945) completed in 0.73 seconds at 2k data points per second. Processing total of 1,582 data points.
2022-11-25T15:04:39.8918962Z TRACE:: Debug: Your log was successfully created and can be retrieved from: /Results/1347518945-log.txt
2022-11-25T15:04:39.8920058Z TRACE:: StopSafely(): waiting for 'Result Thread' thread to stop...
2022-11-25T15:04:39.8934249Z TRACE:: BacktestingResultHandler.Run(): Ending Thread...
2022-11-25T15:04:40.3103850Z TRACE::
STATISTICS:: Total Trades 0
STATISTICS:: Average Win 0%
STATISTICS:: Average Loss 0%
STATISTICS:: Compounding Annual Return 0%
STATISTICS:: Drawdown 0%
STATISTICS:: Expectancy 0
STATISTICS:: Net Profit 0%
STATISTICS:: Sharpe Ratio 0
STATISTICS:: Probabilistic Sharpe Ratio 0%
STATISTICS:: Loss Rate 0%
STATISTICS:: Win Rate 0%
STATISTICS:: Profit-Loss Ratio 0
STATISTICS:: Alpha 0
STATISTICS:: Beta 0
STATISTICS:: Annual Standard Deviation 0
STATISTICS:: Annual Variance 0
STATISTICS:: Information Ratio 0
STATISTICS:: Tracking Error 0
STATISTICS:: Treynor Ratio 0
STATISTICS:: Total Fees $0.00
STATISTICS:: Estimated Strategy Capacity $0
STATISTICS:: Lowest Capacity Asset
STATISTICS:: Fitness Score 0
STATISTICS:: Kelly Criterion Estimate 0
STATISTICS:: Kelly Criterion Probability Value 0
STATISTICS:: Sortino Ratio 79228162514264337593543950335
STATISTICS:: Return Over Maximum Drawdown 79228162514264337593543950335
STATISTICS:: Portfolio Turnover 0
STATISTICS:: Total Insights Generated 0
STATISTICS:: Total Insights Closed 0
STATISTICS:: Total Insights Analysis Completed 0
STATISTICS:: Long Insight Count 0
STATISTICS:: Short Insight Count 0
STATISTICS:: Long/Short Ratio 100%
STATISTICS:: Estimated Monthly Alpha Value $0
STATISTICS:: Total Accumulated Estimated Alpha Value $0
STATISTICS:: Mean Population Estimated Insight Value $0
STATISTICS:: Mean Population Direction 0%
STATISTICS:: Mean Population Magnitude 0%
STATISTICS:: Rolling Averaged Population Direction 0%
STATISTICS:: Rolling Averaged Population Magnitude 0%
STATISTICS:: OrderListHash d41d8cd98f00b204e9800998ecf8427e
2022-11-25T15:04:40.3190085Z TRACE:: BacktestingResultHandler.SendAnalysisResult(): Processed final packet
2022-11-25T15:04:40.3239320Z TRACE:: Engine.Run(): Disconnecting from brokerage...
2022-11-25T15:04:40.3270225Z TRACE:: Engine.Run(): Disposing of setup handler...
2022-11-25T15:04:40.3402854Z TRACE:: Engine.Main(): Analysis Completed and Results Posted.
2022-11-25T15:04:40.3532236Z TRACE:: StopSafely(): waiting for '' thread to stop...
2022-11-25T15:04:40.3767707Z TRACE:: DataMonitor.GenerateReport():
DATA USAGE:: Total data requests 5
DATA USAGE:: Succeeded data requests 5
DATA USAGE:: Failed data requests 0
DATA USAGE:: Failed data requests percentage 0%
DATA USAGE:: Total universe data requests 0
DATA USAGE:: Succeeded universe data requests 0
DATA USAGE:: Failed universe data requests 0
DATA USAGE:: Failed universe data requests percentage 0%
2022-11-25T15:04:40.4603793Z TRACE:: Engine.Main(): Packet removed from queue: 1347518945
2022-11-25T15:04:40.4657487Z TRACE:: LeanEngineSystemHandlers.Dispose(): start...
2022-11-25T15:04:40.4712196Z TRACE:: LeanEngineSystemHandlers.Dispose(): Disposed of system handlers.
2022-11-25T15:04:40.4735564Z TRACE:: LeanEngineAlgorithmHandlers.Dispose(): start...
2022-11-25T15:04:40.4784052Z TRACE:: LeanEngineAlgorithmHandlers.Dispose(): Disposed of algorithm handlers.
        """)

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    def run_image_for_estimate(image: DockerImage, **kwargs) -> bool:
        results_path = next(key for key in kwargs["volumes"].keys() if kwargs["volumes"][key]["bind"] == "/Results")
        log_file = Path(results_path) / "log.txt"
        with log_file.open("w+", encoding="utf-8") as logs:
            logs.write("""
MSBuild version 17.3.2+561848881 for .NET
  Determining projects to restore...
  Restored /LeanCLI/ParametrizedAlgorithm.csproj (in 235 ms).
  ParametrizedAlgorithm -> /Compile/bin/ParametrizedAlgorithm.dll

Build succeeded.
    0 Warning(s)
    0 Error(s)

Time Elapsed 00:00:04.15
20221125 19:01:15.308 TRACE:: Config.GetValue(): debug-mode - Using default value: False
20221125 19:01:15.310 TRACE:: Config.Get(): Configuration key not found. Key: plugin-directory - Using default value:
20221125 19:01:15.315 TRACE:: Config.Get(): Configuration key not found. Key: composer-dll-directory - Using default value:
20221125 19:01:15.319 TRACE:: Composer(): Loading Assemblies from /Lean/Optimizer.Launcher/bin/Debug/
20221125 19:01:15.397 TRACE:: Config.Get(): Configuration key not found. Key: log-handler - Using default value: CompositeLogHandler
20221125 19:01:15.538 TRACE:: Config.GetValue(): optimization-update-interval - Using default value: 10
20221125 19:01:15.553 TRACE:: Config.Get(): Configuration key not found. Key: lean-binaries-location - Using default value: /Lean/Optimizer.Launcher/bin/Debug/../../../Launcher/bin/Debug/QuantConnect.Lean.Launcher.exe
20221125 19:01:15.554 TRACE:: Config.Get(): Configuration key not found. Key: algorithm-type-name - Using default value:
20221125 19:01:15.554 TRACE:: Config.Get(): Configuration key not found. Key: algorithm-language - Using default value:
20221125 19:01:15.555 TRACE:: Config.Get(): Configuration key not found. Key: algorithm-location - Using default value:
20221125 19:01:15.562 TRACE:: Optimization estimate: 50
            """)
        return True

    docker_manager = mock.Mock()
    docker_manager.run_image.side_effect = run_image_for_estimate
    container.initialize(docker_manager=docker_manager)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    result = CliRunner().invoke(lean, ["optimize", "Python Project", "--estimate",
                                       "--max-concurrent-backtests", max_concurrent_backtests])

    assert result.exit_code == 0
    assert "Total backtests: 50" in result.output
    assert f"Estimated runtime: {expected_runtime}" in result.output

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert any(command == 'dotnet QuantConnect.Optimizer.Launcher.dll --estimate' for command in kwargs["commands"])


def test_optimize_runs_lean_container_with_extra_docker_config() -> None:
    import docker.types

    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    docker_manager.run_image.side_effect = run_image
    container.initialize(docker_manager=docker_manager)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project",
                                       "--extra-docker-config",
                                       '{"device_requests": [{"count": -1, "capabilities": [["compute"]]}],'
                                       '"volumes": {"extra/path": {"bind": "/extra/path", "mode": "rw"}}}'])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == ENGINE_IMAGE

    assert "device_requests" in kwargs
    assert kwargs["device_requests"] == [docker.types.DeviceRequest(count=-1, capabilities=[["compute"]])]

    assert "volumes" in kwargs
    volumes = kwargs["volumes"]
    assert "extra/path" in volumes
    assert volumes["extra/path"] == {"bind": "/extra/path", "mode": "rw"}


def test_optimize_used_data_downloader_specified_with_data_provider_option() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.MagicMock()
    docker_manager.run_image.side_effect = run_image
    container.initialize(docker_manager=docker_manager)
    container.optimizer_config_manager = _get_optimizer_config_manager_mock()

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    with mock.patch.object(ModuleManager, "install_module"):
        result = CliRunner().invoke(lean, ["optimize", "Python Project",
                                           "--data-provider", "Polygon",
                                           "--polygon-api-key", "my-key"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args
    mounts = kwargs["mounts"]

    lean_config_filename = next(mount["Source"] for mount in mounts if mount["Target"] == "/Lean/Launcher/bin/Debug/config.json")
    assert lean_config_filename is not None

    config = json.loads(Path(lean_config_filename).read_text(encoding="utf-8"))
    assert "data-downloader" in config
    assert config["data-downloader"] == "QuantConnect.Polygon.PolygonDataDownloader"
