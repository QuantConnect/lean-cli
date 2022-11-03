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
from typing import Optional

from click import option, command, argument

from lean.click import LeanCommand, PathParameter
from lean.container import container
from lean.models.docker import DockerImage
from lean.constants import CUSTOM_FOUNDATION, CUSTOM_RESEARCH, CUSTOM_ENGINE

def _normalize_newlines(text: str) -> str:
    """Normalizes the newlines in a string to use \n (instead of \r or \r\n).

    :param text: the text to normalize the newlines in
    :return: the text with the newlines normalized
    """
    return "\n".join(text.splitlines())


def _is_foundation_dockerfile_same_as_cloud(dockerfile: Path) -> bool:
    """Checks whether a Dockerfile is the same as the Dockerfile used for the quantconnect/lean:foundation image.

    :param dockerfile: the path to the local Dockerfile to check
    :return: whether the local Dockerfile is the same as the one used for the quantconnect/lean:foundation image
    """
    local_dockerfile = dockerfile.read_text(encoding="utf-8").strip()

    try:
        cloud_url = f"https://raw.githubusercontent.com/QuantConnect/Lean/master/{dockerfile.name}"
        cloud_dockerfile = container.http_client.get(cloud_url)
        cloud_dockerfile = cloud_dockerfile.text.strip()
    except:
        # We build a new image if for whatever reason we can't check the Dockerfile used for the official image
        return False

    return _normalize_newlines(local_dockerfile) == _normalize_newlines(cloud_dockerfile)


def _compile_csharp(root: Path, csharp_dir: Path, docker_image: DockerImage) -> None:
    """Compiles C# code.

    :param root: the root directory in which the command is ran
    :param csharp_dir: the directory containing the C# code
    :param docker_image: the Docker image to compile in
    """
    logger = container.logger
    logger.info(f"Compiling the C# code in '{csharp_dir}'")

    build_path = Path("/LeanCLI") / csharp_dir.relative_to(root)

    docker_manager = container.docker_manager
    docker_manager.create_volume("lean_cli_nuget")
    success = docker_manager.run_image(docker_image,
                                       entrypoint=["dotnet", "build", str(build_path)],
                                       environment={
                                           "DOTNET_CLI_TELEMETRY_OPTOUT": "true",
                                           "DOTNET_NOLOGO": "true"
                                       },
                                       volumes={
                                           str(root): {
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


def _build_image(root: Path, dockerfile: Path, base_image: Optional[DockerImage], target_image: DockerImage) -> None:
    """Builds a Docker image.

    :param root: the path to build from
    :param dockerfile: the path to the Dockerfile to build
    :param base_image: the base image to use, or None if the default should be used
    :param target_image: the name of the new image
    """
    from re import MULTILINE, sub

    logger = container.logger
    if base_image is not None:
        logger.info(f"Building '{target_image}' from '{dockerfile}' using '{base_image}' as base image")
    else:
        logger.info(f"Building '{target_image}' from '{dockerfile}'")

    if not dockerfile.is_file():
        raise RuntimeError(f"'{dockerfile}' does not exist")

    current_content = dockerfile.read_text(encoding="utf-8")

    if base_image is not None:
        new_content = sub(r"^FROM.*$", f"FROM {base_image}", current_content, flags=MULTILINE)
        dockerfile.write_text(new_content, encoding="utf-8")

    try:
        docker_manager = container.docker_manager
        docker_manager.build_image(root, dockerfile, target_image)
    finally:
        if base_image is not None:
            dockerfile.write_text(current_content, encoding="utf-8")


@command(cls=LeanCommand, requires_docker=True)
@argument("root", type=PathParameter(exists=True, file_okay=False, dir_okay=True), default=lambda: Path.cwd())
@option("--tag", type=str, default="latest", help="The tag to apply to custom images (defaults to latest)")
def build(root: Path, tag: str) -> None:
    """Build Docker images of your own version of LEAN.

    \b
    ROOT must point to a directory containing the LEAN repository:
    https://github.com/QuantConnect/Lean

    When ROOT is not given, the current directory is used as root directory.

    \b
    This command performs the following actions:
    1. The lean-cli/foundation:latest image is built from Lean/DockerfileLeanFoundation(ARM).
    2. LEAN is compiled in a Docker container using the lean-cli/foundation:latest image.
    3. The lean-cli/engine:latest image is built from Lean/Dockerfile using lean-cli/foundation:latest as base image.
    4. The lean-cli/research:latest image is built from Lean/DockerfileJupyter using lean-cli/engine:latest as base image.
    5. The default engine image is set to lean-cli/engine:latest.
    6. The default research image is set to lean-cli/research:latest.

    When the foundation Dockerfile is the same as the official foundation Dockerfile,
    quantconnect/lean:foundation is used instead of building a custom foundation image.
    """
    lean_dir = root / "Lean"
    if not lean_dir.is_dir():
        raise RuntimeError(f"Please clone https://github.com/QuantConnect/Lean to '{lean_dir}'")

    (root / "DataLibraries").mkdir(exist_ok=True)

    if container.platform_manager.is_host_arm():
        foundation_dockerfile = lean_dir / "DockerfileLeanFoundationARM"
    else:
        foundation_dockerfile = lean_dir / "DockerfileLeanFoundation"

    if _is_foundation_dockerfile_same_as_cloud(foundation_dockerfile):
        foundation_image = DockerImage(name="quantconnect/lean", tag="foundation")
        container.docker_manager.pull_image(foundation_image)
    else:
        foundation_image = DockerImage(name=CUSTOM_FOUNDATION, tag=tag)
        _build_image(root, foundation_dockerfile, None, foundation_image)

    _compile_csharp(root, lean_dir, foundation_image)

    custom_engine_image = DockerImage(name=CUSTOM_ENGINE, tag=tag)
    _build_image(root, lean_dir / "Dockerfile", foundation_image, custom_engine_image)

    custom_research_image = DockerImage(name=CUSTOM_RESEARCH, tag=tag)
    _build_image(root, lean_dir / "DockerfileJupyter", custom_engine_image, custom_research_image)

    logger = container.logger
    cli_config_manager = container.cli_config_manager

    logger.info(f"Setting default engine image to '{custom_engine_image}'")
    cli_config_manager.engine_image.set_value(str(custom_engine_image))

    logger.info(f"Setting default research image to '{custom_research_image}'")
    cli_config_manager.research_image.set_value(str(custom_research_image))
