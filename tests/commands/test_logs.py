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
from typing import Optional, List

import pytest
from click.testing import CliRunner

from lean.commands import lean
from tests.test_helpers import create_fake_lean_cli_directory


def _prepare_directories() -> None:
    create_fake_lean_cli_directory()

    for project in ["Python Project", "CSharp Project"]:
        for mode in ["backtests", "live", "optimizations"]:
            output_directory = Path.cwd() / project / mode / "2020-01-01_00-00-00"
            output_directory.mkdir(parents=True)

            log_file = output_directory / "log.txt"
            with log_file.open("w+") as file:
                file.write(f"{project}/{mode}")


@pytest.mark.parametrize("mode,expected_logs", [(None, "CSharp Project/backtests"),
                                                ("--backtest", "CSharp Project/backtests"),
                                                ("--live", "CSharp Project/live"),
                                                ("--optimization", "CSharp Project/optimizations")])
def test_logs_shows_most_recent_logs_for_each_mode(mode: Optional[str], expected_logs: str) -> None:
    _prepare_directories()

    arguments = ["logs"]
    if mode is not None:
        arguments.append(mode)

    result = CliRunner().invoke(lean, arguments)

    assert result.exit_code == 0

    assert result.output.strip() == expected_logs


@pytest.mark.parametrize("mode,expected_logs", [(None, "Python Project/backtests"),
                                                ("--backtest", "Python Project/backtests"),
                                                ("--live", "Python Project/live"),
                                                ("--optimization", "Python Project/optimizations")])
def test_logs_shows_most_recent_logs_for_project(mode: Optional[str], expected_logs: str) -> None:
    _prepare_directories()

    arguments = ["logs", "--project", "Python Project"]
    if mode is not None:
        arguments.append(mode)

    result = CliRunner().invoke(lean, arguments)

    assert result.exit_code == 0

    assert result.output.strip() == expected_logs


@pytest.mark.parametrize("arguments", [["--backtest", "--live"],
                                       ["--backtest", "--optimization"],
                                       ["--live", "--optimization"],
                                       ["--backtest", "--live", "--optimization"]])
def test_logs_aborts_when_more_than_one_mode_given(arguments: List[str]) -> None:
    _prepare_directories()

    result = CliRunner().invoke(lean, ["logs", *arguments])

    assert result.exit_code != 0
