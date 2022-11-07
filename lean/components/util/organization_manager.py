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

from typing import Optional, Any, Dict

from lean.components.api.api_client import APIClient
from lean.components.config.lean_config_manager import LeanConfigManager
from lean.components.util.logger import Logger


class OrganizationManager:
    """The OrganizationManager class provides utilities to handle the working organization."""

    def __init__(self, logger: Logger, api_client: APIClient, lean_config_manager: LeanConfigManager) -> None:
        """Creates a new OrganizationManager instance.

        :param logger: the logger to use to log messages with
        :param api_client: the API client to use to fetch organizations info
        :param lean_config_manager: the LeanConfigManager to use to manipulate the lean configuration file
        """
        self._logger = logger
        self._api_client = api_client
        self._lean_config_manager = lean_config_manager

    def get_working_organization_id(self, lean_config: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Gets the id of the working organization in the current Lean CLI directory.

        It gets the organization id from the given lean config (if passed).
        Otherwise, it will get it from the lean config manager.

        :return: the id of the working organization or None to use the default/preferred organization
        :raises: Abort: if the user is using an old CLI folder and wants to abort the operation.
        """

        from click import confirm

        lean_config_to_use = lean_config if lean_config is not None else self._lean_config_manager.get_lean_config()
        organization_id = lean_config_to_use.get("organization-id")

        if organization_id is not None:
            return organization_id

        confirm(
            "This is an old Lean CLI root folder. "
            "Please create a new folder for each organization you are a member of  and run `lean init` in it.\n"
            "You can continue using the CLI here but your preferred organization is going to be used from now on.\n"
            "Do you wish to continue?",
            default=False,
            abort=True)

        # Proceed with the operation using the preferred organization
        organizations = self._api_client.organizations.get_all()
        organization = next(iter(organization for organization in organizations if organization.preferred), None)

        if organization is None:
            raise RuntimeError("No preferred organization was found. Please try again later.")

        return organization.id

    def configure_working_organization_id(self, organization_id: str,
                                          lean_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Configures the working organization id in the Lean config

        It will save the organization id either in the given Lean config or using the lean config manager.

        :param organization_id: the working organization di
        :param lean_config: the optional lean config where the organization should be saved to
        """
        if lean_config is not None:
            lean_config["organization-id"] = organization_id
            return

        self._lean_config_manager.set_properties({"organization-id": organization_id})
