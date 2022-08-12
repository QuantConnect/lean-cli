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


import json
from decimal import Decimal
from lean.components.util.custom_json_encoder import DecimalEncoder

def test_custom_json_encoder() -> None:

    data = {
        "symbol": "AAPL",
        "market": "usa",
        "security_type": "equity",
        "quantity": Decimal("100.1235")
    }

    assert json.dumps(data, cls=DecimalEncoder) == '{"symbol": "AAPL", "market": "usa", "security_type": "equity", "quantity": "100.1235"}'

