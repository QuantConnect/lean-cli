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
              help="Directory to store results in (defaults to PROJECT/backtests/TIMESTAMP")
def backtest(project: Path, output: Optional[Path]) -> None:
    """Backtest a project locally using Docker.

    If PROJECT is a directory, the algorithm in the main.py or Main.cs file inside it will be executed.

    If PROJECT is a file, the algorithm in the specified file will be executed.
    """
    project_manager = container.project_manager()
    algorithm_file = project_manager.find_algorithm_file(Path(project))

    if output is None:
        output = algorithm_file.parent / "backtests" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    lean_runner = container.lean_runner()
    lean_runner.run_lean("backtesting", algorithm_file, output)
