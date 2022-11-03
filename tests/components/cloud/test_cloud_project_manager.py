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

from lean.container import container
from lean.models.api import QCBacktest, QCMinimalFile
from tests.test_helpers import create_api_project, create_fake_lean_cli_directory, create_lean_environments


def test_get_cloud_project_pushing_new_project():
    create_fake_lean_cli_directory()

    cloud_project = create_api_project(20, "Python Project")
    cloud_project.description = ""

    api_client = mock.Mock()
    api_client.projects.get.return_value = cloud_project
    api_client.projects.create.return_value = cloud_project
    api_client.files.get_all.return_value = []
    api_client.files.create.return_value = QCMinimalFile(name="file.py", content="", modified=datetime.now())
    api_client.lean.environments.return_value = create_lean_environments()
    container.api_client = api_client

    cloud_project_manager = container.cloud_project_manager
    created_cloud_project = cloud_project_manager.get_cloud_project("Python Project", push=True)

    assert created_cloud_project == cloud_project

    api_client.projects.get.assert_called_with(cloud_project.projectId)
