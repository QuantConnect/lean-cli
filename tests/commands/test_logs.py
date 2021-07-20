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
from tests.test_helpers import create_fake_lean_cli_directory

ENGINE_IMAGE = DockerImage.parse(DEFAULT_ENGINE_IMAGE)


@pytest.fixture(autouse=True)
def update_manager_mock() -> mock.Mock:
    """A pytest fixture which mocks the update manager before every test."""
    update_manager = mock.Mock()
    container.update_manager.override(providers.Object(update_manager))
    return update_manager

def _create_add_text(file):
    file.parent.mkdir(parents=True, exist_ok=True)
    with file.open("w+", encoding="utf-8") as file:
        file.write("\n")


@pytest.fixture(autouse=True)
def setup_log_results() -> None:
    """A pytest fixture which creates a backtest results file before every test."""
    create_fake_lean_cli_directory()

    logs_backtest_path = Path.cwd() / "Python Project" / "backtests" / "2020-01-01_00-00-00" / "log.txt"
    logs_live_path = Path.cwd() / "Python Project" / "live" / "2020-01-01_00-00-00" / "log.txt"
    logs_optimization_path = Path.cwd() / "Python Project" / "optimizations" / "2020-01-01_00-00-00" / "log.txt"
    list(map(_create_add_text,[logs_backtest_path,logs_live_path,logs_optimization_path]))
    return True
    

def test_logs_live_runs_lean_container() -> None:
    result = CliRunner().invoke(lean, ["logs",
                                       "--backtest",
                                       ],input="\n")

    assert result.exit_code == 0

