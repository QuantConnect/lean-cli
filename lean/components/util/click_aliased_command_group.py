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
    """A click.Group wrapper that implements command aliasing and auto-completion/prefix matching."""

    def get_command(self, ctx, cmd_name):
        rv = super().get_command(ctx, cmd_name)
        if rv is not None:
            return rv

        matches = [x for x in self.list_commands(ctx) if x.startswith(cmd_name)]

        if not matches:
            return None
        elif len(matches) == 1:
            return super().get_command(ctx, matches[0])

        ctx.fail(f"Too many matches: {', '.join(sorted(matches))}")

    def command(self, *args, **kwargs):
        aliases = kwargs.pop('aliases', [])

        if not aliases:
            return super().command(*args, **kwargs)

        def _decorator(f):
            if args:
                cmd_name = args[0]
                cmd_args = args[1:]
            else:
                cmd_name = kwargs.get("name", f.__name__.lower().replace("_", "-"))
                cmd_args = ()

            alias_help = f"Alias for '{cmd_name}'"
            cmd_kwargs = dict(kwargs)
            cmd_kwargs.pop("name", None)

            # Add the main command
            cmd = super(AliasedCommandGroup, self).command(*cmd_args, name=cmd_name, **cmd_kwargs)(f)

            # Add a command to the group for each alias with the same callback but using the alias as name
            for alias in aliases:
                alias_cmd = super(AliasedCommandGroup, self).command(name=alias,
                                                                     short_help=alias_help,
                                                                     *cmd_args,
                                                                     **cmd_kwargs)(f)
                alias_cmd.params = cmd.params

            return cmd

        return _decorator
