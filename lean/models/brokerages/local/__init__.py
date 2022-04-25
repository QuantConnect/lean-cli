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
from lean.models.brokerages.local.json_module_base import LocalBrokerage
from lean.models.json_module_config import LeanConfigConfigurer
import json
from lean.models.brokerages.local.json_brokerage import JsonBrokerage
from lean.models.brokerages.local.iqfeed import IQFeedDataFeed

brokerages = []
dataQueueHandlers = []
historyProviders = [] 
brokeragesAndDataQueueHandlers = {}
json_modules = None

dirname = os.path.dirname(__file__)
filename = os.path.join(dirname, '../../../cli_data.json')
with open(filename) as f: 
    data = json.load(f)
    json_modules = data['modules']   
    for json_module in json_modules:
        if "brokerage" in json_module["type"]:
            brokerage = JsonBrokerage(json_module)
            brokerages.append(brokerage)
        if "data-queue-handler" in json_module["type"]:
            dataQueueHandler = JsonBrokerage(json_module)
            dataQueueHandlers.append(dataQueueHandler)
        if "history-provider" in json_module["type"]:
            pass
        if brokerage != None and dataQueueHandler != None:
            brokeragesAndDataQueueHandlers.update({brokerage:[dataQueueHandler]})
            
all_local_brokerages = brokerages

all_local_data_feeds = dataQueueHandlers

local_brokerage_data_feeds: Dict[Type[LocalBrokerage], List[Type[LeanConfigConfigurer]]] = brokeragesAndDataQueueHandlers

if container.platform_manager().is_host_windows() or os.environ.get("__README__", "false") == "true":
    all_local_data_feeds.append(IQFeedDataFeed)
    for key in local_brokerage_data_feeds.keys():
        local_brokerage_data_feeds[key].append(IQFeedDataFeed)
