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

from lean.click import LeanCommand, PathParameter
from lean.constants import DEFAULT_ENGINE_IMAGE
from lean.container import container
from lean.models.config import DebuggingMethod


@click.command(cls=LeanCommand, requires_lean_config=True, requires_docker=True)
@click.argument("project", type=PathParameter(exists=True, file_okay=True, dir_okay=True))
@click.option("--output",
              type=PathParameter(exists=False, file_okay=False, dir_okay=True),
              help="Directory to store results in (defaults to PROJECT/backtests/TIMESTAMP)")
@click.option("--debug",
              type=click.Choice(["pycharm", "ptvsd", "mono"], case_sensitive=False),
              help="Enable a certain debugging method (see --help for more information)")
@click.option("--image",
              type=str,
              help=f"The LEAN engine image to use (defaults to {DEFAULT_ENGINE_IMAGE})")
@click.option("--update",
              is_flag=True,
              default=False,
              help="Pull the LEAN engine image before running the backtest")
def backtest(project: Path, output: Optional[Path], debug: Optional[str], image: Optional[str], update: bool) -> None:
    """Backtest a project locally using Docker.

    \b
    If PROJECT is a directory, the algorithm in the main.py or Main.cs file inside it will be executed.
    If PROJECT is a file, the algorithm in the specified file will be executed.

    \b
    Go to the following url to learn how to debug backtests locally using the Lean CLI:
    https://www.quantconnect.com/docs/v2/lean-cli/tutorials/backtesting/debugging-local-backtests

    By default the official LEAN engine image is used.
    You can override this using the --image option.
    Alternatively you can set the default engine image for all commands using `lean config set engine-image <image>`.
    """
    project_manager = container.project_manager()
    algorithm_file = project_manager.find_algorithm_file(Path(project))

    if output is None:
        output = algorithm_file.parent / "backtests" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Convert the given --debug value to the debugging method to use
    debugging_method = None
    if debug == "pycharm":
        debugging_method = DebuggingMethod.PyCharm
    if debug == "ptvsd":
        debugging_method = DebuggingMethod.PTVSD
    if debug == "mono":
        debugging_method = DebuggingMethod.Mono

    cli_config_manager = container.cli_config_manager()
    engine_image = cli_config_manager.get_engine_image(image)

    docker_manager = container.docker_manager()

    if update:
        docker_manager.pull_image(engine_image)

    lean_runner = container.lean_runner()
    lean_runner.run_lean("backtesting", algorithm_file, output, engine_image, debugging_method)

    if str(engine_image) == DEFAULT_ENGINE_IMAGE and not update:
        update_manager = container.update_manager()
        update_manager.warn_if_docker_image_outdated(engine_image)
