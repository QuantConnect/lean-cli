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

import time
import webbrowser
from pathlib import Path
from typing import Dict, Any

import click
import requests
from docker.errors import APIError
from docker.types import Mount

import lean
from lean.click import LeanCommand, PathParameter
from lean.constants import LOCAL_GUI_CONTAINER_NAME
from lean.container import container
from lean.models.docker import DockerImage


@click.command(cls=LeanCommand, requires_docker=True, requires_lean_config=True)
@click.option("--port", type=int, default=8080, help="The port to run the local GUI on (defaults to 8080)")
@click.option("--no-open",
              is_flag=True,
              default=False,
              help="Skip opening the local GUI in the browser after starting it")
# TODO: Make --gui optional and hidden when we start distributing the GUI wheel through the modules API
@click.option("--gui",
              type=PathParameter(exists=True, file_okay=True, dir_okay=True),
              required=True,
              help="The path to the checked out GUI repository or packaged .whl file")
def start(port: int, no_open: bool, gui: Path) -> None:
    """Start the local GUI."""
    logger = container.logger()
    docker_manager = container.docker_manager()

    gui_container = docker_manager.get_container_by_name(LOCAL_GUI_CONTAINER_NAME)
    if gui_container is not None:
        if gui_container.status == "running":
            raise RuntimeError(
                "The local GUI is already running, run `lean gui restart` to restart it or `lean gui stop` to stop it")

        gui_container.remove()

    # The dict containing all options passed to `docker run`
    # See all available options at https://docker-py.readthedocs.io/en/stable/containers.html
    run_options: Dict[str, Any] = {
        "name": LOCAL_GUI_CONTAINER_NAME,
        "commands": [],
        "environment": {
            "PYTHONUNBUFFERED": "1",
            "RUNNING_IN_DOCKER": "true"
        },
        "mounts": [],
        "volumes": {},
        "ports": {
            "8080": str(port)
        }
    }

    # Cache the site-packages so we don't reinstall everything when the container is restarted
    docker_manager.create_volume("lean_cli_gui_python")
    run_options["volumes"]["lean_cli_gui_python"] = {
        "bind": "/usr/local/lib/python3.9/site-packages",
        "mode": "rw"
    }

    # Install the CLI in the GUI container
    if lean.__version__ == "dev":
        lean_cli_dir = Path(__file__).absolute().parent.parent.parent.parent
        run_options["volumes"][str(lean_cli_dir)] = {
            "bind": "/lean-cli",
            "mode": "rw"
        }

        run_options["commands"].append("cd /lean-cli")
        run_options["commands"].append("pip install --progress-bar off -r requirements.txt")
    else:
        run_options["commands"].append("pip install --progress-bar off --upgrade lean")

    # Install the GUI in the GUI container
    if gui.is_file():
        run_options["mounts"].append(Mount(target=f"/{gui.name}", source=str(gui), type="bind", read_only=True))
        run_options["commands"].append("pip uninstall -y leangui")
        run_options["commands"].append(f"pip install --progress-bar off /{gui.name}")
    else:
        run_options["volumes"][str(gui)] = {
            "bind": "/lean-cli-gui",
            "mode": "rw"
        }

        run_options["commands"].append("cd /lean-cli-gui")
        run_options["commands"].append("pip install --progress-bar off -r requirements.txt")

    # Mount the `lean init` directory in the GUI container
    cli_root_dir = container.lean_config_manager().get_cli_root_directory()
    run_options["volumes"][str(cli_root_dir)] = {
        "bind": "/LeanCLI",
        "mode": "rw"
    }

    # Mount the global config directory in the GUI container
    run_options["volumes"][str(Path("~/.lean").expanduser())] = {
        "bind": "/root/.lean",
        "mode": "rw"
    }

    # Run the GUI in the GUI container
    run_options["commands"].append("cd /LeanCLI")
    run_options["commands"].append(f"leangui {port}")

    # Don't delete temporary directories when the command exits, the container will still need them
    container.temp_manager().delete_temporary_directories_when_done = False

    logger.info("Starting the local GUI, this may take some time...")

    try:
        docker_manager.run_image(DockerImage(name="python", tag="3.9.6-buster"), **run_options)
    except APIError as error:
        msg = error.explanation
        if isinstance(msg, str) and "port is already allocated" in msg:
            raise RuntimeError(f"Port {port} is already in use, please specify a different port using --port <number>")
        raise error

    url = f"http://localhost:{port}/"

    # Wait until the GUI is running
    while True:
        gui_container = docker_manager.get_container_by_name(LOCAL_GUI_CONTAINER_NAME)
        if gui_container is None or gui_container.status != "running":
            docker_manager.show_logs(LOCAL_GUI_CONTAINER_NAME)
            raise RuntimeError(
                "Something went wrong while starting the local GUI, see the logs above for more information")

        try:
            requests.get(url)
            break
        except requests.exceptions.ConnectionError:
            time.sleep(0.25)

    logger.info(f"The local GUI has started and is running on {url}")

    if not no_open:
        webbrowser.open(url)
