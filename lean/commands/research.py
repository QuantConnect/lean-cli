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
from typing import Any, Dict, Optional

import click
from docker.errors import APIError
from docker.types import Mount

from lean.click import LeanCommand, PathParameter
from lean.constants import DEFAULT_RESEARCH_IMAGE
from lean.container import container


def _check_docker_output(chunk: str, port: int) -> None:
    """Checks the output of the Docker container and opens the browser if Jupyter Lab has started.

    :param chunk: the output chunk
    :param port: the port Jupyter Lab will be running on
    """
    if "is running at:" in chunk:
        webbrowser.open(f"http://localhost:{port}/")


@click.command(cls=LeanCommand, requires_lean_config=True, requires_docker=True)
@click.argument("project",
                type=PathParameter(exists=True, file_okay=False, dir_okay=True))
@click.option("--port", type=int, default=8888,
              help="The port to run Jupyter Lab on (defaults to 8888)")
@click.option("--image",
              type=str,
              help=f"The LEAN research image to use (defaults to {DEFAULT_RESEARCH_IMAGE})")
@click.option("--update",
              is_flag=True,
              default=False,
              help="Pull the LEAN research image before starting the research environment")
def research(project: Path, port: int, image: Optional[str], update: bool) -> None:
    """Run a Jupyter Lab environment locally using Docker.

    By default the official LEAN research image is used.
    You can override this using the --image option.
    Alternatively you can set the default research image using `lean config set research-image <image>`.
    """
    cli_config_manager = container.cli_config_manager()

    project_config_manager = container.project_config_manager()
    project_config = project_config_manager.get_project_config(project)

    # Copy the config to a temporary config file before we add some research-specific configuration to it
    config_path = container.temp_manager().create_temporary_directory() / "config.json"
    project_config.file = config_path

    project_config.set("composer-dll-directory", "/Lean/Launcher/bin/Debug")
    project_config.set("messaging-handler", "QuantConnect.Messaging.Messaging")
    project_config.set("job-queue-handler", "QuantConnect.Queues.JobQueue")
    project_config.set("api-handler", "QuantConnect.Api.Api")
    project_config.set("job-user-id", cli_config_manager.user_id.get_value("1"))
    project_config.set("api-access-token", cli_config_manager.api_token.get_value("default"))

    lean_config_manager = container.lean_config_manager()
    data_dir = lean_config_manager.get_data_directory()

    run_options: Dict[str, Any] = {
        "commands": [],
        "environment": {},
        "mounts": [
            Mount(target="/Lean/Launcher/bin/Debug/Notebooks/config.json",
                  source=str(config_path),
                  type="bind",
                  read_only=True)
        ],
        "volumes": {
            str(data_dir): {
                "bind": "/Lean/Launcher/Data",
                "mode": "rw"
            }
        },
        "ports": {
            "8888": str(port)
        },
        "on_output": lambda chunk: _check_docker_output(chunk, port)
    }

    lean_runner = container.lean_runner()
    if project_config.get("algorithm-language", "Python") == "Python":
        lean_runner.set_up_python_options(project, "/Lean/Launcher/bin/Debug/Notebooks", run_options)
    else:
        lean_runner.set_up_csharp_options(project, run_options)
        run_options["volumes"][str(project)] = {
            "bind": "/Lean/Launcher/bin/Debug/Notebooks",
            "mode": "rw"
        }

    # Add references to all DLLs in QuantConnect.csx so custom C# libraries can be imported with using statements
    run_options["commands"].append(" && ".join([
        'find . -maxdepth 1 -iname "*.dll" | xargs -I _ echo \'#r "_"\' | cat - QuantConnect.csx > NewQuantConnect.csx',
        "mv NewQuantConnect.csx QuantConnect.csx"
    ]))

    # Run the script that starts Jupyter Lab when all set up has been done
    run_options["commands"].append("./start.sh")

    cli_config_manager = container.cli_config_manager()
    research_image = cli_config_manager.get_research_image(image)

    docker_manager = container.docker_manager()

    if update or not docker_manager.supports_dotnet_5(research_image):
        docker_manager.pull_image(research_image)

    if str(research_image) == DEFAULT_RESEARCH_IMAGE and not update:
        update_manager = container.update_manager()
        update_manager.warn_if_docker_image_outdated(research_image)

    try:
        docker_manager.run_image(research_image, **run_options)
    except APIError as error:
        msg = error.explanation
        if isinstance(msg, str) and "port is already allocated" in msg:
            raise RuntimeError(f"Port {port} is already in use, please specify a different port using --port <number>")
        raise error
