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


def test_lean_shows_help_when_called_without_arguments() -> None:
    result = CliRunner().invoke(lean, [])

    assert result.exit_code == 0
    assert "Usage: lean [OPTIONS] COMMAND [ARGS]..." in result.output


def test_lean_shows_help_when_called_with_help_option() -> None:
    result = CliRunner().invoke(lean, ["--help"])

    assert result.exit_code == 0
    assert "Usage: lean [OPTIONS] COMMAND [ARGS]..." in result.output


def test_lean_shows_error_when_running_unknown_command() -> None:
    result = CliRunner().invoke(lean, ["this-command-does-not-exist"])

    assert result.exit_code != 0
    assert "No such command" in result.output
