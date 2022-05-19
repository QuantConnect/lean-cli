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
from typing import List

all_cloud_brokerages: List[CloudBrokerage] = []

for json_module in json_modules:
    if "cloud-brokerage" in json_module["type"]:
        all_cloud_brokerages.append(CloudBrokerage(json_module))

[PaperTradingBrokerage] = [
    cloud_brokerage for cloud_brokerage in all_cloud_brokerages if cloud_brokerage._id == "QuantConnectBrokerage"]
