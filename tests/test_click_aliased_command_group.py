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

import click
from click.testing import CliRunner

from lean.components.util.click_aliased_command_group import AliasedCommandGroup


def test_aliased_command_group_takes_named_name_parameter() -> None:
    @click.command(cls=AliasedCommandGroup)
    def group() -> None:
        pass

    @group.command(aliases=["some-other-command"], name="some-command")
    def command() -> None:
        pass

    result = CliRunner().invoke(command)

    assert result.exit_code == 0


def test_aliased_command_group_takes_positional_name_parameter() -> None:
    @click.command(cls=AliasedCommandGroup)
    def group() -> None:
        pass

    @group.command("some-command", aliases=["some-other-command"])
    def command() -> None:
        pass

    result = CliRunner().invoke(command)

    assert result.exit_code == 0


def test_aliased_command_group_creates_command_for_each_alias() -> None:
    @click.command(cls=AliasedCommandGroup)
    def group() -> None:
        pass

    command_name = "some-command"
    aliases = [f"alias-{i}" for i in range(5)]
    main_command_doc = "some command doc string"

    @group.command(command_name, aliases=aliases, help=main_command_doc)
    def command() -> None:
        pass

    command_names = [command_name] + aliases
    assert len(group.commands) == len(command_names)
    assert all(name in command_names for name in group.commands.keys())

    result = CliRunner().invoke(group, ["--help"])

    assert result.exit_code == 0

    commands_help = result.output.split("Commands:\n")[-1].split("\n")
    commands_help = [command_help.strip() for command_help in commands_help]
    commands_help = [command_help for command_help in commands_help if command_help]

    assert len(commands_help) == len(command_names)

    aliases_help = [command_help
                    for command_help in commands_help if any(name in command_help for name in aliases)]
    main_command_help = [command_help
                         for command_help in commands_help if command_help.strip().startswith(command_name)][0]

    assert len(aliases_help) == len(aliases_help)
    assert all(f"Alias for '{command_name}'" in alias_help for alias_help in aliases_help)
    assert main_command_doc in main_command_help


def test_aliased_command_group_resolves_unique_prefix_match() -> None:
    @click.group(cls=AliasedCommandGroup)
    def group() -> None:
        pass

    @group.command()
    def cloud() -> None:
        click.echo("cloud")

    result = CliRunner().invoke(group, ["cl"])

    assert result.exit_code == 0
    assert result.output == "cloud\n"


def test_aliased_command_group_fails_when_prefix_is_ambiguous() -> None:
    @click.group(cls=AliasedCommandGroup)
    def group() -> None:
        pass

    @group.command()
    def cloud() -> None:
        pass

    @group.command()
    def config() -> None:
        pass

    result = CliRunner().invoke(group, ["c"])

    assert result.exit_code != 0
    assert "Too many matches: cloud, config" in result.output


def test_aliased_command_group_ignores_hidden_commands_for_prefix_matching() -> None:
    @click.group(cls=AliasedCommandGroup)
    def group() -> None:
        pass

    @group.command(hidden=True)
    def completion() -> None:
        click.echo("completion")

    @group.command()
    def cloud() -> None:
        click.echo("cloud")

    prefix_result = CliRunner().invoke(group, ["c"])
    exact_result = CliRunner().invoke(group, ["completion"])

    assert prefix_result.exit_code == 0
    assert prefix_result.output == "cloud\n"
    assert exact_result.exit_code == 0
    assert exact_result.output == "completion\n"
