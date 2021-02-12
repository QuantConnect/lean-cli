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

import shutil
import tempfile
from pathlib import Path

from lean.components.docker_manager import DockerManager
from lean.components.lean_config_manager import LeanConfigManager
from lean.components.logger import Logger


class CSharpCompiler:
    """The CSharpCompiler class is responsible for compiling C# projects."""

    def __init__(self,
                 logger: Logger,
                 lean_config_manager: LeanConfigManager,
                 docker_manager: DockerManager,
                 docker_image: str) -> None:
        """Creates a new CSharpCompiler instance.

        :param logger: the logger that is used to print messages
        :param lean_config_manager: the LeanConfigManager instance to retrieve Lean configuration from
        :param docker_manager: the DockerManager instance which is used to interact with Docker
        :param docker_image: the Docker image containing the LEAN engine
        """
        self._logger = logger
        self._lean_config_manager = lean_config_manager
        self._docker_manager = docker_manager
        self._docker_image = docker_image

    def compile_csharp_project(self, project_dir: Path, version: str) -> Path:
        """Compiles a C# project and returns the directory containing the generated DLLs.

        Raises an error if something goes wrong during compilation.

        :param project_dir: the project to compile
        :param version: the LEAN version to compile against
        :return: the path to the directory containing the LeanCLI.{dll,pdb} files
        """
        cli_root_dir = self._lean_config_manager.get_cli_root_directory()

        self._logger.info(f"Compiling all C# files in '{cli_root_dir}'")

        # Create a temporary directory used for compiling the C# files
        compile_dir = Path(tempfile.mkdtemp())

        # Copy all C# files to the temporary directory
        # shutil.copytree() requires the destination not to exist yet, so we delete it first
        compile_dir.rmdir()
        shutil.copytree(str(cli_root_dir),
                        str(compile_dir),
                        ignore=lambda d, files: [f for f in files if (Path(d) / f).is_file() and not f.endswith(".cs")])

        with (compile_dir / "LeanCLI.csproj").open("w+") as file:
            file.write(self._get_csproj(version))

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
            raise RuntimeError("Something went wrong while running nuget")

        success, _ = self._docker_manager.run_image(self._docker_image,
                                                    version,
                                                    "/LeanCLI/LeanCLI.csproj",
                                                    quiet=False,
                                                    entrypoint="msbuild",
                                                    volumes=volumes)

        if not success:
            raise RuntimeError("Something went wrong while running msbuild")

        # Copy the generated LeanCLI.dll file to the user's CLI project
        # This is required for C# debugging to work with Visual Studio and Visual Studio Code
        compiled_dll = compile_dir / "bin" / "Debug" / "LeanCLI.dll"
        local_path = cli_root_dir / "bin" / "Debug" / "LeanCLI.dll"
        local_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(compiled_dll, local_path)

        return compile_dir / "bin" / "Debug"

    def _get_csproj(self, version: str) -> str:
        """Returns the content the csproj file should contain when compiling a project.

        :param version: the LEAN version the project is compiled against
        :return: the content the csproj file should have when compiling a C# project
        """
        success, output = self._docker_manager.run_image(self._docker_image,
                                                         version,
                                                         "-c ls",
                                                         quiet=True,
                                                         entrypoint="bash")

        if not success:
            raise RuntimeError("Could not retrieve DLLs in Docker image")

        dlls = [line for line in output.split("\n") if line.endswith(".dll")]

        # Create Reference items for all DLLs in the Docker image
        references = [f"""
        <Reference Include="{dll.split('.dll')[0]}">
            <HintPath>/Lean/Launcher/bin/Debug/{dll}</HintPath>
        </Reference>
        """.strip() for dll in dlls]
        references = "\n".join(references)

        return f"""
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
        <PathMap>/LeanCLI={str(self._lean_config_manager.get_cli_root_directory())}</PathMap>
    </PropertyGroup>
    <ItemGroup>
        {references}
    </ItemGroup>
</Project>
            """.strip()
