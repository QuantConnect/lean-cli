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

from click import Group


class AliasedCommandGroup(Group):
    """A click.Group wrapper that implements command aliasing."""

    def command(self, *args, **kwargs):
        aliases = kwargs.pop('aliases', [])

        if not args:
            cmd_name = kwargs.pop("name", "")
        else:
            cmd_name = args[0]
            args = args[1:]

        alias_help = f"Alias for '{cmd_name}'"

        def _decorator(f):
            # Add the main command
            cmd = super(AliasedCommandGroup, self).command(name=cmd_name, *args, **kwargs)(f)

            # Add a command to the group for each alias with the same callback but using the alias as name
            for alias in aliases:
                alias_cmd = super(AliasedCommandGroup, self).command(name=alias,
                                                                     short_help=alias_help,
                                                                     *args,
                                                                     **kwargs)(f)
                alias_cmd.params = cmd.params

            return cmd

        return _decorator
