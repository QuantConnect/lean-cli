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

from lean.models.map_file import MapFile, MapFileEntry


def test_get_ticker_ranges_returns_all_ranges_between_two_dates_where_map_file_trades_as_ticker() -> None:
    map_file = MapFile([MapFileEntry(date=datetime(2000, 1, 1), ticker="ABC"),
                        MapFileEntry(date=datetime(2000, 2, 1), ticker="ABC"),
                        MapFileEntry(date=datetime(2000, 3, 1), ticker="ABCD"),
                        MapFileEntry(date=datetime(2000, 4, 1), ticker="ABC"),
                        MapFileEntry(date=datetime(2000, 5, 1), ticker="ABCD"),
                        MapFileEntry(date=datetime(2000, 6, 1), ticker="ABC")])

    ranges = map_file.get_ticker_ranges("ABC", datetime(2000, 2, 1), datetime(2000, 6, 1))

    assert len(ranges) == 2

    assert ranges[0].ticker == "ABC"
    assert ranges[0].start_date == datetime(2000, 3, 1)
    assert ranges[0].end_date == datetime(2000, 3, 31)

    assert ranges[1].ticker == "ABC"
    assert ranges[1].start_date == datetime(2000, 5, 1)
    assert ranges[1].end_date == datetime(2000, 5, 31)


def test_get_ticker_ranges_bounds_ranges_between_given_start_and_end_date() -> None:
    map_file = MapFile([MapFileEntry(date=datetime(2000, 1, 1), ticker="ABC"),
                        MapFileEntry(date=datetime(2000, 2, 1), ticker="ABC"),
                        MapFileEntry(date=datetime(2000, 3, 1), ticker="ABCD"),
                        MapFileEntry(date=datetime(2000, 4, 1), ticker="ABC"),
                        MapFileEntry(date=datetime(2000, 5, 1), ticker="ABCD"),
                        MapFileEntry(date=datetime(2000, 6, 1), ticker="ABC")])

    ranges = map_file.get_ticker_ranges("ABC", datetime(2000, 3, 5), datetime(2000, 5, 25))

    assert len(ranges) == 2

    assert ranges[0].ticker == "ABC"
    assert ranges[0].start_date == datetime(2000, 3, 5)
    assert ranges[0].end_date == datetime(2000, 3, 31)

    assert ranges[1].ticker == "ABC"
    assert ranges[1].start_date == datetime(2000, 5, 1)
    assert ranges[1].end_date == datetime(2000, 5, 25)


def test_get_ticker_ranges_returns_empty_list_when_map_file_never_traded_as_given_ticker() -> None:
    map_file = MapFile([MapFileEntry(date=datetime(2000, 1, 1), ticker="ABC"),
                        MapFileEntry(date=datetime(2000, 2, 1), ticker="ABC"),
                        MapFileEntry(date=datetime(2000, 3, 1), ticker="ABCD"),
                        MapFileEntry(date=datetime(2000, 4, 1), ticker="ABC"),
                        MapFileEntry(date=datetime(2000, 5, 1), ticker="ABCD"),
                        MapFileEntry(date=datetime(2000, 6, 1), ticker="ABC")])

    ranges = map_file.get_ticker_ranges("ABCDE", datetime(2000, 2, 1), datetime(2000, 6, 1))

    assert len(ranges) == 0


def test_get_ticker_ranges_sets_end_event_to_delisted_correctly() -> None:
    map_file = MapFile([MapFileEntry(date=datetime(2000, 1, 1), ticker="ABC"),
                        MapFileEntry(date=datetime(2000, 2, 1), ticker="ABC"),
                        MapFileEntry(date=datetime(2000, 3, 1), ticker="ABCD"),
                        MapFileEntry(date=datetime(2000, 4, 1), ticker="ABC"),
                        MapFileEntry(date=datetime(2000, 5, 1), ticker="ABCD"),
                        MapFileEntry(date=datetime(2000, 6, 1), ticker="ABC")])

    ranges = map_file.get_ticker_ranges("ABC", datetime(2000, 2, 1), datetime(2000, 6, 1))

    assert ranges[1].end_event == "delisted"


def test_get_ticker_ranges_sets_end_event_to_rename_correctly() -> None:
    map_file = MapFile([MapFileEntry(date=datetime(2000, 1, 1), ticker="ABC"),
                        MapFileEntry(date=datetime(2000, 2, 1), ticker="ABC"),
                        MapFileEntry(date=datetime(2000, 3, 1), ticker="ABCD"),
                        MapFileEntry(date=datetime(2000, 4, 1), ticker="ABC"),
                        MapFileEntry(date=datetime(2000, 5, 1), ticker="ABCD"),
                        MapFileEntry(date=datetime(2000, 6, 1), ticker="ABC")])

    ranges = map_file.get_ticker_ranges("ABC", datetime(2000, 2, 1), datetime(2000, 6, 1))

    assert ranges[0].end_event == "changed name to ABCD"


def test_get_historic_ranges_returns_historic_tickers_starting_from_start_date() -> None:
    map_file = MapFile([MapFileEntry(date=datetime(2000, 1, 1), ticker="ABC"),
                        MapFileEntry(date=datetime(2000, 2, 1), ticker="ABC"),
                        MapFileEntry(date=datetime(2000, 3, 1), ticker="ABCD"),
                        MapFileEntry(date=datetime(2000, 4, 1), ticker="ABC"),
                        MapFileEntry(date=datetime(2000, 5, 1), ticker="ABCD"),
                        MapFileEntry(date=datetime(2000, 6, 1), ticker="ABC")])

    ranges = map_file.get_historic_ranges(datetime(2000, 3, 1))

    assert len(ranges) == 2

    assert ranges[0].ticker == "ABCD"
    assert ranges[0].start_date == datetime(2000, 2, 1)
    assert ranges[0].end_date == datetime(2000, 2, 29)

    assert ranges[1].ticker == "ABC"
    assert ranges[1].start_date == datetime(2000, 1, 1)
    assert ranges[1].end_date == datetime(2000, 1, 31)


def test_get_historic_ranges_returns_empty_list_when_start_date_not_at_boundary() -> None:
    map_file = MapFile([MapFileEntry(date=datetime(2000, 1, 1), ticker="ABC"),
                        MapFileEntry(date=datetime(2000, 2, 1), ticker="ABC"),
                        MapFileEntry(date=datetime(2000, 3, 1), ticker="ABCD"),
                        MapFileEntry(date=datetime(2000, 4, 1), ticker="ABC"),
                        MapFileEntry(date=datetime(2000, 5, 1), ticker="ABCD"),
                        MapFileEntry(date=datetime(2000, 6, 1), ticker="ABC")])

    ranges = map_file.get_historic_ranges(datetime(2000, 4, 15))

    assert len(ranges) == 0
