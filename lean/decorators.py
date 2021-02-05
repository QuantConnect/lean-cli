from typing import Any, Callable, Optional

import click

from lean.config.lean_config import get_lean_config_path


class LocalCommand(click.Command):
    """A click.Command wrapper which aborts if the command is not ran in a Lean CLI project."""

    def invoke(self, ctx):
        if get_lean_config_path() is None:
            raise click.ClickException(
                "This command should be executed in a Lean CLI project, run `lean init` in an empty directory to create one or specify the configuration file to use with --config")

        return super().invoke(ctx)


def parse_config_option(ctx: click.Context, param: click.Parameter, value: Optional[str]) -> None:
    """Parse the --config option."""
    ctx.config_option = value


def local_command(func: Callable[..., Any]) -> Callable[..., Any]:
    """A wrapper to @click.command() for commands which should be ran in a Lean CLI project."""
    func = click.command(cls=LocalCommand)(func)
    func = click.option("--config", "-c",
                        type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True),
                        help=f"The configuration file that should be used (defaults to the nearest lean.json)",
                        expose_value=False,
                        is_eager=True,
                        callback=parse_config_option)(func)
    return func
