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

import itertools
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List

import click

from lean.constants import DEFAULT_LEAN_CONFIG_FILE_NAME
from lean.container import container
from lean.models.errors import MoreInfoError
from lean.models.logger import Option


class LeanCommand(click.Command):
    """A click.Command wrapper with some Lean CLI customization."""

    def __init__(self,
                 requires_lean_config: bool = False,
                 requires_docker: bool = False,
                 allow_unknown_options: bool = False,
                 *args,
                 **kwargs):
        """Creates a new LeanCommand instance.

        :param requires_lean_config: True if this command requires a Lean config, False if not
        :param requires_docker: True if this command uses Docker, False if not
        :param allow_unknown_options: True if unknown options are allowed, False if not
        :param args: the args that are passed on to the click.Command constructor
        :param kwargs: the kwargs that are passed on to the click.Command constructor
        """
        self._requires_lean_config = requires_lean_config
        self._requires_docker = requires_docker
        self._allow_unknown_options = allow_unknown_options

        super().__init__(*args, **kwargs)

        # By default the width of help messages is min(terminal_width, max_content_width)
        # max_content_width defaults to 80, which we increase to 120 to improve readability on wide terminals
        self.context_settings["max_content_width"] = 120

        # Don't fail if unknown options are passed in when they're allowed
        self.context_settings["ignore_unknown_options"] = allow_unknown_options
        self.context_settings["allow_extra_args"] = allow_unknown_options

    def invoke(self, ctx: click.Context):
        if self._requires_lean_config:
            lean_config_manager = container.lean_config_manager()
            try:
                # This method will raise an error if the directory cannot be found
                lean_config_manager.get_cli_root_directory()
            except Exception:
                # Use one of the cached Lean config locations to avoid having to abort the command
                lean_config_paths = lean_config_manager.get_known_lean_config_paths()
                if len(lean_config_paths) > 0:
                    lean_config_path = container.logger().prompt_list("Select the Lean configuration file to use", [
                        Option(id=p, label=str(p)) for p in lean_config_paths
                    ])
                    lean_config_manager.set_default_lean_config_path(lean_config_path)
                else:
                    # Abort with a display-friendly error message if the command requires a Lean config and none found
                    raise MoreInfoError(
                        "This command requires a Lean configuration file, run `lean init` in an empty directory to create one, or specify the file to use with --lean-config",
                        "https://www.lean.io/docs/lean-cli/user-guides/troubleshooting#02-Common-errors"
                    )

        if self._requires_docker and "pytest" not in sys.modules:
            is_system_linux = container.platform_manager().is_system_linux()

            # The CLI uses temporary directories in /tmp because sometimes it may leave behind files owned by root
            # These files cannot be deleted by the CLI itself, so we rely on the OS to empty /tmp on reboot
            # The Snap version of Docker does not provide access to files outside $HOME, so we can't support it
            if is_system_linux:
                docker_path = shutil.which("docker")
                if docker_path is not None and docker_path.startswith("/snap"):
                    raise MoreInfoError(
                        "The Lean CLI does not work with the Snap version of Docker, please re-install Docker via the official installation instructions",
                        "https://docs.docker.com/engine/install/")

            # A usual Docker installation on Linux requires the user to use sudo to run Docker
            # If we detect that this is the case and the CLI was started without sudo we elevate automatically
            if is_system_linux and os.getuid() != 0 and container.docker_manager().is_missing_permission():
                container.logger().info(
                    "This command requires access to Docker, you may be asked to enter your password")

                args = ["sudo", "--preserve-env=HOME", sys.executable, *sys.argv]
                os.execlp(args[0], *args)

        if self._allow_unknown_options:
            # Unknown options are passed to ctx.args and need to be parsed manually
            # We parse them to ctx.params so they're available like normal options
            # Because of this all commands with allow_unknown_options=True must have a **kwargs argument
            arguments = list(itertools.chain(*[arg.split("=") for arg in ctx.args]))

            skip_next = False
            for index in range(len(arguments) - 1):
                if skip_next:
                    skip_next = False
                    continue

                if arguments[index].startswith("--"):
                    option = arguments[index].replace("--", "")
                    value = arguments[index + 1]
                    ctx.params[option] = value
                    skip_next = True

        update_manager = container.update_manager()
        update_manager.show_announcements()

        result = super().invoke(ctx)

        update_manager.warn_if_cli_outdated()

        return result

    def get_params(self, ctx: click.Context):
        params = super().get_params(ctx)

        # Add --lean-config option if the command requires a Lean config
        if self._requires_lean_config:
            params.insert(len(params) - 1, click.Option(["--lean-config"],
                                                        type=PathParameter(exists=True, file_okay=True, dir_okay=False),
                                                        help=f"The Lean configuration file that should be used (defaults to the nearest {DEFAULT_LEAN_CONFIG_FILE_NAME})",
                                                        expose_value=False,
                                                        is_eager=True,
                                                        callback=self._parse_config_option))

        # Add --verbose option
        params.insert(len(params) - 1, click.Option(["--verbose"],
                                                    help="Enable debug logging",
                                                    is_flag=True,
                                                    default=False,
                                                    expose_value=False,
                                                    is_eager=True,
                                                    callback=self._parse_verbose_option))

        return params

    def _parse_config_option(self, ctx: click.Context, param: click.Parameter, value: Optional[Path]) -> None:
        """Parses the --config option."""
        if value is not None:
            lean_config_manager = container.lean_config_manager()
            lean_config_manager.set_default_lean_config_path(value)

    def _parse_verbose_option(self, ctx: click.Context, param: click.Parameter, value: Optional[bool]) -> None:
        """Parses the --verbose option."""
        if value:
            logger = container.logger()
            logger.debug_logging_enabled = True


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

        if not container.path_manager().is_path_valid(path):
            self.fail(f"{self._path_type} '{value}' is not a valid path.", param, ctx)

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
        for date_format in ["%Y%m%d", "%Y-%m-%d"]:
            try:
                return datetime.strptime(value, date_format)
            except ValueError:
                pass

        self.fail(f"'{value}' does not match the yyyyMMdd format.", param, ctx)


def ensure_options(options: List[str]) -> None:
    """Ensures certain options have values, raises an error if not.

    :param options: the Python names of the options that must have values
    """
    ctx = click.get_current_context()

    missing_options = []
    for key, value in ctx.params.items():
        has_value = value is not None

        if isinstance(value, tuple) and len(value) == 0:
            has_value = False

        if not has_value and key in options:
            missing_options.append(key)

    if len(missing_options) == 0:
        return

    missing_options = sorted(missing_options, key=lambda param: options.index(param))
    help_records = []

    for name in missing_options:
        option = next(param for param in ctx.command.params if param.name == name)
        help_records.append(option.get_help_record(ctx))

    help_formatter = click.HelpFormatter(max_width=120)
    help_formatter.write_dl(help_records)

    raise RuntimeError(f"""
You are missing the following option{"s" if len(missing_options) > 1 else ""}:
{''.join(help_formatter.buffer)}
    """.strip())
