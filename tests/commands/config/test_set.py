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


@pytest.mark.parametrize("frequency, expected", [("1:0:0:0", timedelta(days=1)),
                                                 ("0:1:0:0", timedelta(hours=1)),
                                                 ("0:0:1:0", timedelta(minutes=1)),
                                                 ("0:0:0:1", timedelta(seconds=1)),
                                                 ("01:00:00:00", timedelta(days=1)),
                                                 ("00:01:00:00", timedelta(hours=1)),
                                                 ("00:00:01:00", timedelta(minutes=1)),
                                                 ("00:00:00:01", timedelta(seconds=1)),
                                                 ("1:00:00:00", timedelta(days=1)),
                                                 ("00:1:00:00", timedelta(hours=1)),
                                                 ("00:00:1:00", timedelta(minutes=1)),
                                                 ("00:00:00:1", timedelta(seconds=1)),
                                                 ("00:1:00:1", timedelta(hours=1, seconds=1)),
                                                 ("00:1:1:1", timedelta(hours=1, minutes=1, seconds=1)),
                                                 ("1:1:1:1", timedelta(days=1, hours=1, minutes=1, seconds=1)),
                                                 ("10:20:30:40", timedelta(days=10, hours=20, minutes=30, seconds=40)),
                                                 ("30:23:59:59", timedelta(days=30, hours=23, minutes=59, seconds=59)),
                                                 ("60:23:59:59", timedelta(days=60, hours=23, minutes=59, seconds=59))])
def test_set_database_update_frequency_works_with_different_timespans(frequency: str, expected: timedelta) -> None:
    result = CliRunner().invoke(lean, ["config", "set", "database-update-frequency", frequency])

    assert result.exit_code == 0
    days, hours, minutes, seconds = map(int, container.cli_config_manager.database_update_frequency.get_value().split(":"))
    frequency = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
    assert frequency == expected


def test_config_set_aborts_when_no_option_with_given_key_exists() -> None:
    result = CliRunner().invoke(lean, ["config", "set", "this-option-does-not-exist", "value"])

    assert result.exit_code != 0
