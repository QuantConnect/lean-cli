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

import click

from lean.click import LeanCommand
from lean.constants import LOCAL_GUI_CONTAINER_NAME
from lean.container import container


@click.command(cls=LeanCommand, requires_docker=True)
def stop() -> None:
    """Stop the local GUI."""
    docker_manager = container.docker_manager()

    gui_container = docker_manager.get_container_by_name(LOCAL_GUI_CONTAINER_NAME)
    if gui_container is None or gui_container.status != "running":
        raise RuntimeError("The local GUI is not running, you can start it using `lean gui start`")

    gui_container.stop()

    for container_name in docker_manager.get_running_containers():
        if container_name.startswith("lean_cli_gui_research_"):
            docker_manager.get_container_by_name(container_name).stop()

    container.logger().info(f"Successfully stopped the local GUI")
