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

from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from lean.constants import DEFAULT_LEAN_CONFIG_FILE_NAME
from lean.container import container


def parse_config_option(ctx: click.Context, param: click.Parameter, value: Optional[Path]) -> None:
    """Parses the --config option."""
    if value is not None:
        lean_config_manager = container.lean_config_manager()
        lean_config_manager.set_default_lean_config_path(value)


def parse_verbose_option(ctx: click.Context, param: click.Parameter, value: Optional[bool]) -> None:
    """Parses the --verbose option."""
    if value:
        logger = container.logger()
        logger.enable_debug_logging()


class LeanCommand(click.Command):
    """A click.Command wrapper with some Lean CLI customization."""

    def __init__(self, requires_lean_config: bool = False, *args, **kwargs):
        """Creates a new LeanCommand instance.

        :param requires_lean_config: True if this command requires a Lean config, False if not
        :param args: the args that are passed on to the click.Command constructor
        :param kwargs: the kwargs that are passed on to the click.Command constructor
        """
        self._requires_lean_config = requires_lean_config

        super().__init__(*args, **kwargs)

        # By default the width of help messages is min(terminal_width, max_content_width)
        # max_content_width defaults to 80, which we increase to 120 to improve readability on wide terminals
        self.context_settings["max_content_width"] = 120

    def invoke(self, ctx):
        if self._requires_lean_config:
            try:
                # This method will throw if the directory cannot be found
                container.lean_config_manager().get_cli_root_directory()
            except Exception:
                # Abort with a display-friendly error message if the command requires a Lean config
                raise RuntimeError(
                    "This command requires a Lean configuration file, run `lean init` in an empty directory to create one, or specify the file to use with --lean-config")

        result = super().invoke(ctx)

        update_manager = container.update_manager()
        update_manager.warn_if_cli_outdated()

        return result

    def get_params(self, ctx):
        params = super().get_params(ctx)

        # Add --lean-config option if the command requires a Lean config
        if self._requires_lean_config:
            params.insert(len(params) - 1, click.Option(["--lean-config"],
                                                        type=PathParameter(exists=True, file_okay=True, dir_okay=False),
                                                        help=f"The Lean configuration file that should be used (defaults to the nearest {DEFAULT_LEAN_CONFIG_FILE_NAME})",
                                                        expose_value=False,
                                                        is_eager=True,
                                                        callback=parse_config_option))

        # Add --verbose option
        params.insert(len(params) - 1, click.Option(["--verbose"],
                                                    help="Enable debug logging",
                                                    is_flag=True,
                                                    default=False,
                                                    expose_value=False,
                                                    is_eager=True,
                                                    callback=parse_verbose_option))

        return params


class PathParameter(click.ParamType):
    """A limited version of click.Path which uses pathlib.Path."""

    def __init__(self, exists: bool = False, file_okay: bool = True, dir_okay: bool = True):
        """Creates a new PathParameter instance.

        :param exists: True if the path needs to point to an existing object, False if not
        :param file_okay: True if the path may point to a file, False if not
        :param dir_okay: True if the path may point to a directory, False if not
        """
        self._exists = exists
        self._file_okay = file_okay
        self._dir_okay = dir_okay

        if file_okay and not dir_okay:
            self.name = "file"
            self._path_type = "File"
        elif dir_okay and not file_okay:
            self.name = "directory"
            self._path_type = "Directory"
        else:
            self.name = "path"
            self._path_type = "Path"

    def convert(self, value: str, param: click.Parameter, ctx: click.Context) -> Path:
        path = Path(value).expanduser().resolve()

        if self._exists and not path.exists():
            self.fail(f"{self._path_type} '{value}' does not exist.", param, ctx)

        if not self._file_okay and path.is_file():
            self.fail(f"{self._path_type} '{value}' is a file.", param, ctx)

        if not self._dir_okay and path.is_dir():
            self.fail(f"{self._path_type} '{value}' is a directory.", param, ctx)

        return path


class DateParameter(click.ParamType):
    """A click parameter which returns datetime.datetime objects and requires yyyyMMdd input."""

    name = "date"

    def get_metavar(self, param: click.Parameter) -> str:
        return "[yyyyMMdd]"

    def convert(self, value: str, param: click.Parameter, ctx: click.Context) -> datetime:
        try:
            return datetime.strptime(value, "%Y%m%d")
        except ValueError:
            self.fail(f"'{value}' does not match the yyyyMMdd format.", param, ctx)
