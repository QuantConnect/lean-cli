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
from lean.constants import ENGINE_IMAGE
from lean.container import container


@click.command(cls=LeanCommand, requires_lean_config=True)
@click.argument("project", type=PathParameter(exists=True, file_okay=True, dir_okay=True))
@click.argument("environment", type=str)
@click.option("--output",
              type=PathParameter(exists=False, file_okay=False, dir_okay=True),
              help="Directory to store results in (defaults to PROJECT/live/TIMESTAMP)")
@click.option("--update",
              is_flag=True,
              default=False,
              help="Pull the selected LEAN engine version before starting live trading")
@click.option("--version",
              type=str,
              default="latest",
              help="The LEAN engine version to run (defaults to the latest installed version)")
def live(project: Path, environment: str, output: Optional[Path], update: bool, version: str) -> None:
    """Start live trading a project locally using Docker.

    \b
    If PROJECT is a directory, the algorithm in the main.py or Main.cs file inside it will be executed.
    If PROJECT is a file, the algorithm in the specified file will be executed.

    \b
    ENVIRONMENT must be the name of an environment in the Lean configuration file with live-mode set to true.
    """
    project_manager = container.project_manager()
    algorithm_file = project_manager.find_algorithm_file(Path(project))

    if output is None:
        output = algorithm_file.parent / "live" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    lean_config_manager = container.lean_config_manager()
    lean_config = lean_config_manager.get_complete_lean_config(environment, algorithm_file, None)

    if "environments" not in lean_config or environment not in lean_config["environments"]:
        lean_config_path = lean_config_manager.get_lean_config_path()
        raise RuntimeError(f"{lean_config_path} does not contain an environment named '{environment}'")

    if not lean_config["environments"][environment]["live-mode"]:
        raise RuntimeError(f"The '{environment}' is not a live trading environment (live-mode is set to false)")

    docker_manager = container.docker_manager()

    if version != "latest":
        if not docker_manager.tag_exists(ENGINE_IMAGE, version):
            raise RuntimeError("The specified version does not exist")

    if update:
        docker_manager.pull_image(ENGINE_IMAGE, version)

    lean_runner = container.lean_runner()
    lean_runner.run_lean(environment, algorithm_file, output, version, None)

    if version == "latest" and not update:
        update_manager = container.update_manager()
        update_manager.warn_if_docker_image_outdated(ENGINE_IMAGE)
