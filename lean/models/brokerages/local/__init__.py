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
from lean.models.brokerages.local.local_brokerage import LocalBrokerage
from lean.models.brokerages.local.data_feed import DataFeed
from lean.models import json_modules

all_local_brokerages: List[LocalBrokerage] = []
all_local_data_feeds: List[DataFeed] = []
local_brokerage_data_feeds: Dict[Type[LocalBrokerage],
                                 List[Type[DataFeed]]] = {}

for json_module in json_modules:
    brokerage = dataQueueHandler = None
    if "local-brokerage" in json_module["type"]:
        brokerage = LocalBrokerage(json_module)
        all_local_brokerages.append(brokerage)
    if "data-queue-handler" in json_module["type"]:
        dataQueueHandler = DataFeed(json_module)
        all_local_data_feeds.append(dataQueueHandler)
    if brokerage is not None and dataQueueHandler is not None:
        local_brokerage_data_feeds.update({brokerage: [dataQueueHandler]})

# IQFeed DataFeed for windows
if container.platform_manager().is_host_windows() or os.environ.get("__README__", "false") == "true":
    [iqfeed_data_feed] = [
        data_feed for data_feed in all_local_data_feeds if data_feed._id == "IQFeed"]
    for key in local_brokerage_data_feeds.keys():
        local_brokerage_data_feeds[key].append(iqfeed_data_feed)
# remove iqfeed from avaiable local data feeds if not windows
else:
    all_local_data_feeds = [
        data_feed for data_feed in all_local_data_feeds if data_feed._id != "IQFeed"]

# add all_local_data_feeds to required brokerages, once IQFEED has been remove from all_local_data_feeds, in case of MAC
[LocalPaperTradingBrokerage] = [
    local_brokerage for local_brokerage in all_local_brokerages if local_brokerage._id == "QuantConnectBrokerage"]
[AtreyuBrokerage] = [
    local_brokerage for local_brokerage in all_local_brokerages if local_brokerage._id == "AtreyuBrokerage"]
local_brokerage_data_feeds[LocalPaperTradingBrokerage] = all_local_data_feeds
local_brokerage_data_feeds[AtreyuBrokerage] = [
    data_feed for data_feed in all_local_data_feeds if data_feed._id != "Custom data only"]
