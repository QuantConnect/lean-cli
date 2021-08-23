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

from dependency_injector.containers import DeclarativeContainer
from dependency_injector.providers import Factory, Singleton

from lean.components.api.api_client import APIClient
from lean.components.cloud.cloud_project_manager import CloudProjectManager
from lean.components.cloud.cloud_runner import CloudRunner
from lean.components.cloud.data_downloader import DataDownloader
from lean.components.cloud.module_manager import ModuleManager
from lean.components.cloud.pull_manager import PullManager
from lean.components.cloud.push_manager import PushManager
from lean.components.config.cli_config_manager import CLIConfigManager
from lean.components.config.lean_config_manager import LeanConfigManager
from lean.components.config.optimizer_config_manager import OptimizerConfigManager
from lean.components.config.output_config_manager import OutputConfigManager
from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.config.storage import Storage
from lean.components.docker.docker_manager import DockerManager
from lean.components.docker.lean_runner import LeanRunner
from lean.components.util.http_client import HTTPClient
from lean.components.util.logger import Logger
from lean.components.util.market_hours_database import MarketHoursDatabase
from lean.components.util.name_generator import NameGenerator
from lean.components.util.path_manager import PathManager
from lean.components.util.platform_manager import PlatformManager
from lean.components.util.project_manager import ProjectManager
from lean.components.util.shortcut_manager import ShortcutManager
from lean.components.util.task_manager import TaskManager
from lean.components.util.temp_manager import TempManager
from lean.components.util.update_manager import UpdateManager
from lean.components.util.xml_manager import XMLManager
from lean.constants import CACHE_PATH, CREDENTIALS_CONFIG_PATH, GENERAL_CONFIG_PATH


class Container(DeclarativeContainer):
    """The Container class wires all reusable components together."""
    logger = Singleton(Logger)

    platform_manager = Singleton(PlatformManager)
    task_manager = Singleton(TaskManager, logger)
    name_generator = Singleton(NameGenerator)
    path_manager = Singleton(PathManager, platform_manager)
    temp_manager = Singleton(TempManager)
    xml_manager = Singleton(XMLManager)
    http_client = Singleton(HTTPClient, logger)

    general_storage = Singleton(Storage, file=GENERAL_CONFIG_PATH)
    credentials_storage = Singleton(Storage, file=CREDENTIALS_CONFIG_PATH)
    cache_storage = Singleton(Storage, file=CACHE_PATH)

    cli_config_manager = Singleton(CLIConfigManager, general_storage, credentials_storage)

    api_client = Factory(APIClient,
                         logger,
                         http_client,
                         user_id=cli_config_manager.provided.user_id.get_value()(),
                         api_token=cli_config_manager.provided.api_token.get_value()())

    module_manager = Singleton(ModuleManager, logger, api_client, http_client)

    project_config_manager = Singleton(ProjectConfigManager, xml_manager)
    lean_config_manager = Singleton(LeanConfigManager,
                                    logger,
                                    cli_config_manager,
                                    project_config_manager,
                                    module_manager,
                                    cache_storage)
    output_config_manager = Singleton(OutputConfigManager, lean_config_manager)
    optimizer_config_manager = Singleton(OptimizerConfigManager, logger)

    project_manager = Singleton(ProjectManager,
                                project_config_manager,
                                lean_config_manager,
                                xml_manager,
                                platform_manager)

    cloud_runner = Singleton(CloudRunner, logger, api_client, task_manager)
    pull_manager = Singleton(PullManager, logger, api_client, project_manager, project_config_manager, platform_manager)
    push_manager = Singleton(PushManager, logger, api_client, project_manager, project_config_manager)
    data_downloader = Singleton(DataDownloader, logger, api_client, lean_config_manager)
    cloud_project_manager = Singleton(CloudProjectManager,
                                      api_client,
                                      project_config_manager,
                                      pull_manager,
                                      push_manager,
                                      path_manager)

    docker_manager = Singleton(DockerManager, logger, temp_manager, platform_manager)
    lean_runner = Singleton(LeanRunner,
                            logger,
                            project_config_manager,
                            lean_config_manager,
                            output_config_manager,
                            docker_manager,
                            module_manager,
                            project_manager,
                            temp_manager,
                            xml_manager)

    market_hours_database = Singleton(MarketHoursDatabase, lean_config_manager)

    shortcut_manager = Singleton(ShortcutManager, logger, lean_config_manager, platform_manager, cache_storage)
    update_manager = Singleton(UpdateManager, logger, http_client, cache_storage, docker_manager)


container = Container()
