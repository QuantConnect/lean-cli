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
from typing import List, Any
from unittest import mock

from lean.components.cloud.pull_manager import PullManager
from lean.components.config.storage import Storage
from lean.models.api import QCProject
from tests.test_helpers import create_fake_lean_cli_directory, create_api_project, create_lean_environments


def _create_pull_manager(api_client: mock.Mock, project_config_manager: mock.Mock) -> PullManager:
    logger = mock.Mock()
    platform_manager = mock.Mock()
    project_manager = mock.Mock()
    return PullManager(logger, api_client, project_manager, project_config_manager, platform_manager)


def _assert_pull_manager_adds_property_to_project_config(prop: str,
                                                         expected_value: Any,
                                                         cloud_projects: List[QCProject]) -> None:
    api_client = mock.Mock()
    api_client.lean.environments = mock.MagicMock(return_value=create_lean_environments())
    api_client.files.get_all = mock.MagicMock(return_value=[])

    project_config = mock.Mock()
    project_config.set = mock.Mock()

    project_config_manager = mock.Mock()
    project_config_manager.get_project_config = mock.MagicMock(return_value=project_config)

    pull_manager = _create_pull_manager(api_client, project_config_manager)
    pull_manager.pull_projects(cloud_projects)

    project_config.set.assert_called_with(prop, expected_value)


def test_pull_manager_adds_lean_engine_version_to_config() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"
    project_id = 1000
    cloud_project = create_api_project(project_id, project_path.name)
    cloud_project.leanPinnedToMaster = False

    _assert_pull_manager_adds_property_to_project_config("lean-engine", cloud_project.leanVersionId, [cloud_project])


def test_pull_manager_adds_python_venv_to_config() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"
    project_id = 1000
    cloud_project = create_api_project(project_id, project_path.name)
    environments = create_lean_environments()
    environment = next(env for env in environments if env.path is not None)
    cloud_project.leanEnvironment = environment.id

    _assert_pull_manager_adds_property_to_project_config("python-venv", environment.path, [cloud_project])


def _assert_pull_manager_removes_property_from_project_config(prop: str, cloud_projects: List[QCProject]) -> None:
    api_client = mock.Mock()
    api_client.lean.environments = mock.MagicMock(return_value=create_lean_environments())
    api_client.files.get_all = mock.MagicMock(return_value=[])

    project_config = mock.Mock()
    project_config.set = mock.Mock()
    project_config.delete = mock.Mock()

    project_config_manager = mock.Mock()
    project_config_manager.get_project_config = mock.MagicMock(return_value=project_config)

    pull_manager = _create_pull_manager(api_client, project_config_manager)
    pull_manager.pull_projects(cloud_projects)

    assert mock.call(prop) in project_config.delete.call_args_list
    assert prop not in [call.args[0] for call in project_config.set.call_args_list]


def test_pull_manager_removes_lean_engine_from_config_when_lean_pinned_to_master() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"
    config = Storage(str(project_path / "config.json"))
    config.set("lean-engine", 456)

    project_id = 1000
    cloud_project = create_api_project(project_id, project_path.name)
    cloud_project.leanPinnedToMaster = True

    _assert_pull_manager_removes_property_from_project_config("lean-engine", [cloud_project])


def test_pull_manager_removes_python_venv_from_config_when_set_to_default() -> None:
    create_fake_lean_cli_directory()

    project_path = Path.cwd() / "Python Project"
    config = Storage(str(project_path / "config.json"))
    environments = create_lean_environments()
    config.set("python-venv", next(env.path for env in environments if env.path is not None))

    project_id = 1000
    cloud_project = create_api_project(project_id, project_path.name)
    cloud_project.leanPinnedToMaster = True

    _assert_pull_manager_removes_property_from_project_config("python-venv", [cloud_project])
