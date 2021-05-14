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

import platform
import re
from pathlib import Path
from typing import Optional

import click

from lean.click import LeanCommand, PathParameter
from lean.container import container
from lean.models.docker import DockerImage

CUSTOM_FOUNDATION_IMAGE = DockerImage(name="lean-cli/foundation", tag="latest")
CUSTOM_ENGINE_IMAGE = DockerImage(name="lean-cli/engine", tag="latest")
CUSTOM_RESEARCH_IMAGE = DockerImage(name="lean-cli/research", tag="latest")


def _compile_lean(lean_dir: Path) -> None:
    """Compiles LEAN's C# code.

    :param lean_dir: the directory containing the LEAN repository
    """
    logger = container.logger()
    logger.info(f"Compiling the C# code in '{lean_dir}'")

    docker_manager = container.docker_manager()
    docker_manager.create_volume("lean_cli_nuget")
    success = docker_manager.run_image(CUSTOM_FOUNDATION_IMAGE,
                                       entrypoint=["dotnet", "build", f"/LeanCLI"],
                                       environment={"DOTNET_CLI_TELEMETRY_OPTOUT": "true",
                                                    "DOTNET_NOLOGO": "true"},
                                       volumes={
                                           str(lean_dir): {
                                               "bind": "/LeanCLI",
                                               "mode": "rw"
                                           },
                                           "lean_cli_nuget": {
                                               "bind": "/root/.nuget/packages",
                                               "mode": "rw"
                                           }
                                       })

    if not success:
        raise RuntimeError("Something went wrong while running dotnet build, see the logs above for more information")


def _build_image(dockerfile: Path, base_image: Optional[DockerImage], target_image: DockerImage) -> None:
    """Builds a Docker image.

    :param dockerfile: the path to the Dockerfile to build
    :param base_image: the base image to use, or None if the default should be used
    :param target_image: the name of the new image
    """
    logger = container.logger()
    if base_image is not None:
        logger.info(f"Building '{target_image}' from '{dockerfile}' using '{base_image}' as base image")
    else:
        logger.info(f"Building '{target_image}' from '{dockerfile}'")

    if not dockerfile.is_file():
        raise RuntimeError(f"'{dockerfile}' does not exist")

    current_content = dockerfile.read_text(encoding="utf-8")

    if base_image is not None:
        new_content = re.sub(r"^FROM.*$", f"FROM {base_image}", current_content, flags=re.MULTILINE)
        dockerfile.write_text(new_content, encoding="utf-8")

    try:
        docker_manager = container.docker_manager()
        docker_manager.build_image(dockerfile, target_image)
    finally:
        if base_image is not None:
            dockerfile.write_text(current_content, encoding="utf-8")


@click.command(cls=LeanCommand, requires_docker=True)
@click.argument("lean", type=PathParameter(exists=True, file_okay=False, dir_okay=True))
def build(lean: Path) -> None:
    """Build Docker images of your own version of LEAN.

    \b
    LEAN must point to a directory containing (a modified version of) the LEAN repository:
    https://github.com/QuantConnect/Lean

    \b
    This command performs the following actions:
    1. The lean-cli/foundation:latest image is built from DockerfileLeanFoundation(ARM).
    2. LEAN is compiled in a Docker container using the lean-cli/foundation:latest image.
    3. The lean-cli/engine:latest image is built from Dockerfile using lean-cli/foundation:latest as base image.
    4. The lean-cli/research:latest image is built from DockerfileJupyter using lean-cli/engine:latest as base image.
    5. The default engine image is set to lean-cli/engine:latest.
    6. The default research image is set to lean-cli/research:latest.
    """
    if platform.machine() in ["arm64", "aarch64"] and (lean / "DockerfileLeanFoundationARM").is_file():
        foundation_dockerfile = lean / "DockerfileLeanFoundationARM"
    else:
        foundation_dockerfile = lean / "DockerfileLeanFoundation"

    _build_image(foundation_dockerfile, None, CUSTOM_FOUNDATION_IMAGE)
    _compile_lean(lean)
    _build_image(lean / "Dockerfile", CUSTOM_FOUNDATION_IMAGE, CUSTOM_ENGINE_IMAGE)
    _build_image(lean / "DockerfileJupyter", CUSTOM_ENGINE_IMAGE, CUSTOM_RESEARCH_IMAGE)

    logger = container.logger()
    cli_config_manager = container.cli_config_manager()

    logger.info(f"Setting default engine image to '{CUSTOM_ENGINE_IMAGE}'")
    cli_config_manager.engine_image.set_value(str(CUSTOM_ENGINE_IMAGE))

    logger.info(f"Setting default research image to '{CUSTOM_RESEARCH_IMAGE}'")
    cli_config_manager.research_image.set_value(str(CUSTOM_RESEARCH_IMAGE))
