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
from datetime import datetime
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree

import click

from lean.click import LeanCommand, PathParameter
from lean.constants import ENGINE_IMAGE
from lean.container import container
from lean.models.config import DebuggingMethod


# The _migrate_dotnet_5_* methods automatically update launch configurations for a given debugging method.
#
# In the update to .NET 5, debugging changed considerably.
# This lead to some required changes in the launch configurations users use to start debugging.
# Projects which are created after the update to .NET 5 have the correct configuration already,
# but projects created before that need changes to their launch configurations.
#
# These methods checks if the project have outdated configurations, and if so, update them to keep it working.
# These methods will only be useful for the first few weeks after the update to .NET 5 and will be removed afterwards.

def _migrate_dotnet_5_python_pycharm(project_dir: Path) -> None:
    workspace_xml_path = project_dir / ".idea" / "workspace.xml"
    if not workspace_xml_path.is_file():
        return

    current_content = workspace_xml_path.read_text(encoding="utf-8")
    if 'remote-root="/LeanCLI"' not in current_content:
        return

    new_content = current_content.replace('remote-root="/LeanCLI"', 'remote-root="/Lean/Launcher/bin/Debug"')
    workspace_xml_path.write_text(new_content, encoding="utf-8")

    logger = container.logger()
    logger.warn("Your run configuration has been updated to work with the .NET 5 version of LEAN")
    logger.warn("Please restart the debugger in PyCharm and run this command again")

    raise click.Abort()


def _migrate_dotnet_5_python_vscode(project_dir: Path) -> None:
    launch_json_path = project_dir / ".vscode" / "launch.json"
    if not launch_json_path.is_file():
        return

    current_content = launch_json_path.read_text(encoding="utf-8")
    if '"remoteRoot": "/LeanCLI"' not in current_content:
        return

    new_content = current_content.replace('"remoteRoot": "/LeanCLI"',
                                          '"remoteRoot": "/Lean/Launcher/bin/Debug"')
    launch_json_path.write_text(new_content, encoding="utf-8")


def _migrate_dotnet_5_csharp_rider(project_dir: Path) -> None:
    made_changes = False

    for dir_name in [f".idea.{project_dir.stem}", f".idea.{project_dir.stem}.dir"]:
        workspace_xml_path = project_dir / ".idea" / dir_name / ".idea" / "workspace.xml"
        if not workspace_xml_path.is_file():
            continue

        current_content = ElementTree.fromstring(workspace_xml_path.read_text(encoding="utf-8"))

        run_manager = current_content.find(".//component[@name='RunManager']")
        if run_manager is None:
            continue

        config = run_manager.find(".//configuration[@name='Debug with Lean CLI']")
        if config is None:
            continue

        run_manager.remove(config)

        new_content = ElementTree.tostring(current_content, encoding="utf-8", method="xml").decode("utf-8")
        workspace_xml_path.write_text(new_content, encoding="utf-8")

        made_changes = True

    if made_changes:
        container.project_manager().generate_rider_config()

        logger = container.logger()
        logger.warn("Your run configuration has been updated to work with the .NET 5 version of LEAN")
        logger.warn("Please restart Rider and start debugging again")
        logger.warn(
            "See https://www.quantconnect.com/docs/v2/lean-cli/tutorials/backtesting/debugging-local-backtests#05-C-and-Rider for the updated instructions")

        raise click.Abort()


def _migrate_dotnet_5_csharp_vscode(project_dir: Path) -> None:
    launch_json_path = project_dir / ".vscode" / "launch.json"
    if not launch_json_path.is_file():
        return

    current_content = json.loads(launch_json_path.read_text(encoding="utf-8"))
    if "configurations" not in current_content or not isinstance(current_content["configurations"], list):
        return

    config = next((c for c in current_content["configurations"] if c["name"] == "Debug with Lean CLI"), None)
    if config is None or config["type"] != "mono":
        return

    del config["address"]
    del config["port"]

    config["type"] = "coreclr"
    config["processId"] = "1"

    config["pipeTransport"] = {
        "pipeCwd": "${workspaceRoot}",
        "pipeProgram": "docker",
        "pipeArgs": ["exec", "-i", "lean_cli_vsdbg"],
        "debuggerPath": "/root/vsdbg/vsdbg",
        "quoteArgs": False
    }

    config["logging"] = {
        "moduleLoad": False
    }

    launch_json_path.write_text(json.dumps(current_content, indent=4), encoding="utf-8")


@click.command(cls=LeanCommand, requires_lean_config=True, requires_docker=True)
@click.argument("project", type=PathParameter(exists=True, file_okay=True, dir_okay=True))
@click.option("--output",
              type=PathParameter(exists=False, file_okay=False, dir_okay=True),
              help="Directory to store results in (defaults to PROJECT/backtests/TIMESTAMP)")
@click.option("--debug",
              type=click.Choice(["pycharm", "ptvsd", "vsdbg", "rider"], case_sensitive=False),
              help="Enable a certain debugging method (see --help for more information)")
@click.option("--update",
              is_flag=True,
              default=False,
              help="Pull the selected LEAN engine version before running the backtest")
@click.option("--version",
              type=str,
              default="latest",
              help="The LEAN engine version to run (defaults to the latest installed version)")
def backtest(project: Path, output: Optional[Path], debug: Optional[str], update: bool, version: str) -> None:
    """Backtest a project locally using Docker.

    \b
    If PROJECT is a directory, the algorithm in the main.py or Main.cs file inside it will be executed.
    If PROJECT is a file, the algorithm in the specified file will be executed.

    \b
    Go to the following url to learn how to debug backtests locally using the Lean CLI:
    https://www.quantconnect.com/docs/v2/lean-cli/tutorials/backtesting/debugging-local-backtests
    """
    project_manager = container.project_manager()
    algorithm_file = project_manager.find_algorithm_file(Path(project))

    if output is None:
        output = algorithm_file.parent / "backtests" / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    debugging_method = None
    if debug == "pycharm":
        debugging_method = DebuggingMethod.PyCharm
        _migrate_dotnet_5_python_pycharm(algorithm_file.parent)
    elif debug == "ptvsd":
        debugging_method = DebuggingMethod.PTVSD
        _migrate_dotnet_5_python_vscode(algorithm_file.parent)
    elif debug == "vsdbg":
        debugging_method = DebuggingMethod.VSDBG
        _migrate_dotnet_5_csharp_vscode(algorithm_file.parent)
    elif debug == "rider":
        debugging_method = DebuggingMethod.Rider
        _migrate_dotnet_5_csharp_rider(algorithm_file.parent)

    docker_manager = container.docker_manager()

    if version != "latest":
        if not docker_manager.tag_exists(ENGINE_IMAGE, version):
            raise RuntimeError(
                f"The specified version does not exist, please pick a valid tag from https://hub.docker.com/r/{ENGINE_IMAGE}/tags")

    if update or not docker_manager.supports_dotnet_5(ENGINE_IMAGE, version):
        docker_manager.pull_image(ENGINE_IMAGE, version)

    lean_runner = container.lean_runner()
    lean_runner.run_lean("backtesting", algorithm_file, output, version, debugging_method)

    if version == "latest" and not update:
        update_manager = container.update_manager()
        update_manager.warn_if_docker_image_outdated(ENGINE_IMAGE)
