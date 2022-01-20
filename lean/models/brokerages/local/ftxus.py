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

from typing import Any, Dict, List

import click

from lean.components.util.logger import Logger
from lean.constants import FTXUS_PRODUCT_ID
from lean.container import container
from lean.models.brokerages.local.base import LocalBrokerage
from lean.models.brokerages.local.ftx import FTXBrokerage
from lean.models.brokerages.local.ftx import FTXDataFeed
from lean.models.config import LeanConfigConfigurer
from lean.models.logger import Option


class FTXUSBrokerage(FTXBrokerage):
    """A LocalBrokerage implementation for the FTX.US brokerage."""

    def __init__(self, organization_id: str, api_key: str, api_secret: str, account_tier: str) -> None:
        super().__init__(organization_id, api_key, api_secret, account_tier)

    @classmethod
    def get_name(cls) -> str:
        return "FTX.US"

    @classmethod
    def get_module_id(cls) -> int:
        return FTXUS_PRODUCT_ID

    @classmethod
    def get_domain(cls) -> str:
        return "ftx.us"

    @classmethod
    def data_queue_handler_name(cls) -> str:
        return "FTXUSBrokerage"
    
    @classmethod
    def property_prefix(cls) -> str:
        return "ftxus"

    @classmethod
    def account_tier_options(cls) -> List[Option]:
        return [Option(id="Tier1", label="Tier1"),
             Option(id="Tier2", label="Tier2"),
             Option(id="Tier3", label="Tier3"),
             Option(id="Tier4", label="Tier4"),
             Option(id="Tier5", label="Tier5"),
             Option(id="Tier6", label="Tier6"),
             Option(id="Tier7", label="Tier7"),
             Option(id="Tier8", label="Tier8"),
             Option(id="Tier9", label="Tier9"),
             Option(id="VIP1", label="VIP1"),
             Option(id="VIP2", label="VIP2"),
             Option(id="MM1", label="MM1"),
             Option(id="MM2", label="MM2"),
             Option(id="MM3", label="MM3")]

class FTXUSDataFeed(FTXDataFeed):
    """A LeanConfigConfigurer implementation for the FTX.US data feed."""

    def __init__(self, brokerage: FTXUSBrokerage) -> None:
        super().__init__(brokerage)

    @classmethod
    def data_queue_handler_name(cls) -> str:
        return "FTXUSBrokerage"

    @classmethod
    def get_name(cls) -> str:
        return FTXUSBrokerage.get_name()

    @classmethod
    def build(cls, lean_config: Dict[str, Any], logger: Logger) -> LeanConfigConfigurer:
        return FTXUSDataFeed(FTXUSBrokerage.build(lean_config, logger))
