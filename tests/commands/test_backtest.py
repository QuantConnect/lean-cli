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
from typing import Optional
from unittest import mock

import pytest
from click.testing import CliRunner
from dependency_injector import providers

from lean.commands import lean
from lean.constants import DEFAULT_ENGINE_IMAGE
from lean.container import container
from lean.models.config import DebuggingMethod
from lean.models.docker import DockerImage
from tests.test_helpers import create_fake_lean_cli_directory

ENGINE_IMAGE = DockerImage.parse(DEFAULT_ENGINE_IMAGE)


@pytest.fixture(autouse=True)
def update_manager_mock() -> mock.Mock:
    """A pytest fixture which mocks the update manager before every test."""
    update_manager = mock.Mock()
    container.update_manager.override(providers.Object(update_manager))
    return update_manager


def test_backtest_calls_lean_runner_with_correct_algorithm_file() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with("backtesting",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 ENGINE_IMAGE,
                                                 None)


def test_backtest_calls_lean_runner_with_default_output_directory() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once()
    args, _ = lean_runner.run_lean.call_args

    # This will raise an error if the output directory is not relative to Python Project/backtests
    args[2].relative_to(Path("Python Project/backtests").resolve())


def test_backtest_calls_lean_runner_with_custom_output_directory() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--output", "Python Project/custom"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once()
    args, _ = lean_runner.run_lean.call_args

    # This will raise an error if the output directory is not relative to Python Project/custom-backtests
    args[2].relative_to(Path("Python Project/custom").resolve())


def test_backtest_aborts_when_project_does_not_exist() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "This Project Does Not Exist"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


def test_backtest_aborts_when_project_does_not_contain_algorithm_file() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "data"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


def test_backtest_forces_update_when_update_option_given() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--update"])

    assert result.exit_code == 0

    docker_manager.pull_image.assert_called_once_with(ENGINE_IMAGE)
    lean_runner.run_lean.assert_called_once_with("backtesting",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 ENGINE_IMAGE,
                                                 None)


def test_backtest_passes_custom_image_to_lean_runner_when_set_in_config() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    container.cli_config_manager().engine_image.set_value("custom/lean:123")

    result = CliRunner().invoke(lean, ["backtest", "Python Project"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with("backtesting",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 DockerImage(name="custom/lean", tag="123"),
                                                 None)


def test_backtest_passes_custom_image_to_lean_runner_when_given_as_option() -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    container.cli_config_manager().engine_image.set_value("custom/lean:123")

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--image", "custom/lean:456"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with("backtesting",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 DockerImage(name="custom/lean", tag="456"),
                                                 None)


@pytest.mark.parametrize("value,debugging_method", [("pycharm", DebuggingMethod.PyCharm),
                                                    ("PyCharm", DebuggingMethod.PyCharm),
                                                    ("ptvsd", DebuggingMethod.PTVSD),
                                                    ("PTVSD", DebuggingMethod.PTVSD),
                                                    ("mono", DebuggingMethod.Mono),
                                                    ("Mono", DebuggingMethod.Mono)])
def test_backtest_passes_correct_debugging_method_to_lean_runner(value: str, debugging_method: DebuggingMethod) -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project/main.py", "--debug", value])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with("backtesting",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 ENGINE_IMAGE,
                                                 debugging_method)


@pytest.mark.parametrize("image_option,update_flag,update_check_expected", [(None, True, False),
                                                                            (None, False, True),
                                                                            ("custom/lean:3", True, False),
                                                                            ("custom/lean:3", False, False),
                                                                            (DEFAULT_ENGINE_IMAGE, True, False),
                                                                            (DEFAULT_ENGINE_IMAGE, False, True)])
def test_backtest_checks_for_updates(update_manager_mock: mock.Mock,
                                     image_option: Optional[str],
                                     update_flag: bool,
                                     update_check_expected: bool) -> None:
    create_fake_lean_cli_directory()

    docker_manager = mock.Mock()
    container.docker_manager.override(providers.Object(docker_manager))

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    options = []
    if image_option is not None:
        options.extend(["--image", image_option])
    if update_flag:
        options.extend(["--update"])

    result = CliRunner().invoke(lean, ["backtest", "Python Project", *options])

    assert result.exit_code == 0

    if update_check_expected:
        update_manager_mock.warn_if_docker_image_outdated.assert_called_once_with(ENGINE_IMAGE)
    else:
        update_manager_mock.warn_if_docker_image_outdated.assert_not_called()
