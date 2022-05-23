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
from lean.models.data_providers.data_provider import DataProvider
from lean.models import json_modules

all_data_providers: List[DataProvider] = []

for json_module in json_modules:
    if "data-provider" in json_module["type"]:
        all_data_providers.append(DataProvider(json_module))

# QuantConnect DataProvider
[QuantConnectDataProvider] = [
    data_provider for data_provider in all_data_providers if data_provider._id == "QuantConnect"]
