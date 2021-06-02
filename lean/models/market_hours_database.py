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

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

from pydantic import validator

from lean.models.pydantic import WrappedBaseModel


class MarketHoursSegment(WrappedBaseModel):
    start: str
    end: str
    state: str


class MarketHoursDatabaseEntry(WrappedBaseModel):
    dataTimeZone: str
    exchangeTimeZone: str
    monday: List[MarketHoursSegment] = []
    tuesday: List[MarketHoursSegment] = []
    wednesday: List[MarketHoursSegment] = []
    thursday: List[MarketHoursSegment] = []
    friday: List[MarketHoursSegment] = []
    saturday: List[MarketHoursSegment] = []
    sunday: List[MarketHoursSegment] = []
    holidays: List[datetime] = []
    earlyCloses: Dict[str, str] = {}
    lateOpens: Dict[str, str] = {}

    @validator("holidays", pre=True)
    def parse_holidays(cls, value: Any) -> Any:
        if isinstance(value, list):
            return [datetime.strptime(x, "%m/%d/%Y") for x in value]
        return value


class SecurityType(str, Enum):
    CFD = "CFD"
    Crypto = "Crypto"
    Equity = "Equity"
    EquityOption = "Equity option"
    Forex = "Forex"
    Future = "Future"
    FutureOption = "Future option"
    Index = "Index"
    IndexOption = "Index option"

    def get_internal_name(self) -> str:
        """Returns the internal name of the security type.

        :return: the name of the security type in LEAN
        """
        return {
            SecurityType.CFD: "Cfd",
            SecurityType.Crypto: "Crypto",
            SecurityType.Equity: "Equity",
            SecurityType.EquityOption: "Option",
            SecurityType.Forex: "Forex",
            SecurityType.Future: "Future",
            SecurityType.FutureOption: "FutureOption",
            SecurityType.Index: "Index",
            SecurityType.IndexOption: "IndexOption"
        }[self]
