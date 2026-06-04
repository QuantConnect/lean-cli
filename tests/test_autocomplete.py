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
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from lean.commands import lean
from lean.components.util.click_shell_autocomplete import register_shell_autocomplete


def test_hidden_completion_alias_prints_powershell_script() -> None:
    result = CliRunner().invoke(lean, ["completion", "--shell", "powershell"])

    assert result.exit_code == 0
    assert "Register-ArgumentCompleter -Native -CommandName lean" in result.output
    assert "_LEAN_COMPLETE" in result.output
    assert "Set-PSReadLineOption -PredictionSource HistoryAndPlugin" not in result.output
    assert "Set-PSReadLineKeyHandler -Key Tab -Function MenuComplete" in result.output
    assert "function lean-autocomplete-off" in result.output
    assert "function lean-autocomplete-on" in result.output
    assert "function lean {" in result.output
    assert '__LeanCliExecutable' in result.output
    assert result.output.index("lean-autocomplete-off") < result.output.index("& $lean @args")


def test_autocomplete_command_prints_powershell_script() -> None:
    result = CliRunner().invoke(lean, ["autocomplete", "--shell", "powershell"])

    assert result.exit_code == 0
    assert "Register-ArgumentCompleter -Native -CommandName lean" in result.output
    assert "& $lean autocomplete --shell powershell | Out-String | Invoke-Expression" in result.output


def test_lean_help_shows_autocomplete_not_hidden_completion_alias() -> None:
    result = CliRunner().invoke(lean, ["--help"])

    assert result.exit_code == 0
    assert "autocomplete" in result.output
    assert "completion" not in result.output


def test_click_shell_autocomplete_prints_powershell_source_script() -> None:
    register_shell_autocomplete()

    result = CliRunner().invoke(lean, [], prog_name="lean", env={
        "_LEAN_COMPLETE": "powershell_source"
    })

    assert result.exit_code == 0
    assert "Register-ArgumentCompleter -Native -CommandName lean" in result.output


def test_click_shell_autocomplete_returns_powershell_completions() -> None:
    register_shell_autocomplete()

    result = CliRunner().invoke(lean, [], prog_name="lean", env={
        "_LEAN_COMPLETE": "powershell_complete",
        "COMP_WORDS": "lean cl",
        "COMP_CWORD": "cl"
    })

    assert result.exit_code == 0

    completions = [json.loads(line) for line in result.output.strip().splitlines()]
    completion_values = [item["value"] for item in completions]
    assert "cloud" in completion_values


def test_click_shell_autocomplete_prints_bash_source_script() -> None:
    result = CliRunner().invoke(lean, [], prog_name="lean", env={
        "_LEAN_COMPLETE": "bash_source"
    })

    assert result.exit_code == 0
    assert "complete -o nosort -F" in result.output


def test_hidden_completion_alias_on_writes_powershell_profile() -> None:
    with TemporaryDirectory() as directory, patch.object(Path, "home", return_value=Path(directory)):
        result = CliRunner().invoke(lean, ["completion", "on", "--shell", "powershell"])

        assert result.exit_code == 0

        profile_path = Path(directory) / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
        assert profile_path.exists()

        content = profile_path.read_text(encoding="utf-8")
        assert "# >>> lean autocomplete >>>" in content
        assert "Register-ArgumentCompleter -Native -CommandName lean" in content


def test_autocomplete_on_writes_powershell_profile() -> None:
    with TemporaryDirectory() as directory, patch.object(Path, "home", return_value=Path(directory)):
        result = CliRunner().invoke(lean, ["autocomplete", "on", "--shell", "powershell"])

        assert result.exit_code == 0

        profile_path = Path(directory) / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
        assert profile_path.exists()

        content = profile_path.read_text(encoding="utf-8")
        assert "# >>> lean autocomplete >>>" in content
        assert "Register-ArgumentCompleter -Native -CommandName lean" in content


def test_autocomplete_on_auto_detects_powershell_profile() -> None:
    with TemporaryDirectory() as directory, \
            patch.object(Path, "home", return_value=Path(directory)), \
            patch("lean.components.util.click_shell_autocomplete.system", return_value="Windows"):
        result = CliRunner().invoke(lean, ["autocomplete", "on"])

        assert result.exit_code == 0

        profile_path = Path(directory) / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
        assert profile_path.exists()
        assert "# >>> lean autocomplete >>>" in profile_path.read_text(encoding="utf-8")


def test_hidden_completion_alias_off_removes_legacy_powershell_profile_block() -> None:
    with TemporaryDirectory() as directory, patch.object(Path, "home", return_value=Path(directory)):
        profile_path = Path(directory) / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(
            "# before\n# >>> lean completion >>>\nlean block\n# <<< lean completion <<<\n# after\n",
            encoding="utf-8"
        )

        result = CliRunner().invoke(lean, ["completion", "off", "--shell", "powershell"])

        assert result.exit_code == 0

        content = profile_path.read_text(encoding="utf-8")
        assert "# >>> lean completion >>>" not in content
        assert "# before" in content
        assert "# after" in content
        assert "lean autocomplete off" in result.output


def test_autocomplete_off_removes_powershell_profile_block() -> None:
    with TemporaryDirectory() as directory, patch.object(Path, "home", return_value=Path(directory)):
        profile_path = Path(directory) / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(
            "# before\n# >>> lean autocomplete >>>\nlean block\n# <<< lean autocomplete <<<\n# after\n",
            encoding="utf-8"
        )

        result = CliRunner().invoke(lean, ["autocomplete", "off", "--shell", "powershell"])

        assert result.exit_code == 0
        assert "# >>> lean autocomplete >>>" not in profile_path.read_text(encoding="utf-8")
        assert "lean autocomplete off" in result.output


def test_autocomplete_off_auto_detects_powershell_profile() -> None:
    with TemporaryDirectory() as directory, \
            patch.object(Path, "home", return_value=Path(directory)), \
            patch("lean.components.util.click_shell_autocomplete.system", return_value="Windows"):
        profile_path = Path(directory) / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text(
            "# before\n# >>> lean autocomplete >>>\nlean block\n# <<< lean autocomplete <<<\n# after\n",
            encoding="utf-8"
        )

        result = CliRunner().invoke(lean, ["autocomplete", "off"])

        assert result.exit_code == 0
        assert "# >>> lean autocomplete >>>" not in profile_path.read_text(encoding="utf-8")
        assert "lean autocomplete off" in result.output


def test_autocomplete_off_current_session_prints_powershell_cleanup_script() -> None:
    result = CliRunner().invoke(lean, ["autocomplete", "off", "--shell", "powershell", "--current-session"])

    assert result.exit_code == 0
    assert "Register-ArgumentCompleter -Native -CommandName lean -ScriptBlock { @() }" in result.output
    assert "Set-PSReadLineOption -PredictionSource None" in result.output
    assert "Remove-Item Function:\\lean" in result.output
    assert "function lean-autocomplete-on" in result.output
    assert "autocomplete --shell powershell" in result.output


def test_autocomplete_off_shows_clear_error_when_profile_cannot_be_updated() -> None:
    with patch("lean.components.util.click_shell_autocomplete.uninstall_autocomplete",
               side_effect=PermissionError(13, "Permission denied", "profile.ps1")):
        result = CliRunner().invoke(lean, ["autocomplete", "off", "--shell", "powershell"])

    assert result.exit_code != 0
    assert "Unable to update profile.ps1" in result.output
    assert "The current PowerShell session is still disabled" in result.output
