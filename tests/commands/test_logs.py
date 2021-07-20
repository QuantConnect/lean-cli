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
from tests.test_helpers import create_fake_lean_cli_directory


BACKTEST_SAMPLE_OLD_LOG = "oldbacktest\n"
BACKTEST_SAMPLE_NEW_LOG = "1\n2\nnewbacktest\n"
OPTIMIZATION_SAMPLE_LOG="optimization\n"
LIVE_SAMPLE_LOG="live\n"
UNKNOWN_MODE_ERROR= "Error: no such option: --wrongmode"
@pytest.fixture(autouse=True)
def update_manager_mock() -> mock.Mock:
    """A pytest fixture which mocks the update manager before every test."""
    update_manager = mock.Mock()
    container.update_manager.override(providers.Object(update_manager))
    return update_manager

def _create_add_text(file_data):
    file_data[0].parent.mkdir(parents=True, exist_ok=True)
    with file_data[0].open("w+", encoding="utf-8") as file:
        file.write(file_data[1])


@pytest.fixture(autouse=True)
def setup_log_results() -> None:
    """A pytest fixture which creates a backtest results file before every test."""
    create_fake_lean_cli_directory()
    logs_backtest_1_path_data_old = [Path.cwd() / "Python Project 1" / "backtests" / "2020-01-01_00-00-00" /"log.txt", BACKTEST_SAMPLE_OLD_LOG]
    logs_backtest_1_path_data_new = [Path.cwd() / "Python Project 1" / "backtests" / "2020-01-02_00-00-00" / "log.txt",BACKTEST_SAMPLE_NEW_LOG]
    logs_backtest_path_data_old = [Path.cwd() / "Python Project" / "backtests" / "2020-01-01_00-00-00" /"log.txt", BACKTEST_SAMPLE_OLD_LOG]
    logs_backtest_path_data_new = [Path.cwd() / "Python Project" / "backtests" / "2020-01-02_00-00-00" / "log.txt",BACKTEST_SAMPLE_NEW_LOG]
    logs_live_path_data = [Path.cwd() / "Python Project" / "live" / "2020-01-01_00-00-00" / "log.txt",LIVE_SAMPLE_LOG]
    list(map(_create_add_text,[logs_backtest_1_path_data_old,logs_backtest_1_path_data_new,logs_backtest_path_data_old,logs_backtest_path_data_new,logs_live_path_data]))
    return True
    

def test_logs_no_mode() -> None:
    result = CliRunner().invoke(lean, ["logs"])

    assert result.exit_code == 0
    assert "Defaulting to backtest." in result.output

def test_logs_mode_not_present() -> None:
    result = CliRunner().invoke(lean, ["logs","--optimization"])

    assert result.exit_code == 1
    assert type(result.exception) == ValueError

def test_logs_no_project_latest() -> None:
    result = CliRunner().invoke(lean,["logs","--backtest"],input="\n")

    assert result.exit_code == 0
    assert BACKTEST_SAMPLE_NEW_LOG in result.output

def test_logs_project_latest() -> None:
    result = CliRunner().invoke(lean,["logs","--backtest","--project",'Python Project 1'],input="\n")

    assert result.exit_code == 0
    assert BACKTEST_SAMPLE_NEW_LOG in result.output

def test_logs_path()->None:
    result = CliRunner().invoke(lean,["logs","--project_path",'Python Project/live/2020-01-01_00-00-00'],input="\n")

    assert LIVE_SAMPLE_LOG in result.output

def test_logs_unknown_mode() -> None:
    result = CliRunner().invoke(lean,["--wrongmode"])
    assert result.exit_code==2
    assert UNKNOWN_MODE_ERROR in result.output





