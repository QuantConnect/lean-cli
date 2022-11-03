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


def test_config_unset_removes_the_value_of_the_option() -> None:
    container.cli_config_manager.user_id.set_value("12345")

    result = CliRunner().invoke(lean, ["config", "unset", "user-id"])

    assert result.exit_code == 0

    assert container.cli_config_manager.user_id.get_value() is None


def test_config_unset_aborts_when_no_option_with_given_key_exists() -> None:
    result = CliRunner().invoke(lean, ["config", "unset", "this-option-does-not-exist"])

    assert result.exit_code != 0
