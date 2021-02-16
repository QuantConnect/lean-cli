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
from time import sleep
from unittest import mock

import pytest
from responses import RequestsMock

from lean.components.api.account_client import AccountClient
from lean.components.api.api_client import APIClient
from lean.components.api.backtest_client import BacktestClient
from lean.components.api.compile_client import CompileClient
from lean.components.api.file_client import FileClient
from lean.components.api.live_client import LiveClient
from lean.components.api.node_client import NodeClient
from lean.components.api.project_client import ProjectClient
from lean.models.api import QCCompileState, QCLanguage

# These tests require a QuantConnect user id and API token
USER_ID = ""
API_TOKEN = ""


@pytest.fixture(autouse=True)
def allow_http_requests(requests_mock: RequestsMock) -> None:
    """A pytest fixture which allows HTTP requests to the API to pass through the requests mock."""
    requests_mock.add_passthru("https://www.quantconnect.com/api/v2")


def create_api_client() -> APIClient:
    if USER_ID == "" or API_TOKEN == "":
        pytest.skip("API credentials not specified")

    return APIClient(mock.Mock(), "https://www.quantconnect.com/api/v2", USER_ID, API_TOKEN)


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

    # Test the project can be deleted
    project_client.delete(created_project.projectId)

    # Test the project is really deleted
    projects = project_client.get_all()
    assert not any([p.projectId == created_project.projectId for p in projects])


def test_files_crud() -> None:
    api_client = create_api_client()
    project_client = ProjectClient(api_client)
    file_client = FileClient(api_client)

    # Create a project to play with
    name = f"Test Project {datetime.now()}"
    project = project_client.create(name, QCLanguage.Python)

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

    # Delete the project that was used to test FileClient
    project_client.delete(project.projectId)


def test_compiling() -> None:
    api_client = create_api_client()
    project_client = ProjectClient(api_client)
    compile_client = CompileClient(api_client)

    # Create a project to play with
    name = f"Test Project {datetime.now()}"
    project = project_client.create(name, QCLanguage.Python)

    # Test a compilation can be started
    created_compile = compile_client.create(project.projectId)

    # Test compilation can be retrieved
    retrieved_compile = compile_client.get(project.projectId, created_compile.compileId)

    assert retrieved_compile.compileId == created_compile.compileId

    # Delete the project that was used to test CompileClient
    project_client.delete(project.projectId)


def test_backtest_crud() -> None:
    api_client = create_api_client()
    project_client = ProjectClient(api_client)
    compile_client = CompileClient(api_client)
    backtest_client = BacktestClient(api_client)

    # Create a project to play with
    project_name = f"Test Project {datetime.now()}"
    project = project_client.create(project_name, QCLanguage.Python)

    # Compile the project
    created_compile = compile_client.create(project.projectId)

    # Wait for the compile to be completed
    while True:
        if compile_client.get(project.projectId, created_compile.compileId).state in [QCCompileState.BuildSuccess,
                                                                                      QCCompileState.BuildError]:
            break
        sleep(1)

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

    # Delete the project that was used to test BacktestClient
    project_client.delete(project.projectId)


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

    # Test get_organization() returns the same value when retrieving default organization with and without parameter
    default_organization = account_client.get_organization()
    specific_organization = account_client.get_organization(default_organization.organizationId)

    assert default_organization == specific_organization
