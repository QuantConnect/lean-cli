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
from datetime import datetime

from click.testing import CliRunner
from dependency_injector import providers

from lean.commands import lean
from lean.components.cloud.push_manager import PushManager
from lean.container import container
from lean.models.api import QCFullFile
from tests.test_helpers import create_fake_lean_cli_directory


def test_cloud_push_pushes_all_projects_when_no_options_given() -> None:
    create_fake_lean_cli_directory()

    push_manager = mock.Mock()
    container.push_manager.override(providers.Object(push_manager))

    result = CliRunner().invoke(lean, ["cloud", "push"])

    assert result.exit_code == 0

    push_manager.push_projects.assert_called_once()
    args, kwargs = push_manager.push_projects.call_args

    assert set(args[0]) == {Path.cwd() / "Python Project", Path.cwd() / "CSharp Project"}


def test_cloud_push_pushes_single_project_when_project_option_given() -> None:
    create_fake_lean_cli_directory()

    push_manager = mock.Mock()
    container.push_manager.override(providers.Object(push_manager))

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", "Python Project"])

    assert result.exit_code == 0

    push_manager.push_projects.assert_called_once_with([Path.cwd() / "Python Project"])


def test_cloud_push_aborts_when_given_directory_is_not_lean_project() -> None:
    create_fake_lean_cli_directory()

    push_manager = mock.Mock()
    container.push_manager.override(providers.Object(push_manager))

    (Path.cwd() / "Empty Project").mkdir()

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", "Empty Project"])

    assert result.exit_code != 0

    push_manager.push_projects.assert_not_called()


def test_cloud_push_aborts_when_given_directory_does_not_exist() -> None:
    create_fake_lean_cli_directory()

    push_manager = mock.Mock()
    container.push_manager.override(providers.Object(push_manager))

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", "Empty Project"])

    assert result.exit_code != 0

    push_manager.push_projects.assert_not_called()


def test_cloud_push_removes_locally_removed_files_in_cloud() -> None:
    create_fake_lean_cli_directory()

    client = mock.Mock()
    fake_cloud_files = [QCFullFile(name="removed_file.py", content="", modified=datetime.now(), isLibrary=False)]
    client.files.get_all = mock.MagicMock(return_value=fake_cloud_files)
    client.files.delete = mock.Mock()

    project = mock.Mock()
    project.projectId = 1
    project.description = ""
    project.parameters = []
    client.projects.get_all = mock.MagicMock(return_value=[project])

    project_config = mock.Mock()
    project_config.get = mock.MagicMock(side_effect=[1, "", {}])

    project_config_manager = mock.Mock()
    project_config_manager.get_project_config = mock.MagicMock(return_value=project_config)

    project_manager = mock.Mock()
    project_manager.get_source_files = mock.MagicMock(return_value=[])

    push_manager = PushManager(mock.Mock(), client, project_manager, project_config_manager)
    container.push_manager.override(providers.Object(push_manager))

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", "Python Project"])

    assert result.exit_code == 0

    project_config.get.assert_called()
    client.projects.get_all.assert_called_once()
    project_manager.get_source_files.assert_called_once()
    project_config_manager.get_project_config.assert_called()
    client.files.get_all.assert_called_once()
    client.files.delete.assert_called_once()
