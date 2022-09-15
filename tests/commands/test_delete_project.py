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
from typing import List
from unittest import mock

import pytest
from click.testing import CliRunner

from lean.commands import lean
from lean.components.api.project_client import ProjectClient
from lean.models.api import QCProject
from tests.test_helpers import create_fake_lean_cli_directory, create_api_project


def assert_project_exists(path: str) -> None:
    project_dir = (Path.cwd() / path)

    assert project_dir.exists()
    assert (project_dir / "main.py").exists()
    assert (project_dir / "research.ipynb").exists()


def assert_project_does_not_exist(path: str) -> None:
    project_dir = (Path.cwd() / path)
    assert not project_dir.exists()


def create_cloud_projects(count: int = 10) -> List[QCProject]:
    return [create_api_project(i, f"Python Project {i}") for i in range(1, count + 1)]


def test_delete_project_locally_that_does_not_have_cloud_counterpart() -> None:
    create_fake_lean_cli_directory()

    path = "Python Project"
    assert_project_exists(path)

    cloud_projects = create_cloud_projects()
    assert not any(project.name == path for project in cloud_projects)

    with mock.patch.object(ProjectClient, 'get_all', return_value=cloud_projects) as mock_get_all,\
         mock.patch.object(ProjectClient, 'delete', return_value=None) as mock_delete:
        result = CliRunner().invoke(lean, ["delete-project", path])
        assert result.exit_code == 0

    mock_get_all.assert_called_once()
    mock_delete.assert_not_called()
    assert_project_does_not_exist(path)


@pytest.mark.parametrize("name_or_id", ["Python Project", "11"])
def test_delete_project_deletes_in_cloud(name_or_id: str) -> None:
    create_fake_lean_cli_directory()

    path = "Python Project"
    assert_project_exists(path)

    cloud_projects = create_cloud_projects(10)
    assert not any(project.name == path for project in cloud_projects)

    cloud_project = create_api_project(len(cloud_projects) + 1, path)
    cloud_projects.append(cloud_project)

    with mock.patch.object(ProjectClient, 'get_all', return_value=cloud_projects) as mock_get_all,\
         mock.patch.object(ProjectClient, 'delete', return_value=None) as mock_delete:
        result = CliRunner().invoke(lean, ["delete-project", name_or_id])
        assert result.exit_code == 0

    mock_get_all.assert_called_once()
    mock_delete.assert_called_once_with(cloud_project.projectId)
    assert_project_does_not_exist(cloud_project.name)


def test_delete_project_aborts_when_path_does_not_exist() -> None:
    create_fake_lean_cli_directory()

    path = "Non Existing Project"
    assert_project_does_not_exist(path)

    with mock.patch.object(ProjectClient, 'get_all', return_value=create_cloud_projects()) as mock_get_all,\
         mock.patch.object(ProjectClient, 'delete', return_value=None) as mock_delete:
        result = CliRunner().invoke(lean, ["delete-project", path])
        assert result.exit_code != 0

    mock_get_all.assert_called_once()
    mock_delete.assert_not_called()


def test_delete_project_by_id_aborts_when_not_found_in_cloud() -> None:
    create_fake_lean_cli_directory()

    path = "Python Project"
    assert_project_exists(path)

    cloud_projects = create_cloud_projects(10)
    project_id = str(len(cloud_projects) + 1)

    with mock.patch.object(ProjectClient, 'get_all', return_value=[]) as mock_get_all,\
         mock.patch.object(ProjectClient, 'delete', return_value=None) as mock_delete:
        result = CliRunner().invoke(lean, ["delete-project", project_id])
        assert result.exit_code != 0

    mock_get_all.assert_called_once()
    mock_delete.assert_not_called()
    assert_project_exists(path)
