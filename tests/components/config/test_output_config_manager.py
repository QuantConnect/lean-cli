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

from pathlib import Path
from unittest import mock

import pytest

from lean.components.config.lean_config_manager import LeanConfigManager
from lean.components.config.output_config_manager import OutputConfigManager
from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.util.xml_manager import XMLManager
from tests.test_helpers import create_fake_lean_cli_directory


def _create_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _create_output_config_manager() -> OutputConfigManager:
    return OutputConfigManager(LeanConfigManager(mock.Mock(), mock.Mock(), ProjectConfigManager(XMLManager())))


def test_get_backtest_id_returns_id_prefixed_by_1() -> None:
    create_fake_lean_cli_directory()

    directory = _create_directory(Path.cwd() / "Python Project" / "backtests" / "2021-01-01_00-00-00")

    manager = _create_output_config_manager()

    backtest_id = str(manager.get_backtest_id(directory))
    assert len(backtest_id) == 10
    assert backtest_id[0] == "1"


def test_get_backtest_id_returns_different_ids_for_different_directories() -> None:
    create_fake_lean_cli_directory()

    directory_1 = _create_directory(Path.cwd() / "Python Project" / "backtests" / "2021-01-01_00-00-00")
    directory_2 = _create_directory(Path.cwd() / "Python Project" / "backtests" / "2021-01-02_00-00-00")

    manager = _create_output_config_manager()

    assert manager.get_backtest_id(directory_1) != manager.get_backtest_id(directory_2)


def test_get_backtest_id_returns_same_id_for_same_directory() -> None:
    create_fake_lean_cli_directory()

    directory = _create_directory(Path.cwd() / "Python Project" / "backtests" / "2021-01-01_00-00-00")

    manager = _create_output_config_manager()

    assert manager.get_backtest_id(directory) == manager.get_backtest_id(directory)


@pytest.mark.parametrize("path", ["backtests/2021-01-01_00-00-00", "optimizations/2021-01-01_00-00-00/backtest"])
def test_get_backtest_by_id_finds_backtest_with_given_id(path: str) -> None:
    create_fake_lean_cli_directory()

    directory = _create_directory(Path.cwd() / "Python Project" / path)

    manager = _create_output_config_manager()

    backtest_id = manager.get_backtest_id(directory)
    assert manager.get_backtest_by_id(backtest_id) == directory


def test_get_backtest_by_id_raises_when_backtest_with_given_id_does_not_exist() -> None:
    create_fake_lean_cli_directory()

    manager = _create_output_config_manager()

    with pytest.raises(Exception):
        manager.get_backtest_by_id(123)


def test_get_optimization_id_returns_id_prefixed_by_2() -> None:
    create_fake_lean_cli_directory()

    directory = _create_directory(Path.cwd() / "Python Project" / "optimizations" / "2021-01-01_00-00-00")

    manager = _create_output_config_manager()

    optimization_id = str(manager.get_optimization_id(directory))
    assert len(optimization_id) == 10
    assert optimization_id[0] == "2"


def test_get_optimization_id_returns_different_ids_for_different_directories() -> None:
    create_fake_lean_cli_directory()

    directory_1 = _create_directory(Path.cwd() / "Python Project" / "optimizations" / "2021-01-01_00-00-00")
    directory_2 = _create_directory(Path.cwd() / "Python Project" / "optimizations" / "2021-01-02_00-00-00")

    manager = _create_output_config_manager()

    assert manager.get_optimization_id(directory_1) != manager.get_optimization_id(directory_2)


def test_get_optimization_id_returns_same_id_for_same_directory() -> None:
    create_fake_lean_cli_directory()

    directory = _create_directory(Path.cwd() / "Python Project" / "optimizations" / "2021-01-01_00-00-00")

    manager = _create_output_config_manager()

    assert manager.get_optimization_id(directory) == manager.get_optimization_id(directory)


def test_get_optimization_by_id_finds_optimization_with_given_id() -> None:
    create_fake_lean_cli_directory()

    directory = _create_directory(Path.cwd() / "Python Project" / "optimizations" / "2021-01-01_00-00-00")

    manager = _create_output_config_manager()

    optimization_id = manager.get_optimization_id(directory)
    assert manager.get_optimization_by_id(optimization_id) == directory


def test_get_optimization_by_id_raises_when_optimization_with_given_id_does_not_exist() -> None:
    create_fake_lean_cli_directory()

    manager = _create_output_config_manager()

    with pytest.raises(Exception):
        manager.get_optimization_by_id(123)


def test_get_live_deployment_id_returns_id_prefixed_by_3() -> None:
    create_fake_lean_cli_directory()

    directory = _create_directory(Path.cwd() / "Python Project" / "live" / "2021-01-01_00-00-00")

    manager = _create_output_config_manager()

    live_deployment_id = str(manager.get_live_deployment_id(directory))
    assert len(live_deployment_id) == 10
    assert live_deployment_id[0] == "3"


def test_get_live_deployment_id_returns_different_ids_for_different_directories() -> None:
    create_fake_lean_cli_directory()

    directory_1 = _create_directory(Path.cwd() / "Python Project" / "live" / "2021-01-01_00-00-00")
    directory_2 = _create_directory(Path.cwd() / "Python Project" / "live" / "2021-01-02_00-00-00")

    manager = _create_output_config_manager()

    assert manager.get_live_deployment_id(directory_1) != manager.get_live_deployment_id(directory_2)


def test_get_live_deployment_id_returns_same_id_for_same_directory() -> None:
    create_fake_lean_cli_directory()

    directory = _create_directory(Path.cwd() / "Python Project" / "live" / "2021-01-01_00-00-00")

    manager = _create_output_config_manager()

    assert manager.get_live_deployment_id(directory) == manager.get_live_deployment_id(directory)


def test_get_live_deployment_by_id_finds_live_deployment_with_given_id() -> None:
    create_fake_lean_cli_directory()

    directory = _create_directory(Path.cwd() / "Python Project" / "live" / "2021-01-01_00-00-00")

    manager = _create_output_config_manager()

    live_deployment_id = manager.get_live_deployment_id(directory)
    assert manager.get_live_deployment_by_id(live_deployment_id) == directory


def test_get_live_deployment_by_id_raises_when_live_deployment_with_given_id_does_not_exist() -> None:
    create_fake_lean_cli_directory()

    manager = _create_output_config_manager()

    with pytest.raises(Exception):
        manager.get_live_deployment_by_id(123)
