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
from pathlib import Path
from unittest import mock

from lean.container import container
from lean.models.api import QCMinimalFile
from tests.test_helpers import create_api_project, create_fake_lean_cli_directory, create_lean_environments
from tests.conftest import initialize_container


def test_get_cloud_project_pushing_new_project():
    create_fake_lean_cli_directory()

    cloud_project = create_api_project(20, "Python Project")
    cloud_project.description = ""

    api_client = mock.Mock()
    api_client.projects.get_all.return_value = [cloud_project]
    api_client.projects.get.return_value = cloud_project

    push_manager = mock.Mock()
    push_manager.push_projects = mock.Mock()

    project_config = mock.Mock()
    project_config.get = mock.MagicMock(return_value=cloud_project.projectId)
    project_config_manager = mock.Mock()
    project_config_manager.try_get_project_config = mock.MagicMock(return_value=None)
    project_config_manager.get_project_config = mock.MagicMock(return_value=project_config)

    initialize_container(api_client_to_use=api_client, push_manager_to_use=push_manager,
                         project_config_manager_to_use=project_config_manager)

    cloud_project_manager = container.cloud_project_manager
    created_cloud_project = cloud_project_manager.get_cloud_project("Python Project", push=True)

    assert created_cloud_project == cloud_project

    api_client.projects.get.assert_called_with(cloud_project.projectId, "abc")
    push_manager.push_projects.assert_called_once_with([Path.cwd() / "Python Project"])
