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

from pathlib import Path
from typing import Union, Any, Optional, Tuple

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
from lean.constants import CACHE_PATH, CREDENTIALS_CONFIG_PATH, GENERAL_CONFIG_PATH, DEFAULT_RESEARCH_IMAGE
from lean.constants import DEFAULT_ENGINE_IMAGE, CONTAINER_LABEL_LEAN_VERSION_NAME
from lean.models.docker import DockerImage


class Container:

    def __init__(self):
        self.project_config_manager = None
        self.cli_config_manager = None
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
        self.temp_manager = TempManager(self.logger)
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

        self.docker_manager = docker_manager
        if not self.docker_manager:
            self.docker_manager = DockerManager(self.logger, self.temp_manager, self.platform_manager)

        self.project_manager = ProjectManager(self.logger,
                                              self.project_config_manager,
                                              self.lean_config_manager,
                                              self.path_manager,
                                              self.xml_manager,
                                              self.platform_manager,
                                              self.cli_config_manager,
                                              self.docker_manager)
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
                                        self.platform_manager,
                                        self.organization_manager)

        self.push_manager = push_manager
        if not push_manager:
            self.push_manager = PushManager(self.logger,
                                            self.api_client,
                                            self.project_manager,
                                            self.project_config_manager,
                                            self.organization_manager)
        self.data_downloader = DataDownloader(self.logger,
                                              self.api_client,
                                              self.lean_config_manager,
                                              self.cli_config_manager.database_update_frequency.get_value())
        self.cloud_project_manager = CloudProjectManager(self.api_client,
                                                         self.project_config_manager,
                                                         self.pull_manager,
                                                         self.push_manager,
                                                         self.path_manager,
                                                         self.project_manager,
                                                         self.organization_manager)

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

    def manage_docker_image(self, image: Optional[str], update: bool, no_update: bool,
                            project_directory: Path = None,
                            is_engine_image: bool = True) -> Tuple[DockerImage, str, Optional[Storage]]:
        """
        Manages the Docker image for the LEAN engine by:
        1. Retrieving the engine image from the provided image or project config.
        2. Pulling the image if necessary based on the update flags.
        3. Logging a warning if a custom image is used.

        :param project_directory: Path to the project directory, used to get the project configuration.
        :param image: Optional custom Docker image. Defaults to the project configuration if not provided.
        :param update: Whether to update the Docker image.
        :param no_update: Whether to skip updating the Docker image.
        :param is_engine_image: True to manage the 'engine-image', False to manage the 'research-image'.
        :return: A tuple containing the engine image, its version label, and the project configuration.
        """

        project_config = None
        image_project_config = None
        image_type_name = "engine-image" if is_engine_image else "research-image"
        if project_directory:
            project_config = self.project_config_manager.get_project_config(project_directory)
            image_project_config = project_config.get(image_type_name, None)

        if is_engine_image:
            engine_image = self.cli_config_manager.get_engine_image(image or image_project_config)
        else:
            engine_image = self.cli_config_manager.get_research_image(image or image_project_config)

        container.update_manager.pull_docker_image_if_necessary(engine_image, update, no_update)

        container_module_version = container.docker_manager.get_image_label(
            engine_image, CONTAINER_LABEL_LEAN_VERSION_NAME, None
        )

        default_image_name = DEFAULT_ENGINE_IMAGE if is_engine_image else DEFAULT_RESEARCH_IMAGE
        if str(engine_image) != default_image_name:
            self.logger.warn(f'A custom {image_type_name} image: "{engine_image}" is being used!')

        return engine_image, container_module_version, project_config


container = Container()