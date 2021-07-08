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
from typing import Optional

import click
from docker.errors import APIError
from docker.types import Mount

from lean.click import LeanCommand, PathParameter
from lean.constants import DEFAULT_RESEARCH_IMAGE
from lean.container import container
from lean.models.data_providers import all_data_providers
from lean.models.data_providers.quantconnect import QuantConnectDataProvider


def _check_docker_output(chunk: str, port: int) -> None:
    """Checks the output of the Docker container and opens the browser if Jupyter Lab has started.

    :param chunk: the output chunk
    :param port: the port Jupyter Lab will be running on
    """
    if "is running at:" in chunk:
        webbrowser.open(f"http://localhost:{port}/")


@click.command(cls=LeanCommand, requires_lean_config=True, requires_docker=True)
@click.argument("project", type=PathParameter(exists=True, file_okay=False, dir_okay=True))
@click.option("--port", type=int, default=8888, help="The port to run Jupyter Lab on (defaults to 8888)")
@click.option("--data-provider",
              type=click.Choice([dp.get_name() for dp in all_data_providers], case_sensitive=False),
              help="Update the Lean configuration file to retrieve data from the given provider")
@click.option("--download-data",
              is_flag=True,
              default=False,
              help=f"Update the Lean configuration file to download data from the QuantConnect API, alias for --data-provider {QuantConnectDataProvider.get_name()}")
@click.option("--data-purchase-limit",
              type=int,
              help="The maximum amount of QCC to spend on downloading data during the research session when using QuantConnect as data provider")
@click.option("--image", type=str, help=f"The LEAN research image to use (defaults to {DEFAULT_RESEARCH_IMAGE})")
@click.option("--update",
              is_flag=True,
              default=False,
              help="Pull the LEAN research image before starting the research environment")
def research(project: Path,
             port: int,
             data_provider: Optional[str],
             download_data: bool,
             data_purchase_limit: Optional[int],
             image: Optional[str],
             update: bool) -> None:
    """Run a Jupyter Lab environment locally using Docker.

    By default the official LEAN research image is used.
    You can override this using the --image option.
    Alternatively you can set the default research image using `lean config set research-image <image>`.
    """
    project_manager = container.project_manager()
    algorithm_file = project_manager.find_algorithm_file(project)

    lean_config_manager = container.lean_config_manager()
    lean_config = lean_config_manager.get_complete_lean_config("backtesting", algorithm_file, None)
    lean_config["composer-dll-directory"] = "/Lean/Launcher/bin/Debug"

    if download_data:
        data_provider = QuantConnectDataProvider.get_name()

    if data_provider is not None:
        data_provider = next(dp for dp in all_data_providers if dp.get_name() == data_provider)
        data_provider.build(lean_config, container.logger()).configure(lean_config, "backtesting")

    lean_config_manager.configure_data_purchase_limit(lean_config, data_purchase_limit)

    lean_runner = container.lean_runner()
    temp_manager = container.temp_manager()
    run_options = lean_runner.get_basic_docker_config(lean_config,
                                                      algorithm_file,
                                                      temp_manager.create_temporary_directory(),
                                                      None,
                                                      False)

    # Mount the config in the notebooks directory as well
    local_config_path = next(m["Source"] for m in run_options["mounts"] if m["Target"].endswith("config.json"))
    run_options["mounts"].append(Mount(target="/Lean/Launcher/bin/Debug/Notebooks/config.json",
                                       source=str(local_config_path),
                                       type="bind",
                                       read_only=True))

    # Jupyter Lab runs on port 8888, we expose it to the local port specified by the user
    run_options["ports"]["8888"] = str(port)

    # Open the browser as soon as Jupyter Lab has started
    run_options["on_output"] = lambda chunk: _check_docker_output(chunk, port)

    # Make Ctrl+C stop Jupyter Lab immediately
    run_options["stop_signal"] = "SIGKILL"

    # Mount the project to the notebooks directory
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
