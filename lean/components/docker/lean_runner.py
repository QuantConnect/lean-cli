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
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from docker.types import Mount

from lean.components.config.lean_config_manager import LeanConfigManager
from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.docker.docker_manager import DockerManager
from lean.components.util.logger import Logger
from lean.components.util.temp_manager import TempManager
from lean.models.config import DebuggingMethod
from lean.models.docker import DockerImage


class LeanRunner:
    """The LeanRunner class contains the code that runs the LEAN engine locally."""

    def __init__(self,
                 logger: Logger,
                 project_config_manager: ProjectConfigManager,
                 lean_config_manager: LeanConfigManager,
                 docker_manager: DockerManager,
                 temp_manager: TempManager) -> None:
        """Creates a new LeanRunner instance.

        :param logger: the logger that is used to print messages
        :param project_config_manager: the ProjectConfigManager instance to retrieve project configuration from
        :param lean_config_manager: the LeanConfigManager instance to retrieve Lean configuration from
        :param docker_manager: the DockerManager instance which is used to interact with Docker
        :param temp_manager: the TempManager instance to use when creating temporary directories
        """
        self._logger = logger
        self._project_config_manager = project_config_manager
        self._lean_config_manager = lean_config_manager
        self._docker_manager = docker_manager
        self._temp_manager = temp_manager

    def run_lean(self,
                 lean_config: Dict[str, Any],
                 environment: str,
                 algorithm_file: Path,
                 output_dir: Path,
                 image: DockerImage,
                 debugging_method: Optional[DebuggingMethod]) -> None:
        """Runs the LEAN engine locally in Docker.

        Raises an error if something goes wrong.

        :param lean_config: the LEAN configuration to use
        :param environment: the environment to run the algorithm in
        :param algorithm_file: the path to the file containing the algorithm
        :param output_dir: the directory to save output data to
        :param image: the LEAN engine image to use
        :param debugging_method: the debugging method if debugging needs to be enabled, None if not
        """
        project_dir = algorithm_file.parent

        # The dict containing all options passed to `docker run`
        # See all available options at https://docker-py.readthedocs.io/en/stable/containers.html
        run_options = self.get_basic_docker_config(lean_config, algorithm_file, output_dir, debugging_method)

        # Set up PTVSD debugging
        if debugging_method == DebuggingMethod.PTVSD:
            run_options["ports"]["5678"] = "5678"

        # Set up VSDBG debugging
        if debugging_method == DebuggingMethod.VSDBG:
            run_options["name"] = "lean_cli_vsdbg"

        # Set up Rider debugging
        if debugging_method == DebuggingMethod.Rider:
            run_options["ports"]["22"] = "2222"
            run_options["commands"].append("/usr/sbin/enable_insecure_key")
            run_options["commands"].append("chmod 600 /etc/insecure_key")
            run_options["commands"].append('echo "HostKey /etc/insecure_key" >> /etc/ssh/sshd_config')
            run_options["commands"].append("/usr/sbin/sshd")

            self._docker_manager.create_volume("lean_cli_rider")
            run_options["volumes"]["lean_cli_rider"] = {
                "bind": "/root/.local/share/JetBrains",
                "mode": "rw"
            }

        run_options["commands"].append("exec dotnet QuantConnect.Lean.Launcher.dll")

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
                                lean_config: Dict[str, Any],
                                algorithm_file: Path,
                                output_dir: Path,
                                debugging_method: Optional[DebuggingMethod]) -> Dict[str, Any]:
        """Creates a basic Docker config to run the engine with.

        This method constructs the parts of the Docker config that is the same for both the engine and the optimizer.

        :param lean_config: the LEAN configuration to use
        :param algorithm_file: the path to the file containing the algorithm
        :param output_dir: the directory to save output data to
        :param debugging_method: the debugging method if debugging needs to be enabled, None if not
        :return: the Docker configuration containing basic configuration to run Lean
        """
        project_dir = algorithm_file.parent

        # Create the output directory if it doesn't exist yet
        if not output_dir.exists():
            output_dir.mkdir(parents=True)

        # Create the storage directory if it doesn't exist yet
        storage_dir = project_dir / "storage"
        if not storage_dir.exists():
            storage_dir.mkdir(parents=True)

        lean_config["data-folder"] = "/Lean/Data"
        lean_config["results-destination-folder"] = "/Results"
        lean_config["object-store-root"] = "/Storage"

        config_path = self._temp_manager.create_temporary_directory() / "config.json"
        with config_path.open("w+", encoding="utf-8") as file:
            file.write(json.dumps(lean_config, indent=4))

        # The dict containing all options passed to `docker run`
        # See all available options at https://docker-py.readthedocs.io/en/stable/containers.html
        run_options: Dict[str, Any] = {
            "commands": [],
            "environment": {},
            "stop_signal": "SIGINT" if debugging_method is None else "SIGKILL",
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

        # Set up language-specific run options
        if algorithm_file.name.endswith(".py"):
            self.set_up_python_options(project_dir, "/LeanCLI", run_options)
        else:
            self.set_up_csharp_options(project_dir, run_options)

        return run_options

    def set_up_python_options(self, project_dir: Path, remote_directory: str, run_options: Dict[str, Any]) -> None:
        """Sets up Docker run options specific to Python projects.

        :param project_dir: the path to the project directory
        :param remote_directory: the path to mount the project directory to, ending without a forward slash
        :param run_options: the dictionary to append run options to
        """
        # Mount the project directory
        run_options["volumes"][str(project_dir)] = {
            "bind": remote_directory,
            "mode": "rw"
        }

        # Check if we have any dependencies to install, so we don't mount volumes needlessly
        if not (project_dir / "requirements.txt").is_file():
            return
        if len((project_dir / "requirements.txt").read_text(encoding="utf-8").strip()) == 0:
            return

        # Mount a volume to pip's cache directory so we only download packages once
        self._docker_manager.create_volume("lean_cli_pip")
        run_options["volumes"]["lean_cli_pip"] = {
            "bind": "/root/.cache/pip",
            "mode": "rw"
        }

        # Mount a volume to the user packages directory so we don't install packages every time
        site_packages_volume = self._docker_manager.create_site_packages_volume(project_dir / "requirements.txt")
        run_options["volumes"][site_packages_volume] = {
            "bind": "/root/.local/lib/python3.6/site-packages",
            "mode": "rw"
        }

        # Update PATH in the Docker container to prevent pip install warnings
        run_options["commands"].append('export PATH="$PATH:/root/.local/bin"')

        # Install custom libraries to the cached user packages directory
        # We only need to do this if it hasn't already been done before for this site packages volume
        # To keep track of this we create a special file in the site packages directory after installation
        # If this file already exists we can skip pip install completely
        marker_file = "/root/.local/lib/python3.6/site-packages/pip-install-done"
        run_options["commands"].extend([
            f"! test -f {marker_file} && pip install --user -r {remote_directory}/requirements.txt",
            f"touch {marker_file}"
        ])

    def set_up_csharp_options(self, project_dir: Path, run_options: Dict[str, Any]) -> None:
        """Sets up Docker run options specific to C# projects.

        :param project_dir: the path to the file containing the algorithm
        :param run_options: the dictionary to append run options to
        """
        # Create a temporary directory used for compiling the C# files
        compile_dir = self._temp_manager.create_temporary_directory()

        # Copy all the C# files in the project to compile_dir
        for source_path in project_dir.rglob("*.cs"):
            posix_path = source_path.relative_to(project_dir).as_posix()
            if "bin/" in posix_path or "obj/" in posix_path or ".ipynb_checkpoints/" in posix_path:
                continue

            new_path = compile_dir / source_path.relative_to(project_dir)
            new_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, new_path)

        # Create a .csproj file to compile with
        with (compile_dir / f"{project_dir.name}.csproj").open("w+", encoding="utf-8") as file:
            libraries = self._project_config_manager.get_csharp_libraries(project_dir)
            package_references = "\n".join(
                f'<PackageReference Include="{library.name}" Version="{library.version}" />' for library in libraries)

            file.write(f"""
<Project Sdk="Microsoft.NET.Sdk">
    <PropertyGroup>
        <Configuration Condition=" '$(Configuration)' == '' ">Debug</Configuration>
        <Platform Condition=" '$(Platform)' == '' ">AnyCPU</Platform>
        <TargetFramework>net5.0</TargetFramework>
        <LangVersion>9</LangVersion>
        <GenerateAssemblyInfo>false</GenerateAssemblyInfo>
        <OutputPath>/Lean/Launcher/bin/Debug</OutputPath>
        <AppendTargetFrameworkToOutputPath>false</AppendTargetFrameworkToOutputPath>
        <AutoGenerateBindingRedirects>true</AutoGenerateBindingRedirects>
        <GenerateBindingRedirectsOutputType>true</GenerateBindingRedirectsOutputType>
        <AutomaticallyUseReferenceAssemblyPackages>false</AutomaticallyUseReferenceAssemblyPackages>
        <CopyLocalLockFileAssemblies>true</CopyLocalLockFileAssemblies>
        <PathMap>/LeanCLI={str(project_dir)}</PathMap>
        <NoWarn>CS0618</NoWarn>
    </PropertyGroup>
    <ItemGroup>
        <Reference Include="/Lean/Launcher/bin/Debug/*.dll">
            <Private>False</Private>
        </Reference>
        {package_references}
    </ItemGroup>
</Project>
            """.strip())

        # Mount the compile directory
        run_options["volumes"][str(compile_dir)] = {
            "bind": "/LeanCLI",
            "mode": "rw"
        }

        # Mount a volume to NuGet's cache directory so we only download packages once
        self._docker_manager.create_volume("lean_cli_nuget")
        run_options["volumes"]["lean_cli_nuget"] = {
            "bind": "/root/.nuget/packages",
            "mode": "rw"
        }

        # Reduce the dotnet output
        run_options["environment"]["DOTNET_NOLOGO"] = "true"
        run_options["environment"]["DOTNET_CLI_TELEMETRY_OPTOUT"] = "true"

        # Build the project before running LEAN
        run_options["commands"].append(f'dotnet build "/LeanCLI/{project_dir.name}.csproj"')
