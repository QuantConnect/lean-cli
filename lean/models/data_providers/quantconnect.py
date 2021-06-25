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

from typing import Dict, Any

from lean.components.util.logger import Logger
from lean.container import container
from lean.models.config import LeanConfigConfigurer
from lean.models.logger import Option


class QuantConnectDataProvider(LeanConfigConfigurer):
    def __init__(self, organization_id: str) -> None:
        self._organization_id = organization_id

    @classmethod
    def get_name(cls) -> str:
        return "QuantConnect"

    @classmethod
    def build(cls, lean_config: Dict[str, Any], logger: Logger) -> LeanConfigConfigurer:
        api_client = container.api_client()

        organizations = api_client.organizations.get_all()
        options = [Option(id=organization.id, label=organization.name) for organization in organizations]

        logger = container.logger()
        organization_id = logger.prompt_list("Select the organization to purchase and download data with", options)

        return QuantConnectDataProvider(organization_id)

    def configure(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        lean_config["job-organization-id"] = self._organization_id
        lean_config["data-provider"] = "QuantConnect.Lean.Engine.DataFeeds.ApiDataProvider"
        lean_config["map-file-provider"] = "QuantConnect.Data.Auxiliary.LocalZipMapFileProvider"
        lean_config["factor-file-provider"] = "QuantConnect.Data.Auxiliary.LocalZipFactorFileProvider"

        self._save_properties(lean_config,
                              ["job-organization-id", "data-provider", "map-file-provider", "factor-file-provider"])
