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

import click
import requests

from lean.click import LeanCommand
from lean.constants import LOCAL_GUI_CONTAINER_NAME
from lean.container import container


@click.command(cls=LeanCommand, requires_docker=True)
@click.option("--no-open",
              is_flag=True,
              default=False,
              help="Skip opening the local GUI in the browser after restarting it")
def restart(no_open: bool) -> None:
    """Restart the local GUI and open it in the browser."""
    logger = container.logger()
    docker_manager = container.docker_manager()

    gui_container = docker_manager.get_container_by_name(LOCAL_GUI_CONTAINER_NAME)
    if gui_container is None or gui_container.status != "running":
        raise RuntimeError("The local GUI is not running, you can start it using `lean gui start`")

    logger.info("Restarting the local GUI's Docker container")
    gui_container.restart()

    port = gui_container.ports["5612/tcp"][0]["HostPort"]
    url = f"http://localhost:{port}/"

    # Wait until the GUI is running again
    while True:
        if LOCAL_GUI_CONTAINER_NAME not in docker_manager.get_running_containers():
            docker_manager.show_logs(LOCAL_GUI_CONTAINER_NAME)
            raise RuntimeError(
                "Something went wrong while restarting the local GUI, see the logs above for more information")

        try:
            requests.get(url)
            break
        except requests.exceptions.ConnectionError:
            time.sleep(0.25)

    container.logger().info(f"The local GUI has restarted and is running on {url}")

    if not no_open:
        webbrowser.open(url)
