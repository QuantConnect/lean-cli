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

from lean.constants import MODULE_BROKERAGE, MODULE_TYPE, MODULE_CLOUD_PLATFORM, MODULE_PLATFORM, \
    MODULE_DATA_QUEUE_HANDLER
from lean.models import json_modules
from lean.models.json_module import JsonModule

# load the modules
cloud_brokerages: List[JsonModule] = []
cloud_data_queue_handlers: List[JsonModule] = []

for json_module in json_modules:
    module_type = json_module[MODULE_TYPE]
    platform = json_module[MODULE_PLATFORM]

    if MODULE_CLOUD_PLATFORM in platform:
        if MODULE_BROKERAGE in module_type:
            cloud_brokerages.append(JsonModule(json_module, MODULE_BROKERAGE, MODULE_CLOUD_PLATFORM))
        if MODULE_DATA_QUEUE_HANDLER in module_type:
            cloud_data_queue_handlers.append(JsonModule(json_module, MODULE_DATA_QUEUE_HANDLER, MODULE_CLOUD_PLATFORM))
