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

# This program automatically updates the commands reference part of the readme
# It should be ran using `python scripts/readme.py` from the root of the project

import os

os.environ["__README__"] = "true"

import re
from pathlib import Path
from typing import List

from click import Command, Group
from click.testing import CliRunner

from lean.commands import lean
from lean.models.pydantic import WrappedBaseModel
from lean.components.util.click_group_default_command import DefaultCommandGroup
from lean.container import container

class NamedCommand(WrappedBaseModel):
    name: str
    command: Command

    class Config:
        arbitrary_types_allowed = True


def get_commands(group: Group, parent_names: List[str] = []) -> List[NamedCommand]:
    """Returns all lean commands by name.

    :param group: the group to get the commands from
    :param parent_names: the names of the groups leading up to the current group
    :return: a list containing all commands in the current group with their full names
    """
    all_commands = []

    for obj in group.commands.values():
        if isinstance(obj, DefaultCommandGroup):
            name_parts = parent_names + [group.name, obj.name]
            all_commands.append(NamedCommand(name=" ".join(name_parts), command=obj))
        if isinstance(obj, Group):
            all_commands.extend(get_commands(obj, parent_names + [group.name]))
        else:
            name_parts = parent_names + [group.name, obj.name]
            all_commands.append(NamedCommand(name=" ".join(name_parts), command=obj))

    return all_commands


def get_header_id(name: str) -> str:
    """Returns the id of the header with the given name in a GitHub readme.

    :param name: the name of the header to get the id of
    :return: the id of the header with the given name when rendered on GitHub
    """
    name = name.lower()
    name = re.sub(r"\s", "-", name)
    name = re.sub(r"[^a-zA-Z0-9-]", "", name)
    return name

def get_configurations() -> List[dict]:
    """Returns all available configurations with their keys and descriptions."""
    config_manager = container.cli_config_manager
    configurations = []

    for option in config_manager.all_options:
        configurations.append({
            "key": option.key,
            "description": option.description
        })

    return configurations

def generate_configurations_table(configurations: List[dict]) -> str:
    """Generates a Markdown table for the given configurations."""
    table = ["| Key | Description |", "| --- | --- |"]

    for config in configurations:
        table.append(f"| `{config['key']}` | {config['description']} |")

    return "\n".join(table)


def main() -> None:
    named_commands = get_commands(lean)
    #print(named_commands)
    named_commands = sorted(named_commands, key=lambda c: c.name)

    table_of_contents = []
    command_sections = []

    for c in named_commands:
        #print(c)
        header = f"### `{c.name}`"
        help_str = c.command.get_short_help_str(limit=120)

        help_output = CliRunner().invoke(c.command, ["--help"], prog_name=c.name, terminal_width=120).output.strip()
        help_output = f"```\n{help_output}\n```"

        command_source = None
        if not isinstance(c.command, DefaultCommandGroup):
            command_source = f"lean/commands/{c.name.replace('lean ', '').replace(' ', '/').replace('-', '_')}.py"
            command_source = f"_See code: [{command_source}]({command_source})_"

        section_parts = [header, help_str, help_output, command_source]

        table_of_contents.append(f"- [`{c.name}`](#{get_header_id(c.name)})")
        command_sections.append("\n\n".join(filter(None, section_parts)))

    configurations = get_configurations()
    configurations_table = generate_configurations_table(configurations)
    full_text = "\n".join(table_of_contents) + "\n\n"
    full_text += "## Configurations\n\n" + configurations_table + "\n\n"
    full_text += "\n\n".join(command_sections)
    full_text = "\n".join(["<!-- commands start -->", full_text, "<!-- commands end -->"])

    readme_path = Path.cwd() / "README.md"
    readme_content = readme_path.read_text(encoding="utf-8")

    readme_content = re.sub(r"<!-- commands start -->.*<!-- commands end -->",
                            full_text,
                            readme_content,
                            flags=re.DOTALL)

    readme_path.write_text(readme_content, encoding="utf-8")


if __name__ == "__main__":
    main()
    
