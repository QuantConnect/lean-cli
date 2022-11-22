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

from typing import Union, Any

from lean.components.api.api_client import APIClient
from lean.components.config.lean_config_manager import LeanConfigManager
from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.util.path_manager import PathManager
from lean.components.cloud.cloud_project_manager import CloudProjectManager
from lean.components.cloud.cloud_runner import CloudRunner
from lean.components.cloud.data_downloader import DataDownloader
from lean.components.cloud.module_manager import ModuleManager
from lean.components.cloud.pull_manager import PullManager
from lean.components.cloud.push_manager import PushManager
from lean.components.config.cli_config_manager import CLIConfigManager
from lean.components.config.optimizer_config_manager import OptimizerConfigManager
from lean.components.config.output_config_manager import OutputConfigManager
from lean.components.config.storage import Storage
from lean.components.docker.docker_manager import DockerManager
from lean.components.docker.lean_runner import LeanRunner
from lean.components.util.http_client import HTTPClient
from lean.components.util.library_manager import LibraryManager
from lean.components.util.logger import Logger
from lean.components.util.market_hours_database import MarketHoursDatabase
from lean.components.util.name_generator import NameGenerator
from lean.components.util.organization_manager import OrganizationManager
from lean.components.util.platform_manager import PlatformManager
from lean.components.util.project_manager import ProjectManager
from lean.components.util.task_manager import TaskManager
from lean.components.util.temp_manager import TempManager
from lean.components.util.update_manager import UpdateManager
from lean.components.util.xml_manager import XMLManager
from lean.constants import CACHE_PATH, CREDENTIALS_CONFIG_PATH, GENERAL_CONFIG_PATH


class Container:

    def __init__(self):
        self.initialize()

    def initialize(self,
                   docker_manager: Union[DockerManager, Any] = None,
                   api_client: Union[APIClient, Any] = None,
                   lean_runner: Union[LeanRunner, Any] = None,
                   cloud_runner: Union[CloudRunner, Any] = None,
                   push_manager: Union[PushManager, Any] = None,
                   organization_manager: Union[OrganizationManager, Any] = None,
                   project_config_manager: Union[ProjectConfigManager, Any] = None):
        """The Container class wires all reusable components together."""
        self.logger = Logger()

        self.platform_manager = PlatformManager()
        self.task_manager = TaskManager(self.logger)
        self.name_generator = NameGenerator()
        self.temp_manager = TempManager()
        self.xml_manager = XMLManager()
        self.http_client = HTTPClient(self.logger)

        self.general_storage = Storage(file=GENERAL_CONFIG_PATH)
        self.credentials_storage = Storage(file=CREDENTIALS_CONFIG_PATH)
        self.cache_storage = Storage(file=CACHE_PATH)

        self.cli_config_manager = CLIConfigManager(self.general_storage, self.credentials_storage)

        self.api_client = api_client
        if not self.api_client:
            self.api_client = APIClient(self.logger,
                                        self.http_client,
                                        user_id=self.cli_config_manager.user_id.get_value(),
                                        api_token=self.cli_config_manager.api_token.get_value())

        self.module_manager = ModuleManager(self.logger, self.api_client, self.http_client)

        self.project_config_manager = project_config_manager
        if not self.project_config_manager:
            self.project_config_manager = ProjectConfigManager(self.xml_manager)

        self.lean_config_manager = LeanConfigManager(self.logger,
                                                     self.cli_config_manager,
                                                     self.project_config_manager,
                                                     self.module_manager,
                                                     self.cache_storage)
        self.path_manager = PathManager(self.lean_config_manager, self.platform_manager)
        self.output_config_manager = OutputConfigManager(self.lean_config_manager)
        self.optimizer_config_manager = OptimizerConfigManager(self.logger)

        self.project_manager = ProjectManager(self.logger,
                                              self.project_config_manager,
                                              self.lean_config_manager,
                                              self.path_manager,
                                              self.xml_manager,
                                              self.platform_manager)
        self.library_manager = LibraryManager(self.logger,
                                              self.project_manager,
                                              self.project_config_manager,
                                              self.lean_config_manager,
                                              self.path_manager,
                                              self.xml_manager)

        self.organization_manager = organization_manager
        if not self.organization_manager:
            self.organization_manager = OrganizationManager(self.logger, self.lean_config_manager)

        self.cloud_runner = cloud_runner
        if not cloud_runner:
            self.cloud_runner = CloudRunner(self.logger, self.api_client, self.task_manager)
        self.pull_manager = PullManager(self.logger,
                                        self.api_client,
                                        self.project_manager,
                                        self.project_config_manager,
                                        self.library_manager,
                                        self.platform_manager)

        self.push_manager = push_manager
        if not push_manager:
            self.push_manager = PushManager(self.logger,
                                            self.api_client,
                                            self.project_manager,
                                            self.project_config_manager,
                                            self.organization_manager)
        self.data_downloader = DataDownloader(self.logger, self.api_client, self.lean_config_manager)
        self.cloud_project_manager = CloudProjectManager(self.api_client,
                                                         self.project_config_manager,
                                                         self.pull_manager,
                                                         self.push_manager,
                                                         self.path_manager,
                                                         self.project_manager,
                                                         self.organization_manager)

        self.docker_manager = docker_manager
        if not self.docker_manager:
            self.docker_manager = DockerManager(self.logger, self.temp_manager, self.platform_manager)

        self.lean_runner = lean_runner
        if not self.lean_runner:
            self.lean_runner = LeanRunner(self.logger,
                                          self.project_config_manager,
                                          self.lean_config_manager,
                                          self.output_config_manager,
                                          self.docker_manager,
                                          self.module_manager,
                                          self.project_manager,
                                          self.temp_manager,
                                          self.xml_manager)

        self.market_hours_database = MarketHoursDatabase(self.lean_config_manager)

        self.update_manager = UpdateManager(self.logger, self.http_client, self.cache_storage, self.docker_manager)


container = Container()
container.data_downloader.update_database_files()
