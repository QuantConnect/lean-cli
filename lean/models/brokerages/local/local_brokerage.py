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

from typing import Any, Dict
from lean.models.lean_config_configurer import LeanConfigConfigurer


class LocalBrokerage(LeanConfigConfigurer):
    """A JsonModule implementation for the Json brokerage module."""

    def __init__(self, json_brokerage_data: Dict[str, Any]) -> None:
        super().__init__(json_brokerage_data)

    def get_live_name(self, environment_name: str) -> str:
        live_name = self._id
        environment_obj = self.get_configurations_env_values_from_name(
            environment_name)
        if environment_obj:
            [live_name] = [x["value"]
                           for x in environment_obj if x["name"] == "live-mode-brokerage"]
        return live_name
