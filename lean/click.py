from pathlib import Path
from typing import Optional

import click

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

    def __init__(self, requires_project: bool = False, *args, **kwargs):
        """Creates a new LeanCommand instance.

        :param requires_project: True if this command needs to be ran in a Lean CLI project, False if not
        :param args: the args that are passed on to the click.Command constructor
        :param kwargs: the kwargs that are passed on to the click.Command constructor
        """
        self._requires_project = requires_project

        super().__init__(*args, **kwargs)

    def get_params(self, ctx):
        params = super().get_params(ctx)

        # Add --config option if the commands needs to be ran inside a Lean CLI project
        if self._requires_project:
            params += [click.Option(["--config", "-c"],
                                    type=PathParameter(exists=True, file_okay=True, dir_okay=False),
                                    help=f"The configuration file that should be used (defaults to the nearest {container.config()['default_lean_config_file_name']})",
                                    expose_value=False,
                                    is_eager=True,
                                    callback=parse_config_option)]

        # Add --verbose option
        params += [click.Option(["--verbose"],
                                type=bool,
                                help="Enable debug logging",
                                is_flag=True,
                                default=False,
                                expose_value=False,
                                is_eager=True,
                                callback=parse_verbose_option)]

        return params


class PathParameter(click.ParamType):
    """A limited version of click.Path which uses pathlib.Path."""

    name = "path"

    def __init__(self, exists: bool = False, file_okay: bool = True, dir_okay: bool = True):
        """Creates a new Path instance.

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
        path = Path(value).resolve()

        if self._exists and not path.exists():
            self.fail(f"{self._path_type} '{value}' does not exist.", param, ctx)

        if not self._file_okay and path.is_file():
            self.fail(f"{self._path_type} '{value}' is a file.", param, ctx)

        if not self._dir_okay and path.is_dir():
            self.fail(f"{self._path_type} '{value}' is a directory.", param, ctx)

        return path
