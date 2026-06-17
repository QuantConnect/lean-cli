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

try {
    Set-PSReadLineKeyHandler -Key Tab -Function MenuComplete -ErrorAction SilentlyContinue
} catch {}

function __LeanCliExecutable {
    $command = Get-Command %(prog_name)s -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command) {
        return $command.Source
    }

    return "%(prog_name)s"
}

function lean-autocomplete-off {
    Register-ArgumentCompleter -Native -CommandName lean -ScriptBlock { @() }

    try {
        Set-PSReadLineOption -PredictionSource None -ErrorAction SilentlyContinue
    } catch {}

    Write-Output "Disabled Lean autocomplete for this PowerShell session."
    Remove-Item Function:\lean -ErrorAction SilentlyContinue
    Remove-Item Function:\lean-autocomplete-on -ErrorAction SilentlyContinue
    Remove-Item Function:\lean-autocomplete-off -ErrorAction SilentlyContinue
    Remove-Item Function:\__LeanCliExecutable -ErrorAction SilentlyContinue
}

function lean-autocomplete-on {
    $lean = __LeanCliExecutable
    & $lean autocomplete --shell powershell | Out-String | Invoke-Expression
}

function lean {
    $lean = __LeanCliExecutable

    if ($args.Count -ge 2 -and ($args[0] -eq "completion" -or $args[0] -eq "autocomplete") -and $args[1] -eq "off") {
        lean-autocomplete-off
        & $lean @args
        return
    }

    if ($args.Count -ge 2 -and ($args[0] -eq "completion" -or $args[0] -eq "autocomplete") -and $args[1] -eq "on") {
        & $lean @args
        lean-autocomplete-on
        return
    }

    & $lean @args
}
"""


class PowerShellComplete(ShellComplete):
    """Shell autocomplete for PowerShell."""

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


def register_shell_autocomplete() -> None:
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


def get_autocomplete_script(shell: Optional[str], prog_name: str = "lean") -> str:
    register_shell_autocomplete()

    shell_name = (shell or detect_shell()).lower()
    complete_var = f"_{prog_name.replace('-', '_').replace('.', '_')}_COMPLETE".upper()
    completion_class = get_completion_class(shell_name)

    if completion_class is None:
        supported_shells = ", ".join(sorted(["bash", "fish", "powershell", "zsh"]))
        raise RuntimeError(f"Unsupported shell '{shell_name}'. Supported shells: {supported_shells}")

    return completion_class(None, {}, prog_name, complete_var).source()


def get_autocomplete_cleanup_script(shell: Optional[str], prog_name: str = "lean") -> str:
    shell_name = (shell or detect_shell()).lower()

    if shell_name == "powershell":
        return f"""
Register-ArgumentCompleter -Native -CommandName {prog_name} -ScriptBlock {{ @() }}

try {{
    Set-PSReadLineOption -PredictionSource None -ErrorAction SilentlyContinue
}} catch {{}}

Remove-Item Function:\\lean -ErrorAction SilentlyContinue
Remove-Item Function:\\lean-autocomplete-on -ErrorAction SilentlyContinue
Remove-Item Function:\\lean-autocomplete-off -ErrorAction SilentlyContinue
Remove-Item Function:\\__LeanCliExecutable -ErrorAction SilentlyContinue

function lean-autocomplete-on {{
    & {prog_name} autocomplete --shell powershell | Out-String | Invoke-Expression
}}
""".strip()

    return ""


def get_profile_path(shell: Optional[str]) -> Path:
    shell_name = (shell or detect_shell()).lower()

    if shell_name == "powershell":
        if system() == "Windows":
            return Path.home() / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"

        return Path.home() / ".config" / "powershell" / "Microsoft.PowerShell_profile.ps1"

    if shell_name == "zsh":
        return Path.home() / ".zshrc"

    if shell_name == "fish":
        return Path.home() / ".config" / "fish" / "completions" / "lean.fish"

    return Path.home() / ".bashrc"


def install_autocomplete(shell: Optional[str], prog_name: str = "lean") -> Path:
    profile_path = get_profile_path(shell)
    marker_start = "# >>> lean autocomplete >>>"
    marker_end = "# <<< lean autocomplete <<<"
    script = get_autocomplete_script(shell, prog_name).strip()

    content = profile_path.read_text(encoding="utf-8") if profile_path.exists() else ""
    if marker_start in content:
        return profile_path

    profile_path.parent.mkdir(parents=True, exist_ok=True)
    block = f"\n{marker_start}\n{script}\n{marker_end}\n"

    with profile_path.open("a", encoding="utf-8") as file:
        file.write(block)

    return profile_path


def uninstall_autocomplete(shell: Optional[str]) -> tuple[Path, bool]:
    profile_path = get_profile_path(shell)

    if not profile_path.exists():
        return profile_path, False

    content = profile_path.read_text(encoding="utf-8")
    markers = [
        ("# >>> lean autocomplete >>>", "# <<< lean autocomplete <<<"),
        ("# >>> lean completion >>>", "# <<< lean completion <<<")
    ]

    start_index = -1
    end_index = -1
    for marker_start, marker_end in markers:
        start_index = content.find(marker_start)
        if start_index == -1:
            continue

        end_index = content.find(marker_end, start_index)
        if end_index != -1:
            break

    if start_index == -1 or end_index == -1:
        return profile_path, False

    end_index += len(marker_end)
    new_content = content[:start_index].rstrip("\n")
    tail = content[end_index:].lstrip("\n")

    if new_content and tail:
        new_content = f"{new_content}\n{tail}"
    elif tail:
        new_content = tail
    elif new_content:
        new_content = f"{new_content}\n"

    profile_path.write_text(new_content, encoding="utf-8")
    return profile_path, True
