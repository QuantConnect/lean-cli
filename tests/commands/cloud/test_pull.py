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

from unittest import mock

from click.testing import CliRunner
from dependency_injector import providers

from lean.commands import lean
from lean.container import container
from tests.test_helpers import create_api_project, create_fake_lean_cli_directory


def test_cloud_pull_pulls_all_non_bootcamp_projects_when_no_options_given() -> None:
    create_fake_lean_cli_directory()

    cloud_projects = [create_api_project(1, "Project 1"),
                      create_api_project(2, "Project 2"),
                      create_api_project(3, "Project 3"),
                      create_api_project(4, "Boot Camp/Project 4"),
                      create_api_project(5, "Boot Camp/Project 5")]

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = cloud_projects
    container.api_client.override(providers.Object(api_client))

    pull_manager = mock.Mock()
    container.pull_manager.override(providers.Object(pull_manager))

    result = CliRunner().invoke(lean, ["cloud", "pull"])

    assert result.exit_code == 0

    pull_manager.pull_projects.assert_called_once_with(cloud_projects[:3], cloud_projects)


def test_cloud_pull_pulls_all_projects_when_pull_bootcamp_option_given() -> None:
    create_fake_lean_cli_directory()

    cloud_projects = [create_api_project(1, "Project 1"),
                      create_api_project(2, "Project 2"),
                      create_api_project(3, "Project 3"),
                      create_api_project(4, "Boot Camp/Project 4"),
                      create_api_project(5, "Boot Camp/Project 5")]

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = cloud_projects
    container.api_client.override(providers.Object(api_client))

    pull_manager = mock.Mock()
    container.pull_manager.override(providers.Object(pull_manager))

    result = CliRunner().invoke(lean, ["cloud", "pull", "--pull-bootcamp"])

    assert result.exit_code == 0

    pull_manager.pull_projects.assert_called_once_with(cloud_projects, cloud_projects)


def test_cloud_pull_pulls_project_by_id() -> None:
    create_fake_lean_cli_directory()

    cloud_projects = [create_api_project(1, "Project 1"),
                      create_api_project(2, "Project 2"),
                      create_api_project(3, "Project 3"),
                      create_api_project(4, "Boot Camp/Project 4"),
                      create_api_project(5, "Boot Camp/Project 5")]

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = cloud_projects
    container.api_client.override(providers.Object(api_client))

    pull_manager = mock.Mock()
    container.pull_manager.override(providers.Object(pull_manager))

    result = CliRunner().invoke(lean, ["cloud", "pull", "--project", "1"])

    assert result.exit_code == 0

    pull_manager.pull_projects.assert_called_once_with([cloud_projects[0]], cloud_projects)


def test_cloud_pull_pulls_project_by_name() -> None:
    create_fake_lean_cli_directory()

    cloud_projects = [create_api_project(1, "Project 1"),
                      create_api_project(2, "Project 2"),
                      create_api_project(3, "Project 3"),
                      create_api_project(4, "Boot Camp/Project 4"),
                      create_api_project(5, "Boot Camp/Project 5")]

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = cloud_projects
    container.api_client.override(providers.Object(api_client))

    pull_manager = mock.Mock()
    container.pull_manager.override(providers.Object(pull_manager))

    result = CliRunner().invoke(lean, ["cloud", "pull", "--project", "Project 1"])

    assert result.exit_code == 0

    pull_manager.pull_projects.assert_called_once_with([cloud_projects[0]], cloud_projects)


def test_cloud_pull_aborts_when_project_input_matches_no_cloud_projects() -> None:
    create_fake_lean_cli_directory()

    cloud_projects = [create_api_project(1, "Project 1"),
                      create_api_project(2, "Project 2"),
                      create_api_project(3, "Project 3"),
                      create_api_project(4, "Boot Camp/Project 4"),
                      create_api_project(5, "Boot Camp/Project 5")]

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = cloud_projects
    container.api_client.override(providers.Object(api_client))

    pull_manager = mock.Mock()
    container.pull_manager.override(providers.Object(pull_manager))

    result = CliRunner().invoke(lean, ["cloud", "pull", "--project", "Project 4"])

    assert result.exit_code != 0

    pull_manager.pull_projects.assert_not_called()
