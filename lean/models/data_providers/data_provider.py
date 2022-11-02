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

class DataProvider(LeanConfigConfigurer):
    """A JsonModule implementation for the Json data provider module."""

    def __init__(self, json_data_provider_data: Dict[str, Any]) -> None:
        super().__init__(json_data_provider_data)

    def configure_credentials(self, lean_config: Dict[str, Any]) -> None:
        super().configure_credentials(lean_config)
        self._save_properties(
            lean_config, self.get_non_user_required_properties())
