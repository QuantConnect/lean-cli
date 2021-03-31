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
from typing import Any, Dict, List, Optional

from pydantic import validator

from lean.models.api import QCResolution, QCSecurityType
from lean.models.pydantic import WrappedBaseModel


class DataFile(WrappedBaseModel):
    path: str
    security_type: QCSecurityType
    ticker: str
    market: str
    resolution: QCResolution
    date: Optional[datetime]

    def get_url(self) -> str:
        """Returns the link to the data in QuantConnect's Data Library."""
        if self.resolution == QCResolution.Daily or self.resolution == QCResolution.Hour:
            return f"https://www.quantconnect.com/data/file/{self.path}/{self.ticker.lower()}.csv"
        else:
            type = self.security_type.value.lower()
            resolution = self.resolution.value.lower()
            return f"https://www.quantconnect.com/data/tree/{type}/{self.market}/{resolution}/{self.ticker.lower()}"


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
