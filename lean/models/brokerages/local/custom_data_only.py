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
from lean.models.config import LeanConfigConfigurer


class CustomDataOnlyDataFeed(LeanConfigConfigurer):
    """A LeanConfigConfigurer implementation for the custom data only data feed."""

    @classmethod
    def get_name(cls) -> str:
        return "Custom data only"

    @classmethod
    def build(cls, lean_config: Dict[str, Any], logger: Logger) -> LeanConfigConfigurer:
        return CustomDataOnlyDataFeed()

    def configure(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        lean_config["environments"][environment_name]["data-queue-handler"] = \
            "QuantConnect.Lean.Engine.DataFeeds.Queues.LiveDataQueue"
