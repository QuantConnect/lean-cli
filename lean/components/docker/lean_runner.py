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

        :param project_dir: the path to the project directory
        :param run_options: the dictionary to append run options to
        """
        compile_root = self._get_csharp_compile_root(project_dir)

        # Mount the compile root
        run_options["volumes"][str(compile_root)] = {
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

        # Set up the MSBuild properties
        msbuild_properties = {
            "Configuration": "Debug",
            "Platform": "AnyCPU",
            "TargetFramework": "net5.0",
            "LangVersion": "9",
            "OutputPath": "/Compile/bin",
            "GenerateAssemblyInfo": "false",
            "GenerateTargetFrameworkAttribute": "false",
            "AppendTargetFrameworkToOutputPath": "false",
            "AutoGenerateBindingRedirects": "true",
            "GenerateBindingRedirectsOutputType": "true",
            "AutomaticallyUseReferenceAssemblyPackages": "false",
            "CopyLocalLockFileAssemblies": "true",
            "PathMap": f"/LeanCLI={str(compile_root)}"
        }

        tmp_directory = self._temp_manager.create_temporary_directory()

        directory_build_props = tmp_directory / "Directory.Build.props"
        with directory_build_props.open("w+", encoding="utf-8") as file:
            file.write("""
<Project>
    <PropertyGroup>
        <BaseIntermediateOutputPath>/Compile/obj/$(MSBuildProjectName)/</BaseIntermediateOutputPath>
        <IntermediateOutputPath>/Compile/obj/$(MSBuildProjectName)/</IntermediateOutputPath>
    </PropertyGroup>
</Project>
            """.strip())

        copy_csharp_dependencies = tmp_directory / "copy_csharp_dependencies.py"
        with copy_csharp_dependencies.open("w+", encoding="utf-8") as file:
            file.write("""
import json
import os
import platform
import shutil
import sys
from pathlib import Path

project_assets = json.loads(Path(sys.argv[-1]).read_text(encoding="utf-8"))
package_folders = [Path(folder) for folder in project_assets["packageFolders"].keys()]

ubuntu_version = os.popen("lsb_release -rs").read().strip()
accepted_runtime_identifiers = ["base", "unix", "linux", "debian", "ubuntu", f"ubuntu.{ubuntu_version}"]

if platform.machine() in ["arm64", "aarch64"]:
    accepted_runtime_identifiers.extend(["unix-arm", "linux-arm", "debian-arm", "ubuntu-arm", f"ubuntu.{ubuntu_version}-arm"])
else:
    accepted_runtime_identifiers.extend(["unix-x64", "linux-x64", "debian-x64", "ubuntu-x64", f"ubuntu.{ubuntu_version}-x64"])

def copy_file(library_id, partial_path):
    for folder in package_folders:
        full_path = folder / library_id.lower() / partial_path
        if full_path.exists():
            break
    else:
        return

    target_path = Path("/Lean/Launcher/bin/Debug") / full_path.name
    if not target_path.exists():
        shutil.copy(full_path, target_path)

project_target = list(project_assets["targets"].keys())[0]
for library_id, library_data in project_assets["targets"][project_target].items():
    for key, value in library_data.get("runtimeTargets", {}).items():
        if "rid" not in value or value["rid"] in accepted_runtime_identifiers:
            copy_file(library_id, key)

    for key, value in library_data.get("runtime", {}).items():
        if "rid" not in value or value["rid"] in accepted_runtime_identifiers:
            copy_file(library_id, key)
            """.strip())

        run_options["mounts"].extend([Mount(target="/Directory.Build.props",
                                            source=str(directory_build_props),
                                            type="bind",
                                            read_only=False),
                                      Mount(target="/copy_csharp_dependencies.py",
                                            source=str(copy_csharp_dependencies),
                                            type="bind",
                                            read_only=False)])

        # Build the project before running LEAN
        relative_project_dir = str(project_dir.relative_to(compile_root)).replace("\\", "/")
        msbuild_properties = ";".join(f"{key}={value}" for key, value in msbuild_properties.items())
        run_options["commands"].append(f'dotnet build "/LeanCLI/{relative_project_dir}" "-p:{msbuild_properties}"')

        # Copy over the algorithm DLL
        run_options["commands"].append(
            f'cp "/Compile/bin/{project_dir.name}.dll" "/Lean/Launcher/bin/Debug/{project_dir.name}.dll"')

        # Copy over all library DLLs that don't already exist in /Lean/Launcher/bin/Debug
        # CopyLocalLockFileAssemblies does not copy the OS-specific DLLs to the output directory
        # We therefore use a custom Python script that does take the OS into account when deciding what to copy
        run_options["commands"].append(
            f'python /copy_csharp_dependencies.py "/Compile/obj/{project_dir.name}/project.assets.json"')

        # Copy over all output DLLs that don't already exist in /Lean/Launcher/bin/Debug
        # The call above does not copy over DLLs of project references, so we still need this
        run_options["commands"].append(f"cp -R -n /Compile/bin/. /Lean/Launcher/bin/Debug/")

    def _get_csharp_compile_root(self, project_dir: Path) -> Path:
        """Returns the path to the directory that should be mounted to compile the project directory.

        If the project is part of a solution this is the solution root.
        If the project is not part of a solution this is the project directory itself.

        :param project_dir: the path to the project directory
        :return: the path that should be mounted in the Docker container when compiling the C# project
        """
        current_dir = project_dir
        while current_dir.parent != current_dir:
            if next(current_dir.glob("*.sln"), None) is not None:
                return current_dir

            current_dir = current_dir.parent

        return project_dir
