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

from unittest import mock

from click.testing import CliRunner
from rich.console import ConsoleDimensions

from lean.commands import lean
from lean.container import container


@mock.patch("rich.console.Console.size", new_callable=mock.PropertyMock)
def test_config_list_lists_all_options(size) -> None:
    size.return_value = ConsoleDimensions(1000, 1000)

    result = CliRunner().invoke(lean, ["config", "list"])

    assert result.exit_code == 0

    for option in container.cli_config_manager().all_options:
        assert option.key in result.output
        assert option.description in result.output


@mock.patch("rich.console.Console.size", new_callable=mock.PropertyMock)
def test_config_list_does_not_show_complete_values_of_sensitive_options(size) -> None:
    container.cli_config_manager().user_id.set_value("123")
    container.cli_config_manager().api_token.set_value("abcdefghijklmnopqrstuvwxyz")

    size.return_value = ConsoleDimensions(1000, 1000)

    result = CliRunner().invoke(lean, ["config", "list"])

    assert result.exit_code == 0

    assert "123" not in result.output
    assert "abcdefghijklmnopqrstuvwxyz" not in result.output
