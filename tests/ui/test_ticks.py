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

from datetime import datetime, timezone

import pytest

from lean.ui.ticks import format_value_ticks, time_ticks, value_ticks


def _labels(low: float, high: float, max_ticks: int, unit: str = "") -> list:
    ticks, step = value_ticks(low, high, max_ticks)
    return format_value_ticks(ticks, step, unit)


@pytest.mark.parametrize("low,high,max_ticks,unit,expected", [
    (97_980, 100_800, 5, "$", ["$98k", "$99k", "$100k"]),
    (100_000, 236_588, 5, "$", ["$100k", "$150k", "$200k"]),
    (1.394e6, 6.435e6, 5, "$", ["$2M", "$3M", "$4M", "$5M", "$6M"]),
    (-0.84, 0.82, 5, "%", ["-0.5%", "0.0%", "0.5%"]),
    (-1.34, 0, 3, "%", ["-1.0%", "-0.5%", "0.0%"]),
    (0, 1, 5, "", ["0.00", "0.25", "0.50", "0.75", "1.00"]),
])
def test_value_ticks_are_round_and_formatted_with_unit(low, high, max_ticks, unit, expected) -> None:
    assert _labels(low, high, max_ticks, unit) == expected


@pytest.mark.parametrize("low,high,max_ticks", [
    (0.11, 0.14, 2), (0.111, 0.119, 2), (99_839.1, 99_839.6, 3), (-5e-7, 3e-7, 3), (1, 1e9, 3),
])
def test_value_ticks_are_never_empty_and_stay_within_the_range(low, high, max_ticks) -> None:
    ticks, _ = value_ticks(low, high, max_ticks)

    assert 0 < len(ticks) <= max_ticks
    assert all(low - 1e-12 <= t <= high + 1e-12 for t in ticks)


def test_value_ticks_of_a_flat_series() -> None:
    assert value_ticks(5, 5, 4) == ([5], 0.0)


def _timestamp(*args) -> float:
    return datetime(*args, tzinfo=timezone.utc).timestamp()


def test_time_ticks_use_days_for_a_week() -> None:
    _, labels = time_ticks(_timestamp(2013, 10, 7, 4), _timestamp(2013, 10, 11, 20), 6)

    assert labels == ["2013-10-08", "2013-10-09", "2013-10-10", "2013-10-11"]


def test_time_ticks_use_hours_within_a_day() -> None:
    _, labels = time_ticks(_timestamp(2013, 10, 7, 13, 30), _timestamp(2013, 10, 7, 18), 5)

    assert labels == ["10-07 14:00", "10-07 15:00", "10-07 16:00", "10-07 17:00", "10-07 18:00"]


def test_time_ticks_use_years_for_decades() -> None:
    _, labels = time_ticks(_timestamp(2000, 1, 1), _timestamp(2026, 10, 7), 6)

    assert labels == ["2000", "2005", "2010", "2015", "2020", "2025"]


def test_time_ticks_use_months_for_a_year() -> None:
    _, labels = time_ticks(_timestamp(2023, 1, 15), _timestamp(2023, 12, 20), 6)

    assert labels == ["2023-03", "2023-05", "2023-07", "2023-09", "2023-11"]
