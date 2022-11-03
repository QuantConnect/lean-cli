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
from datetime import datetime

import pytest
from click.testing import CliRunner

from lean.commands import lean
from lean.components.cloud.push_manager import PushManager
from lean.container import container
from lean.models.api import QCFullFile, QCLanguage
from tests.test_helpers import create_fake_lean_cli_directory, create_api_project
from tests.conftest import initialize_container


def test_cloud_push_pushes_all_projects_when_no_options_given() -> None:
    create_fake_lean_cli_directory()

    cloud_projects = [
        create_api_project(1, "Python Project"),
        create_api_project(2, "CSharp Project"),
        create_api_project(3, "Library/Python Library"),
        create_api_project(4, "Library/CSharp Library")
    ]
    api_client = mock.Mock()
    api_client.projects.get_all = mock.MagicMock(return_value=cloud_projects)

    push_manager = mock.Mock()
    initialize_container(api_client_to_use=api_client, push_manager_to_use=push_manager)

    result = CliRunner().invoke(lean, ["cloud", "push"])

    assert result.exit_code == 0

    push_manager.push_projects.assert_called_once()
    args, kwargs = push_manager.push_projects.call_args

    expected_args = {
        Path.cwd() / "Python Project",
        Path.cwd() / "CSharp Project",
        Path.cwd() / "Library/Python Library",
        Path.cwd() / "Library/CSharp Library"
    }

    assert set(args[0]) == expected_args


def test_cloud_push_pushes_single_project_when_project_option_given() -> None:
    create_fake_lean_cli_directory()

    cloud_projects = [create_api_project(1, "Python Project")]
    api_client = mock.Mock()
    api_client.projects.get_all = mock.MagicMock(return_value=cloud_projects)

    push_manager = mock.Mock()
    initialize_container(api_client_to_use=api_client, push_manager_to_use=push_manager)

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", "Python Project"])

    assert result.exit_code == 0

    push_manager.push_project.assert_called_once_with(Path.cwd() / "Python Project", None)


def test_cloud_push_aborts_when_given_directory_is_not_lean_project() -> None:
    create_fake_lean_cli_directory()

    push_manager = mock.Mock()
    initialize_container(push_manager_to_use=push_manager)

    (Path.cwd() / "Empty Project").mkdir()

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", "Empty Project"])

    assert result.exit_code != 0

    push_manager.push_projects.assert_not_called()


def test_cloud_push_aborts_when_given_directory_does_not_exist() -> None:
    create_fake_lean_cli_directory()

    push_manager = mock.Mock()
    initialize_container(push_manager_to_use=push_manager)

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", "Empty Project"])

    assert result.exit_code != 0

    push_manager.push_projects.assert_not_called()


@pytest.mark.parametrize("organization_id", ["d6e62db42593c72e67a534513413b692", None])
def test_cloud_push_creates_project_with_optional_organization_id(organization_id: Optional[str]) -> None:
    create_fake_lean_cli_directory()

    path = "Python Project"
    cloud_project = create_api_project(1, path)

    with mock.patch.object(container.api_client.projects, 'create', return_value=create_api_project(1, path)) as mock_create_project:
        organization_id_option = ["--organization-id", organization_id] if organization_id is not None else []
        result = CliRunner().invoke(lean, ["cloud", "push", "--project", path, *organization_id_option])

    assert result.exit_code == 0

    mock_create_project.assert_called_once_with(path, QCLanguage.Python, organization_id)


def test_cloud_push_updates_lean_config() -> None:

    create_fake_lean_cli_directory()

    cloud_project = create_api_project(1, "Python Project")
    api_client = mock.Mock()
    api_client.projects.create = mock.MagicMock(return_value=cloud_project)
    fake_cloud_files = [QCFullFile(name="removed_file.py", content="", modified=datetime.now(), isLibrary=False)]
    api_client.files.get_all = mock.MagicMock(return_value=fake_cloud_files)
    api_client.files.delete = mock.Mock()

    api_client.projects.get_all = mock.MagicMock(return_value=[cloud_project])
    api_client.projects.get = mock.MagicMock(return_value=create_api_project(1, "Python Project"))

    project_config = mock.Mock()
    project_config.get = mock.MagicMock(side_effect=[None, "Python", "", {}, -1, None, []])

    project_config_manager = mock.Mock()
    project_config_manager.get_project_config = mock.MagicMock(return_value=project_config)

    project_manager = mock.Mock()
    project_manager.get_source_files = mock.MagicMock(return_value=[])
    project_manager.get_project_libraries = mock.MagicMock(return_value=[])

    push_manager = PushManager(mock.Mock(), api_client, project_manager, project_config_manager)

    initialize_container(push_manager_to_use=push_manager, api_client_to_use=api_client)

    result = CliRunner().invoke(lean, ["cloud", "push", "--project", "Python Project"])

    assert result.exit_code == 0

    project_config.set.assert_called_with("name", "Python Project")
