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
from typing import Any, Dict, Optional, List

from lean.components.cloud.module_manager import ModuleManager
from lean.components.config.lean_config_manager import LeanConfigManager
from lean.components.config.output_config_manager import OutputConfigManager
from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.docker.docker_manager import DockerManager
from lean.components.util.logger import Logger
from lean.components.util.project_manager import ProjectManager
from lean.components.util.temp_manager import TempManager
from lean.components.util.xml_manager import XMLManager
from lean.constants import MODULES_DIRECTORY, LEAN_ROOT_PATH, DEFAULT_DATA_DIRECTORY_NAME, \
    DEFAULT_LEAN_DOTNET_FRAMEWORK, DEFAULT_LEAN_PYTHON_VERSION
from lean.constants import DOCKER_PYTHON_SITE_PACKAGES_PATH
from lean.models.docker import DockerImage
from lean.models.utils import DebuggingMethod

class LeanRunner:
    """The LeanRunner class contains the code that runs the LEAN engine locally."""

    def __init__(self,
                 logger: Logger,
                 project_config_manager: ProjectConfigManager,
                 lean_config_manager: LeanConfigManager,
                 output_config_manager: OutputConfigManager,
                 docker_manager: DockerManager,
                 module_manager: ModuleManager,
                 project_manager: ProjectManager,
                 temp_manager: TempManager,
                 xml_manager: XMLManager) -> None:
        """Creates a new LeanRunner instance.

        :param logger: the logger that is used to print messages
        :param project_config_manager: the ProjectConfigManager instance to retrieve project configuration from
        :param lean_config_manager: the LeanConfigManager instance to retrieve Lean configuration from
        :param output_config_manager: the OutputConfigManager instance to retrieve backtest/live configuration from
        :param docker_manager: the DockerManager instance which is used to interact with Docker
        :param module_manager: the ModuleManager instance to retrieve the installed modules from
        :param project_manager: the ProjectManager instance to use for copying source code to output directories
        :param temp_manager: the TempManager instance to use for creating temporary directories
        :param xml_manager: the XMLManager instance to use for reading/writing XML files
        """
        self._logger = logger
        self._project_config_manager = project_config_manager
        self._lean_config_manager = lean_config_manager
        self._output_config_manager = output_config_manager
        self._docker_manager = docker_manager
        self._module_manager = module_manager
        self._project_manager = project_manager
        self._temp_manager = temp_manager
        self._xml_manager = xml_manager

    def run_lean(self,
                 lean_config: Dict[str, Any],
                 environment: str,
                 algorithm_file: Path,
                 output_dir: Path,
                 image: DockerImage,
                 debugging_method: Optional[DebuggingMethod],
                 release: bool,
                 detach: bool,
                 extra_docker_config: Optional[Dict[str, Any]] = None,
                 paths_to_mount: Optional[Dict[str, str]] = None) -> None:
        """Runs the LEAN engine locally in Docker.

        Raises an error if something goes wrong.

        :param lean_config: the LEAN configuration to use
        :param environment: the environment to run the algorithm in
        :param algorithm_file: the path to the file containing the algorithm
        :param output_dir: the directory to save output data to
        :param image: the LEAN engine image to use
        :param debugging_method: the debugging method if debugging needs to be enabled, None if not
        :param release: whether C# projects should be compiled in release configuration instead of debug
        :param detach: whether LEAN should run in a detached container
        :param extra_docker_config: additional docker configurations
        :param paths_to_mount: additional paths to mount to the container
        """
        self._logger.debug(f'LeanRunner().run_lean: lean_config: {lean_config}')
        project_dir = algorithm_file.parent

        # The dict containing all options passed to `docker run`
        # See all available options at https://docker-py.readthedocs.io/en/stable/containers.html
        run_options = self.get_basic_docker_config(lean_config,
                                                   algorithm_file,
                                                   output_dir,
                                                   debugging_method,
                                                   release,
                                                   detach,
                                                   image,
                                                   paths_to_mount)

        # Add known additional run options from the extra docker config
        self.parse_extra_docker_config(run_options, extra_docker_config)

        # Set up PTVSD or DebugPy debugging
        if debugging_method == DebuggingMethod.PTVSD or debugging_method == DebuggingMethod.DebugPy:
            run_options["ports"]["5678"] = "5678"

        # Set up VSDBG debugging
        if debugging_method == DebuggingMethod.VSDBG:
            run_options["name"] = "lean_cli_vsdbg"

            # lean_cli_vsdbg is not unique, so we don't store the container name in the output directory's config
            output_config = self._output_config_manager.get_output_config(output_dir)
            output_config.delete("container")

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

        # Setup debugging with QC Extension
        if debugging_method == DebuggingMethod.LocalPlatform:
            run_options["ports"]["5678"] = "0" # Using port 0 will assign a random port every time

        run_options["commands"].append("exec dotnet QuantConnect.Lean.Launcher.dll")

        # Copy the project's code to the output directory
        self._project_manager.copy_code(algorithm_file.parent, output_dir / "code")

        # Run the engine and log the result
        # Run as a subprocess to capture the output before logging it

        # Format error messages for cleaner output logs
        run_options["format_output"] = self.format_error_before_logging

        success = self._docker_manager.run_image(image, **run_options)

        cli_root_dir = self._lean_config_manager.get_cli_root_directory()
        relative_project_dir = project_dir.relative_to(cli_root_dir)
        relative_output_dir = output_dir.relative_to(cli_root_dir)

        if debugging_method == DebuggingMethod.LocalPlatform:
            # set the container port mapped with host in config for later retrieval
            port = self._docker_manager.get_container_port(run_options["name"], "5678/tcp")
            output_config = self._output_config_manager.get_output_config(output_dir)
            output_config.set("debugport", port)

        if detach:
            self._temp_manager.delete_temporary_directories_when_done = False

            self._logger.info(
                f"Successfully started '{relative_project_dir}' in the '{environment}' environment in the '{run_options['name']}' container")
            self._logger.info(f"The output will be stored in '{relative_output_dir}'")
            self._logger.info("You can use Docker's own commands to manage the detached container")
        elif success:
            self._logger.info(
                f"Successfully ran '{relative_project_dir}' in the '{environment}' environment and stored the output in '{relative_output_dir}'")
        else:
            raise RuntimeError(
                f"Something went wrong while running '{relative_project_dir}' in the '{environment}' environment, the output is stored in '{relative_output_dir}'")

    def get_basic_docker_config(self,
                                lean_config: Dict[str, Any],
                                algorithm_file: Path,
                                output_dir: Path,
                                debugging_method: Optional[DebuggingMethod],
                                release: bool,
                                detach: bool,
                                image: DockerImage,
                                paths_to_mount: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Creates a basic Docker config to run the engine with.

        This method constructs the parts of the Docker config that is the same for both the engine and the optimizer.

        :param lean_config: the LEAN configuration to use
        :param algorithm_file: the path to the file containing the algorithm
        :param output_dir: the directory to save output data to
        :param debugging_method: the debugging method if debugging needs to be enabled, None if not
        :param release: whether C# projects should be compiled in release configuration instead of debug
        :param detach: whether LEAN should run in a detached container
        :param image: The docker image that will be used
        :return: the Docker configuration containing basic configuration to run Lean
        :param paths_to_mount: additional paths to mount to the container
        """

        project_dir = algorithm_file.parent
        project_config = self._project_config_manager.get_project_config(project_dir)
        docker_project_config = project_config.get("docker", {})

        # Force the use of the LocalDisk map/factor providers if no recent zip present and not using ApiDataProvider
        data_dir = self._lean_config_manager.get_data_directory()
        self._handle_data_providers(lean_config, data_dir)

        storage_dir = self._lean_config_manager.get_cli_root_directory() / "storage"

        # Create the output directory if it doesn't exist yet
        # Create the storage directory if it doesn't exist yet
        self._ensure_directories_exist([output_dir, storage_dir])

        lean_config.update({
            "debug-mode": self._logger.debug_logging_enabled,
            "data-folder": "/Lean/Data",
            "results-destination-folder": "/Results",
            "object-store-root": "/Storage"
        })

        run_options = self._initialize_run_options(detach, docker_project_config, debugging_method)

        self._mount_common_directories(run_options, paths_to_mount, lean_config, data_dir, storage_dir, project_dir, output_dir)

        # Update all hosts that need to point to the host's localhost to host.docker.internal so they resolve properly
        # TODO: we should remove it or add to config json
        for key in ["terminal-link-server-host"]:
            if key not in lean_config:
                continue

            if lean_config[key] == "localhost" or lean_config[key] == "127.0.0.1":
                lean_config[key] = "host.docker.internal"

        # Set up modules
        set_up_common_csharp_options_called = self._setup_installed_packages(run_options, image)

        # Set up language-specific run options
        self.setup_language_specific_run_options(run_options, project_dir, algorithm_file,
                                                 set_up_common_csharp_options_called, release,
                                                 image)

        self._mount_lean_config_and_finalize(run_options, lean_config, output_dir)

        return run_options

    def get_basic_docker_config_without_algo(self,
                                             lean_config: Dict[str, Any],
                                             debugging_method: Optional[DebuggingMethod],
                                             detach: bool,
                                             image: DockerImage,
                                             target_path: str,
                                             paths_to_mount: Optional[Dict[str, str]] = None,
                                             config_local_path: Path = None) -> Dict[str, Any]:
        """Creates a basic Docker config to run the engine with.

        This method constructs the parts of the Docker config that is the same for both the engine and the optimizer.

        :param lean_config: the LEAN configuration to use
        :param debugging_method: the debugging method if debugging needs to be enabled, None if not
        :param detach: whether LEAN should run in a detached container
        :param image: The docker image that will be used
        :param target_path: The target path inside the Docker container where the C# project should be located.
        :param paths_to_mount: additional paths to mount to the container
        :param config_local_path: optional config local path
        :return: the Docker configuration containing basic configuration to run Lean
        """

        docker_project_config = {"docker": {}}
        # Force the use of the LocalDisk map/factor providers if no recent zip present and not using ApiDataProvider
        data_dir = self._lean_config_manager.get_data_directory()
        self._handle_data_providers(lean_config, data_dir)

        # Create the storage directory if it doesn't exist yet
        storage_dir = self._lean_config_manager.get_cli_root_directory() / "storage"
        self._ensure_directories_exist([storage_dir])

        lean_config.update({
            "debug-mode": self._logger.debug_logging_enabled,
            "data-folder": "/Lean/Data",
            "object-store-root": "/Storage"
        })

        run_options = self._initialize_run_options(detach, docker_project_config, debugging_method)

        self._mount_common_directories(run_options, paths_to_mount, lean_config, data_dir, storage_dir, None, None)

        # Update all hosts that need to point to the host's localhost to host.docker.internal so they resolve properly
        # TODO: we should remove it or add to config json
        for key in ["terminal-link-server-host"]:
            if key not in lean_config:
                continue

            if lean_config[key] == "localhost" or lean_config[key] == "127.0.0.1":
                lean_config[key] = "host.docker.internal"

        # Set up modules
        self._setup_installed_packages(run_options, image, target_path)

        self._mount_lean_config_and_finalize(run_options, lean_config, None, config_local_path)

        return run_options

    def _mount_lean_config_and_finalize(self, run_options: Dict[str, Any], lean_config: Dict[str, Any],
                                        output_dir: Optional[Path], config_local_path: Path = None):
        """Mounts Lean config and finalizes."""
        from docker.types import Mount
        from uuid import uuid4
        from json import dumps
        from os import makedirs

        # Save the final Lean config to a temporary file so we can mount it into the container
        if not config_local_path:
            config_local_path = self._temp_manager.create_temporary_directory()
        makedirs(config_local_path, exist_ok=True)
        config_path = config_local_path / "config.json"
        with config_path.open("w+", encoding="utf-8") as file:
            file.write(dumps(lean_config, indent=4))

        # Mount the Lean config
        run_options["mounts"].append(Mount(target=f"{LEAN_ROOT_PATH}/config.json",
                                           source=str(config_path),
                                           type="bind",
                                           read_only=True))

        # Assign the container a name and store it in the output directory's configuration
        run_options["name"] = lean_config.get("container-name", f"lean_cli_{str(uuid4()).replace('-', '')}")

        # set the hostname
        if "hostname" in lean_config:
            run_options["hostname"] = lean_config["hostname"]

        if output_dir:
            output_config = self._output_config_manager.get_output_config(output_dir)
            output_config.set("container", run_options["name"])
            if "backtest-name" in lean_config:
                output_config.set("backtest-name", lean_config["backtest-name"])
            if "environment" in lean_config and "environments" in lean_config:
                environment = lean_config["environments"][lean_config["environment"]]
                if "live-mode-brokerage" in environment:
                    output_config.set("brokerage", environment["live-mode-brokerage"].split(".")[-1])

    def _setup_installed_packages(self, run_options: Dict[str, Any], image: DockerImage, target_path: str = "/Lean/Launcher/bin/Debug"):
        """Sets up installed packages."""
        installed_packages = self._module_manager.get_installed_packages()
        if installed_packages:
            self._logger.debug(f"LeanRunner._setup_installed_packages(): installed packages {len(installed_packages)}")
            self.set_up_common_csharp_options(run_options, target_path)

            # Mount the modules directory
            run_options["volumes"][MODULES_DIRECTORY] = {"bind": "/Modules", "mode": "ro"}

            # Add the modules directory as a NuGet source root
            run_options["commands"].append("dotnet nuget add source /Modules")
            # Create a C# project used to resolve the dependencies of the modules
            run_options["commands"].append("mkdir /ModulesProject")
            run_options["commands"].append("dotnet new sln -o /ModulesProject")

            framework_ver = self._docker_manager.get_image_label(image, 'target_framework', DEFAULT_LEAN_DOTNET_FRAMEWORK)
            run_options["commands"].append(f"dotnet new classlib -o /ModulesProject -f {framework_ver} --no-restore")
            run_options["commands"].append("rm /ModulesProject/Class1.cs")

            # Add all modules to the project, automatically resolving all dependencies
            for package in installed_packages:
                self._logger.debug(f"LeanRunner._setup_installed_packages(): Adding module {package} to the project")
                run_options["commands"].append(f"rm -rf /root/.nuget/packages/{package.name.lower()}")
                run_options["commands"].append(f"dotnet add /ModulesProject package {package.name} --version {package.version}")

            # Copy all module files to /Lean/Launcher/bin/Debug, but don't overwrite anything that already exists
            run_options["commands"].append("python /copy_csharp_dependencies.py /Compile/obj/ModulesProject/project.assets.json")

        return bool(installed_packages)

    def _mount_common_directories(self,
                                  run_options: Dict[str, Any],
                                  paths_to_mount: Optional[Dict[str, str]],
                                  lean_config: Dict[str, Any],
                                  data_dir: Path,
                                  storage_dir: Path,
                                  project_dir: Optional[Path],
                                  output_dir: Optional[Path]):
        """
        Mounts common directories.

        1. mount the paths passed in
        2. mount the project and library directories (param: `project_dir` is not None)
        3. mount the data directory
        4. mount the output directory (param: `output_dir` is not None)
        5. mount the local object store directory
        6. mount all local files referenced in the Lean config
        """
        from docker.types import Mount

        # 1
        self.mount_paths(paths_to_mount, lean_config, run_options)

        # 2
        if project_dir:
            self.mount_project_and_library_directories(project_dir, run_options)

        # 3
        run_options["volumes"][str(data_dir)] = {"bind": "/Lean/Data", "mode": "rw"}

        # 4
        if output_dir:
            run_options["volumes"][str(output_dir)] = {"bind": "/Results", "mode": "rw"}
        # 5
        run_options["volumes"][str(storage_dir)] = {"bind": "/Storage", "mode": "rw"}

        # 6
        cli_root_dir = self._lean_config_manager.get_cli_root_directory()
        files_to_mount = [
            ("transaction-log", cli_root_dir),
            ("terminal-link-symbol-map-file", cli_root_dir / DEFAULT_DATA_DIRECTORY_NAME / "symbol-properties")
        ]
        for key, base_path in files_to_mount:
            if key not in lean_config or lean_config[key] == "":
                continue

            lean_config_entry = Path(lean_config[key])
            local_path = lean_config_entry if lean_config_entry.is_absolute() else base_path / lean_config_entry
            if not local_path.exists():
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.touch()

            run_options["mounts"].append(Mount(target=f"/Files/{key}",
                                               source=str(local_path),
                                               type="bind",
                                               read_only=False))

            lean_config[key] = f"/Files/{key}"


    def _initialize_run_options(self, detach: bool, docker_project_config: Dict[str, Any], debugging_method: Optional[DebuggingMethod]):
        """
        Initializes run options.

        The dict containing all options passed to `docker run`
        See all available options at https://docker-py.readthedocs.io/en/stable/containers.html
        """
        return {
            "detach": detach,
            "commands": [],
            "environment": docker_project_config.get("environment", {}),
            "stop_signal": "SIGINT" if debugging_method is None else "SIGKILL",
            "mounts": [],
            "volumes": {},
            "ports": docker_project_config.get("ports", {})
        }

    def _ensure_directories_exist(self, dirs: List[Path]):
        """Ensures directories exist."""
        for dir_path in dirs:
            if not dir_path.exists():
                dir_path.mkdir(parents=True)

    def _handle_data_providers(self, lean_config: Dict[str, Any], data_dir: Path):
        """Handles data provider logic."""
        if lean_config.get("data-provider", None) != "QuantConnect.Lean.Engine.DataFeeds.ApiDataProvider":
            self._force_disk_provider_if_necessary(lean_config,
                                                   "map-file-provider",
                                                   "QuantConnect.Data.Auxiliary.LocalZipMapFileProvider",
                                                   "QuantConnect.Data.Auxiliary.LocalDiskMapFileProvider",
                                                   data_dir / "equity" / "usa" / "map_files")
            self._force_disk_provider_if_necessary(lean_config,
                                                   "factor-file-provider",
                                                   "QuantConnect.Data.Auxiliary.LocalZipFactorFileProvider",
                                                   "QuantConnect.Data.Auxiliary.LocalDiskFactorFileProvider",
                                                   data_dir / "equity" / "usa" / "factor_files")

    def set_up_python_options(self, project_dir: Path, run_options: Dict[str, Any], image: DockerImage) -> None:
        """Sets up Docker run options specific to Python projects.

        :param project_dir: the path to the project directory
        :param run_options: the dictionary to append run options to
        :param image: the docker image that will be used
        """

        from docker.types import Mount
        # Compile python files
        source_files = self._project_manager.get_source_files(project_dir)
        source_files = [file.relative_to(
            project_dir).as_posix() for file in source_files]
        source_files = [f'"/LeanCLI/{file}"' for file in source_files]

        # Only need to compile files in backtest/live (where the files were mounted in "/LeanCLI") but not research
        run_options["commands"].append(
            f"""if [ -d '/LeanCLI' ];
            then
                python -m compileall {' '.join(source_files)};
            else
                echo '/LeanCLI is not mounted, skipping compilation...';
            fi""")

        # Combine the requirements from all library projects and the current project
        library_dir = self._lean_config_manager.get_cli_root_directory() / "Library"
        requirements_files = list(library_dir.rglob("requirements.txt")) + [project_dir / "requirements.txt"]
        requirements_files = [file for file in requirements_files if file.is_file()]
        requirements = self._concat_python_requirements(requirements_files)

        # Check if we have any dependencies to install, so we don't mount volumes needlessly
        if requirements == "":
            return

        # Create a requirements.txt file for the combined requirements
        requirements_txt = self._temp_manager.create_temporary_directory() / "requirements.txt"
        with requirements_txt.open("w+", encoding="utf-8") as file:
            file.write(requirements)

        # Mount the requirements.txt file
        run_options["mounts"].append(Mount(target="/requirements.txt",
                                           source=str(requirements_txt),
                                           type="bind",
                                           read_only=True))

        # Mount a volume to pip's cache directory so we only download packages once
        self._docker_manager.create_volume("lean_cli_pip")
        run_options["volumes"]["lean_cli_pip"] = {
            "bind": "/root/.cache/pip",
            "mode": "rw"
        }

        python_version = self._docker_manager.get_image_label(image, 'python_version',
                                                              DEFAULT_LEAN_PYTHON_VERSION)
        site_packages_path = DOCKER_PYTHON_SITE_PACKAGES_PATH.replace('{LEAN_PYTHON_VERSION}', python_version)

        # Mount a volume to the user packages directory so we don't install packages every time
        site_packages_volume = self._docker_manager.create_site_packages_volume(requirements_txt)
        run_options["volumes"][site_packages_volume] = {
            "bind": f"{site_packages_path}",
            "mode": "rw"
        }

        # Update PATH in the Docker container to prevent pip install warnings about its executables not being on PATH
        run_options["commands"].append('export PATH="$PATH:/root/.local/bin"')

        # Install custom libraries to the cached user packages directory
        # We only need to do this if it hasn't already been done before for this site packages volume
        # To keep track of this we create a special file in the site packages directory after installation
        # If this file already exists we can skip pip install completely
        marker_file = f"{site_packages_path}/pip-install-done"
        run_options["commands"].extend([
            f"! test -f {marker_file} && pip install --user --progress-bar off -r /requirements.txt",
            f"touch {marker_file}"
        ])

    def _concat_python_requirements(self, requirements_files: List[Path]) -> str:
        """Combines the requirements from multiple requirements.txt files.

        Ensures there are no duplicate requirements and that all output lines are valid.
        Requirements are sorted alphabetically to ensure consistent output.

        :param requirements_files: the paths to the requirements.txt files
        :return: the normalized requirements from all given requirements.txt files
        """
        from pkg_resources import Requirement
        requirements = []
        for file in requirements_files:
            for line in file.read_text(encoding="utf-8").splitlines():
                try:
                    requirements.append(Requirement.parse(line))
                except ValueError:
                    pass

        requirements = [str(requirement) for requirement in requirements]
        requirements = sorted(set(requirements))
        return "\n".join(requirements)

    def set_up_csharp_options(self, project_dir: Path, run_options: Dict[str, Any], release: bool,
                              image: DockerImage) -> None:
        """Sets up Docker run options specific to C# projects.

        :param project_dir: the path to the project directory
        :param run_options: the dictionary to append run options to
        :param release: whether C# projects should be compiled in release configuration instead of debug
        :param image: the docker image that will be used
        """
        compile_root = self._get_csharp_compile_root(project_dir)

        if compile_root != project_dir:
            # The /LeanCLI needs to be properly mounted to the compile root when the project is part of a solution
            run_options["volumes"].pop(str(project_dir))
            run_options["volumes"][str(compile_root)] = {
                "bind": "/LeanCLI",
                "mode": "rw"
            }

        framework_ver = self._docker_manager.get_image_label(image, 'target_framework',
                                                             DEFAULT_LEAN_DOTNET_FRAMEWORK)

        # Ensure all .csproj files refer to the version of LEAN in the Docker container
        csproj_temp_dir = self._temp_manager.create_temporary_directory()
        for path in compile_root.rglob("*.csproj"):
            self._ensure_csproj_is_valid(compile_root, path, csproj_temp_dir, run_options, framework_ver)

        # Set up the MSBuild properties
        msbuild_properties = {
            "Configuration": "Release" if release else "Debug",
            "Platform": "AnyCPU",
            "TargetFramework": framework_ver,
            "OutputPath": "/Compile/bin",
            "GenerateAssemblyInfo": "false",
            "GenerateTargetFrameworkAttribute": "false",
            "AppendTargetFrameworkToOutputPath": "false",
            "AutomaticallyUseReferenceAssemblyPackages": "false",
            "CopyLocalLockFileAssemblies": "true",
            "PathMap": f"/LeanCLI={str(compile_root)}",
            "NoWarn": ["MSB3277"]
        }

        # Find the .csproj file to compile
        project_file = next(project_dir.glob("*.csproj"))

        # Inherit NoWarn from the user's .csproj
        csproj = self._xml_manager.parse(project_file.read_text(encoding="utf-8"))
        existing_no_warn = csproj.find(".//NoWarn")
        from re import split
        if existing_no_warn is not None:
            codes = [c for c in split(r"[^a-zA-Z0-9]", existing_no_warn.text) if c != ""]
            msbuild_properties["NoWarn"] += codes

        # Turn the NoWarn property into a string
        # %3B is the encoded version of ";", because a raw ";" is seen as a separator between properties
        msbuild_properties["NoWarn"] = "%3B".join(msbuild_properties["NoWarn"])

        # Build the project before running LEAN
        relative_project_file = str(project_file.relative_to(compile_root)).replace("\\", "/")
        msbuild_properties = ";".join(f"{key}={value}" for key, value in msbuild_properties.items())
        run_options["commands"].append(f'dotnet build "/LeanCLI/{relative_project_file}" "-p:{msbuild_properties}"')

        # Copy over the algorithm DLL
        # Copy over the project reference DLLs'
        # Copy over all output DLLs that don't already exist in /Lean/Launcher/bin/Debug
        run_options["commands"].append(f"cp -R -n /Compile/bin/. {LEAN_ROOT_PATH}/")

        # Copy over all library DLLs that don't already exist in /Lean/Launcher/bin/Debug
        # CopyLocalLockFileAssemblies does not copy the OS-specific DLLs to the output directory
        # We therefore use a custom Python script that does take the OS into account when deciding what to copy
        run_options["commands"].append(
            f'python /copy_csharp_dependencies.py "/Compile/obj/{project_file.stem}/project.assets.json"')

    def set_up_common_csharp_options(self, run_options: Dict[str, Any], target_path: str = "/Lean/Launcher/bin/Debug") -> None:
        """
        Sets up common Docker run options that is needed for all C# work.

        This method prepares the Docker run options required to run C# projects inside a Docker container. It is called
        when the user has installed specific modules or when the project to run is written in C#.

        Parameters:
        - run_options (Dict[str, Any]): A dictionary to which the Docker run options will be appended.
        - target_path (str, optional): The target path inside the Docker container where the C# project should be located.
                                   Default value is "/Lean/Launcher/bin/Debug".
                                   A Python script is typically used to copy the right C# dependencies to this path.
                                   This script ensures that the correct DLLs are copied, even if they are OS-specific.

        Returns:
        - None: This function does not return anything. It modifies the `run_options` dictionary in place.
        """
        from docker.types import Mount
        # Mount a volume to NuGet's cache directory so we only download packages once
        self._docker_manager.create_volume("lean_cli_nuget")
        run_options["volumes"]["lean_cli_nuget"] = {
            "bind": "/root/.nuget/packages",
            "mode": "rw"
        }

        # Reduce the dotnet output
        run_options["environment"]["DOTNET_NOLOGO"] = "true"
        run_options["environment"]["DOTNET_CLI_TELEMETRY_OPTOUT"] = "true"

        temp_files_directory = self._temp_manager.create_temporary_directory()

        # Create a Directory.Build.props file to ensure /Compile/obj is used instead of <project>/obj
        # This is necessary because the files in obj/ will contain absolute paths, which are valid only in the container
        # Rider is okay with this, but Visual Studio throws a lot of errors if this happens
        directory_build_props = temp_files_directory / "Directory.Build.props"
        with directory_build_props.open("w+", encoding="utf-8") as file:
            file.write("""
<Project>
    <PropertyGroup>
        <BaseIntermediateOutputPath>/Compile/obj/$(MSBuildProjectName)/</BaseIntermediateOutputPath>
        <IntermediateOutputPath>/Compile/obj/$(MSBuildProjectName)/</IntermediateOutputPath>
        <DefaultItemExcludes>$(DefaultItemExcludes);backtests/*/code/**;live/*/code/**;optimizations/*/code/**</DefaultItemExcludes>
        <NoWarn>CS0618</NoWarn>
    </PropertyGroup>
</Project>
            """.strip())

        # Create a Python script that can be used to copy the right C# dependencies to /Lean/Launcher/bin/Debug
        # This script copies the correct DLLs even if a project has OS-specific DLLs
        copy_csharp_dependencies = temp_files_directory / "copy_csharp_dependencies.py"
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

def copy_file(library_id, partial_path, file_data):
    if "rid" in file_data and file_data["rid"] not in accepted_runtime_identifiers:
        return

    if not file_data.get("copyToOutput", True):
        return

    for folder in package_folders:
        full_path = folder / library_id.lower() / partial_path
        if full_path.exists():
            break
    else:
        return

    output_name = file_data.get("outputPath", full_path.name)

    target_path = Path(""" + f'"{target_path}"' + """) / output_name
    if not target_path.exists():
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(full_path, target_path)

project_target = list(project_assets["targets"].keys())[0]
for library_id, library_data in project_assets["targets"][project_target].items():
    for key, value in library_data.get("runtimeTargets", {}).items():
        copy_file(library_id, key, value)

    for key, value in library_data.get("runtime", {}).items():
        copy_file(library_id, key, value)

    for key, value in library_data.get("contentFiles", {}).items():
        copy_file(library_id, key, value)
            """.strip())

        run_options["mounts"].extend([Mount(target="/Directory.Build.props",
                                            source=str(directory_build_props),
                                            type="bind",
                                            read_only=False),
                                      Mount(target="/copy_csharp_dependencies.py",
                                            source=str(copy_csharp_dependencies),
                                            type="bind",
                                            read_only=False)])

    def _get_csharp_compile_root(self, project_dir: Path) -> Path:
        """Returns the path to the directory that should be mounted to compile the project directory.

        If the project is part of a solution this is the solution root.
        If the project is not part of a solution this is the project directory itself.

        :param project_dir: the path to the project directory
        :return: the path that should be mounted in the Docker container when compiling the C# project
        """
        current_dir = project_dir.parent
        while current_dir.parent != current_dir:
            if next(current_dir.glob("*.sln"), None) is not None:
                return current_dir

            current_dir = current_dir.parent

        return project_dir

    def _ensure_csproj_is_valid(self,
                                compile_root: Path,
                                csproj_path: Path,
                                temp_dir: Path,
                                run_options: Dict[str, Any],
                                net_framework: str) -> None:
        """Ensures a C# project is compiled using the version of LEAN in the Docker container.

        When a .csproj file refers to the NuGet version of LEAN,
        we mount a temporary file on top of it which refers to the version of LEAN in the Docker container.
        In the case there is a breaking change between the two,
        this causes compiling to fail with readable error messages instead of ugly messages at runtime.

        :param compile_root: the path that is mounted in the Docker container
        :param csproj_path: the path to the .csproj file
        :param temp_dir: the temporary directory in which temporary .csproj files should be placed
        :param run_options: the dictionary to append run options to
        """
        from docker.types import Mount
        csproj = self._xml_manager.parse(csproj_path.read_text(encoding="utf-8"))
        include_added = False

        if net_framework:
            target_framework_iter = csproj.iter("TargetFramework")
            if target_framework_iter:
                target_frameworks = [framework.text for framework in target_framework_iter]
                if target_frameworks:
                    if net_framework not in target_frameworks:
                        raise RuntimeError(f"This project is targeting {target_frameworks[0].replace('net', 'Net ')}"
                                           f" and {net_framework.replace('net', 'Net ')} is required. Please"
                                           f" update the \"Target Framework\" project setting in VSCode to"
                                           f" the new SDK or modify the csproj file directly to "
                                           f"\"<TargetFramework>{net_framework}</TargetFramework>\".")

        for package_reference in csproj.iter("PackageReference"):
            if not package_reference.get("Include", "").lower().startswith("quantconnect."):
                continue

            if include_added:
                package_reference.getparent().remove(package_reference)

            package_reference.clear()

            package_reference.tag = "Reference"
            package_reference.set("Include", f"{LEAN_ROOT_PATH}/*.dll")
            package_reference.append(self._xml_manager.parse("<Private>False</Private>"))

            include_added = True

        if not include_added:
            return

        new_csproj_file = temp_dir / csproj_path.relative_to(compile_root)
        new_csproj_file.parent.mkdir(parents=True, exist_ok=True)
        with new_csproj_file.open("w+", encoding="utf-8") as file:
            file.write(self._xml_manager.to_string(csproj))

        run_options["mounts"].append(Mount(target=f"/LeanCLI/{csproj_path.relative_to(compile_root).as_posix()}",
                                           source=str(new_csproj_file),
                                           type="bind",
                                           read_only=True))

    def _force_disk_provider_if_necessary(self,
                                          lean_config: Dict[str, Any],
                                          config_key: str,
                                          zip_provider: str,
                                          disk_provider: str,
                                          zip_dir: Path) -> None:
        """Updates the Lean config to use the disk provider instead of the zip one if there are no zips to use.

        :param lean_config: the Lean config to update
        :param config_key: the key of the configuration property
        :param zip_provider: the fully classified name of the zip provider for this property
        :param disk_provider: the fully classified name of the disk provider for this property
        :param zip_dir: the directory where the zip provider looks for zip files
        """
        from re import sub
        from datetime import datetime

        if lean_config.get(config_key, None) != zip_provider:
            return

        if not zip_dir.exists():
            lean_config[config_key] = disk_provider
            return

        zip_names = sorted([f.name for f in zip_dir.iterdir() if f.name.endswith(".zip")], reverse=True)
        zip_names = [sub(r"[^\d]", "", name) for name in zip_names]

        if len(zip_names) == 0 or (datetime.now() - datetime.strptime(zip_names[0], "%Y%m%d")).days > 7:
            lean_config[config_key] = disk_provider

    def setup_language_specific_run_options(self, run_options, project_dir, algorithm_file,
                                            set_up_common_csharp_options_called, release, image: DockerImage) -> None:
        # Set up language-specific run options
        if algorithm_file.name.endswith(".py"):
            self.set_up_python_options(project_dir, run_options, image)
        else:
            if not set_up_common_csharp_options_called:
                self.set_up_common_csharp_options(run_options)
            self.set_up_csharp_options(project_dir, run_options, release, image)

    def format_error_before_logging(self, chunk: str):
        from lean.components.util import compiler
        from json import loads
        errors = []

        # As we don't have algorithm type information. We can check errors for both
        # Python
        jsonString = compiler.get_errors("python", chunk)
        jsonData = loads(jsonString)
        errors.extend(jsonData["aErrors"])
        # CSharp
        jsonString = compiler.get_errors("csharp", chunk)
        jsonData = loads(jsonString)
        errors.extend(jsonData["aErrors"])

        for error in errors:
            self._logger.info(error)

    def mount_project_and_library_directories(self, project_dir: Path, run_options: Dict[str, Any]) -> None:
        # Mount the project directory
        run_options["volumes"][str(project_dir)] = {
            "bind": "/LeanCLI",
            "mode": "rw"
        }

        # Check if the user has library projects and mount the Library directory
        library_dir = self._lean_config_manager.get_cli_root_directory() / "Library"
        if library_dir.is_dir():
            # Mount the library projects
            run_options["volumes"][str(library_dir)] = {
                "bind": "/Library",
                "mode": "rw"
            }

    def mount_paths(self, paths_to_mount, lean_config, run_options):
        if not paths_to_mount:
            return

        from docker.types import Mount

        environment = {}
        if "environment" in lean_config and "environments" in lean_config:
            environment = lean_config["environments"][lean_config["environment"]]
        else:
            environment = lean_config
        mounts = run_options["mounts"]

        for key, pathStr in paths_to_mount.items():
            path = Path(pathStr).resolve()
            target = f"/Files/{Path(path).name}"

            self._logger.debug(f"Mounting {path} to {target}")

            mounts.append(Mount(target=target,
                                source=str(path),
                                type="bind",
                                read_only=True))
            environment[key] = target

    @staticmethod
    def parse_extra_docker_config(run_options: Dict[str, Any], extra_docker_config: Optional[Dict[str, Any]]) -> None:
        # Add known additional run options from the extra docker config.
        # For now, only device_requests is supported
        if extra_docker_config is not None:

            if "name" in extra_docker_config:
                run_options["name"] = extra_docker_config["name"]
            
            if "environment" in extra_docker_config:
                target = run_options.get("environment")
                if not target:
                    target = run_options["environment"] = {}
                if isinstance(extra_docker_config["environment"], list):
                    target.update({item[0]: item[1] for item in [
                        item if not isinstance(item, str) else (item.split("=")[0], item.split("=")[1]) for item in extra_docker_config["environment"]
                    ]})
                elif isinstance(extra_docker_config["environment"], dict): 
                    target.update(extra_docker_config["environment"])
                else:
                    raise ValueError("Additional environment variables can be passed to the container in a dictionary, list of '{key}={value}' strings, or list of '(key, value)' tuples.")

            if "device_requests" in extra_docker_config:
                from docker.types import DeviceRequest
                run_options["device_requests"] = [DeviceRequest(**device_request)
                                                  for device_request in extra_docker_config["device_requests"]]

            if "volumes" in extra_docker_config:
                target = run_options.get("volumes")
                if not target:
                    target = run_options["volumes"] = {}
                target.update(extra_docker_config["volumes"])

            if "mounts" in extra_docker_config:
                from docker.types import Mount

                target = run_options.get("mounts")
                if not target:
                    target = run_options["mounts"] = []

                for mount in extra_docker_config["mounts"]:
                    read_only = True
                    if "read_only" in mount:
                        read_only = mount["read_only"]
                    target.append(Mount(target=mount["target"], source=mount["source"], type="bind", read_only=read_only))
