import tempfile
from pathlib import Path
from typing import Optional
from unittest import mock

from dependency_injector import containers, providers

from lean.commands.create_project import (DEFAULT_CSHARP_MAIN, DEFAULT_CSHARP_NOTEBOOK, DEFAULT_PYTHON_MAIN,
                                          DEFAULT_PYTHON_NOTEBOOK)
from lean.components.api_client import APIClient
from lean.components.backtest_runner import BacktestRunner
from lean.components.cli_config_manager import CLIConfigManager
from lean.components.docker_manager import DockerManager
from lean.components.http_client import HTTPClient
from lean.components.lean_config_manager import LeanConfigManager
from lean.components.logger import Logger
from lean.components.project_manager import ProjectManager
from lean.components.storage import Storage
from lean.container import container
from lean.models.options import Option


class MockContainer:
    """A class holding all the mocks used by MockedContainer.

    *_mock_class represents the class itself.
    *_mock represents the instance(s) of the class.
    """
    config = {
        # The file in which general CLI configuration is stored
        "general_config_file": str(Path(tempfile.gettempdir()) / "config"),

        # The file in which credentials are stored
        "credentials_config_file": str(Path(tempfile.gettempdir()) / "credentials"),

        # The default name of the configuration file in a Lean CLI project
        "default_lean_config_file_name": "lean.json",

        # The default name of the data directory in a Lean CLI project
        "default_data_directory_name": "data",

        # The Docker image used when running the LEAN engine locally
        "lean_engine_docker_image": "quantconnect/lean",

        # The tag of the Docker image used when running the LEAN engine locally
        "lean_engine_docker_tag": "latest",

        # The base url of the QuantConnect API
        "api_base_url": "https://www.quantconnect.com/api/v2"
    }

    logger_mock_class = mock.Mock(spec=Logger)
    logger_mock: mock.NonCallableMock = logger_mock_class.return_value

    general_storage_mock_class = mock.Mock(spec=Storage)
    general_storage_mock: mock.NonCallableMock = general_storage_mock_class.return_value

    credentials_storage_mock_class = mock.Mock(spec=Storage)
    credentials_storage_mock: mock.NonCallableMock = credentials_storage_mock_class.return_value

    cli_config_manager_mock_class = mock.Mock(spec=CLIConfigManager)
    cli_config_manager_mock: mock.NonCallableMock = cli_config_manager_mock_class.return_value

    lean_config_manager_mock_class = mock.Mock(spec=LeanConfigManager)
    lean_config_manager_mock: mock.NonCallableMock = lean_config_manager_mock_class.return_value

    http_client_mock_class = mock.Mock(spec=HTTPClient)
    http_client_mock: mock.NonCallableMock = http_client_mock_class.return_value

    api_client_mock_class = mock.Mock(spec=APIClient)
    api_client_mock: mock.NonCallableMock = api_client_mock_class.return_value

    project_manager_mock_class = mock.Mock(spec=ProjectManager)
    project_manager_mock: mock.NonCallableMock = project_manager_mock_class.return_value

    docker_manager_mock_class = mock.Mock(spec=DockerManager)
    docker_manager_mock: mock.NonCallableMock = docker_manager_mock_class.return_value

    backtest_runner_mock_class = mock.Mock(spec=BacktestRunner)
    backtest_runner_mock: mock.NonCallableMock = backtest_runner_mock_class.return_value


class MockedContainer(containers.DeclarativeContainer):
    """A version of lean.container.Container in which everything is mocked.

    Dependency Injector removes all non-provider members from the class, so the mocks are stored in MockContainer.
    """
    config = providers.Configuration(default=MockContainer.config)

    logger = providers.Singleton(MockContainer.logger_mock_class)

    general_storage = providers.Singleton(MockContainer.general_storage_mock_class)
    credentials_storage = providers.Singleton(MockContainer.credentials_storage_mock_class)

    cli_config_manager = providers.Singleton(MockContainer.cli_config_manager_mock_class)
    lean_config_manager = providers.Singleton(MockContainer.lean_config_manager_mock_class)

    http_client = providers.Singleton(MockContainer.http_client_mock_class)
    api_client = providers.Singleton(MockContainer.api_client_mock_class)

    project_manager = providers.Singleton(MockContainer.project_manager_mock_class)

    docker_manager = providers.Singleton(MockContainer.docker_manager_mock_class)

    backtest_runner = providers.Singleton(MockContainer.backtest_runner_mock_class)


def create_fake_lean_cli_project() -> None:
    """Creates a directory structure similar to the one created by `lean init` with a Python and C# project."""
    (Path.cwd() / container.config()["default_data_directory_name"]).mkdir()

    with open(Path.cwd() / container.config()["default_lean_config_file_name"], "w+") as config_file:
        config_file.write(f"""
{{
    "data-folder": "{container.config()["default_data_directory_name"]}"
}}
        """)

    files = {
        (Path.cwd() / "Python Project" / "main.py"): DEFAULT_PYTHON_MAIN.replace("$NAME", "PythonProject"),
        (Path.cwd() / "Python Project" / "research.ipynb"): DEFAULT_PYTHON_NOTEBOOK,
        (Path.cwd() / "CSharp Project" / "Main.cs"): DEFAULT_CSHARP_MAIN.replace("$NAME", "CSharpProject"),
        (Path.cwd() / "CSharp Project" / "research.ipynb"): DEFAULT_CSHARP_NOTEBOOK,
    }

    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w+") as file:
            file.write(content)


def create_option(key: str, value: Optional[str], sensitive: bool) -> mock.Mock:
    """Creates a fake option."""
    option = mock.Mock(spec=Option)
    option.key = key
    option.description = f"{key} documentation"
    option.is_sensitive = sensitive
    option.location = Path.home() / key
    option.get_value.return_value = value
    return option
