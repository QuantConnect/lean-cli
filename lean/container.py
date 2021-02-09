from pathlib import Path

from dependency_injector import containers, providers

from lean.components.api_client import APIClient
from lean.components.backtest_runner import BacktestRunner
from lean.components.cli_config_manager import CLIConfigManager
from lean.components.docker_manager import DockerManager
from lean.components.http_client import HTTPClient
from lean.components.lean_config_manager import LeanConfigManager
from lean.components.logger import Logger
from lean.components.project_manager import ProjectManager
from lean.components.storage import Storage


class Container(containers.DeclarativeContainer):
    """The Container class contains providers for all components used by the CLI."""
    config = providers.Configuration(strict=True)

    logger = providers.Singleton(Logger)

    general_storage = providers.Singleton(Storage, file=config.general_config_file)
    credentials_storage = providers.Singleton(Storage, file=config.credentials_config_file)

    cli_config_manager = providers.Singleton(CLIConfigManager,
                                             general_storage=general_storage,
                                             credentials_storage=credentials_storage)
    lean_config_manager = providers.Singleton(LeanConfigManager,
                                              cli_config_manager=cli_config_manager,
                                              default_file_name=config.default_lean_config_file_name)

    http_client = providers.Singleton(HTTPClient, logger=logger)
    api_client = providers.Factory(APIClient, http_client=http_client, base_url=config.api_base_url)

    project_manager = providers.Singleton(ProjectManager)

    docker_manager = providers.Singleton(DockerManager, logger=logger)

    backtest_runner = providers.Singleton(BacktestRunner,
                                          logger=logger,
                                          lean_config_manager=lean_config_manager,
                                          docker_manager=docker_manager,
                                          docker_image=config.lean_engine_docker_image,
                                          docker_tag=config.lean_engine_docker_tag)


container = Container()
container.config.from_dict({
    # The file in which general CLI configuration is stored
    "general_config_file": str(Path("~/.lean/config").resolve()),

    # The file in which credentials are stored
    "credentials_config_file": str(Path("~/.lean/credentials").resolve()),

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
})
