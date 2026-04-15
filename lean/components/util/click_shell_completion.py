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
import os
from pathlib import Path
from platform import system
from typing import Optional

from click.shell_completion import ShellComplete, add_completion_class, get_completion_class, split_arg_string

_SOURCE_POWERSHELL = r"""
Register-ArgumentCompleter -Native -CommandName %(prog_name)s -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $Env:%(complete_var)s = "powershell_complete"
    $Env:COMP_WORDS = $commandAst.ToString()
    $Env:COMP_CWORD = $wordToComplete

    try {
        & %(prog_name)s | ForEach-Object {
            if ([string]::IsNullOrWhiteSpace($_)) {
                return
            }

            $item = $_ | ConvertFrom-Json
            $tooltip = if ($item.help) { $item.help } else { $item.value }

            [System.Management.Automation.CompletionResult]::new(
                $item.value,
                $item.value,
                'ParameterValue',
                $tooltip
            )
        }
    } finally {
        Remove-Item Env:%(complete_var)s -ErrorAction SilentlyContinue
        Remove-Item Env:COMP_WORDS -ErrorAction SilentlyContinue
        Remove-Item Env:COMP_CWORD -ErrorAction SilentlyContinue
    }
}
"""


class PowerShellComplete(ShellComplete):
    """Shell completion for PowerShell."""

    name = "powershell"
    source_template = _SOURCE_POWERSHELL

    def get_completion_args(self) -> tuple[list[str], str]:
        cwords = split_arg_string(os.environ.get("COMP_WORDS", ""))
        incomplete = os.environ.get("COMP_CWORD", "")
        args = cwords[1:]

        if incomplete and args and args[-1] == incomplete:
            args.pop()

        return args, incomplete

    def format_completion(self, item) -> str:
        return json.dumps({
            "type": item.type,
            "value": item.value,
            "help": item.help or ""
        }, separators=(",", ":"))


def register_shell_completion() -> None:
    if get_completion_class(PowerShellComplete.name) is None:
        add_completion_class(PowerShellComplete)


def detect_shell() -> str:
    """Auto-detect the current shell environment."""
    if system() == "Windows":
        return "powershell"

    shell_path = os.environ.get("SHELL", "/bin/bash")
    shell_name = Path(shell_path).name.lower()

    if "zsh" in shell_name:
        return "zsh"

    if "fish" in shell_name:
        return "fish"

    return "bash"


def get_completion_script(shell: Optional[str], prog_name: str = "lean") -> str:
    register_shell_completion()

    shell_name = (shell or detect_shell()).lower()
    complete_var = f"_{prog_name.replace('-', '_').replace('.', '_')}_COMPLETE".upper()
    completion_class = get_completion_class(shell_name)

    if completion_class is None:
        supported_shells = ", ".join(sorted(["bash", "fish", "powershell", "zsh"]))
        raise RuntimeError(f"Unsupported shell '{shell_name}'. Supported shells: {supported_shells}")

    return completion_class(None, {}, prog_name, complete_var).source()
