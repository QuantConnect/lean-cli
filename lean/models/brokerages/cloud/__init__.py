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

from lean.models.brokerages.cloud.cloud_brokerage import CloudBrokerage
from lean.models import json_modules
from typing import Dict, Type, List
from lean.models.brokerages.local.data_feed import DataFeed

all_cloud_brokerages: List[CloudBrokerage] = []
all_cloud_data_feeds: List[DataFeed] = []
cloud_brokerage_data_feeds: Dict[Type[CloudBrokerage],
                                 List[Type[DataFeed]]] = {}

for json_module in json_modules:
    if "cloud-brokerage" in json_module["type"]:
        all_cloud_brokerages.append(CloudBrokerage(json_module))
    if "data-queue-handler" in json_module["type"]:
        all_cloud_data_feeds.append((DataFeed(json_module)))

for cloud_brokerage in all_cloud_brokerages:
    data_feed_property_found = False
    for x in cloud_brokerage.get_all_input_configs():
        if "data-feed" in x.__getattribute__("_id"):
            data_feed_property_found = True
            cloud_brokerage_data_feeds[cloud_brokerage] = x.__getattribute__("_choices")
    if not data_feed_property_found:
        cloud_brokerage_data_feeds[cloud_brokerage] = []

[PaperTradingBrokerage] = [
    cloud_brokerage for cloud_brokerage in all_cloud_brokerages if cloud_brokerage._id == "QuantConnectBrokerage"]
