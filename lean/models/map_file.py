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

from datetime import datetime, timedelta
from typing import List, Optional

from lean.models.pydantic import WrappedBaseModel


class MapFileEntry(WrappedBaseModel):
    date: datetime
    ticker: str


class MapFileRange(WrappedBaseModel):
    ticker: str
    start_date: datetime
    end_date: datetime
    end_event: Optional[str]

    def get_label(self) -> str:
        label = f"{self.start_date.strftime('%Y-%m-%d')} - {self.end_date.strftime('%Y-%m-%d')}"

        if self.end_event is not None:
            label += f" ({self.end_event})"

        return label


class MapFile:
    """The MapFile class handles extracting useful information out of map files."""

    def __init__(self, entries: List[MapFileEntry]) -> None:
        """Creates a new MapFile instance.

        :param entries: the entries of this map file
        """
        self._ranges: List[MapFileRange] = []

        current_start = None
        for i, entry in enumerate(entries):
            if current_start is not None:
                if i + 1 < len(entries):
                    end_event = f"changed name to {entries[i + 1].ticker}"
                elif entry.date.year != 2050:
                    end_event = "delisted"
                else:
                    end_event = None

                self._ranges.append(MapFileRange(ticker=entry.ticker,
                                                 start_date=current_start,
                                                 end_date=entry.date - timedelta(days=1),
                                                 end_event=end_event))

            current_start = entry.date

    def get_ticker_ranges(self, ticker: str, start_date: datetime, end_date: datetime) -> List[MapFileRange]:
        """Returns the date ranges between two dates during which this map file's symbol traded as the given ticker.

        :param ticker: the ticker to get the date ranges for
        :param start_date: the inclusive start date to look for
        :param end_date: the inclusive end date to look for
        :return: a list of ranges indicating when this map file's symbol traded as the ticker within the given dates
        """
        ranges = []

        for r in self._ranges:
            if r.ticker != ticker.upper():
                continue

            if r.start_date > end_date or r.end_date < start_date:
                continue

            range_start = max(r.start_date, start_date)
            range_end = min(r.end_date, end_date)

            ranges.append(MapFileRange(ticker=r.ticker,
                                       start_date=range_start,
                                       end_date=range_end,
                                       end_event=r.end_event if range_end == r.end_date else None))

        return ranges

    def get_historic_ranges(self, start_date: datetime) -> List[MapFileRange]:
        """Returns the historical tickers of this map file's symbol which may be interested to the user.

        :param start_date: the inclusive start date the user selected
        :return: a list of date ranges to offer to the user, descending by time
        """
        ranges = []
        current_start_date = start_date

        for r in reversed(self._ranges):
            if r.end_date < current_start_date and (current_start_date - r.end_date).days < 5:
                ranges.append(r)
                current_start_date = r.start_date

        return ranges

    @classmethod
    def parse(cls, file_content: str) -> 'MapFile':
        """Parses a map file.

        :param file_content: the content of the map file
        :return: the parsed map file
        """
        entries = []
        for line in file_content.splitlines():
            parts = line.split(",")
            entries.append(MapFileEntry(date=datetime.strptime(parts[0], "%Y%m%d"), ticker=parts[1].upper()))

        return MapFile(entries)
