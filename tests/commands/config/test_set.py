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

from click.testing import CliRunner

from lean.commands import lean
from lean.container import container
from datetime import timedelta
import pytest


def test_config_set_updates_the_value_of_the_option() -> None:
    result = CliRunner().invoke(lean, ["config", "set", "user-id", "12345"])

    assert result.exit_code == 0

    assert container.cli_config_manager.user_id.get_value() == "12345"


@pytest.mark.parametrize("raw_frequency, expected", [("1 days", timedelta(days=1)),
                                                 ("1 hours", timedelta(hours=1)),
                                                 ("1 minutes", timedelta(minutes=1)),
                                                 ("1 seconds", timedelta(seconds=1)),
                                                 ("500 milliseconds", timedelta(milliseconds=500)),
                                                 ("0.5 days", timedelta(hours=12)),
                                                 ("12:30:45", timedelta(hours=12, minutes=30, seconds=45)),
                                                 ("10us", timedelta(microseconds=10)),
                                                 ("365 days", timedelta(days=365)),
                                                 ("10 days 20:30:40", timedelta(days=10, hours=20, minutes=30, seconds=40)),
                                                 ("30 days 23:59:59", timedelta(days=30, hours=23, minutes=59, seconds=59)),
                                                 ("60 days 23:59:59", timedelta(days=60, hours=23, minutes=59, seconds=59)),
                                                 ("1 day 12:30:45", timedelta(days= 1, hours=12, minutes=30, seconds=45)),
                                                 ("2 hours 30 minutes 15 seconds", timedelta(hours=2, minutes=30, seconds=15)),
                                                 ("6 days 23 hours 59 minutes 59 seconds", timedelta(days=6, hours=23, minutes=59, seconds=59)),
                                                 ("1D 5h 30m 45s 10ms 5us", timedelta(days=1, hours=5, minutes=30, seconds=45, milliseconds=10, microseconds=5))])
def test_set_database_update_frequency_works_with_different_timespans(raw_frequency: str, expected: timedelta) -> None:
    result = CliRunner().invoke(lean, ["config", "set", "database-update-frequency", raw_frequency])

    assert result.exit_code == 0

    from pandas import Timedelta
    frequency = Timedelta(raw_frequency)
    assert frequency == expected


def test_config_set_aborts_when_no_option_with_given_key_exists() -> None:
    result = CliRunner().invoke(lean, ["config", "set", "this-option-does-not-exist", "value"])

    assert result.exit_code != 0
