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
from unittest import mock
from re import sub

from click.testing import CliRunner

from lean.commands import lean
from lean.components.api.project_client import ProjectClient
from lean.components.config.storage import Storage
from tests.test_helpers import create_fake_lean_cli_directory


def assert_project_exists(path: str) -> None:
    project_dir = (Path.cwd() / path)

    assert project_dir.exists()
    assert (project_dir / "main.py").exists()
    assert (project_dir / "research.ipynb").exists()


def assert_project_does_not_exist(path: str) -> None:
    project_dir = (Path.cwd() / path)
    assert not project_dir.exists()


def test_delete_project_deletes_project_directory() -> None:
    create_fake_lean_cli_directory()

    path = "Python Project"
    assert_project_exists(path)

    with mock.patch.object(ProjectClient, 'delete', return_value=None) as mock_delete:
        result = CliRunner().invoke(lean, ["delete-project", path])
        assert result.exit_code == 0

    mock_delete.assert_not_called()
    assert_project_does_not_exist(path)


def test_delete_project_deletes_in_cloud_if_cloud_id_is_set() -> None:
    create_fake_lean_cli_directory()

    project_id = 1
    path = "Python Project"
    assert_project_exists(path)

    with mock.patch.object(Storage, 'get', return_value=project_id) as mock_get,\
         mock.patch.object(ProjectClient, 'delete', return_value=None) as mock_delete:
        result = CliRunner().invoke(lean, ["delete-project", path])
        assert result.exit_code == 0

    mock_get.assert_called_once_with("cloud-id")
    mock_delete.assert_called_once_with(project_id)
    assert_project_does_not_exist(path)


def test_delete_project_aborts_when_path_does_not_exist() -> None:
    create_fake_lean_cli_directory()

    path = "Non Existing Project"
    assert_project_does_not_exist(path)
    result = CliRunner().invoke(lean, ["delete-project", path])

    assert result.exit_code != 0
