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
from typing import List

from lean.constants import MODULE_BROKERAGE, MODULE_TYPE, MODULE_PLATFORM, MODULE_CLI_PLATFORM, \
    MODULE_DATA_DOWNLOADER, MODULE_HISTORY_PROVIDER, MODULE_DATA_QUEUE_HANDLER, MODULE_ADDON, MODULE_COMPUTE
from lean.models import json_modules
from lean.models.json_module import JsonModule

# load the modules
cli_brokerages: List[JsonModule] = []
cli_addon_modules: List[JsonModule] = []
cli_data_downloaders: List[JsonModule] = []
cli_history_provider: List[JsonModule] = []
cli_data_queue_handlers: List[JsonModule] = []
cli_compute: List[JsonModule] = []

for json_module in json_modules:
    module_type = json_module[MODULE_TYPE]
    platform = json_module[MODULE_PLATFORM]

    if MODULE_CLI_PLATFORM in platform:
        if MODULE_BROKERAGE in module_type:
            cli_brokerages.append(JsonModule(json_module, MODULE_BROKERAGE, MODULE_CLI_PLATFORM))
        if MODULE_DATA_DOWNLOADER in module_type:
            cli_data_downloaders.append(JsonModule(json_module, MODULE_DATA_DOWNLOADER, MODULE_CLI_PLATFORM))
        if MODULE_HISTORY_PROVIDER in module_type:
            cli_history_provider.append(JsonModule(json_module, MODULE_HISTORY_PROVIDER, MODULE_CLI_PLATFORM))
        if MODULE_DATA_QUEUE_HANDLER in module_type:
            cli_data_queue_handlers.append(JsonModule(json_module, MODULE_DATA_QUEUE_HANDLER, MODULE_CLI_PLATFORM))
        if MODULE_ADDON in module_type:
            cli_addon_modules.append(JsonModule(json_module, MODULE_ADDON, MODULE_CLI_PLATFORM))
        if MODULE_COMPUTE in module_type:
            cli_compute.append(JsonModule(json_module, MODULE_COMPUTE, MODULE_CLI_PLATFORM))
