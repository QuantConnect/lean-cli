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

import os
from pathlib import Path
from unittest import mock

import certifi
import pytest
from pyfakefs.fake_filesystem import FakeFilesystem
from responses import RequestsMock
from lean.models.api import QCMinimalOrganization

from lean.container import container


def initialize_container(docker_manager_to_use=None, lean_runner_to_use=None, api_client_to_use=None,
                         cloud_runner_to_use=None, push_manager_to_use=None, organization_manager_to_use=None,
                         project_config_manager_to_use=None):
    api_client = mock.MagicMock()
    api_client.is_authenticated.return_value = True
    api_client.organizations.get_all.return_value = [
        QCMinimalOrganization(id="abc", name="abc", type="type", ownerName="You", members=1, preferred=True)
    ]
    if api_client_to_use:
        api_client = api_client_to_use

    docker_manager = mock.Mock()
    if docker_manager_to_use:
        docker_manager = docker_manager_to_use
    docker_manager.get_image_label = mock.MagicMock(return_value="net6.0")

    lean_runner = mock.Mock()
    if lean_runner_to_use:
        lean_runner = lean_runner_to_use

    cloud_runner = mock.Mock()
    if cloud_runner_to_use:
        cloud_runner = cloud_runner_to_use

    push_manager = None
    if push_manager_to_use:
        push_manager = push_manager_to_use

    if organization_manager_to_use:
        organization_manager = organization_manager_to_use
    else:
        organization_manager = mock.Mock()
        organization_manager.get_working_organization_id = mock.MagicMock(return_value="abc")
        organization_manager.try_get_working_organization_id = mock.MagicMock(return_value="abc")

    project_config_manager = None
    if project_config_manager_to_use:
        project_config_manager = project_config_manager_to_use

    # Reset all singletons so Path instances get recreated
    # Path instances are bound to the filesystem that was active at the time of their creation
    # When the filesystem changes, old Path instances bound to previous filesystems may cause weird behavior

    container.initialize(docker_manager, api_client, lean_runner, cloud_runner, push_manager, organization_manager,
                         project_config_manager)

    return container


# conftest.py is ran by pytest before loading each testing module
# Fixtures defined in here are therefore available in all testing modules


@pytest.fixture(autouse=True)
def fake_filesystem(fs: FakeFilesystem) -> FakeFilesystem:
    """A pytest fixture which mocks the filesystem before each test."""
    # The "fs" argument triggers pyfakefs' own pytest fixture to register
    # After pyfakefs has started all filesystem actions will happen on a fake in-memory filesystem

    # Proxy access to certifi's certificate authority bundle to the real filesystem
    # This is required to be able to send HTTP requests using requests
    fs.add_real_file(certifi.where())

    # Proxy access to package data to the real filesystem
    fs.add_real_directory(os.path.join(os.path.dirname(__file__), "../lean/ssh"))

    # Create a fake home directory and set the cwd to an empty directory
    fs.create_dir(Path.home() / "testing")
    os.chdir(Path.home() / "testing")

    initialize_container()

    return fs


@pytest.fixture(autouse=True)
def requests_mock() -> RequestsMock:
    """A pytest fixture which mocks the requests library before each test.

    If a test makes an HTTP request which hasn't been mocked, the request will fail.
    """
    with RequestsMock() as mock:
        yield mock


@pytest.fixture(autouse=True)
def reset_container_overrides() -> None:
    """A pytest fixture which makes sure all container and provider overrides are reset before each test."""
    initialize_container()
