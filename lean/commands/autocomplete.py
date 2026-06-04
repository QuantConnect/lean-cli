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

from click import Choice, ClickException, Context, echo, group, option, pass_context

from lean.components.util.click_aliased_command_group import AliasedCommandGroup


SHELL_OPTION = option("--shell",
                      "-s",
                      type=Choice(["powershell", "bash", "zsh", "fish"], case_sensitive=False),
                      default=None,
                      help="Target shell. Auto-detected if not specified.")


def _profile_permission_error(exception: PermissionError) -> ClickException:
    path = exception.filename or "the shell profile"
    return ClickException(
        f"Unable to update {path}. "
        "The current PowerShell session is still disabled if Lean autocomplete was loaded there. "
        "To remove it permanently, close any editor or terminal using that profile, or remove the Lean autocomplete block manually."
    )


@group(cls=AliasedCommandGroup, invoke_without_command=True)
@SHELL_OPTION
@pass_context
def autocomplete(ctx: Context, shell: Optional[str]) -> None:
    """Print the native shell autocomplete script for your shell.

    \b
    PowerShell (current session):
        lean autocomplete --shell powershell | Out-String | Invoke-Expression

    \b
    Bash or Zsh (current session):
        eval "$(lean autocomplete --shell bash)"

    \b
    Fish (current session):
        lean autocomplete --shell fish | source
    """
    if ctx.invoked_subcommand is None:
        from lean.components.util.click_shell_autocomplete import get_autocomplete_script
        echo(get_autocomplete_script(shell))


@autocomplete.command(name="show", help="Print the native shell autocomplete script for your shell")
@SHELL_OPTION
def show(shell: Optional[str]) -> None:
    from lean.components.util.click_shell_autocomplete import get_autocomplete_script
    echo(get_autocomplete_script(shell))


@autocomplete.command(name="on", help="Enable shell autocomplete in your shell profile")
@SHELL_OPTION
def on(shell: Optional[str]) -> None:
    from lean.components.util.click_shell_autocomplete import install_autocomplete
    try:
        profile_path = install_autocomplete(shell)
    except PermissionError as exception:
        raise _profile_permission_error(exception)

    echo(f"Enabled shell autocomplete in {profile_path}")
    echo("Open a new terminal session for the change to take effect.")


@autocomplete.command(name="off", help="Disable shell autocomplete in your shell profile")
@option("--current-session", is_flag=True, help="Print a script that disables autocomplete in the current shell session.")
@SHELL_OPTION
def off(shell: Optional[str], current_session: bool) -> None:
    from lean.components.util.click_shell_autocomplete import get_autocomplete_cleanup_script, uninstall_autocomplete

    if current_session:
        echo(get_autocomplete_cleanup_script(shell))
        return

    try:
        profile_path, removed = uninstall_autocomplete(shell)
    except PermissionError as exception:
        raise _profile_permission_error(exception)

    if removed:
        echo(f"Disabled shell autocomplete in {profile_path}")
        echo("Open a new terminal session for the change to take effect.")
        echo("To disable it in this PowerShell session, run `lean autocomplete off` again after reloading the updated script.")
    else:
        echo(f"Shell autocomplete was not enabled in {profile_path}")
