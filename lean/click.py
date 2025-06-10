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

from pathlib import Path
from typing import Optional, List, Callable

from click import Command, Context, Parameter, ParamType, Option as ClickOption
from click.decorators import FC, option

from lean.constants import DEFAULT_LEAN_CONFIG_FILE_NAME, CONTAINER_LABEL_LEAN_VERSION_NAME
from lean.container import container
from lean.models.errors import MoreInfoError
from lean.models.logger import Option
from lean.models.errors import AuthenticationError


def get_whoami_message() -> str:
    """
    Retrieves a message indicating the currently logged-in user's name and email.

    This function checks if the user is logged in by verifying the presence of a user ID
    and API token. If the user is logged in, it retrieves the user's personal organization
    and finds the admin member associated with that organization. It then returns a message
    containing the admin member's name and email address. If the user is not logged in,
    it returns a message indicating that the user is not logged in.

    Returns:
        str: A message indicating the logged-in user's name and email,
             or a message stating that the user is not logged in.
    """
    api_client = container.api_client
    cli_config_manager = container.cli_config_manager

    if cli_config_manager.user_id.get_value() is not None and cli_config_manager.api_token.get_value() is not None:
        try:
            organizations = api_client.organizations.get_all()
            logged_in = True
        except AuthenticationError:
            logged_in = False
    else:
        logged_in = False

    if not logged_in:
        return "not logged in"

    personal_organization_id = next(o.id for o in organizations if o.ownerName == "You")
    personal_organization = api_client.organizations.get(personal_organization_id)
    member = next(m for m in personal_organization.members if m.isAdmin)

    return f"logged in as {member.name} ({member.email})"

def get_disk_space_info(path: Path) -> str:
    try:
        from shutil import disk_usage
        usage = disk_usage(str(path))
        total, used, free = usage.total, usage.used, usage.free

        return (
            f"Space in temporary location - "
            f"Total: {total / (1024 ** 3):.2f} GB, "
            f"Used: {used / (1024 ** 3):.2f} GB, "
            f"Free: {free / (1024 ** 3):.2f} GB"
        )
    except Exception as e:
        return f"Error getting disk space: {str(e)}"

class VerboseOption(ClickOption):
    def __init__(self, *args, **kwargs):
        super().__init__(["--verbose"],
                         help="Enable debug logging",
                         is_flag=True,
                         default=False,
                         expose_value=False,
                         is_eager=True,
                         callback=self._parse_verbose_option)

    @staticmethod
    def _parse_verbose_option(ctx: Context, param: Parameter, value: Optional[bool]) -> None:
        """Parses the --verbose option."""
        if not value:
            return

        from platform import platform
        from sys import version as sys_version
        from lean import __version__ as lean_cli_version
        from subprocess import run
        from os import getcwd, getlogin
        from socket import gethostname
        from lean.container import container

        logger = container.logger
        logger.debug_logging_enabled = True

        # show additional context information
        python_version = sys_version.replace("\n", ". ")
        try:
            hostname = gethostname()
            hostname = f"  Hostname: {hostname}\n"
        except:
            hostname = ""

        try:
            username = getlogin()
            username = f"  Username: {username}\n"
        except:
            username = ""

        try:
            dotnet_version = run("dotnet --version", capture_output=True).stdout.decode("utf").replace("\n", "")
        except:
            dotnet_version = "Not installed"

        try:
            vscode_version = run("code --version", shell=True, capture_output=True).stdout.decode("utf").replace("\n", "-")[:-1]
        except:
            vscode_version = "Not installed"

        try:
            vscode_installed_extensions = run("code --list-extensions --show-versions", shell=True, capture_output=True).stdout.decode("utf")
            vscode_installed_extensions = vscode_installed_extensions[:-1].replace("\n", "\n" + (" " * len("  VS Code installed versions: ")))
        except:
            vscode_installed_extensions = "Not installed"

        try:
            project_config = container.project_config_manager.get_project_config(Path(getcwd()))
            engine_image = container.cli_config_manager.get_engine_image(project_config.get("engine-image", None))
            container.docker_manager.get_image_label(engine_image, 'strict_python_version', "Unknown")
            container.docker_manager.get_image_label(engine_image, 'python_version', "Unknown")
            container.docker_manager.get_image_label(engine_image, 'target_framework', "Unknown")
            container.docker_manager.get_image_label(engine_image, CONTAINER_LABEL_LEAN_VERSION_NAME, None)
        except:
            pass

        try:
            docker_version = run("docker --version", shell=True, capture_output=True).stdout.decode("utf").replace("Docker version ", "")
        except:
            docker_version = "Not installed"
        
        try:
            temp_dir = container.temp_manager.create_temporary_directory().parent
            space_info = get_disk_space_info(temp_dir)
        except:
            temp_dir = ""
            space_info = ""

        logger.debug(f"Context information:\n" +
                     hostname +
                     username +
                     f"  Python version: {python_version}\n"
                     f"  OS: {platform()}\n"
                     f"  Temporary directory: {temp_dir}\n"
                     f"  {space_info}\n"
                     f"  Lean CLI version: {lean_cli_version}\n"
                     f"  .NET version: {dotnet_version}\n"
                     f"  VS Code version: {vscode_version}\n"
                     f"  VS Code installed versions: {vscode_installed_extensions}\n"
                     f"  Docker version: {docker_version}\n")
        try:
            logger.debug(get_whoami_message())
        except:
            logger.debug("Unable to retrieve login information. The user might not be logged in.")


def verbose_option() -> Callable[[FC], FC]:
    return option(cls=VerboseOption)


class LeanCommand(Command):
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

    def invoke(self, ctx: Context):
        container.data_downloader.update_database_files()
        if self._requires_lean_config:
            lean_config_manager = container.lean_config_manager
            try:
                # This method will raise an error if the directory cannot be found
                lean_config_manager.get_cli_root_directory()
            except Exception:
                # Use one of the cached Lean config locations to avoid having to abort the command
                lean_config_paths = lean_config_manager.get_known_lean_config_paths()
                if len(lean_config_paths) > 0:
                    lean_config_path = container.logger.prompt_list("Select the Lean configuration file to use", [
                        Option(id=p, label=str(p)) for p in lean_config_paths
                    ])
                    lean_config_manager.set_default_lean_config_path(lean_config_path)
                else:
                    # Abort with a display-friendly error message if the command requires a Lean config and none found
                    raise MoreInfoError(
                        "This command requires a Lean configuration file, run `lean init` in an empty directory to create one, or specify the file to use with --lean-config",
                        "https://www.lean.io/docs/v2/lean-cli/key-concepts/troubleshooting#02-Common-Errors"
                    )

        if self._requires_docker and container.platform_manager.is_system_linux():
            from sys import modules, executable, argv
            if "pytest" not in modules:
                from shutil import which
                from os import getuid, execlp
                # The CLI uses temporary directories in /tmp because sometimes it may leave behind files owned by root
                # These files cannot be deleted by the CLI itself, so we rely on the OS to empty /tmp on reboot
                # The Snap version of Docker does not provide access to files outside $HOME, so we can't support it

                docker_path = which("docker")
                if docker_path is not None and docker_path.startswith("/snap"):
                    raise MoreInfoError(
                        "The Lean CLI does not work with the Snap version of Docker, please re-install Docker via the official installation instructions",
                        "https://docs.docker.com/engine/install/")

                # A usual Docker installation on Linux requires the user to use sudo to run Docker
                # If we detect that this is the case and the CLI was started without sudo we elevate automatically
                if getuid() != 0 and container.docker_manager.is_missing_permission():
                    container.logger.info(
                        "This command requires access to Docker, you may be asked to enter your password")

                    args = ["sudo", "--preserve-env=HOME", executable, *argv]
                    execlp(args[0], *args)

        if self._allow_unknown_options:
            from itertools import chain
            # Unknown options are passed to ctx.args and need to be parsed manually
            # We parse them to ctx.params so they're available like normal options
            # Because of this all commands with allow_unknown_options=True must have a **kwargs argument
            arguments = list(chain(*[arg.split("=") for arg in ctx.args]))

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

        update_manager = container.update_manager
        update_manager.show_announcements()

        result = super().invoke(ctx)

        update_manager.warn_if_cli_outdated()

        return result

    def get_params(self, ctx: Context):
        params = super().get_params(ctx)

        # Add --lean-config option if the command requires a Lean config
        if self._requires_lean_config:
            params.insert(len(params) - 1, ClickOption(["--lean-config"],
                                                        type=PathParameter(exists=True, file_okay=True, dir_okay=False),
                                                        help=f"The Lean configuration file that should be used (defaults to the nearest {DEFAULT_LEAN_CONFIG_FILE_NAME})",
                                                        expose_value=False,
                                                        is_eager=True,
                                                        callback=self._parse_config_option))

        # Add --verbose option
        params.insert(len(params) - 1, VerboseOption())

        return params

    def _parse_config_option(self, ctx: Context, param: Parameter, value: Optional[Path]) -> None:
        """Parses the --config option."""
        if value is not None:
            lean_config_manager = container.lean_config_manager
            lean_config_manager.set_default_lean_config_path(value)



class PathParameter(ParamType):
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

    def convert(self, value: str, param: Parameter, ctx: Context) -> Path:
        path = Path(value).expanduser().resolve()

        if not container.path_manager.is_cli_path_valid(path):
            self.fail(f"{self._path_type} '{value}' is not a valid path.", param, ctx)

        if self._exists and not path.exists():
            self.fail(f"{self._path_type} '{value}' does not exist.", param, ctx)

        if not self._file_okay and path.is_file():
            self.fail(f"{self._path_type} '{value}' is a file.", param, ctx)

        if not self._dir_okay and path.is_dir():
            self.fail(f"{self._path_type} '{value}' is a directory.", param, ctx)

        return path


class DateParameter(ParamType):
    """A click parameter which returns datetime.datetime objects and requires yyyyMMdd input."""

    name = "date"

    def get_metavar(self, param: Parameter) -> str:
        return "[yyyyMMdd]"

    def convert(self, value: str, param: Parameter, ctx: Context):
        from datetime import datetime
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
    from click import get_current_context

    ctx = get_current_context()

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

    from click import HelpFormatter

    help_formatter = HelpFormatter(max_width=120)
    help_formatter.write_dl(help_records)

    raise RuntimeError(f"""
You are missing the following option{"s" if len(missing_options) > 1 else ""}:
{''.join(help_formatter.buffer)}
    """.strip())
