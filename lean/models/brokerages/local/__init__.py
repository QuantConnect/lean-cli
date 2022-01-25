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
from lean.models.brokerages.local.atreyu import AtreyuBrokerage
from lean.models.brokerages.local.base import LocalBrokerage
from lean.models.brokerages.local.binance import BinanceBrokerage, BinanceDataFeed
from lean.models.brokerages.local.bitfinex import BitfinexBrokerage, BitfinexDataFeed
from lean.models.brokerages.local.terminal_link import TerminalLinkBrokerage, TerminalLinkDataFeed
from lean.models.brokerages.local.coinbase_pro import CoinbaseProBrokerage, CoinbaseProDataFeed
from lean.models.brokerages.local.custom_data_only import CustomDataOnlyDataFeed
from lean.models.brokerages.local.interactive_brokers import InteractiveBrokersBrokerage, InteractiveBrokersDataFeed
from lean.models.brokerages.local.iqfeed import IQFeedDataFeed
from lean.models.brokerages.local.oanda import OANDABrokerage, OANDADataFeed
from lean.models.brokerages.local.paper_trading import PaperTradingBrokerage
from lean.models.brokerages.local.tradier import TradierBrokerage, TradierDataFeed
from lean.models.brokerages.local.trading_technologies import TradingTechnologiesBrokerage, TradingTechnologiesDataFeed
from lean.models.brokerages.local.zerodha import ZerodhaBrokerage, ZerodhaDataFeed
from lean.models.brokerages.local.samco import SamcoBrokerage, SamcoDataFeed
from lean.models.brokerages.local.kraken import KrakenBrokerage, KrakenDataFeed
from lean.models.brokerages.local.ftx import FTXBrokerage, FTXDataFeed
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
    SamcoBrokerage,
    TerminalLinkBrokerage,
    AtreyuBrokerage,
    TradingTechnologiesBrokerage,
    KrakenBrokerage,
    FTXBrokerage
]

all_local_data_feeds = [
    InteractiveBrokersDataFeed,
    TradierDataFeed,
    OANDADataFeed,
    BitfinexDataFeed,
    CoinbaseProDataFeed,
    BinanceDataFeed,
    ZerodhaDataFeed,
    SamcoDataFeed,
    TerminalLinkDataFeed,
    TradingTechnologiesDataFeed,
    CustomDataOnlyDataFeed,
    KrakenDataFeed,
    FTXDataFeed
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
    SamcoBrokerage: [SamcoDataFeed],
    TerminalLinkBrokerage: [TerminalLinkDataFeed],
    AtreyuBrokerage: [x for x in all_local_data_feeds if x != CustomDataOnlyDataFeed],
    TradingTechnologiesBrokerage: [TradingTechnologiesDataFeed],
    KrakenBrokerage: [KrakenDataFeed],
    FTXBrokerage: [FTXDataFeed]
}

if container.platform_manager().is_host_windows() or os.environ.get("__README__", "false") == "true":
    all_local_data_feeds.append(IQFeedDataFeed)
    for key in local_brokerage_data_feeds.keys():
        local_brokerage_data_feeds[key].append(IQFeedDataFeed)
