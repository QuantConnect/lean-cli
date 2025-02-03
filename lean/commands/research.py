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
from typing import Optional, Tuple
from click import command, argument, option, Choice
from lean.click import LeanCommand, PathParameter
from lean.components.docker.lean_runner import LeanRunner
from lean.constants import DEFAULT_RESEARCH_IMAGE, LEAN_ROOT_PATH
from lean.container import container
from lean.models.cli import cli_data_downloaders
from lean.components.util.name_extraction import convert_to_class_name
from lean.components.util.json_modules_handler import non_interactive_config_build_for_name
from lean.models.click_options import options_from_json, get_configs_for_options

def _check_docker_output(chunk: str, port: int) -> None:
    """Checks the output of the Docker container and opens the browser if Jupyter Lab has started.

    :param chunk: the output chunk
    :param port: the port Jupyter Lab will be running on
    """
    from webbrowser import open
    if "is running at:" in chunk:
        open(f"http://localhost:{port}/")


@command(cls=LeanCommand, requires_lean_config=True, requires_docker=True)
@argument("project", type=PathParameter(exists=True, file_okay=False, dir_okay=True))
@option("--port", type=int, default=8888, help="The port to run Jupyter Lab on (defaults to 8888)")
@option("--data-provider-historical",
              type=Choice([dp.get_name() for dp in cli_data_downloaders], case_sensitive=False),
              default="Local",
              help="Update the Lean configuration file to retrieve data from the given historical provider")
@options_from_json(get_configs_for_options("research"))
@option("--download-data",
              is_flag=True,
              default=False,
              help=f"Update the Lean configuration file to download data from the QuantConnect API, alias for --data-provider-historical QuantConnect")
@option("--data-purchase-limit",
              type=int,
              help="The maximum amount of QCC to spend on downloading data during the research session when using QuantConnect as historical data provider")
@option("--detach", "-d",
              is_flag=True,
              default=False,
              help="Run Jupyter Lab in a detached Docker container and return immediately")
@option("--no-open",
              is_flag=True,
              default=False,
              help="Don't open the Jupyter Lab environment in the browser after starting it")
@option("--image", type=str, help=f"The LEAN research image to use (defaults to {DEFAULT_RESEARCH_IMAGE})")
@option("--update",
              is_flag=True,
              default=False,
              help="Pull the LEAN research image before starting the research environment")
@option("--extra-config",
              type=(str, str),
              multiple=True,
              hidden=True)
@option("--extra-docker-config",
              type=str,
              default="{}",
              help="Extra docker configuration as a JSON string. "
                   "For more information https://docker-py.readthedocs.io/en/stable/containers.html")
@option("--no-update",
              is_flag=True,
              default=False,
              help="Use the local LEAN research image instead of pulling the latest version")
def research(project: Path,
             port: int,
             data_provider_historical: Optional[str],
             download_data: bool,
             data_purchase_limit: Optional[int],
             detach: bool,
             no_open: bool,
             image: Optional[str],
             update: bool,
             extra_config: Optional[Tuple[str, str]],
             extra_docker_config: Optional[str],
             no_update: bool,
             **kwargs) -> None:
    """Run a Jupyter Lab environment locally using Docker.

    By default the official LEAN research image is used.
    You can override this using the --image option.
    Alternatively you can set the default research image using `lean config set research-image <image>`.
    """
    from docker.types import Mount
    from docker.errors import APIError
    from json import loads

    logger = container.logger

    project_manager = container.project_manager
    algorithm_file = project_manager.find_algorithm_file(project, not_throw = True)

    # We just need the algorithm file name to create the configurations for lean and
    # the docker container. We do not need an algorithm file to run a research project
    if algorithm_file is None:
        algorithm_file = project / 'main.py'
    algorithm_name = convert_to_class_name(project)

    environment_name = "backtesting"
    lean_config_manager = container.lean_config_manager
    lean_config = lean_config_manager.get_complete_lean_config(environment_name, algorithm_file, None)
    lean_config["composer-dll-directory"] = LEAN_ROOT_PATH
    lean_config["research-object-store-name"] = algorithm_name

    if download_data:
        data_provider_historical = "QuantConnect"

    research_image, container_module_version, project_config = container.manage_docker_image(image, update, no_update,
                                                                                             algorithm_file.parent,
                                                                                             False)

    paths_to_mount = None

    if data_provider_historical is not None:
        organization_id = container.organization_manager.try_get_working_organization_id()
        data_provider = non_interactive_config_build_for_name(lean_config, data_provider_historical,
                                                              cli_data_downloaders, kwargs, logger, environment_name)
        data_provider.ensure_module_installed(organization_id, container_module_version)
        container.lean_config_manager.set_properties(data_provider.get_settings())
        paths_to_mount = data_provider.get_paths_to_mount()
    lean_config_manager.configure_data_purchase_limit(lean_config, data_purchase_limit)

    lean_runner = container.lean_runner
    temp_manager = container.temp_manager

    # Set extra config
    for key, value in extra_config:
        lean_config[key] = value

    run_options = lean_runner.get_basic_docker_config(lean_config,
                                                      algorithm_file,
                                                      temp_manager.create_temporary_directory(),
                                                      None,
                                                      False,
                                                      detach,
                                                      research_image,
                                                      paths_to_mount)

    # Mount project dir to the Notebooks directory first, avoid using volumes to prevent overwriting mounting logic for /LeanCLI
    run_options["mounts"].append(Mount(
        target=f"{LEAN_ROOT_PATH}/Notebooks",
        source=str(project),
        type="bind",
        read_only=False
    ))

    # Mount the config in the notebooks directory as well
    local_config_path = next(m["Source"] for m in run_options["mounts"] if m["Target"].endswith("config.json"))
    run_options["mounts"].append(Mount(target=f"{LEAN_ROOT_PATH}/Notebooks/config.json",
                                       source=str(local_config_path),
                                       type="bind",
                                       read_only=True))

    # Jupyter Lab runs on port 8888, we expose it to the local port specified by the user
    run_options["ports"]["8888"] = str(port)

    # Open the browser as soon as Jupyter Lab has started
    if detach or not no_open:
        run_options["on_output"] = lambda chunk: _check_docker_output(chunk, port)

    # Make Ctrl+C stop Jupyter Lab immediately
    run_options["stop_signal"] = "SIGKILL"

    # Allow notebooks to be embedded in iframes
    run_options["commands"].append("mkdir -p ~/.jupyter")
    run_options["commands"].append(
        'echo "c.ServerApp.disable_check_xsrf = True\nc.ServerApp.tornado_settings = {\'headers\': {\'Content-Security-Policy\': \'frame-ancestors self *\'}}" > ~/.jupyter/jupyter_server_config.py')

    # Hide headers in notebooks
    run_options["commands"].append("mkdir -p ~/.ipython/profile_default/static/custom")
    run_options["commands"].append(
        'echo "#header-container { display: none !important; }" > ~/.ipython/profile_default/static/custom/custom.css')

    # Run the script that starts Jupyter Lab when all set up has been done
    run_options["commands"].append("./start.sh")

    # Add known additional run options from the extra docker config
    LeanRunner.parse_extra_docker_config(run_options, loads(extra_docker_config))

    try:
        container.docker_manager.run_image(research_image, **run_options)
    except APIError as error:
        msg = error.explanation
        if isinstance(msg, str) and any(m in msg.lower() for m in [
            "port is already allocated",
            "ports are not available"
            "an attempt was made to access a socket in a way forbidden by its access permissions"
        ]):
            raise RuntimeError(f"Port {port} is already in use, please specify a different port using --port <number>")
        raise error

    if detach:
        temp_manager.delete_temporary_directories_when_done = False

        relative_project_dir = algorithm_file.parent.relative_to(lean_config_manager.get_cli_root_directory())

        logger.info(
            f"Successfully started Jupyter Lab environment for '{relative_project_dir}' in the '{run_options['name']}' container")
        logger.info("You can use Docker's own commands to manage the detached container")
