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

from datetime import datetime
from unittest import mock

from click.testing import CliRunner

import pytest
from lean.commands import lean
from lean.container import container
from lean.components import reserved_names
from lean.models.api import QCBacktest
from tests.test_helpers import create_api_project, create_fake_lean_cli_directory
from tests.conftest import initialize_container


def create_api_backtest() -> QCBacktest:
    return QCBacktest(
        backtestId="123",
        projectId=1,
        status="Completed.",
        name="Backtest name",
        created=datetime.now(),
        completed=True,
        progress=1.0,
        runtimeStatistics={},
        statistics={}
    )


def test_cloud_backtest_runs_project_by_id() -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")
    backtest = create_api_backtest()

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [project]

    cloud_runner = mock.Mock()
    cloud_runner.run_backtest.return_value = backtest
    initialize_container(api_client_to_use=api_client, cloud_runner_to_use=cloud_runner)

    result = CliRunner().invoke(lean, ["cloud", "backtest", "1"])

    assert result.exit_code == 0

    cloud_runner.run_backtest.assert_called_once_with(project, mock.ANY)


def test_cloud_backtest_runs_project_by_name() -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")
    backtest = create_api_backtest()

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [project]

    cloud_runner = mock.Mock()
    cloud_runner.run_backtest.return_value = backtest
    initialize_container(api_client_to_use=api_client, cloud_runner_to_use=cloud_runner)

    result = CliRunner().invoke(lean, ["cloud", "backtest", "My Project"])

    assert result.exit_code == 0

    cloud_runner.run_backtest.assert_called_once_with(project, mock.ANY)


def test_cloud_backtest_uses_given_name() -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")
    backtest = create_api_backtest()

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [project]
    cloud_runner = mock.Mock()
    cloud_runner.run_backtest.return_value = backtest

    initialize_container(api_client_to_use=api_client, cloud_runner_to_use=cloud_runner)

    result = CliRunner().invoke(lean, ["cloud", "backtest", "My Project", "--name", "My Name"])

    assert result.exit_code == 0

    cloud_runner.run_backtest.assert_called_once()
    args, kwargs = cloud_runner.run_backtest.call_args

    assert args[1] == "My Name"

@pytest.mark.parametrize("name", reserved_names)
def test_cloud_backtest_uses_generated_name_when_given_is_invalid(name) -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")
    backtest = create_api_backtest()

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [project]
    cloud_runner = mock.Mock()
    cloud_runner.run_backtest.return_value = backtest

    initialize_container(api_client_to_use=api_client, cloud_runner_to_use=cloud_runner)

    result = CliRunner().invoke(lean, ["cloud", "backtest", "My Project", "--name", name])

    assert result.exit_code == 0

    cloud_runner.run_backtest.assert_called_once()
    args, kwargs = cloud_runner.run_backtest.call_args

    assert args[1] != name

def test_cloud_backtest_logs_statistics() -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")
    backtest = create_api_backtest()

    backtest.statistics = {
        "stat1": "1.0",
        "stat2": "-1.0",
        "stat3": "0.0"
    }

    backtest.runtimeStatistics = {
        "stat3": "1.0",
        "stat4": "-1.0",
        "stat5": "0.0"
    }

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [project]

    cloud_runner = mock.Mock()
    cloud_runner.run_backtest.return_value = backtest

    initialize_container(api_client_to_use=api_client, cloud_runner_to_use=cloud_runner)

    result = CliRunner().invoke(lean, ["cloud", "backtest", "My Project"])

    assert result.exit_code == 0

    for i in range(1, 6):
        assert f"stat{i}" in result.output


@mock.patch("webbrowser.open")
def test_cloud_backtest_opens_browser_when_open_option_given(open) -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")
    backtest = create_api_backtest()

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [project]

    cloud_runner = mock.Mock()
    cloud_runner.run_backtest.return_value = backtest
    initialize_container(api_client_to_use=api_client, cloud_runner_to_use=cloud_runner)

    result = CliRunner().invoke(lean, ["cloud", "backtest", "My Project", "--open"])

    assert result.exit_code == 0

    open.assert_called_once_with(backtest.get_url())


@mock.patch("webbrowser.open")
def test_cloud_backtest_does_not_open_browser_when_init_error_happens(open) -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")
    backtest = create_api_backtest()
    backtest.error = "During the algorithm initialization, the following exception has occurred:\nOops"

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [project]

    cloud_runner = mock.Mock()
    cloud_runner.run_backtest.return_value = backtest
    initialize_container(api_client_to_use=api_client, cloud_runner_to_use=cloud_runner)

    result = CliRunner().invoke(lean, ["cloud", "backtest", "My Project", "--open"])

    assert result.exit_code == 0

    open.assert_not_called()


def test_cloud_backtest_pushes_nothing_when_project_does_not_exist_locally() -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")
    backtest = create_api_backtest()

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [project]

    cloud_runner = mock.Mock()
    cloud_runner.run_backtest.return_value = backtest

    push_manager = mock.Mock()
    initialize_container(api_client_to_use=api_client,
                         cloud_runner_to_use=cloud_runner,
                         push_manager_to_use=push_manager)

    result = CliRunner().invoke(lean, ["cloud", "backtest", "My Project", "--push"])

    assert result.exit_code == 0

    push_manager.push_projects.assert_not_called()


def test_cloud_backtest_aborts_when_backtest_fails() -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")

    def run_backtest(*args, **kwargs):
        raise RuntimeError("Oops")

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [project]

    cloud_runner = mock.Mock()
    cloud_runner.run_backtest.side_effect = run_backtest
    initialize_container(api_client_to_use=api_client, cloud_runner_to_use=cloud_runner)

    result = CliRunner().invoke(lean, ["cloud", "backtest", "My Project"])

    assert result.exit_code != 0

    cloud_runner.run_backtest.assert_called_once()


def test_cloud_backtest_aborts_when_input_matches_no_cloud_project() -> None:
    create_fake_lean_cli_directory()

    project = create_api_project(1, "My Project")
    backtest = create_api_backtest()

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [project]

    cloud_runner = mock.Mock()
    cloud_runner.run_backtest.return_value = backtest
    initialize_container(api_client_to_use=api_client, cloud_runner_to_use=cloud_runner)

    result = CliRunner().invoke(lean, ["cloud", "backtest", "Fake Project"])

    assert result.exit_code != 0

    cloud_runner.run_backtest.assert_not_called()
