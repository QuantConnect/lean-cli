from dependency_injector import containers, providers

from lean.components.api_client import APIClient
from lean.components.backtest_runner import BacktestRunner
from lean.components.cli_config_manager import CLIConfigManager
from lean.components.docker_manager import DockerManager
from lean.components.lean_config_manager import LeanConfigManager
from lean.components.logger import Logger
from lean.components.project_manager import ProjectManager
from lean.components.storage import Storage
from lean.config import Config


class Container(containers.DeclarativeContainer):
    """The Container class contains providers for all components used by the CLI."""
    # config = providers.Configuration(strict=True, default={
    #     # The file in which general CLI configuration is stored
    #     "general_config_file": str(Path("~/.lean/config").expanduser()),
    #
    #     # The file in which credentials are stored
    #     "credentials_config_file": str(Path("~/.lean/credentials").expanduser()),
    #
    #     # The default name of the configuration file in a Lean CLI project
    #     "default_lean_config_file_name": "lean.json",
    #
    #     # The default name of the data directory in a Lean CLI project
    #     "default_data_directory_name": "data",
    #
    #     # The Docker image used when running the LEAN engine locally
    #     "lean_engine_docker_image": "quantconnect/lean",
    #
    #     # The tag of the Docker image used when running the LEAN engine locally
    #     "lean_engine_docker_tag": "latest",
    #
    #     # The base url of the QuantConnect API
    #     "api_base_url": "https://www.quantconnect.com/api/v2"
    # })
    logger = providers.Singleton(Logger)

    general_storage = providers.Singleton(Storage, file=Config.general_config_file)
    credentials_storage = providers.Singleton(Storage, file=Config.credentials_config_file)

    cli_config_manager = providers.Singleton(CLIConfigManager,
                                             general_storage=general_storage,
                                             credentials_storage=credentials_storage)
    lean_config_manager = providers.Singleton(LeanConfigManager,
                                              cli_config_manager=cli_config_manager,
                                              default_file_name=Config.default_lean_config_file_name)

    api_client = providers.Factory(APIClient,
                                   logger=logger,
                                   base_url=Config.api_base_url,
                                   user_id=cli_config_manager.provided.user_id.get_value(),
                                   api_token=cli_config_manager.provided.api_token.get_value())

    project_manager = providers.Singleton(ProjectManager)

    docker_manager = providers.Singleton(DockerManager, logger=logger)

    backtest_runner = providers.Singleton(BacktestRunner,
                                          logger=logger,
                                          lean_config_manager=lean_config_manager,
                                          docker_manager=docker_manager,
                                          docker_image=Config.lean_engine_docker_image,
                                          docker_tag=Config.lean_engine_docker_tag)


container = Container()
