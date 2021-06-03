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

from pathlib import Path
from unittest import mock

import pytest

from lean.components.util.market_hours_database import MarketHoursDatabase
from lean.models.market_hours_database import SecurityType


@pytest.fixture(autouse=True)
def create_market_hours_database() -> None:
    """A pytest fixture which creates a fake market hours database before every test."""
    path = Path.cwd() / "data" / "market-hours" / "market-hours-database.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w+", encoding="utf-8") as file:
        file.write("""
{
  "entries": {
    // Documentation about the Cfd-fxcm-[*] entry
    /*
    Line 1
    Line 2
    Line 3
    */
    "Cfd-fxcm-[*]": {
      "dataTimeZone": "UTC-05",
      "exchangeTimeZone": "UTC-05",
      "sunday": [
        {
          "start": "17:00:00",
          "end": "1.00:00:00",
          "state": "market"
        }
      ],
      "monday": [
        {
          "start": "00:00:00",
          "end": "1.00:00:00",
          "state": "market"
        }
      ],
      "tuesday": [
        {
          "start": "00:00:00",
          "end": "1.00:00:00",
          "state": "market"
        }
      ],
      "wednesday": [
        {
          "start": "00:00:00",
          "end": "1.00:00:00",
          "state": "market"
        }
      ],
      "thursday": [
        {
          "start": "00:00:00",
          "end": "1.00:00:00",
          "state": "market"
        }
      ],
      "friday": [
        {
          "start": "00:00:00",
          "end": "17:00:00",
          "state": "market"
        }
      ],
      "saturday": [],
      "holidays": []
    },
    "Cfd-fxcm-AU200AUD": {
      "dataTimeZone": "UTC",
      "exchangeTimeZone": "UTC",
      "sunday": [
        {
          "start": "22:50:00",
          "end": "1.00:00:00",
          "state": "market"
        }
      ],
      "monday": [
        {
          "start": "00:00:00",
          "end": "05:30:00",
          "state": "market"
        },
        {
          "start": "06:10:00",
          "end": "21:00:00",
          "state": "market"
        },
        {
          "start": "22:50:00",
          "end": "1.00:00:00",
          "state": "market"
        }
      ],
      "tuesday": [
        {
          "start": "00:00:00",
          "end": "05:30:00",
          "state": "market"
        },
        {
          "start": "06:10:00",
          "end": "21:00:00",
          "state": "market"
        },
        {
          "start": "22:50:00",
          "end": "1.00:00:00",
          "state": "market"
        }
      ],
      "wednesday": [
        {
          "start": "00:00:00",
          "end": "05:30:00",
          "state": "market"
        },
        {
          "start": "06:10:00",
          "end": "21:00:00",
          "state": "market"
        },
        {
          "start": "22:50:00",
          "end": "1.00:00:00",
          "state": "market"
        }
      ],
      "thursday": [
        {
          "start": "00:00:00",
          "end": "05:30:00",
          "state": "market"
        },
        {
          "start": "06:10:00",
          "end": "21:00:00",
          "state": "market"
        },
        {
          "start": "22:50:00",
          "end": "1.00:00:00",
          "state": "market"
        }
      ],
      "friday": [
        {
          "start": "00:00:00",
          "end": "05:30:00",
          "state": "market"
        },
        {
          "start": "06:10:00",
          "end": "21:00:00",
          "state": "market"
        }
      ],
      "saturday": [],
      "holidays": [
        "1/2/2017",
        "1/26/2017",
        "4/14/2017",
        "4/17/2017",
        "4/25/2017",
        "6/12/2017",
        "12/25/2017",
        "12/26/2017",
        "1/1/2018",
        "1/26/2018",
        "3/30/2018",
        "4/2/2018",
        "4/25/2018",
        "6/11/2018",
        "12/25/2018",
        "12/26/2018",
        "1/1/2019",
        "1/28/2019",
        "4/19/2019",
        "4/22/2019",
        "4/25/2019",
        "6/10/2019",
        "12/25/2019",
        "12/26/2019",
        "1/1/2020",
        "1/27/2020",
        "4/10/2020",
        "4/13/2020",
        "4/27/2020",
        "6/8/2020",
        "12/25/2020",
        "12/26/2020",
        "1/1/2021",
        "1/26/2021",
        "4/2/2021",
        "4/5/2021",
        "4/26/2021",
        "6/14/2021",
        "12/27/2021",
        "12/28/2021",
        "1/3/2022",
        "1/26/2022",
        "4/15/2022",
        "4/18/2022",
        "4/25/2022",
        "6/13/2022",
        "12/26/2022",
        "12/27/2022"
      ]
    }
  }
}
        """)


def test_get_entry_returns_entry_scoped_to_symbol() -> None:
    lean_config_manager = mock.Mock()
    lean_config_manager.get_data_directory.return_value = Path.cwd() / "data"

    market_hours_database = MarketHoursDatabase(lean_config_manager)
    entry = market_hours_database.get_entry(SecurityType.CFD, "fxcm", "AU200AUD")

    assert len(entry.monday) > 0
    assert len(entry.tuesday) > 0
    assert len(entry.wednesday) > 0
    assert len(entry.thursday) > 0
    assert len(entry.friday) > 0
    assert len(entry.saturday) == 0
    assert len(entry.sunday) > 0

    assert len(entry.holidays) > 0


def test_get_entry_returns_entry_scoped_to_wildcard() -> None:
    lean_config_manager = mock.Mock()
    lean_config_manager.get_data_directory.return_value = Path.cwd() / "data"

    market_hours_database = MarketHoursDatabase(lean_config_manager)
    entry = market_hours_database.get_entry(SecurityType.CFD, "fxcm", "XXXXXX")

    assert len(entry.monday) > 0
    assert len(entry.tuesday) > 0
    assert len(entry.wednesday) > 0
    assert len(entry.thursday) > 0
    assert len(entry.friday) > 0
    assert len(entry.saturday) == 0
    assert len(entry.sunday) > 0

    assert len(entry.holidays) == 0


def test_get_entry_raises_when_entry_does_not_exist() -> None:
    lean_config_manager = mock.Mock()
    lean_config_manager.get_data_directory.return_value = Path.cwd() / "data"

    market_hours_database = MarketHoursDatabase(lean_config_manager)

    with pytest.raises(Exception):
        market_hours_database.get_entry(SecurityType.CFD, "fake-market", "XXXXXX")
