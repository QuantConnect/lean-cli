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
import platform
from typing import Dict, Type, List

from lean.models.brokerages.local.atreyu import AtreyuBrokerage
from lean.models.brokerages.local.base import LocalBrokerage
from lean.models.brokerages.local.binance import BinanceBrokerage, BinanceDataFeed
from lean.models.brokerages.local.bitfinex import BitfinexBrokerage, BitfinexDataFeed
from lean.models.brokerages.local.bloomberg import BloombergBrokerage, BloombergDataFeed
from lean.models.brokerages.local.coinbase_pro import CoinbaseProBrokerage, CoinbaseProDataFeed
from lean.models.brokerages.local.interactive_brokers import InteractiveBrokersBrokerage, InteractiveBrokersDataFeed
from lean.models.brokerages.local.iqfeed import IQFeedDataFeed
from lean.models.brokerages.local.oanda import OANDABrokerage, OANDADataFeed
from lean.models.brokerages.local.paper_trading import PaperTradingBrokerage
from lean.models.brokerages.local.tradier import TradierBrokerage, TradierDataFeed
from lean.models.brokerages.local.trading_technologies import TradingTechnologiesBrokerage, TradingTechnologiesDataFeed
from lean.models.brokerages.local.zerodha import ZerodhaBrokerage, ZerodhaDataFeed
from lean.models.config import LeanConfigConfigurer

all_local_brokerages = [
    PaperTradingBrokerage,
    InteractiveBrokersBrokerage,
    TradierBrokerage,
    OANDABrokerage,
    BitfinexBrokerage,
    CoinbaseProBrokerage,
    BinanceBrokerage,
    ZerodhaBrokerage,
    BloombergBrokerage,
    AtreyuBrokerage,
    TradingTechnologiesBrokerage
]

all_local_data_feeds = [
    InteractiveBrokersDataFeed,
    TradierDataFeed,
    OANDADataFeed,
    BitfinexDataFeed,
    CoinbaseProDataFeed,
    BinanceDataFeed,
    ZerodhaDataFeed,
    BloombergDataFeed,
    TradingTechnologiesDataFeed
]

local_brokerage_data_feeds: Dict[Type[LocalBrokerage], List[Type[LeanConfigConfigurer]]] = {
    PaperTradingBrokerage: all_local_data_feeds.copy(),
    InteractiveBrokersBrokerage: [InteractiveBrokersDataFeed],
    TradierBrokerage: [TradierDataFeed],
    OANDABrokerage: [OANDADataFeed],
    BitfinexBrokerage: [BitfinexDataFeed],
    CoinbaseProBrokerage: [CoinbaseProDataFeed],
    BinanceBrokerage: [BinanceDataFeed],
    ZerodhaBrokerage: [ZerodhaDataFeed],
    BloombergBrokerage: [BloombergDataFeed],
    AtreyuBrokerage: all_local_data_feeds.copy(),
    TradingTechnologiesBrokerage: [TradingTechnologiesDataFeed]
}

if platform.system() == "Windows" or os.environ.get("__README__", "false") == "true":
    all_local_data_feeds.append(IQFeedDataFeed)
    for key in local_brokerage_data_feeds.keys():
        local_brokerage_data_feeds[key].append(IQFeedDataFeed)
