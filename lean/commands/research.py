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

import webbrowser
from pathlib import Path

import click

from lean.click import LeanCommand, PathParameter
from lean.constants import RESEARCH_IMAGE
from lean.container import container


@click.command(cls=LeanCommand, requires_cli_project=True)
@click.argument("project", type=PathParameter(exists=True, file_okay=False, dir_okay=True))
@click.option("--port", type=int, default=8888, help="The port to run Jupyter Lab on (defaults to 8888)")
@click.option("--update",
              is_flag=True,
              default=False,
              help="Pull the selected research environment version before starting it")
@click.option("--version",
              type=str,
              default="latest",
              help="The version of the research environment version to run (defaults to the latest installed version)")
def research(project: Path, port: int, update: bool, version: str) -> None:
    """Run a Jupyter Lab environment locally using Docker."""
    cli_config_manager = container.cli_config_manager()

    project_config_manager = container.project_config_manager()
    project_config = project_config_manager.get_project_config(project)
    project_config.set("composer-dll-directory", "/Lean/Launcher/bin/Debug")
    project_config.set("messaging-handler", "QuantConnect.Messaging.Messaging")
    project_config.set("job-queue-handler", "QuantConnect.Queues.JobQueue")
    project_config.set("api-handler", "QuantConnect.Api.Api")
    project_config.set("job-user-id", cli_config_manager.user_id.get_value("1"))
    project_config.set("api-access-token", cli_config_manager.api_token.get_value("default"))

    lean_config_manager = container.lean_config_manager()
    data_dir = lean_config_manager.get_data_directory()

    run_options = {
        "volumes": {
            str(data_dir): {
                "bind": "/Lean/Launcher/Data",
                "mode": "ro"
            },
            str(project): {
                "bind": "/Lean/Launcher/bin/Debug/Notebooks",
                "mode": "rw"
            }
        },
        "ports": {
            "8888": str(port)
        },
        "on_run": lambda: webbrowser.open(f"http://localhost:{port}/")
    }

    docker_manager = container.docker_manager()

    if version != "latest":
        if not docker_manager.tag_exists(RESEARCH_IMAGE, version):
            raise RuntimeError("The specified version does not exist")

    if update:
        docker_manager.pull_image(RESEARCH_IMAGE, version)

    if version == "latest" and not update:
        update_manager = container.update_manager()
        update_manager.warn_if_docker_image_outdated(RESEARCH_IMAGE)

    docker_manager.run_image(RESEARCH_IMAGE, version, **run_options)
