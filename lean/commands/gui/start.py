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
import os
import platform
import time
import tkinter
import tkinter.messagebox
import webbrowser
import zipfile
from pathlib import Path
from typing import Dict, Any, Optional

import click
import requests
from docker.errors import APIError
from docker.types import Mount

import lean
from lean.click import LeanCommand, PathParameter
from lean.constants import LOCAL_GUI_CONTAINER_NAME, GUI_PRODUCT_ID
from lean.container import container
from lean.models.docker import DockerImage
from lean.models.logger import Option


def _error(message: str, shortcut_launch: bool) -> None:
    """Halts operation of the CLI in a way that is user-friendly to both CLI and desktop shortcut users.

    :poram message: the error message
    :param shortcut_launch: whether the command was invoked using the desktop shortcut
    """
    if shortcut_launch:
        # By default tkinter.messagebox.showerror creates an empty root window and shows it
        # By manually creating and hiding that root window we can show just the error box
        root = tkinter.Tk()
        root.overrideredirect(1)
        root.withdraw()

        tkinter.messagebox.showerror("Lean CLI", message)

    raise RuntimeError(message)


def _get_organization_id(given_input: str, shortcut_launch: bool) -> str:
    """Converts the organization name or id given by the user to an organization id.

    Raises an error if the user is not a member of an organization with the given name or id.

    :param given_input: the input given by the user
    :param shortcut_launch: whether the command was invoked using the desktop shortcut
    :return: the id of the organization given by the user
    """
    all_organizations = container.api_client().organizations.get_all()

    organization = next((o for o in all_organizations if o.id == given_input or o.name == given_input), None)
    if organization is None:
        _error(f"You are not a member of an organization with name or id '{given_input}'", shortcut_launch)

    return organization.id


@click.command(cls=LeanCommand, requires_docker=True, requires_lean_config=True)
@click.option("--organization",
              type=str,
              help="The name or id of the organization with the local GUI module subscription")
@click.option("--port", type=int, default=5612, help="The port to run the local GUI on (defaults to 5612)")
@click.option("--no-open",
              is_flag=True,
              default=False,
              help="Skip opening the local GUI in the browser after starting it")
@click.option("--shortcut",
              is_flag=True,
              default=False,
              help="Create a desktop shortcut for launching the local GUI")
@click.option("--gui",
              type=PathParameter(exists=True, file_okay=True, dir_okay=True),
              hidden=True,
              help="The path to the checked out GUI repository or packaged .whl file")
@click.option("--shortcut-launch",
              is_flag=True,
              default=False,
              hidden=True,
              help="Hidden flag which tells the CLI the command has been launched from the desktop shortcut")
def start(organization: Optional[str],
          port: int,
          no_open: bool,
          shortcut: bool,
          gui: Optional[Path],
          shortcut_launch: bool) -> None:
    """Start the local GUI."""
    logger = container.logger()
    docker_manager = container.docker_manager()
    temp_manager = container.temp_manager()
    module_manager = container.module_manager()
    api_client = container.api_client()

    gui_container = docker_manager.get_container_by_name(LOCAL_GUI_CONTAINER_NAME)
    if gui_container is not None:
        if gui_container.status == "running":
            if shortcut_launch:
                port = gui_container.ports["5612/tcp"][0]["HostPort"]
                url = f"http://localhost:{port}/"
                webbrowser.open(url)
                return
            else:
                _error(
                    "The local GUI is already running, run `lean gui restart` to restart it or `lean gui stop` to stop it",
                    shortcut_launch
                )

        gui_container.remove()

    if organization is not None:
        organization_id = _get_organization_id(organization, shortcut_launch)
    else:
        organizations = api_client.organizations.get_all()
        options = [Option(id=organization.id, label=organization.name) for organization in organizations]
        organization_id = logger.prompt_list("Select the organization with the local GUI module subscription", options)

    module_manager.install_module(GUI_PRODUCT_ID, organization_id)

    shortcut_manager = container.shortcut_manager()
    if shortcut:
        shortcut_manager.create_shortcut(organization_id)
    else:
        shortcut_manager.prompt_if_necessary(organization_id)

    # The dict containing all options passed to `docker run`
    # See all available options at https://docker-py.readthedocs.io/en/stable/containers.html
    run_options: Dict[str, Any] = {
        "name": LOCAL_GUI_CONTAINER_NAME,
        "detach": True,
        "remove": False,
        "commands": [],
        "environment": {
            "PYTHONUNBUFFERED": "1",
            "QC_LOCAL_GUI": "true",
            "QC_DOCKER_HOST_SYSTEM": platform.system(),
            "QC_DOCKER_HOST_MACHINE": platform.machine(),
            "QC_ORGANIZATION_ID": organization_id,
            "QC_API": os.environ.get("QC_API", "")
        },
        "mounts": [],
        "volumes": {},
        "ports": {
            "5612": str(port)
        }
    }

    # Cache the site-packages so we don't re-install everything when the container is restarted
    docker_manager.create_volume("lean_cli_gui_python")
    run_options["volumes"]["lean_cli_gui_python"] = {
        "bind": "/root/.local/lib/python3.9/site-packages",
        "mode": "rw"
    }

    # Update PATH in the GUI container to add executables installed with pip
    run_options["commands"].append('export PATH="$PATH:/root/.local/bin"')

    package_file_name = module_manager.get_installed_packages_by_module(GUI_PRODUCT_ID)[0].get_file_name()
    with zipfile.ZipFile(Path.home() / ".lean" / "modules" / package_file_name) as package_file:
        content_file_names = [f.replace("content/", "") for f in package_file.namelist() if f.startswith("content/")]
        wheel_file_name = next(f for f in content_file_names if f.endswith(".whl"))
        terminal_file_name = next(f for f in content_file_names if f.endswith(".zip"))

    # Install the CLI in the GUI container
    run_options["commands"].append("pip uninstall -y lean")
    if lean.__version__ == "dev":
        lean_cli_dir = Path(__file__).absolute().parent.parent.parent.parent
        run_options["volumes"][str(lean_cli_dir)] = {
            "bind": "/lean-cli",
            "mode": "rw"
        }

        run_options["commands"].append("cd /lean-cli")
        run_options["commands"].append("pip install --user --progress-bar off -r requirements.txt")
    else:
        run_options["commands"].append("pip install --user --progress-bar off --upgrade lean")

    # Install the GUI in the GUI container
    run_options["commands"].append("pip uninstall -y leangui")
    if gui is None:
        run_options["commands"].append(
            f"unzip -p /root/.lean/modules/{package_file_name} content/{wheel_file_name} > /{wheel_file_name}")
        run_options["commands"].append(f"pip install --user --progress-bar off /{wheel_file_name}")
    elif gui.is_file():
        run_options["mounts"].append(Mount(target=f"/{gui.name}", source=str(gui), type="bind", read_only=True))
        run_options["commands"].append(f"pip install --user --progress-bar off /{gui.name}")
    else:
        run_options["volumes"][str(gui)] = {
            "bind": "/lean-cli-gui",
            "mode": "rw"
        }

        run_options["commands"].append("cd /lean-cli-gui")
        run_options["commands"].append("pip install --user --progress-bar off -r requirements.txt")

    # Extract the terminal in the GUI container
    run_options["commands"].append(
        f"unzip -p /root/.lean/modules/{package_file_name} content/{terminal_file_name} > /{terminal_file_name}")
    run_options["commands"].append(f"unzip -o /{terminal_file_name} -d /terminal")

    # Write correct streaming url to /terminal/local.socket.host.conf
    run_options["commands"].append(f'echo "ws://localhost:{port}/streaming" > /terminal/local.socket.host.conf')

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

    # Mount a directory to the tmp directory in the GUI container
    gui_tmp_directory = temp_manager.create_temporary_directory()
    run_options["volumes"][str(gui_tmp_directory)] = {
        "bind": "/tmp",
        "mode": "rw"
    }

    # Set up the path mappings between paths in the host system and paths in the GUI container
    run_options["environment"]["DOCKER_PATH_MAPPINGS"] = json.dumps({
        "/LeanCLI": cli_root_dir.as_posix(),
        "/root/.lean": Path("~/.lean").expanduser().as_posix(),
        "/tmp": gui_tmp_directory.as_posix()
    })

    # Mount the Docker socket in the GUI container
    run_options["mounts"].append(Mount(target="/var/run/docker.sock",
                                       source="/var/run/docker.sock",
                                       type="bind",
                                       read_only=False))

    # Run the GUI in the GUI container
    run_options["commands"].append("cd /LeanCLI")
    run_options["commands"].append(f"leangui")

    # Don't delete temporary directories when the command exits, the container will still need them
    temp_manager.delete_temporary_directories_when_done = False

    logger.info("Starting the local GUI, this may take some time...")

    # Pull the Docker images used by the local GUI
    # If this is done while the local GUI is running there is a big delay between pressing Backtest and seeing it run
    update_manager = container.update_manager()
    cli_config_manager = container.cli_config_manager()
    update_manager.pull_docker_image_if_necessary(cli_config_manager.get_engine_image(), False)
    update_manager.pull_docker_image_if_necessary(cli_config_manager.get_research_image(), False)

    try:
        docker_manager.run_image(DockerImage(name="python", tag="3.9.6-buster"), **run_options)
    except APIError as error:
        msg = error.explanation
        if isinstance(msg, str) and any(m in msg.lower() for m in [
            "port is already allocated",
            "ports are not available"
            "an attempt was made to access a socket in a way forbidden by its access permissions"
        ]):
            _error(f"Port {port} is already in use, please specify a different port using --port <number>",
                   shortcut_launch)
        raise error

    url = f"http://localhost:{port}/"

    # Wait until the GUI is running
    while True:
        gui_container = docker_manager.get_container_by_name(LOCAL_GUI_CONTAINER_NAME)
        if gui_container is None or gui_container.status != "running":
            docker_manager.show_logs(LOCAL_GUI_CONTAINER_NAME)
            if shortcut_launch:
                _error("Something went wrong while starting the local GUI, run `lean gui logs` for more information",
                       shortcut_launch)
            else:
                _error("Something went wrong while starting the local GUI, see the logs above for more information",
                       shortcut_launch)

        try:
            requests.get(url)
            break
        except requests.exceptions.ConnectionError:
            time.sleep(0.25)

    logger.info(f"The local GUI has started and is running on {url}")

    if not no_open:
        webbrowser.open(url)
