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

from click import Choice, Context, echo, group, option, pass_context

from lean.components.util.click_aliased_command_group import AliasedCommandGroup
from lean.components.util.click_shell_completion import get_completion_script, install_completion, uninstall_completion


SHELL_OPTION = option("--shell",
                      "-s",
                      type=Choice(["powershell", "bash", "zsh", "fish"], case_sensitive=False),
                      default=None,
                      help="Target shell. Auto-detected if not specified.")


@group(cls=AliasedCommandGroup, invoke_without_command=True)
@SHELL_OPTION
@pass_context
def completion(ctx: Context, shell: Optional[str]) -> None:
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
    if ctx.invoked_subcommand is None:
        echo(get_completion_script(shell))


@completion.command(name="show", help="Print the native shell completion script for your shell")
@SHELL_OPTION
def show(shell: Optional[str]) -> None:
    echo(get_completion_script(shell))


@completion.command(name="on", help="Enable shell completion in your shell profile")
@SHELL_OPTION
def on(shell: Optional[str]) -> None:
    profile_path = install_completion(shell)
    echo(f"Enabled shell completion in {profile_path}")
    echo("Open a new terminal session for the change to take effect.")


@completion.command(name="off", help="Disable shell completion in your shell profile")
@SHELL_OPTION
def off(shell: Optional[str]) -> None:
    profile_path, removed = uninstall_completion(shell)

    if removed:
        echo(f"Disabled shell completion in {profile_path}")
        echo("Open a new terminal session for the change to take effect.")
    else:
        echo(f"Shell completion was not enabled in {profile_path}")
