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
from pathlib import Path

from lean.components.docker.docker_manager import DockerManager
from lean.components.util.logger import Logger
from lean.components.util.temp_manager import TempManager
from lean.constants import ENGINE_IMAGE


class CSharpCompiler:
    """The CSharpCompiler class is responsible for compiling C# projects."""

    def __init__(self, logger: Logger, docker_manager: DockerManager, temp_manager: TempManager) -> None:
        """Creates a new CSharpCompiler instance.

        :param logger: the logger that is used to print messages
        :param docker_manager: the DockerManager instance which is used to interact with Docker
        :param temp_manager: the TempManager instance to use when creating temporary directories
        """
        self._logger = logger
        self._docker_manager = docker_manager
        self._temp_manager = temp_manager

    def compile_csharp_project(self, project_dir: Path, version: str) -> Path:
        """Compiles a C# project and returns the directory containing the generated DLLs.

        Raises an error if something goes wrong during compilation.

        :param project_dir: the project to compile
        :param version: the LEAN version to compile against
        :return: the path to the directory containing the LeanCLI.{dll,pdb} files
        """
        self._logger.info(f"Compiling all C# files in '{project_dir}'")

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

        with (compile_dir / f"{project_dir.name}.csproj").open("w+", encoding="utf-8") as file:
            file.write(f"""
<Project Sdk="Microsoft.NET.Sdk">
    <PropertyGroup>
        <Configuration Condition=" '$(Configuration)' == '' ">Debug</Configuration>
        <Platform Condition=" '$(Platform)' == '' ">AnyCPU</Platform>
        <TargetFramework>net462</TargetFramework>
        <FrameworkPathOverride>/usr/lib/mono/4.6.2-api</FrameworkPathOverride>
        <LangVersion>6</LangVersion>
        <GenerateAssemblyInfo>false</GenerateAssemblyInfo>
        <OutputPath>bin/$(Configuration)/</OutputPath>
        <AppendTargetFrameworkToOutputPath>false</AppendTargetFrameworkToOutputPath>
        <AutoGenerateBindingRedirects>true</AutoGenerateBindingRedirects>
        <GenerateBindingRedirectsOutputType>true</GenerateBindingRedirectsOutputType>
        <AutomaticallyUseReferenceAssemblyPackages>false</AutomaticallyUseReferenceAssemblyPackages>
        <PathMap>/LeanCLI={str(project_dir)}</PathMap>
    </PropertyGroup>
    <ItemGroup>
        <Reference Include="/usr/lib/mono/4.6.2-api/Microsoft.CSharp.dll">
            <Private>False</Private>
        </Reference>
        <Reference Include="/Lean/Launcher/bin/Debug/*.dll">
            <Private>False</Private>
        </Reference>
    </ItemGroup>
</Project>
            """.strip())

        success = self._docker_manager.run_image(ENGINE_IMAGE,
                                                 version,
                                                 entrypoint=["dotnet", "msbuild",
                                                             "-restore", f"/LeanCLI/{project_dir.name}.csproj"],
                                                 environment={"DOTNET_CLI_TELEMETRY_OPTOUT": "true",
                                                              "DOTNET_NOLOGO": "true"},
                                                 volumes={
                                                     str(compile_dir): {
                                                         "bind": "/LeanCLI",
                                                         "mode": "rw"
                                                     }
                                                 })

        if not success:
            raise RuntimeError("Something went wrong while running msbuild, see the logs above for more information")

        # Copy the generated dll and pdb files to the user's project directory
        # This is required for C# debugging to work with Visual Studio and Visual Studio Code
        for extension in ["dll", "pdb"]:
            compile_path = compile_dir / "bin" / "Debug" / f"{project_dir.name}.{extension}"
            local_path = project_dir / "bin" / "Debug" / f"{project_dir.name}.{extension}"
            local_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(compile_path, local_path)

        return compile_dir / "bin" / "Debug"
