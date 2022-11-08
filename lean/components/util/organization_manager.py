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

from typing import Optional

from lean.components.config.lean_config_manager import LeanConfigManager
from lean.components.util.logger import Logger


class OrganizationManager:
    """The OrganizationManager class provides utilities to handle the working organization."""

    def __init__(self, logger: Logger, lean_config_manager: LeanConfigManager) -> None:
        """Creates a new OrganizationManager instance.

        :param logger: the logger to use to log messages with
        :param api_client: the API client to use to fetch organizations info
        :param lean_config_manager: the LeanConfigManager to use to manipulate the lean configuration file
        """
        self._logger = logger
        self._lean_config_manager = lean_config_manager

        self._working_organization_id = None

    def get_working_organization_id(self) -> Optional[str]:
        """Gets the id of the working organization in the current Lean CLI directory.

        :return: the id of the working organization. None if the organization id was not found in the lean config
        """
        if self._working_organization_id is None:
            lean_config = self._lean_config_manager.get_lean_config()
            self._working_organization_id = lean_config.get("organization-id")

        return self._working_organization_id

    def try_get_working_organization_id(self) -> Optional[str]:
        """Gets the id of the working organization in the current Lean CLI directory.

        :return: the id of the working organization
        :raises RuntimeError: if the working organization is not found in the lean config
        """
        organization_id = self.get_working_organization_id()

        if organization_id is None:
            raise RuntimeError(
                "The working organization for this Lean CLI folder could not be determined.\n"
                "Make sure you run `lean init` on an empty folder for each organization you are a member of")

        return organization_id

    def configure_working_organization_id(self, organization_id: str) -> None:
        """
        Configures the working organization id in the Lean config

        :param organization_id: the working organization di
        """
        self._lean_config_manager.set_properties({"organization-id": organization_id})
        self._working_organization_id = organization_id
