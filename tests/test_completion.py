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

import json

from click.testing import CliRunner

from lean.commands import lean


def test_completion_command_prints_powershell_script() -> None:
    result = CliRunner().invoke(lean, ["completion", "--shell", "powershell"])

    assert result.exit_code == 0
    assert "Register-ArgumentCompleter -Native -CommandName lean" in result.output
    assert "_LEAN_COMPLETE" in result.output


def test_click_shell_completion_prints_powershell_source_script() -> None:
    result = CliRunner().invoke(lean, [], prog_name="lean", env={
        "_LEAN_COMPLETE": "powershell_source"
    })

    assert result.exit_code == 0
    assert "Register-ArgumentCompleter -Native -CommandName lean" in result.output


def test_click_shell_completion_returns_powershell_completions() -> None:
    result = CliRunner().invoke(lean, [], prog_name="lean", env={
        "_LEAN_COMPLETE": "powershell_complete",
        "COMP_WORDS": "lean cl",
        "COMP_CWORD": "cl"
    })

    assert result.exit_code == 0

    completions = [json.loads(line) for line in result.output.strip().splitlines()]
    completion_values = [item["value"] for item in completions]
    assert "cloud" in completion_values


def test_click_shell_completion_prints_bash_source_script() -> None:
    result = CliRunner().invoke(lean, [], prog_name="lean", env={
        "_LEAN_COMPLETE": "bash_source"
    })

    assert result.exit_code == 0
    assert "complete -o nosort -F" in result.output
