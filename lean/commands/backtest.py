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
@click.option("--update", is_flag=True, help="Update the LEAN engine to the latest version before running the backtest")
@click.option("--version", type=str, default="latest", show_default=True, help="The LEAN engine version to run")
@click.option("--debug",
              type=click.Choice(["pycharm", "vs", "vscode"], case_sensitive=False),
              help="Enable debugging for a certain editor")
def backtest(project: Path, output: Optional[Path], update: bool, version: Optional[int], debug: Optional[str]) -> None:
    """Backtest a project locally using Docker.

    \b
    If PROJECT is a directory, the algorithm in the main.py or Main.cs file inside it will be executed.
    If PROJECT is a file, the algorithm in the specified file will be executed.

    \b
    To debug Python algorithms with PyCharm:
    1. Start the debugging server in PyCharm using the drop down configuration “Debug in Container”.
    2. Run this command with the `--debug pycharm` option.

    \b
    To debug C# algorithms with Visual Studio:
    1. Install the "VSMonoDebugger" extension.
    2. Go to "Extensions > Mono > Settings" and fill in the following:
        Remote Host IP: 127.0.0.1
        Remote Host Port: 55555
        Mono Debug Port: 55555
    3. Click Save and close the extension settings.
    4. Run this command with the `--debug vs` option.
    5. Wait until the Lean CLI tells you to attach to the debugger.
    6. Click "Extensions > Mono > Attach to mono debugger" in Visual Studio.

    \b
    To debug Python algorithms with VS Code:
    1. Install the "Python" extension.
    2. Run this command with the `--debug vscode` option.
    3. Wait until the Lean CLI tells you to attach to the debugger.
    4. On the Run tab, click on "Run and Debug" and select "Remote Attach > localhost > 5678".
    """
    project_manager = container.project_manager()
    algorithm_file = project_manager.find_algorithm_file(Path(project))

    if output is None:
        output = algorithm_file.parent / "backtests" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    lean_runner = container.lean_runner()

    if update:
        lean_runner.force_update()

    # Convert editor to debugging method
    if debug == "pycharm":
        debug = "PyCharm"
    if debug == "vs":
        debug = "VisualStudio"
    if debug == "vscode":
        debug = "PTVSD"

    lean_runner.run_lean("backtesting", algorithm_file, output, version, debug)
