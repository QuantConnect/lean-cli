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
import platform
from pathlib import Path
from typing import Any, Dict, Optional

from docker.types import Mount

from lean.components.config.lean_config_manager import LeanConfigManager
from lean.components.docker.csharp_compiler import CSharpCompiler
from lean.components.docker.docker_manager import DockerManager
from lean.components.util.logger import Logger
from lean.components.util.temp_manager import TempManager
from lean.models.config import DebuggingMethod
from lean.models.docker import DockerImage


class LeanRunner:
    """The LeanRunner class contains the code that runs the LEAN engine locally."""

    def __init__(self,
                 logger: Logger,
                 csharp_compiler: CSharpCompiler,
                 lean_config_manager: LeanConfigManager,
                 docker_manager: DockerManager,
                 temp_manager: TempManager) -> None:
        """Creates a new LeanRunner instance.

        :param logger: the logger that is used to print messages
        :param csharp_compiler: the CSharpCompiler instance used to compile C# projects before running them
        :param lean_config_manager: the LeanConfigManager instance to retrieve Lean configuration from
        :param docker_manager: the DockerManager instance which is used to interact with Docker
        :param temp_manager: the TempManager instance to use when creating temporary directories
        """
        self._logger = logger
        self._csharp_compiler = csharp_compiler
        self._lean_config_manager = lean_config_manager
        self._docker_manager = docker_manager
        self._temp_manager = temp_manager

    def run_lean(self,
                 environment: str,
                 algorithm_file: Path,
                 output_dir: Path,
                 image: DockerImage,
                 debugging_method: Optional[DebuggingMethod]) -> None:
        """Runs the LEAN engine locally in Docker.

        Raises an error if something goes wrong.

        :param environment: the environment to run the algorithm in
        :param algorithm_file: the path to the file containing the algorithm
        :param output_dir: the directory to save output data to
        :param image: the LEAN engine image to use
        :param debugging_method: the debugging method if debugging needs to be enabled, None if not
        """
        project_dir = algorithm_file.parent

        # The dict containing all options passed to `docker run`
        # See all available options at https://docker-py.readthedocs.io/en/stable/containers.html
        run_options = self.get_basic_docker_config(environment, algorithm_file, output_dir, image, debugging_method)

        run_options["entrypoint"] = ["dotnet", "QuantConnect.Lean.Launcher.dll"]

        # Set up PTVSD debugging
        if debugging_method == DebuggingMethod.PTVSD:
            run_options["ports"]["5678"] = "5678"

        # Set up VSDBG debugging
        if debugging_method == DebuggingMethod.VSDBG:
            run_options["name"] = "lean_cli_vsdbg"

        # Set up Rider debugging
        if debugging_method == DebuggingMethod.Rider:
            run_options["ports"]["22"] = "2222"
            run_options["entrypoint"] = ["/sbin/my_init", "--enable-insecure-key", "--",
                                         "bash", "-c",
                                         "chmod 600 /etc/insecure_key && echo 'HostKey /etc/insecure_key' >> /etc/ssh/sshd_config && /usr/sbin/sshd && dotnet QuantConnect.Lean.Launcher.dll"]

            self._docker_manager.create_volume("lean_cli_rider")
            run_options["volumes"]["lean_cli_rider"] = {
                "bind": "/root/.local/share/JetBrains",
                "mode": "rw"
            }

        # Run the engine and log the result
        success = self._docker_manager.run_image(image, **run_options)

        cli_root_dir = self._lean_config_manager.get_cli_root_directory()
        relative_project_dir = project_dir.relative_to(cli_root_dir)
        relative_output_dir = output_dir.relative_to(cli_root_dir)

        if success:
            self._logger.info(
                f"Successfully ran '{relative_project_dir}' in the '{environment}' environment and stored the output in '{relative_output_dir}'")
        else:
            raise RuntimeError(
                f"Something went wrong while running '{relative_project_dir}' in the '{environment}' environment, the output is stored in '{relative_output_dir}'")

    def get_basic_docker_config(self,
                                environment: str,
                                algorithm_file: Path,
                                output_dir: Path,
                                image: DockerImage,
                                debugging_method: Optional[DebuggingMethod]) -> Dict[str, Any]:
        """Creates a basic Docker config to run the engine with.

        This method constructs the parts of the Docker config that is the same for both the engine and the optimizer.

        :param environment: the environment to run the algorithm in
        :param algorithm_file: the path to the file containing the algorithm
        :param output_dir: the directory to save output data to
        :param image: the LEAN engine image to run
        :param debugging_method: the debugging method if debugging needs to be enabled, None if not
        :return: the Docker configuration containing basic configuration to run Lean
        """
        project_dir = algorithm_file.parent

        # Compile the project first if it is a C# project
        # If compilation fails, there is no need to do anything else
        csharp_dll_dir = None
        if algorithm_file.name.endswith(".cs"):
            csharp_dll_dir = self._csharp_compiler.compile_csharp_project(project_dir, image)

        # Create the output directory if it doesn't exist yet
        if not output_dir.exists():
            output_dir.mkdir(parents=True)

        # Create the storage directory if it doesn't exist yet
        storage_dir = project_dir / "storage"
        if not storage_dir.exists():
            storage_dir.mkdir(parents=True)

        # Create a file containing the complete Lean configuration
        config = self._lean_config_manager.get_complete_lean_config(environment,
                                                                    algorithm_file,
                                                                    debugging_method)

        config["data-folder"] = "/Lean/Data"
        config["results-destination-folder"] = "/Results"
        config["object-store-root"] = "/Storage"

        config_path = self._temp_manager.create_temporary_directory() / "config.json"
        with config_path.open("w+", encoding="utf-8") as file:
            file.write(json.dumps(config, indent=4))

        # The dict containing all options passed to `docker run`
        # See all available options at https://docker-py.readthedocs.io/en/stable/containers.html
        run_options: Dict[str, Any] = {
            "mounts": [
                Mount(target="/Lean/Launcher/bin/Debug/config.json",
                      source=str(config_path),
                      type="bind",
                      read_only=True)
            ],
            "volumes": {},
            "ports": {}
        }

        # Mount the data directory
        data_dir = self._lean_config_manager.get_data_directory()
        run_options["volumes"][str(data_dir)] = {
            "bind": "/Lean/Data",
            "mode": "rw"
        }

        # Mount the output directory
        run_options["volumes"][str(output_dir)] = {
            "bind": "/Results",
            "mode": "rw"
        }

        # Mount the local object store directory
        run_options["volumes"][str(storage_dir)] = {
            "bind": "/Storage",
            "mode": "rw"
        }

        # Make sure host.docker.internal resolves on Linux
        # See https://github.com/QuantConnect/Lean/pull/5092
        if platform.system() == "Linux":
            run_options["extra_hosts"] = {
                "host.docker.internal": "172.17.0.1"
            }

        # Mount the project which needs to be ran
        if algorithm_file.name.endswith(".py"):
            run_options["volumes"][str(project_dir)] = {
                "bind": "/LeanCLI",
                "mode": "ro"
            }
        else:
            for extension in ["dll", "pdb"]:
                run_options["mounts"].append(
                    Mount(target=f"/Lean/Launcher/bin/Debug/{project_dir.name}.{extension}",
                          source=str(csharp_dll_dir / f"{project_dir.name}.{extension}"),
                          type="bind"))

        return run_options
