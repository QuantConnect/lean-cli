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

from dependency_injector import containers, providers

from lean.components.api.api_client import APIClient
from lean.components.api.backtest_client import BacktestClient
from lean.components.api.compile_client import CompileClient
from lean.components.api.file_client import FileClient
from lean.components.api.live_client import LiveClient
from lean.components.api.node_client import NodeClient
from lean.components.api.project_client import ProjectClient
from lean.components.config.cli_config_manager import CLIConfigManager
from lean.components.config.lean_config_manager import LeanConfigManager
from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.config.storage import Storage
from lean.components.docker_manager import DockerManager
from lean.components.engine.csharp_compiler import CSharpCompiler
from lean.components.engine.lean_runner import LeanRunner
from lean.components.logger import Logger
from lean.components.project_manager import ProjectManager
from lean.config import Config


class Container(containers.DeclarativeContainer):
    """The Container class contains providers for all reusable components used by the CLI."""
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
                                   user_id=cli_config_manager.provided.user_id.get_value()(),
                                   api_token=cli_config_manager.provided.api_token.get_value()())
    file_client = providers.Singleton(FileClient, api_client=api_client)
    project_client = providers.Singleton(ProjectClient, api_client=api_client)
    compile_client = providers.Singleton(CompileClient, api_client=api_client)
    backtest_client = providers.Singleton(BacktestClient, api_client=api_client)
    node_client = providers.Singleton(NodeClient, api_client=api_client)
    live_client = providers.Singleton(LiveClient, api_client=api_client)

    project_manager = providers.Singleton(ProjectManager)
    project_config_manager = providers.Singleton(ProjectConfigManager, file_name=Config.project_config_file_name)

    docker_manager = providers.Singleton(DockerManager, logger=logger)

    csharp_compiler = providers.Singleton(CSharpCompiler,
                                          logger=logger,
                                          lean_config_manager=lean_config_manager,
                                          docker_manager=docker_manager,
                                          docker_image=Config.lean_engine_docker_image)
    lean_runner = providers.Singleton(LeanRunner,
                                      logger=logger,
                                      csharp_compiler=csharp_compiler,
                                      lean_config_manager=lean_config_manager,
                                      docker_manager=docker_manager,
                                      docker_image=Config.lean_engine_docker_image)


container = Container()
