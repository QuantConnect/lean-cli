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
import sys
import tempfile
import zipfile
from pathlib import Path

import click
import requests

from lean.click import LeanCommand
from lean.constants import DEFAULT_DATA_DIRECTORY_NAME, DEFAULT_LEAN_CONFIG_FILE_NAME
from lean.container import container

CSPROJ = """
<!--
This file exists to make C# autocompletion and debugging work.

Custom libraries added in this file won't be used when compiling your code.
When using the Lean CLI to run algorithms, this csproj file is overwritten
to make your code compile against all the DLLs in the QuantConnect/Lean
Docker container. This container contains the following libraries besides
the System.* and QuantConnect.* libraries:
https://www.quantconnect.com/docs/key-concepts/supported-libraries

If you want to get autocompletion to work for any of the C# libraries listed
on the page above, you can add a PackageReference for it.
-->
<Project Sdk="Microsoft.NET.Sdk">
    <PropertyGroup>
        <Configuration Condition=" '$(Configuration)' == '' ">Debug</Configuration>
        <Platform Condition=" '$(Platform)' == '' ">AnyCPU</Platform>
        <TargetFramework>net462</TargetFramework>
        <LangVersion>6</LangVersion>
        <OutputPath>bin/$(Configuration)</OutputPath>
        <AppendTargetFrameworkToOutputPath>false</AppendTargetFrameworkToOutputPath>
    </PropertyGroup>
     <PropertyGroup>
        <IsWindows>false</IsWindows>
        <IsWindows Condition="'$(OS)' == 'Windows_NT'">true</IsWindows>
        <IsOSX>false</IsOSX>
        <IsOSX Condition="'$(IsWindows)' != 'true' AND '$([System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform($([System.Runtime.InteropServices.OSPlatform]::OSX)))' == 'true'">true</IsOSX>
        <IsLinux>false</IsLinux>
        <IsLinux Condition="'$(IsWindows)' != 'true' AND '$(IsOSX)' != 'true' AND '$([System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform($([System.Runtime.InteropServices.OSPlatform]::Linux)))' == 'true'">true</IsLinux>
    </PropertyGroup>
    <Choose>
        <When Condition="$(IsWindows)">
            <ItemGroup>
                <Reference Include="Python.Runtime, Version=1.0.5.30, Culture=neutral, processorArchitecture=MSIL">
                    <HintPath>$(NuGetPackageRoot)/quantconnect.pythonnet/1.0.5.30/lib/win/Python.Runtime.dll</HintPath>
                </Reference>
            </ItemGroup>
        </When>
        <When Condition="$(IsLinux)">
            <ItemGroup>
                <Reference Include="Python.Runtime, Version=1.0.5.30, Culture=neutral, processorArchitecture=MSIL">
                    <HintPath>$(NuGetPackageRoot)/quantconnect.pythonnet/1.0.5.30/lib/linux/Python.Runtime.dll</HintPath>
                </Reference>
            </ItemGroup>
        </When>
        <When Condition="$(IsOSX)">
            <ItemGroup>
                <Reference Include="Python.Runtime, Version=1.0.5.30, Culture=neutral, processorArchitecture=MSIL">
                    <HintPath>$(NuGetPackageRoot)/quantconnect.pythonnet/1.0.5.30/lib/osx/Python.Runtime.dll</HintPath>
                </Reference>
            </ItemGroup>
        </When>
    </Choose>
    <ItemGroup>
        <PackageReference Include="QuantConnect.Lean" Version="2.*"/>
    </ItemGroup>
</Project>
""".strip() + "\n"

PYCHARM_WORKSPACE_XML = """
<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="RunManager" selected="Python Debug Server.Debug with Lean CLI">
    <configuration name="Debug with Lean CLI" type="PyRemoteDebugConfigurationType" factoryName="Python Remote Debug">
      <module name="LEAN" />
      <option name="PORT" value="6000" />
      <option name="HOST" value="localhost" />
      <PathMappingSettings>
        <option name="pathMappings">
          <list>
            <mapping local-root="$PROJECT_DIR$" remote-root="/LeanCLI" />
          </list>
        </option>
      </PathMappingSettings>
      <option name="REDIRECT_OUTPUT" value="true" />
      <option name="SUSPEND_AFTER_CONNECT" value="true" />
      <method v="2" />
    </configuration>
    <list>
      <item itemvalue="Python Debug Server.Debug with Lean CLI" />
    </list>
  </component>
</project>
""".strip() + "\n"

RIDER_WORKSPACE_XML = """
<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="RunManager">
    <configuration name="Debug with Lean CLI" type="ConnectRemote" factoryName="Mono Remote" show_console_on_std_err="false" show_console_on_std_out="false" port="55555" address="localhost">
      <option name="allowRunningInParallel" value="false" />
      <option name="listenPortForConnections" value="false" />
      <option name="selectedOptions">
        <list />
      </option>
      <method v="2" />
    </configuration>
  </component>
</project>
""".strip() + "\n"

VSCODE_LAUNCH_JSON = """
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Python with Lean CLI",
            "type": "python",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5678
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "/LeanCLI"
                }
            ]
        },
        {
            "name": "Debug C# with Lean CLI",
            "request": "attach",
            "type": "mono",
            "address": "localhost",
            "port": 55555
        }
    ]
}
""".strip() + "\n"

VSCODE_SETTINGS_JSON = """
{
    "python.pythonPath": "$PYTHON$"
}
""".strip() + "\n"


@click.command(cls=LeanCommand)
def init() -> None:
    """Bootstrap a Lean CLI project."""
    current_dir = Path.cwd()
    data_dir = current_dir / DEFAULT_DATA_DIRECTORY_NAME
    lean_config_path = current_dir / DEFAULT_LEAN_CONFIG_FILE_NAME

    # Abort if one of the files we are going to create already exists to prevent us from overriding existing files
    for path in [data_dir, lean_config_path]:
        if path.exists():
            relative_path = path.relative_to(current_dir)
            raise RuntimeError(f"{relative_path} already exists, please run this command in an empty directory")

    logger = container.logger()

    # Warn the user if the current directory is not empty
    if next(current_dir.iterdir(), None) is not None:
        logger.info("This command will bootstrap a Lean CLI project in the current directory")
        click.confirm("The current directory is not empty, continue?", default=False, abort=True)

    # Download the Lean repository
    logger.info("Downloading latest sample data from the Lean repository...")
    tmp_directory = Path(tempfile.mkdtemp())

    # We download the entire Lean repository and extract the data and the launcher's config file
    # GitHub doesn't allow downloading a specific directory
    # Since we need ~80% of the total repository in terms of file size this shouldn't be too big of a problem
    with requests.get("https://github.com/QuantConnect/Lean/archive/master.zip", stream=True) as response:
        response.raise_for_status()

        with (tmp_directory / "master.zip").open("wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

    # Extract the downloaded repository
    with zipfile.ZipFile(tmp_directory / "master.zip") as zip_file:
        zip_file.extractall(tmp_directory / "master")

    # Copy the data directory
    shutil.copytree(tmp_directory / "master" / "Lean-master" / "Data", data_dir)

    # Create the config file
    lean_config_manager = container.lean_config_manager()
    config = (tmp_directory / "master" / "Lean-master" / "Launcher" / "config.json").read_text()
    config = lean_config_manager.clean_lean_config(config)

    # Update the data-folder configuration
    config = config.replace('"data-folder": "../../../Data/"', f'"data-folder": "{DEFAULT_DATA_DIRECTORY_NAME}"')

    with lean_config_path.open("w+") as file:
        file.write(config)

    # Create files which make debugging and autocompletion possible
    extra_files = {
        "LeanCLI.csproj": CSPROJ,
        ".idea/workspace.xml": PYCHARM_WORKSPACE_XML,
        ".idea/.idea.LeanCLI.dir/.idea/workspace.xml": RIDER_WORKSPACE_XML,
        ".vscode/launch.json": VSCODE_LAUNCH_JSON,
        ".vscode/settings.json": VSCODE_SETTINGS_JSON.replace("$PYTHON$", sys.executable)
    }

    for location, content in extra_files.items():
        path = Path(Path.cwd() / location)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w+") as file:
            file.write(content)

    # Prompt for some general configuration if not set yet
    cli_config_manager = container.cli_config_manager()
    if cli_config_manager.default_language.get_value() is None:
        default_language = click.prompt("What should the default language for new projects be?",
                                        type=click.Choice(cli_config_manager.default_language.allowed_values))
        cli_config_manager.default_language.set_value(default_language)

    logger.info(f"""
Successfully bootstrapped your Lean CLI project!

The following structure has been created:
- {DEFAULT_LEAN_CONFIG_FILE_NAME} contains the configuration used when running the LEAN engine locally
- {DEFAULT_DATA_DIRECTORY_NAME}/ contains the data that is used when running the LEAN engine locally

Here are some commands to get you going:
- Run `lean create-project "My Project"` to create a new project with starter code
- Run `lean backtest "My Project"` to backtest a project locally with the data in {DEFAULT_DATA_DIRECTORY_NAME}/
""".strip())
