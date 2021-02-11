from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from lean.click import LeanCommand, PathParameter
from lean.container import container


@click.command(cls=LeanCommand, requires_project=True)
@click.argument("project", type=PathParameter(exists=True, file_okay=True, dir_okay=True))
@click.option("--output", "-o",
              type=PathParameter(exists=False),
              help="Directory to store results in (defaults to PROJECT/backtests/TIMESTAMP)")
@click.option("--update", is_flag=True, help="Pull the latest LEAN engine version before running the backtest")
@click.option("--version",
              type=str,
              default="latest",
              help="The LEAN engine version to run (defaults to the latest installed version)")
@click.option("--debug",
              type=click.Choice(["pycharm", "vs", "vscode"], case_sensitive=False),
              help="Enable debugging for a certain editor (see --help for more information)")
def backtest(project: Path, output: Optional[Path], update: bool, version: Optional[int], debug: Optional[str]) -> None:
    """Backtest a project locally using Docker.

    \b
    If PROJECT is a directory, the algorithm in the main.py or Main.cs file inside it will be executed.
    If PROJECT is a file, the algorithm in the specified file will be executed.

    \b
    Go to the following url to learn how to debug backtests using the Lean CLI:
    https://github.com/QuantConnect/lean-cli#debugging-backtests
    """
    project_manager = container.project_manager()
    algorithm_file = project_manager.find_algorithm_file(Path(project))

    if output is None:
        output = algorithm_file.parent / "backtests" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    lean_runner = container.lean_runner()

    if update:
        lean_runner.force_update()

    # Detect the debugging method to use based on the editor and project language
    debugging_method = None

    if debug == "pycharm":
        debugging_method = "PyCharm"

    if debug == "vs":
        debugging_method = "VisualStudio"

    if debug == "vscode":
        debugging_method = "PTVSD" if algorithm_file.name.endswith(".py") else "VisualStudio"

    lean_runner.run_lean("backtesting", algorithm_file, output, version, debugging_method)
