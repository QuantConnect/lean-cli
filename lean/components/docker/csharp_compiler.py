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
from typing import List

from lean.components.config.lean_config_manager import LeanConfigManager
from lean.components.docker.docker_manager import DockerManager
from lean.components.util.logger import Logger
from lean.constants import ENGINE_IMAGE


class CSharpCompiler:
    """The CSharpCompiler class is responsible for compiling C# projects."""

    def __init__(self, logger: Logger, lean_config_manager: LeanConfigManager, docker_manager: DockerManager) -> None:
        """Creates a new CSharpCompiler instance.

        :param logger: the logger that is used to print messages
        :param lean_config_manager: the LeanConfigManager instance to retrieve Lean configuration from
        :param docker_manager: the DockerManager instance which is used to interact with Docker
        """
        self._logger = logger
        self._lean_config_manager = lean_config_manager
        self._docker_manager = docker_manager

    def compile_csharp_project(self, project_dir: Path, version: str) -> Path:
        """Compiles a C# project and returns the directory containing the generated DLLs.

        Raises an error if something goes wrong during compilation.

        :param project_dir: the project to compile
        :param version: the LEAN version to compile against
        :return: the path to the directory containing the LeanCLI.{dll,pdb} files
        """
        cli_root_dir = self._lean_config_manager.get_cli_root_directory()

        self._logger.info(f"Compiling all C# files in '{project_dir}'")

        # Create a temporary directory used for compiling the C# files
        compile_dir = Path(tempfile.mkdtemp())

        # Copy all C# files in the project directory to the temporary directory
        # To make debugging work properly we need to preserve the directory structure of the Lean CLI project
        def get_objects_to_ignore(directory: str, objects: List[str]) -> List[str]:
            paths = [(Path(directory) / x) for x in objects]
            files = [p for p in paths if p.is_file()]
            return [f.name for f in files] if str(project_dir) + "/" not in directory + "/" else []

        # shutil.copytree() requires the destination not to exist yet, so we delete it first
        compile_dir.rmdir()
        shutil.copytree(str(cli_root_dir), str(compile_dir), ignore=get_objects_to_ignore)

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
        <Reference Include="/Lean/Launcher/bin/Debug/*.dll">
            <Private>False</Private>
        </Reference>
    </ItemGroup>
</Project>
            """.strip())

        success = self._docker_manager.run_image(ENGINE_IMAGE,
                                                 version,
                                                 entrypoint=["msbuild", "-restore", "/LeanCLI/LeanCLI.csproj"],
                                                 volumes={
                                                     str(compile_dir): {
                                                         "bind": "/LeanCLI",
                                                         "mode": "rw"
                                                     }
                                                 })

        if not success:
            raise RuntimeError("Something went wrong while running msbuild")

        # Copy the generated LeanCLI.dll file to the user's CLI project
        # This is required for C# debugging to work with Visual Studio and Visual Studio Code
        compiled_dll = compile_dir / "bin" / "Debug" / "LeanCLI.dll"
        local_path = cli_root_dir / "bin" / "Debug" / "LeanCLI.dll"
        local_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(compiled_dll, local_path)

        return compile_dir / "bin" / "Debug"
