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
from click.testing import CliRunner
from dependency_injector import providers

from lean.commands import lean
from lean.container import container
from lean.models.config import DebuggingMethod
from tests.test_helpers import create_fake_lean_cli_project


def test_backtest_calls_lean_runner_with_correct_algorithm_file() -> None:
    create_fake_lean_cli_project()

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with("backtesting",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 "latest",
                                                 None)


def test_backtest_calls_lean_runner_with_default_output_directory() -> None:
    create_fake_lean_cli_project()

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once()
    args, _ = lean_runner.run_lean.call_args

    # This will raise an error if the output directory is not relative to Python Project/backtests
    args[2].relative_to(Path("Python Project/backtests").resolve())


def test_backtest_calls_lean_runner_with_custom_output_directory() -> None:
    create_fake_lean_cli_project()

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--output", "Python Project/custom-backtests"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once()
    args, _ = lean_runner.run_lean.call_args

    # This will raise an error if the output directory is not relative to Python Project/custom-backtests
    args[2].relative_to(Path("Python Project/custom-backtests").resolve())


def test_backtest_aborts_when_project_does_not_exist() -> None:
    create_fake_lean_cli_project()

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "This Project Does Not Exist"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


def test_backtest_aborts_when_project_does_not_contain_algorithm_file() -> None:
    create_fake_lean_cli_project()

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "data"])

    assert result.exit_code != 0

    lean_runner.run_lean.assert_not_called()


def test_backtest_forces_update_when_update_option_given() -> None:
    create_fake_lean_cli_project()

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--update"])

    assert result.exit_code == 0

    lean_runner.force_update.assert_called_once()
    lean_runner.run_lean.assert_called_once_with("backtesting",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 "latest",
                                                 None)


def test_backtest_passes_custom_version_to_lean_runner() -> None:
    create_fake_lean_cli_project()

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project", "--version", "3"])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with("backtesting",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 "3",
                                                 None)


@pytest.mark.parametrize("value,debugging_method", [("pycharm", DebuggingMethod.PyCharm),
                                                    ("PyCharm", DebuggingMethod.PyCharm),
                                                    ("ptvsd", DebuggingMethod.PTVSD),
                                                    ("PTVSD", DebuggingMethod.PTVSD),
                                                    ("mono", DebuggingMethod.Mono),
                                                    ("Mono", DebuggingMethod.Mono)])
def test_backtest_passes_correct_debugging_method_to_lean_runner(value: str, debugging_method: DebuggingMethod) -> None:
    create_fake_lean_cli_project()

    lean_runner = mock.Mock()
    container.lean_runner.override(providers.Object(lean_runner))

    result = CliRunner().invoke(lean, ["backtest", "Python Project/main.py", "--debug", value])

    assert result.exit_code == 0

    lean_runner.run_lean.assert_called_once_with("backtesting",
                                                 Path("Python Project/main.py").resolve(),
                                                 mock.ANY,
                                                 "latest",
                                                 debugging_method)
