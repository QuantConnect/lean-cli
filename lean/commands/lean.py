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

from click import group, option, Context, pass_context, echo

from lean import __version__
from lean.click import verbose_option
from lean.components.util.click_aliased_command_group import AliasedCommandGroup
from lean.container import container


@group(cls=AliasedCommandGroup, invoke_without_command=True)
@option("--version", is_flag=True, is_eager=True, help="Show the version and exit.")
@verbose_option()
@pass_context
def lean(ctx: Context, version: bool) -> None:
    """The Lean CLI by QuantConnect."""
    # This method is used as the command group for all `lean <command>` commands

    if ctx.invoked_subcommand is None:
        if version:
            program_name = ctx.find_root().info_name
            container.logger.info(f"{program_name} {__version__}")
            ctx.exit()
        else:
            echo(ctx.get_help())
