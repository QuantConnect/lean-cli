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

import os
from typing import Dict, Type, List
from lean.container import container
from lean.models.json_module_config import LeanConfigConfigurer
import json
from lean.models.brokerages.local.json_brokerage import JsonBrokerage
from lean.models.brokerages.local.json_data_feed import JsonDataFeed
from lean.models.brokerages.local.json_module import JsonModule
from lean.models.data_providers.json_data_provider import JsonDataProvider

all_local_brokerages = []
all_local_data_feeds = []
historyProviders = []
all_data_providers = [] 
brokeragesAndDataQueueHandlers = {}

dirname = os.path.dirname(__file__)
filename = os.path.join(dirname, '../../../cli_data.json')
with open(filename) as f: 
    data = json.load(f)
    json_modules = data['modules']   
    for json_module in json_modules:
        brokerage = dataQueueHandler = dataProviders = None
        if "brokerage" in json_module["type"]:
            brokerage = JsonBrokerage(json_module)
            all_local_brokerages.append(brokerage)
        if "data-queue-handler" in json_module["type"]:
            dataQueueHandler = JsonDataFeed(json_module)
            all_local_data_feeds.append(dataQueueHandler)
        if "data-provider" in json_module["type"]:
            dataProviders = JsonDataProvider(json_module)
            all_data_providers.append(dataProviders)
        if "history-provider" in json_module["type"]:
            pass
        if brokerage != None and dataQueueHandler != None:
            brokeragesAndDataQueueHandlers.update({brokerage:[dataQueueHandler]})

local_brokerage_data_feeds: Dict[Type[JsonModule], List[Type[LeanConfigConfigurer]]] = brokeragesAndDataQueueHandlers

if container.platform_manager().is_host_windows() or os.environ.get("__README__", "false") == "true":
    [iqfeed_data_feed] = [data_feed for data_feed in all_local_data_feeds if data_feed.get_name() == "IQFeed"]
    for key in local_brokerage_data_feeds.keys():
        local_brokerage_data_feeds[key].append(iqfeed_data_feed)
# remove iqfeed from avaiable local data feeds
else:
    all_local_data_feeds = [data_feed for data_feed in all_local_data_feeds if data_feed.get_name() != "IQFeed"]

[QuantConnectDataProvider] = [data_provider for data_provider in all_data_providers if data_provider.get_name() == "QuantConnect"]