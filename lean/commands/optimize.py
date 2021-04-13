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

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from docker.types import Mount
from jsoncomment import JsonComment

from lean.click import LeanCommand, PathParameter
from lean.constants import ENGINE_IMAGE
from lean.container import container
from lean.models.api import QCParameter
from lean.models.errors import MoreInfoError


@click.command(cls=LeanCommand, requires_lean_config=True, requires_docker=True)
@click.argument("project", type=PathParameter(exists=True, file_okay=True, dir_okay=True))
@click.option("--output",
              type=PathParameter(exists=False, file_okay=False, dir_okay=True),
              help="Directory to store results in (defaults to PROJECT/optimizations/TIMESTAMP)")
@click.option("--optimizer-config",
              type=PathParameter(exists=True, file_okay=True, dir_okay=False),
              help=f"The optimizer configuration file that should be used")
@click.option("--update",
              is_flag=True,
              default=False,
              help="Pull the selected LEAN engine version before running the optimizer")
@click.option("--version",
              type=str,
              default="latest",
              help="The LEAN engine version to run (defaults to the latest installed version)")
def optimize(project: Path,
             output: Optional[Path],
             optimizer_config: Optional[Path],
             update: bool,
             version: str) -> None:
    """Optimize a project's parameters locally using Docker.

    \b
    If PROJECT is a directory, the algorithm in the main.py or Main.cs file inside it will be executed.
    If PROJECT is a file, the algorithm in the specified file will be executed.

    \b
    The --optimizer-config option can be used to specify the configuration to run the optimizer with.
    When using the option it should point to a file like this (the algorithm-* properties should be omitted):
    https://github.com/QuantConnect/Lean/blob/master/Optimizer.Launcher/config.json

    When --optimizer-config is not set, an interactive prompt will be shown to configure the optimizer.
    """
    project_manager = container.project_manager()
    algorithm_file = project_manager.find_algorithm_file(project)

    if output is None:
        output = algorithm_file.parent / "optimizations" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    if optimizer_config is None:
        project_config_manager = container.project_config_manager()
        project_config = project_config_manager.get_project_config(algorithm_file.parent)
        project_parameters = [QCParameter(key=k, value=v) for k, v in project_config.get("parameters", {}).items()]

        if len(project_parameters) == 0:
            raise MoreInfoError("The given project has no parameters to optimize",
                                "https://www.quantconnect.com/docs/v2/lean-cli/tutorials/optimization/project-parameters")

        optimizer_config_manager = container.optimizer_config_manager()
        optimization_strategy = optimizer_config_manager.configure_strategy(cloud=False)
        optimization_target = optimizer_config_manager.configure_target()
        optimization_parameters = optimizer_config_manager.configure_parameters(project_parameters, cloud=False)
        optimization_constraints = optimizer_config_manager.configure_constraints()

        config = {
            "optimization-strategy": optimization_strategy,
            "optimization-strategy-settings": {
                "$type": "QuantConnect.Optimizer.Strategies.StepBaseOptimizationStrategySettings, QuantConnect.Optimizer",
                "default-segment-amount": 10
            },
            "optimization-criterion": {
                "target": optimization_target.target,
                "extremum": optimization_target.extremum.value
            },
            "parameters": [parameter.dict() for parameter in optimization_parameters],
            "constraints": [constraint.dict(by_alias=True) for constraint in optimization_constraints]
        }
    else:
        config_text = optimizer_config.read_text(encoding="utf-8")

        # JsonComment can parse JSON with non-inline comments, so we remove the inline ones first
        config_without_inline_comments = re.sub(r",\s*//.*", ",", config_text, flags=re.MULTILINE)
        config = JsonComment().loads(config_without_inline_comments)

        # Remove keys which are configured in the Lean config
        for key in ["algorithm-type-name", "algorithm-language", "algorithm-location"]:
            config.pop(key, None)

    config["optimizer-close-automatically"] = True
    config["results-destination-folder"] = "/Results"

    config_path = output / "optimizer-config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w+", encoding="utf-8") as file:
        file.write(json.dumps(config, indent=4) + "\n")

    lean_runner = container.lean_runner()
    run_options = lean_runner.get_basic_docker_config("backtesting", algorithm_file, output, version, None)

    run_options["working_dir"] = "/Lean/Optimizer.Launcher/bin/Debug"
    run_options["entrypoint"] = ["mono", "QuantConnect.Optimizer.Launcher.exe"]
    run_options["mounts"].append(
        Mount(target="/Lean/Optimizer.Launcher/bin/Debug/config.json",
              source=str(config_path),
              type="bind",
              read_only=True)
    )

    docker_manager = container.docker_manager()

    if version != "latest":
        if not docker_manager.tag_exists(ENGINE_IMAGE, version):
            raise RuntimeError(
                f"The specified version does not exist, please pick a valid tag from https://hub.docker.com/r/{ENGINE_IMAGE}/tags")

    if update:
        docker_manager.pull_image(ENGINE_IMAGE, version)

    success = docker_manager.run_image(ENGINE_IMAGE, version, **run_options)

    cli_root_dir = container.lean_config_manager().get_cli_root_directory()
    relative_project_dir = project.relative_to(cli_root_dir)
    relative_output_dir = output.relative_to(cli_root_dir)

    if success:
        logger = container.logger()
        logger.info(f"Successfully optimized '{relative_project_dir}' and stored the output in '{relative_output_dir}'")
    else:
        raise RuntimeError(
            f"Something went wrong while running the optimization, the output is stored in '{relative_output_dir}'")

    if version == "latest" and not update:
        update_manager = container.update_manager()
        update_manager.warn_if_docker_image_outdated(ENGINE_IMAGE)
