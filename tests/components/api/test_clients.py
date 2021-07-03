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

import contextlib
import os
from datetime import datetime
from time import sleep
from typing import ContextManager
from unittest import mock

import pytest
from responses import RequestsMock

from lean.components.api.account_client import AccountClient
from lean.components.api.api_client import APIClient
from lean.components.api.backtest_client import BacktestClient
from lean.components.api.compile_client import CompileClient
from lean.components.api.data_client import DataClient
from lean.components.api.file_client import FileClient
from lean.components.api.live_client import LiveClient
from lean.components.api.node_client import NodeClient
from lean.components.api.organization_client import OrganizationClient
from lean.components.api.project_client import ProjectClient
from lean.constants import API_BASE_URL
from lean.models.api import QCCompileState, QCLanguage, QCParameter, QCProject

# These tests require a QuantConnect user id and API token
# The credentials can also be provided using the QC_USER_ID and QC_API_TOKEN environment variables
USER_ID = ""
API_TOKEN = ""


@pytest.fixture(autouse=True)
def allow_http_requests(requests_mock: RequestsMock) -> None:
    """A pytest fixture which allows HTTP requests to the API to pass through the requests mock."""
    requests_mock.add_passthru(API_BASE_URL)


def create_api_client() -> APIClient:
    user_id = USER_ID or os.getenv("QC_USER_ID", "")
    api_token = API_TOKEN or os.getenv("QC_API_TOKEN", "")

    if user_id == "" or api_token == "":
        pytest.skip("API credentials not specified")

    return APIClient(mock.Mock(), user_id, api_token)


@contextlib.contextmanager
def create_project(api_client: APIClient, name_prefix: str) -> ContextManager[QCProject]:
    project_client = ProjectClient(api_client)

    # Create the project
    created_project = project_client.create(f"{name_prefix} {datetime.now()}", QCLanguage.Python)

    # Retrieve full project details
    project = project_client.get(created_project.projectId)

    # Do something with the project
    yield project

    # Delete the project
    project_client.delete(project.projectId)


def test_api_credentials_valid() -> None:
    assert create_api_client().is_authenticated()


def test_projects_crud() -> None:
    api_client = create_api_client()
    project_client = ProjectClient(api_client)

    # Test a project can be created
    name = f"Test Project {datetime.now()}"
    created_project = project_client.create(name, QCLanguage.Python)

    assert created_project.name == name
    assert created_project.projectId > 0

    # Test the project can be retrieved
    retrieved_project = project_client.get(created_project.projectId)

    assert retrieved_project.projectId == created_project.projectId

    # Test the project's name can be updated
    project_client.update(created_project.projectId, name="New Name")
    retrieved_project = project_client.get(created_project.projectId)

    assert retrieved_project.name == "New Name"

    # Test the project's description can be updated
    project_client.update(created_project.projectId, description="New description")
    retrieved_project = project_client.get(created_project.projectId)

    assert retrieved_project.description == "New description"

    # Test the project's parameters can be updated
    project_client.update(created_project.projectId, parameters={"key1": "value1", "key2": "value2", "key3": "value3"})
    retrieved_project = project_client.get(created_project.projectId)

    assert retrieved_project.parameters == [
        QCParameter(key="key1", value="value1"),
        QCParameter(key="key2", value="value2"),
        QCParameter(key="key3", value="value3")
    ]

    # Test libraries can be added
    with create_project(api_client, "Library/Test Project") as library_project:
        project_client.add_library(created_project.projectId, library_project.projectId)
        retrieved_project = project_client.get(created_project.projectId)

        assert retrieved_project.libraries == [library_project.projectId]

        # Test libraries can be deleted
        project_client.delete_library(created_project.projectId, library_project.projectId)
        retrieved_project = project_client.get(created_project.projectId)

        assert retrieved_project.libraries == []

    # Test the project can be deleted
    project_client.delete(created_project.projectId)

    # Test the project is really deleted
    projects = project_client.get_all()
    assert not any([p.projectId == created_project.projectId for p in projects])


def test_files_crud() -> None:
    api_client = create_api_client()
    file_client = FileClient(api_client)

    with create_project(api_client, "Test Project") as project:
        # Test a file can be created
        created_file = file_client.create(project.projectId, "file.py", "# This is a comment")

        assert created_file.name == "file.py"
        assert created_file.content == "# This is a comment"

        # Test the file can be retrieved
        retrieved_file = file_client.get(project.projectId, "file.py")

        assert retrieved_file.name == "file.py"
        assert retrieved_file.content == "# This is a comment"

        # Test the file can be updated
        file_client.update(project.projectId, "file.py", "# This is a new comment")
        retrieved_file = file_client.get(project.projectId, "file.py")

        assert retrieved_file.name == "file.py"
        assert retrieved_file.content == "# This is a new comment"

        # Test the file can be deleted
        file_client.delete(project.projectId, "file.py")

        # Test the file is really deleted
        files = file_client.get_all(project.projectId)

        assert not any([file.name == "file.py" for file in files])


def test_compiling() -> None:
    api_client = create_api_client()
    compile_client = CompileClient(api_client)

    with create_project(api_client, "Test Project") as project:
        # Test a compilation can be started
        created_compile = compile_client.create(project.projectId)

        # Test compilation can be retrieved
        retrieved_compile = compile_client.get(project.projectId, created_compile.compileId)

        assert retrieved_compile.compileId == created_compile.compileId


def test_backtest_crud() -> None:
    api_client = create_api_client()
    compile_client = CompileClient(api_client)
    backtest_client = BacktestClient(api_client)
    node_client = NodeClient(api_client)

    with create_project(api_client, "Test Project") as project:
        # Compile the project
        created_compile = compile_client.create(project.projectId)

        # Wait for the compile to be completed
        while True:
            if compile_client.get(project.projectId, created_compile.compileId).state in [QCCompileState.BuildSuccess,
                                                                                          QCCompileState.BuildError]:
                break
            sleep(1)

        # Ensure we have a backtest node to run on
        backtest_nodes = node_client.get_all(project.organizationId).backtest
        if all(node.busy for node in backtest_nodes):
            node_client.stop(project.organizationId, backtest_nodes[0].id)

        # Test a backtest can be started
        backtest_name = f"Test Backtest {datetime.now()}"
        created_backtest = backtest_client.create(project.projectId, created_compile.compileId, backtest_name)

        assert created_backtest.name == backtest_name

        # Wait for the backtest to be completed
        while True:
            if backtest_client.get(project.projectId, created_backtest.backtestId).completed:
                break
            sleep(1)

        # Test the backtest can be retrieved
        retrieved_backtest = backtest_client.get(project.projectId, created_backtest.backtestId)

        assert retrieved_backtest.backtestId == created_backtest.backtestId
        assert retrieved_backtest.name == backtest_name

        # Test the backtest can be updated
        backtest_client.update(project.projectId, created_backtest.backtestId, backtest_name + "2", "This is a note")
        retrieved_backtest = backtest_client.get(project.projectId, created_backtest.backtestId)

        assert retrieved_backtest.backtestId == created_backtest.backtestId
        assert retrieved_backtest.name == backtest_name + "2"
        assert retrieved_backtest.note == "This is a note"

        # Test the backtest can be deleted
        backtest_client.delete(project.projectId, created_backtest.backtestId)

        # Test the backtest is really deleted
        backtests = backtest_client.get_all(project.projectId)

        assert not any([backtest.backtestId == created_backtest.backtestId for backtest in backtests])


def test_live_client_get_all_parses_response() -> None:
    api_client = create_api_client()
    live_client = LiveClient(api_client)

    # Test live algorithms can be retrieved
    # All we can do here is make sure LiveClient can parse the response
    # Tests aren't supposed to trigger actions which cost money, so we can't launch a live algorithm here
    live_client.get_all()


def test_node_client_get_all_parses_response() -> None:
    api_client = create_api_client()
    account_client = AccountClient(api_client)
    node_client = NodeClient(api_client)

    # Retrieve the organization details
    organization = account_client.get_organization()

    # Test nodes can be retrieved
    # All we can do here is make sure NodeClient can parse the response
    # Tests aren't supposed to trigger actions which cost money, so we can't create a node here
    node_client.get_all(organization.organizationId)


def test_account_client_get_organization() -> None:
    api_client = create_api_client()
    account_client = AccountClient(api_client)
    organization_client = OrganizationClient(api_client)

    # Test get_organization() returns the same value when retrieving preferred organization with and without parameter
    preferred_organization = account_client.get_organization()
    specific_organization = account_client.get_organization(preferred_organization.organizationId)

    # Test default organization is preferred organization
    all_organizations = organization_client.get_all()
    assert next(x.id for x in all_organizations if x.preferred) == preferred_organization.organizationId

    assert preferred_organization == specific_organization


def test_organization_client_get_details() -> None:
    api_client = create_api_client()
    organization_client = OrganizationClient(api_client)

    # Test organizations can be retrieved
    organizations = organization_client.get_all()

    # Test full organization details can be retrieved
    for organization in organizations:
        full_organization = organization_client.get(organization.id)
        assert organization.id == full_organization.id
        assert organization.name == full_organization.name


def test_data_client_list_files() -> None:
    api_client = create_api_client()
    data_client = DataClient(api_client)

    # Test files can be listed
    files = data_client.list_files("crypto/gdax/daily/")

    # Test all files start with the requested prefix
    for file in files:
        assert file.startswith("crypto/gdax/daily/")


def test_data_client_get_info() -> None:
    api_client = create_api_client()
    account_client = AccountClient(api_client)
    data_client = DataClient(api_client)

    # Test data information can be parsed
    preferred_organization = account_client.get_organization()
    data_client.get_info(preferred_organization.organizationId)
