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

from lean.models.brokerages.cloud.bitfinex import BitfinexBrokerage
from lean.models.brokerages.cloud.coinbase_pro import CoinbaseProBrokerage
from lean.models.brokerages.cloud.interactive_brokers import InteractiveBrokersBrokerage
from lean.models.brokerages.cloud.oanda import OANDABrokerage
from lean.models.brokerages.cloud.paper_trading import PaperTradingBrokerage
from lean.models.brokerages.cloud.tradier import TradierBrokerage

all_cloud_brokerages = [
    PaperTradingBrokerage,
    InteractiveBrokersBrokerage,
    TradierBrokerage,
    OANDABrokerage,
    BitfinexBrokerage,
    CoinbaseProBrokerage
]
