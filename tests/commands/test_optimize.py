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
from typing import Optional
from unittest import mock

import pytest
from click.testing import CliRunner
from dependency_injector import providers

from lean.commands import lean
from lean.components.config.storage import Storage
from lean.constants import DEFAULT_ENGINE_IMAGE
from lean.container import container
from lean.models.docker import DockerImage
from lean.models.optimizer import (OptimizationConstraint, OptimizationExtremum, OptimizationParameter,
                                   OptimizationTarget)
from tests.test_helpers import create_fake_lean_cli_directory

ENGINE_IMAGE = DockerImage.parse(DEFAULT_ENGINE_IMAGE)


@pytest.fixture(autouse=True)
def update_manager_mock() -> mock.Mock:
    """A pytest fixture which mocks the update manager before every test."""
    update_manager = mock.Mock()
    container.update_manager.override(providers.Object(update_manager))
    return update_manager


@pytest.fixture(autouse=True)
def optimizer_config_manager_mock() -> mock.Mock:
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
        OptimizationConstraint(**{"target": "TotalPerformance.PortfolioStatistics.Drawdown",
                                  "operator": "less",
                                  "target-value": "0.25"})
    ]

    container.optimizer_config_manager.override(providers.Object(optimizer_config_manager))
    return optimizer_config_manager


def test_optimize_runs_lean_container() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == ENGINE_IMAGE


def test_optimize_runs_optimizer() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert kwargs["working_dir"] == "/Lean/Optimizer.Launcher/bin/Debug"
    assert kwargs["entrypoint"][0] == "dotnet"
    assert kwargs["entrypoint"][1] == "QuantConnect.Optimizer.Launcher.dll"


def test_optimize_mounts_optimizer_config() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert any([mount["Target"] == "/Lean/Optimizer.Launcher/bin/Debug/config.json" for mount in kwargs["mounts"]])


def test_optimize_mounts_lean_config() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert any([mount["Target"] == "/Lean/Launcher/bin/Debug/config.json" for mount in kwargs["mounts"]])


def test_optimize_mounts_data_directory() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

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

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

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
    container.docker_manager.override(providers.Object(docker_manager))

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project", "--output", "output"])

    assert result.exit_code == 0

    assert (Path.cwd() / "output").is_dir()


def test_optimize_creates_correct_config_from_optimizer_config_manager_output() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

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

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

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

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

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

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {})

    result = CliRunner().invoke(lean, ["optimize", "Python Project"])

    assert result.exit_code != 0

    docker_manager.run_image.assert_not_called()


def test_optimize_aborts_when_run_image_fails() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    docker_manager.run_image.return_value = False
    container.docker_manager.override(providers.Object(docker_manager))

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project"])

    assert result.exit_code != 0

    docker_manager.run_image.assert_called_once()


def test_optimize_forces_update_when_update_option_given() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project", "--update"])

    assert result.exit_code == 0

    docker_manager.pull_image.assert_called_once_with(ENGINE_IMAGE)
    docker_manager.run_image.assert_called_once()


def test_optimize_runs_custom_image_when_set_in_config() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    container.cli_config_manager().engine_image.set_value("custom/lean:123")

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == DockerImage(name="custom/lean", tag="123")


def test_optimize_runs_custom_image_when_given_as_option() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    container.cli_config_manager().engine_image.set_value("custom/lean:123")

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    result = CliRunner().invoke(lean, ["optimize", "Python Project", "--image", "custom/lean:456"])

    assert result.exit_code == 0

    docker_manager.run_image.assert_called_once()
    args, kwargs = docker_manager.run_image.call_args

    assert args[0] == DockerImage(name="custom/lean", tag="456")


@pytest.mark.parametrize("image_option,update_flag,update_check_expected", [(None, True, False),
                                                                            (None, False, True),
                                                                            ("custom/lean:3", True, False),
                                                                            ("custom/lean:3", False, False),
                                                                            (DEFAULT_ENGINE_IMAGE, True, False),
                                                                            (DEFAULT_ENGINE_IMAGE, False, True)])
def test_optimize_checks_for_updates(update_manager_mock: mock.Mock,
                                     image_option: Optional[str],
                                     update_flag: bool,
                                     update_check_expected: bool) -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    Storage(str(Path.cwd() / "Python Project" / "config.json")).set("parameters", {"param1": "1"})

    options = []
    if image_option is not None:
        options.extend(["--image", image_option])
    if update_flag:
        options.extend(["--update"])

    result = CliRunner().invoke(lean, ["optimize", "Python Project", *options])

    assert result.exit_code == 0

    if update_check_expected:
        update_manager_mock.warn_if_docker_image_outdated.assert_called_once_with(ENGINE_IMAGE)
    else:
        update_manager_mock.warn_if_docker_image_outdated.assert_not_called()
