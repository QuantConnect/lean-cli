import json
import platform
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

from docker.types import Mount

from lean.components.docker_manager import DockerManager
from lean.components.lean_config_manager import LeanConfigManager
from lean.components.logger import Logger
from lean.models.config import DebuggingMethod


class LeanRunner:
    """The LeanRunner class contains the code that runs the LEAN engine locally."""

    def __init__(self,
                 logger: Logger,
                 lean_config_manager: LeanConfigManager,
                 docker_manager: DockerManager,
                 docker_image: str) -> None:
        """Creates a new LeanRunner instance.

        :param logger: the logger that is used to print messages
        :param lean_config_manager: the LeanConfigManager instance to retrieve Lean configuration from
        :param docker_manager: the DockerManager instance which is used to interact with Docker
        :param docker_image: the Docker image containing the LEAN engine
        """
        self._logger = logger
        self._lean_config_manager = lean_config_manager
        self._docker_manager = docker_manager
        self._docker_image = docker_image

    def run_lean(self,
                 environment: str,
                 algorithm_file: Path,
                 output_dir: Path,
                 version: str,
                 debugging_method: Optional[DebuggingMethod]) -> None:
        """Runs the LEAN engine locally in Docker.

        :param environment: the environment to run the algorithm in
        :param algorithm_file: the path to the file containing the algorithm
        :param output_dir: the directory to save output data to
        :param version: the LEAN engine version to run
        :param debugging_method: the debugging method if debugging needs to be enabled, None if not
        """
        project_dir = algorithm_file.parent

        # Create the output directory if it doesn't exist yet
        if not output_dir.exists():
            output_dir.mkdir(parents=True)

        # Create a file containing the complete Lean configuration
        config = self._lean_config_manager.get_complete_lean_config(environment,
                                                                    algorithm_file,
                                                                    debugging_method)
        config_path = Path(tempfile.mkdtemp()) / "config.json"
        with config_path.open("w+") as file:
            file.write(json.dumps(config, indent=4))

        # The dict containing all options passed to `docker run`
        # See all available options at https://docker-py.readthedocs.io/en/stable/containers.html
        run_options: Dict[str, Any] = {
            "mounts": [
                Mount(target="/Lean/Launcher/config.json", source=str(config_path), type="bind", read_only=True)
            ],
            "volumes": {},
            "ports": {}
        }

        # Mount the data directory
        data_dir = self._lean_config_manager.get_data_directory()
        run_options["volumes"][str(data_dir)] = {
            "bind": "/Data",
            "mode": "ro"
        }

        # Mount the output directory
        run_options["volumes"][str(output_dir)] = {
            "bind": "/Results",
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
            # To get Python debugging to work correctly we need to mount all Lean CLI projects
            run_options["volumes"][str(self._lean_config_manager.get_lean_config_path().parent)] = {
                "bind": "/LeanCLI",
                "mode": "ro"
            }
        else:
            # C# projects need to be compiled before they can be mounted
            csharp_binaries_dir = self._compile_csharp_project(version)

            for extension in ["dll", "pdb"]:
                run_options["mounts"].append(
                    Mount(target=f"/Lean/Launcher/bin/Debug/LeanCLI.{extension}",
                          source=str(csharp_binaries_dir / f"LeanCLI.{extension}"),
                          type="bind"))

        command = "--data-folder /Data --results-destination-folder /Results --config /Lean/Launcher/config.json"

        # Set up PTVSD debugging
        if debugging_method == DebuggingMethod.PTVSD:
            run_options["ports"]["5678"] = "5678"

        # Set up Mono debugging
        if debugging_method == DebuggingMethod.Mono:
            run_options["ports"]["55555"] = "55555"
            run_options["entrypoint"] = "mono"

            command = " ".join([
                "--debug",
                "--debugger-agent=transport=dt_socket,server=y,address=0.0.0.0:55555,suspend=y",
                "QuantConnect.Lean.Launcher.exe",
                command
            ])

            self._logger.info("Docker container starting, attach to Mono debugger at localhost:55555 to begin")

        # Run the engine and log the result
        success, _ = self._docker_manager.run_image(self._docker_image,
                                                    version,
                                                    command,
                                                    quiet=False,
                                                    **run_options)

        lean_project_root = self._lean_config_manager.get_lean_config_path().parent
        relative_project_dir = project_dir.relative_to(lean_project_root)
        relative_output_dir = output_dir.relative_to(lean_project_root)

        if success:
            self._logger.info(
                f"Successfully ran '{relative_project_dir}' in the '{environment}' environment and stored the output in '{relative_output_dir}'")
        else:
            raise RuntimeError(
                f"Something went wrong while running '{relative_project_dir}'  in the '{environment}' environment, the output is stored in '{relative_output_dir}'")

    def force_update(self) -> None:
        """Pulls the latest version of the Docker image containing the LEAN engine."""
        self._docker_manager.pull_image(self._docker_image, "latest")

    def _compile_csharp_project(self, version: str) -> Path:
        """Compiles the C# code in the Lean CLI project and returns the path where the binaries are stored.

        :param version: the LEAN version to compile against
        :return: the path to the directory containing the LeanCLI.{dll,pdb} files
        """
        cli_root_dir = self._lean_config_manager.get_lean_config_path().parent
        self._logger.info(f"Compiling all C# files in '{cli_root_dir}'")

        # Create a temporary directory used for compiling the C# files
        compile_dir = Path(tempfile.mkdtemp())

        # Copy all C# files to the temporary directory
        # shutil.copytree() requires the destination not to exist yet, so we delete it for now
        compile_dir.rmdir()
        shutil.copytree(str(cli_root_dir),
                        str(compile_dir),
                        ignore=lambda d, files: [f for f in files if (Path(d) / f).is_file() and not f.endswith(".cs")])

        # Get a list of all dll's in the docker image
        success, output = self._docker_manager.run_image(self._docker_image,
                                                         version,
                                                         "-c ls",
                                                         quiet=True,
                                                         entrypoint="bash")

        if not success:
            raise RuntimeError("Something went wrong while compiling your project")

        dlls = [line for line in output.split("\n") if line.endswith(".dll")]

        # Create a csproj file which will be used to compile the project
        references = [f"""
        <Reference Include="{dll.split('.dll')[0]}">
            <HintPath>/Lean/Launcher/bin/Debug/{dll}</HintPath>
        </Reference>
        """.strip() for dll in dlls]
        references = "\n".join(references)

        with (compile_dir / "LeanCLI.csproj").open("w+") as file:
            file.write(f"""
<Project Sdk="Microsoft.NET.Sdk">
    <PropertyGroup>
        <Configuration Condition=" '$(Configuration)' == '' ">Debug</Configuration>
        <Platform Condition=" '$(Platform)' == '' ">AnyCPU</Platform>
        <TargetFramework>net462</TargetFramework>
        <LangVersion>6</LangVersion>
        <GenerateAssemblyInfo>false</GenerateAssemblyInfo>
        <OutputPath>bin/$(Configuration)/</OutputPath>
        <AppendTargetFrameworkToOutputPath>false</AppendTargetFrameworkToOutputPath>
        <AutoGenerateBindingRedirects>true</AutoGenerateBindingRedirects>
        <GenerateBindingRedirectsOutputType>true</GenerateBindingRedirectsOutputType>
        <PathMap>/LeanCLI={str(cli_root_dir)}</PathMap>
    </PropertyGroup>
    <ItemGroup>
        {references}
    </ItemGroup>
</Project>
            """.strip())

        # Compile the project in a Docker container
        volumes = {
            str(compile_dir): {
                "bind": "/LeanCLI",
                "mode": "rw"
            }
        }

        success, _ = self._docker_manager.run_image(self._docker_image,
                                                    version,
                                                    "restore /LeanCLI/LeanCLI.csproj",
                                                    quiet=False,
                                                    entrypoint="nuget",
                                                    volumes=volumes)

        if not success:
            raise RuntimeError("Something went wrong while compiling your project")

        success, _ = self._docker_manager.run_image(self._docker_image,
                                                    version,
                                                    "/LeanCLI/LeanCLI.csproj",
                                                    quiet=False,
                                                    entrypoint="msbuild",
                                                    volumes=volumes)

        if not success:
            raise RuntimeError("Something went wrong while compiling your project")

        # Copy the generated LeanCLI.dll file to the user's CLI project
        # This is required for C# debugging to work with Visual Studio and Visual Studio Code
        compiled_dll = compile_dir / "bin" / "Debug" / "LeanCLI.dll"
        local_path = cli_root_dir / "bin" / "Debug" / "LeanCLI.dll"
        local_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(compiled_dll, local_path)

        return compile_dir / "bin" / "Debug"
