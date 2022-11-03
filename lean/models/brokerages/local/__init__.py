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

from os import environ
from typing import Dict, Type, List
from lean.container import container
from lean.models.brokerages.local.local_brokerage import LocalBrokerage
from lean.models.brokerages.local.data_feed import DataFeed
from lean.models import json_modules

all_local_brokerages: List[LocalBrokerage] = []
all_local_data_feeds: List[DataFeed] = []
local_brokerage_data_feeds: Dict[Type[LocalBrokerage],
                                 List[Type[DataFeed]]] = {}

for json_module in json_modules:
    if "local-brokerage" in json_module["type"]:
        all_local_brokerages.append(LocalBrokerage(json_module))
    if "data-queue-handler" in json_module["type"]:
        all_local_data_feeds.append(DataFeed(json_module))

# Remove IQFeed DataFeed for other than windows machines
if not [container.platform_manager.is_host_windows() or environ.get("__README__", "false") == "true"]:
    all_local_data_feeds = [
        data_feed for data_feed in all_local_data_feeds if data_feed._id != "IQFeed"]

for local_brokerage in all_local_brokerages:
    local_brokerage_data_feeds[local_brokerage] = all_local_data_feeds
