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
import json
from lean.models.brokerages.local.local_brokerage import LocalBrokerage
from lean.models.brokerages.local.data_feed import DataFeed
from lean.models.data_providers.data_provider import DataProvider
from lean.models.brokerages.cloud.cloud_brokerage import CloudBrokerage

all_local_brokerages: List[LocalBrokerage] = []
all_local_data_feeds: List[DataFeed] = []
all_data_providers: List[DataFeed] = [] 
local_brokerage_data_feeds: Dict[Type[LocalBrokerage], List[Type[DataFeed]]] = {}
all_cloud_brokerages: List[DataFeed] = []

dirname = os.path.dirname(__file__)
filename = os.path.join(dirname, '../../../cli_data.json')
with open(filename) as f: 
    data = json.load(f)
    json_modules = data['modules']   
    for json_module in json_modules:
        brokerage = dataQueueHandler = dataProviders = None
        if "brokerage" in json_module["type"]:
            brokerage = LocalBrokerage(json_module)
            all_local_brokerages.append(brokerage)
        if "data-queue-handler" in json_module["type"]:
            dataQueueHandler = DataFeed(json_module)
            all_local_data_feeds.append(dataQueueHandler)
        if "data-provider" in json_module["type"]:
            all_data_providers.append(DataProvider(json_module))
        if "cloud-brokerage" in json_module["type"]:
            all_cloud_brokerages.append(CloudBrokerage(json_module))
        if "history-provider" in json_module["type"]:
            pass
        if brokerage is not None and dataQueueHandler is not None:
            local_brokerage_data_feeds.update({brokerage:[dataQueueHandler]})

#IQFeed DataFeed for windows
if container.platform_manager().is_host_windows() or os.environ.get("__README__", "false") == "true":
    [iqfeed_data_feed] = [data_feed for data_feed in all_local_data_feeds if data_feed.get_name() == "IQFeed"]
    for key in local_brokerage_data_feeds.keys():
        local_brokerage_data_feeds[key].append(iqfeed_data_feed)
# remove iqfeed from avaiable local data feeds if not windows
else:
    all_local_data_feeds = [data_feed for data_feed in all_local_data_feeds if data_feed.get_name() != "IQFeed"]

# QuantConnect DataProvider
[QuantConnectDataProvider] = [data_provider for data_provider in all_data_providers if data_provider.get_name() == "QuantConnect"]

[PaperTradingBrokerage] = [cloud_brokerage for cloud_brokerage in all_cloud_brokerages if cloud_brokerage.get_name() == "Paper Trading"]

#add all_local_data_feeds to paper trading brokerage, once IQFEED has been remove from all_local_data_feeds, in case of MAC
[LocalPaperTradingBrokerage] = [local_brokerage for local_brokerage in all_local_brokerages if local_brokerage.get_name() == "Paper Trading"]
local_brokerage_data_feeds[LocalPaperTradingBrokerage] = all_local_data_feeds
