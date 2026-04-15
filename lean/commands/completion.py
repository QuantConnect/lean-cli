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

from typing import Optional

from click import Choice, command, echo, option

from lean.components.util.click_shell_completion import get_completion_script


@command()
@option("--shell",
        "-s",
        type=Choice(["powershell", "bash", "zsh", "fish"], case_sensitive=False),
        default=None,
        help="Target shell. Auto-detected if not specified.")
def completion(shell: Optional[str]) -> None:
    """Print the native shell completion script for your shell.

    \b
    PowerShell (current session):
        lean completion --shell powershell | Out-String | Invoke-Expression

    \b
    Bash or Zsh (current session):
        eval "$(lean completion --shell bash)"

    \b
    Fish (current session):
        lean completion --shell fish | source
    """
    echo(get_completion_script(shell))
