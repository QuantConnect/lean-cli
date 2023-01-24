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

from click import command, Group

from lean.models.errors import MoreInfoError


class AnyCommandGroup(Group):
    """A command group that can be used to have single action to perform on any command or sub-command in the group,
    regardless of the sub-command name.

    For instance, the following would raise an exception on any of these calls:
    `mycommand`, `mycommand subcommand`, `mycommand anothersubcommand`, etc.

    ```
@command(cls=AnyCommandGroup, invoke_without_command=True)
def mycommand() -> None:
    raise MoreInfoError("Message")
    ```
    """

    def get_command(self, ctx, cmd_name):
        # always return the same command for any sub-command
        return self

    def resolve_command(self, ctx, args):
        _, cmd, args = super().resolve_command(ctx, args)
        return cmd.name, cmd, args


@command(cls=AnyCommandGroup, invoke_without_command=True)
def gui() -> None:
    """Work with the local GUI."""
    # This method is only used to warn users about GUI deprecation and point them to the new VSCode extension.
    raise MoreInfoError(
        "The LEAN GUI was deprecated in 2019 and has been replaced by a VSCode extension "
        "which allows seamless local and cloud quantitative research. "
        "See more information in the VSCode Marketplace.",
        "https://marketplace.visualstudio.com/items?itemName=quantconnect.quantconnect")
