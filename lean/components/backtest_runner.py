import json
import platform
import tempfile
from distutils import dir_util
from pathlib import Path
from typing import Any, Dict

from docker.types import Mount

from lean.components.docker_manager import DockerManager
from lean.components.lean_config_manager import LeanConfigManager
from lean.components.logger import Logger


class BacktestRunner:
    """The BacktestRunner contains the code that runs backtests locally."""

    def __init__(self,
                 logger: Logger,
                 lean_config_manager: LeanConfigManager,
                 docker_manager: DockerManager,
                 docker_image: str,
                 docker_tag: str) -> None:
        """Creates a new BacktestRunner instance.

        :param logger: the logger that is used to print messages
        :param lean_config_manager: the LeanConfigManager instance to retrieve Lean configuration from
        :param docker_manager: the DockerManager instance which is used to interact with Docker
        :param docker_image: the Docker image containing the LEAN engine
        :param docker_tag: the tag of the image to run
        """
        self._logger = logger
        self._lean_config_manager = lean_config_manager
        self._docker_manager = docker_manager
        self._docker_image = docker_image
        self._docker_tag = docker_tag

    def run_backtest(self, algorithm_file: Path, output_dir: Path) -> None:
        """Runs a backtest in Docker.

        :param algorithm_file: the path to the file containing the algorithm
        :param output_dir: the directory to save output data to
        """
        project_dir = algorithm_file.parent

        # Create the output directory if it doesn't exist yet
        if not output_dir.exists():
            output_dir.mkdir(parents=True)

        # Create a file containing the complete Lean configuration
        config = self._lean_config_manager.get_complete_lean_config("backtesting", algorithm_file)
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
            "ports": {
                "5678": "5678",
                "6000": "6000"
            }
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

        # Mount the project which needs to be backtested
        if algorithm_file.name.endswith(".py"):
            run_options["volumes"][str(project_dir)] = {
                "bind": "/Project",
                "mode": "rw"
            }
        else:
            # C# projects need to be compiled before the backtest can run
            csharp_binaries_dir = self._compile_csharp_project(project_dir)

            for extension in ["dll", "pdb"]:
                run_options["mounts"].append(
                    Mount(target=f"/Lean/Launcher/bin/Debug/QuantConnect.Algorithm.CSharp.{extension}",
                          source=str(csharp_binaries_dir / f"QuantConnect.Algorithm.CSharp.{extension}"),
                          type="bind"))

        # Run the backtest and log the result
        command = "--data-folder /Data --results-destination-folder /Results --config /Lean/Launcher/config.json"
        success, _ = self._docker_manager.run_image(self._docker_image,
                                                    self._docker_tag,
                                                    command,
                                                    quiet=False,
                                                    **run_options)

        lean_project_root = self._lean_config_manager.get_lean_config_path().parent
        relative_project_dir = project_dir.relative_to(lean_project_root)
        relative_output_dir = output_dir.relative_to(lean_project_root)

        if success:
            self._logger.info(
                f"Successfully backtested '{relative_project_dir}' and stored the output in '{relative_output_dir}'")
        else:
            raise RuntimeError(
                f"Something went wrong while backtesting '{relative_project_dir}', the output is stored in '{relative_output_dir}'")

    def _compile_csharp_project(self, project_dir: Path) -> Path:
        """Compiles the C# project in the given directory and returns the path where the binaries are stored.

        :param project_dir: the path to the directory containing C# files that need to be compiled
        :return: the path to the directory containing the QuantConnect.Algorithm.CSharp.{dll,pdb} files
        """
        self._logger.info(f"Compiling the C# files in '{project_dir}'")

        # Create a temporary directory used for compiling the C# project
        compile_dir = Path(tempfile.mkdtemp())

        # Copy all project files to the temporary directory
        dir_util.copy_tree(str(project_dir), str(compile_dir))

        # Get a list of all dll's in the docker image
        _, output = self._docker_manager.run_image(self._docker_image,
                                                   self._docker_tag,
                                                   "-c ls",
                                                   quiet=True,
                                                   entrypoint="bash")

        dlls = [line for line in output.split("\n") if line.endswith(".dll")]

        # Create a csproj file which will be used to compile the project
        references = [f"""
        <Reference Include="{dll.split('.dll')[0]}">
            <HintPath>/Lean/Launcher/bin/Debug/{dll}</HintPath>
        </Reference>
        """.strip() for dll in dlls]
        references = "\n".join(references)

        with (compile_dir / "Project.csproj").open("w+") as file:
            file.write(f"""
<Project Sdk="Microsoft.NET.Sdk">
    <PropertyGroup>
        <Configuration Condition=" '$(Configuration)' == '' ">Debug</Configuration>
        <Platform Condition=" '$(Platform)' == '' ">AnyCPU</Platform>
        <RootNamespace>QuantConnect.Algorithm.CSharp</RootNamespace>
        <AssemblyName>QuantConnect.Algorithm.CSharp</AssemblyName>
        <TargetFramework>net462</TargetFramework>
        <LangVersion>6</LangVersion>
        <GenerateAssemblyInfo>false</GenerateAssemblyInfo>
        <OutputPath>bin/$(Configuration)/</OutputPath>
        <AppendTargetFrameworkToOutputPath>false</AppendTargetFrameworkToOutputPath>
        <AutoGenerateBindingRedirects>true</AutoGenerateBindingRedirects>
        <GenerateBindingRedirectsOutputType>true</GenerateBindingRedirectsOutputType>
    </PropertyGroup>
    <ItemGroup>
        {references}
    </ItemGroup>
</Project>
            """.strip())

        # Compile the project in a Docker container
        volumes = {
            str(compile_dir): {
                "bind": "/Project",
                "mode": "rw"
            }
        }

        success, _ = self._docker_manager.run_image(self._docker_image,
                                                    self._docker_tag,
                                                    "restore /Project/Project.csproj",
                                                    quiet=False,
                                                    entrypoint="nuget",
                                                    volumes=volumes)

        if not success:
            raise RuntimeError("Something went wrong while compiling your project")

        success, _ = self._docker_manager.run_image(self._docker_image,
                                                    self._docker_tag,
                                                    "/Project/Project.csproj",
                                                    quiet=False,
                                                    entrypoint="msbuild",
                                                    volumes=volumes)

        if not success:
            raise RuntimeError("Something went wrong while compiling your project")

        return compile_dir / "bin" / "Debug"
