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

from typing import Any, Callable, Optional, Union, overload

from click import Command, Context, Group


CommandCallback = Callable[..., Any]
CommandDecorator = Callable[[CommandCallback], Command]


class AliasedCommandGroup(Group):
    """A click.Group wrapper that implements command aliasing and autocomplete prefix matching."""

    def get_command(self, ctx: Context, cmd_name: str) -> Optional[Command]:
        rv = super().get_command(ctx, cmd_name)
        if rv is not None:
            return rv

        matches = []
        for name in self.list_commands(ctx):
            command = super().get_command(ctx, name)
            if command is not None and not command.hidden and name.startswith(cmd_name):
                matches.append(name)

        if not matches:
            return None
        elif len(matches) == 1:
            return super().get_command(ctx, matches[0])

        ctx.fail(f"Too many matches: {', '.join(sorted(matches))}")

    @overload
    def command(self, __func: CommandCallback) -> Command:
        ...

    @overload
    def command(self, *args: Any, **kwargs: Any) -> CommandDecorator:
        ...

    def command(self, *args: Any, **kwargs: Any) -> Union[CommandDecorator, Command]:
        aliases = kwargs.pop('aliases', [])

        if not aliases:
            return super().command(*args, **kwargs)

        func = None
        if args and callable(args[0]):
            assert len(args) == 1, "Use 'command(**kwargs)(callable)' to provide arguments."
            func = args[0]
            args = ()

        def _decorator(f: CommandCallback) -> Command:
            cmd_kwargs = dict(kwargs)
            cmd_name = cmd_kwargs.pop("name", None)

            if args:
                if cmd_name is None:
                    cmd_name = args[0]
                    cmd_args = args[1:]
                else:
                    cmd_args = args
            else:
                cmd_name = cmd_name or f.__name__.lower().replace("_", "-")
                cmd_args = ()

            alias_help = f"Alias for '{cmd_name}'"

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

        if func is not None:
            return _decorator(func)

        return _decorator
