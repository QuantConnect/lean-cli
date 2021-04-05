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
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from xml.etree import ElementTree

from lean.components.config.project_config_manager import ProjectConfigManager
from lean.models.api import QCLanguage, QCProject


class ProjectManager:
    """The ProjectManager class provides utilities for handling a single project."""

    def __init__(self, project_config_manager: ProjectConfigManager) -> None:
        """Creates a new ProjectManager instance.

        :param project_config_manager: the ProjectConfigManager to use when creating new projects
        """
        self._project_config_manager = project_config_manager

    def find_algorithm_file(self, input: Path) -> Path:
        """Returns the path to the file containing the algorithm.

        Raises an error if the algorithm file cannot be found.

        :param input: the path to the algorithm or the path to the project
        :return: the path to the file containing the algorithm
        """
        if input.is_file():
            return input

        for file_name in ["main.py", "Main.cs"]:
            target_file = input / file_name
            if target_file.exists():
                return target_file

        raise ValueError("The specified project does not contain a main.py or Main.cs file")

    def get_files_to_sync(self, project: Path) -> List[Path]:
        """Returns the paths of all the local files that need to be synchronized with the cloud.

        :param project: the path to a local project directory
        :return: the list of files in the given project directory that need to be synchronized with the cloud
        """
        local_files = list(project.rglob("*.py")) + list(project.rglob("*.cs")) + list(project.rglob("*.ipynb"))
        files_to_sync = []

        for local_file in local_files:
            posix_path = local_file.as_posix()
            if "bin/" in posix_path or "obj/" in posix_path or ".ipynb_checkpoints/" in posix_path:
                continue

            files_to_sync.append(local_file)

        return files_to_sync

    def should_sync_files(self, local_project: Path, cloud_project: QCProject) -> bool:
        """Returns whether there are files to synchronize based on last modified times.

        Without the logic in this method the pull/push flow looks like this:
        1. Retrieve all project information from projects/read endpoint
        2. For each project, retrieve all remote files from files/read endpoint
        3. For each file, check if the local content differs from the remote content

        This method uses the last modified times of local files and the information retrieved in step 1 to
        skip step 2 and 3 for projects of which we know there is nothing to pull/push. This lowers the
        amount of API requests, speeds up pull/push (especially if the user has a lot of projects).

        This method is not perfect as it may return True if there are no updates to pull/push.
        This happens due to the limited amount of information that is available after step 1.
        In that case the only way to know whether there is something to sync is by querying the files/read endpoint.

        :param local_project: the path to the local project directory
        :param cloud_project: the cloud counterpart of the local project
        :return: True if there may be updates to synchronize, False if not
        """
        paths_to_check = [local_project] + self.get_files_to_sync(local_project)

        last_modified_time = max((file.stat().st_mtime_ns / 1e9) for file in paths_to_check)
        last_modified_time = datetime.fromtimestamp(last_modified_time).astimezone(tz=timezone.utc)

        # If the last modified time of the local files equal the last modified time of the project,
        # we can safely assume there are no changes to pull/push.
        return last_modified_time.replace(tzinfo=None, microsecond=0) != cloud_project.modified

    def update_last_modified_time(self, local_file_path: Path, cloud_timestamp: datetime) -> None:
        """Updates the last modified time of a local path to that of the cloud counterpart.

        :param local_file_path: the path to the local file to update the last modified time of
        :param cloud_timestamp: the last modified time of the counterpart of the local file in the cloud
        """
        # Timestamps are stored in UTC in the cloud, but utime() requires them in the local timezone
        time = cloud_timestamp.replace(tzinfo=timezone.utc).astimezone(tz=None)
        time = round(time.timestamp() * 1e9)
        os.utime(local_file_path, ns=(time, time))

    def create_new_project(self, project_dir: Path, language: QCLanguage) -> None:
        """Creates a new project directory and fills it with some useful files.

        :param project_dir: the directory of the new project
        :param language: the language of the new project
        """
        project_dir.mkdir(parents=True, exist_ok=True)

        project_config = self._project_config_manager.get_project_config(project_dir)
        project_config.set("algorithm-language", language.name)
        project_config.set("parameters", {})
        project_config.set("description", "")

        if language == QCLanguage.Python:
            self._generate_vscode_python_config(project_dir)
            self._generate_pycharm_config(project_dir)
        else:
            self._generate_vscode_csharp_config(project_dir)
            self._generate_csproj(project_dir)
            self._generate_rider_config(project_dir)

    def _generate_vscode_python_config(self, project_dir: Path) -> None:
        """Generates Python interpreter configuration and Python debugging configuration for VS Code.

        :param project_dir: the directory of the new project
        """
        self._generate_file(project_dir / ".vscode" / "settings.json", json.dumps({
            "python.pythonPath": sys.executable,
            "python.languageServer": "Pylance"
        }, indent=4))

        self._generate_file(project_dir / ".vscode" / "launch.json", """
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug with Lean CLI",
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
        }
    ]
}
        """)

    def _generate_pycharm_config(self, project_dir: Path) -> None:
        """Generates Python interpreter configuration and Python debugging configuration for PyCharm.

        :param project_dir: the directory of the new project
        """
        # Generate Python JDK entry for PyCharm Professional and PyCharm Community
        self._generate_pycharm_jdk_entry("PyCharm")
        self._generate_pycharm_jdk_entry("PyCharmCE")

        self._generate_file(project_dir / ".idea" / f"{project_dir.name}.iml", """
<?xml version="1.0" encoding="UTF-8"?>
<module type="PYTHON_MODULE" version="4">
  <component name="NewModuleRootManager">
    <content url="file://$MODULE_DIR$" />
    <orderEntry type="jdk" jdkName="Lean CLI" jdkType="Python SDK" />
    <orderEntry type="sourceFolder" forTests="false" />
  </component>
</module>
        """)

        self._generate_file(project_dir / ".idea" / "misc.xml", """
<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="ProjectRootManager" version="2" project-jdk-name="Lean CLI" project-jdk-type="Python SDK" />
</project>
        """)

        self._generate_file(project_dir / ".idea" / "modules.xml", f"""
<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="ProjectModuleManager">
    <modules>
      <module fileurl="file://$PROJECT_DIR$/.idea/{project_dir.name}.iml" filepath="$PROJECT_DIR$/.idea/{project_dir.name}.iml" />
    </modules>
  </component>
</project>
        """)

        self._generate_file(project_dir / ".idea" / "workspace.xml", """
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
        """)

    def _generate_pycharm_jdk_entry(self, editor_name: str) -> None:
        """Generates a "LeanCLI" Python JDK entry to PyCharm's internal JDK table.

        When we generate PyCharm's .idea directory we want to tell PyCharm where the Python interpreter is located.
        PyCharm stores this bit of configuration globally, so we find the global location and update it to our needs.

        If PyCharm is not installed yet, we create the configuration anyways.
        Once the user installs PyCharm, it will then automatically pick up the configuration we created in the past.

        :param editor_name: the name of the JetBrains editor, like PyCharm or PyCharmCE
        """
        # Find JetBrains' global config directory
        # See https://www.jetbrains.com/help/pycharm/project-and-ide-settings.html#ide_settings
        if platform.system() == "Windows":
            # Windows
            jetbrains_config_dir = Path("~/AppData/Roaming/JetBrains").expanduser()
        elif platform.system() == "Darwin":
            # macOS
            jetbrains_config_dir = Path("~/Library/Application Support/JetBrains").expanduser()
        else:
            # Linux
            jetbrains_config_dir = Path("~/.config/JetBrains").expanduser()

        # Find PyCharm's global config directory
        pycharm_config_dirs = sorted(p for p in jetbrains_config_dir.glob(f"{editor_name}*"))
        if len(pycharm_config_dirs) > 0:
            pycharm_config_dir = pycharm_config_dirs[-1]
        else:
            pycharm_config_dir = jetbrains_config_dir / editor_name

        # Parse the file containing PyCharm's internal table of Python interpreters
        jdk_table_file = pycharm_config_dir / "options" / "jdk.table.xml"
        if jdk_table_file.exists():
            root = ElementTree.fromstring(jdk_table_file.read_text(encoding="utf-8"))
        else:
            root = ElementTree.fromstring("""
<application>
  <component name="ProjectJdkTable">
  </component>
</application>
            """)

        # Don't do anything if the LeanCLI interpreter entry already exists
        if root.find(".//jdk/name[@value='Lean CLI']") is not None:
            return

        # Add the new JDK entry to the XML tree
        classpath_entries = [Path(p).as_posix() for p in sys.path if p != "" and not p.endswith(".zip")]
        classpath_entries = [f'<root url="{p}" type="simple" />' for p in classpath_entries]
        classpath_entries = "\n".join(classpath_entries)

        component_element = root.find(".//component[@name='ProjectJdkTable']")
        component_element.append(ElementTree.fromstring(f"""
<jdk version="2">
  <name value="Lean CLI" />
  <type value="Python SDK" />
  <version value="Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}" />
  <homePath value="{Path(sys.executable).as_posix()}" />
  <roots>
    <classPath>
      <root type="composite">
        {classpath_entries}
        <root url="file://$APPLICATION_HOME_DIR$/plugins/python/helpers/python-skeletons" type="simple" />
        <root url="file://$APPLICATION_HOME_DIR$/plugins/python/helpers/typeshed/stdlib/3" type="simple" />
        <root url="file://$APPLICATION_HOME_DIR$/plugins/python/helpers/typeshed/stdlib/2and3" type="simple" />
        <root url="file://$APPLICATION_HOME_DIR$/plugins/python/helpers/typeshed/third_party/3" type="simple" />
        <root url="file://$APPLICATION_HOME_DIR$/plugins/python/helpers/typeshed/third_party/2and3" type="simple" />
      </root>
    </classPath>
    <sourcePath>
      <root type="composite" />
    </sourcePath>
  </roots>
</jdk>
        """))

        # Save the modified XML tree
        self._generate_file(jdk_table_file, ElementTree.tostring(root, encoding="utf-8", method="xml").decode("utf-8"))

    def _generate_vscode_csharp_config(self, project_dir: Path) -> None:
        """Generates C# debugging configuration for VS Code.

        :param project_dir: the directory of the new project
        """
        self._generate_file(project_dir / ".vscode" / "launch.json", """
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug with Lean CLI",
            "request": "attach",
            "type": "mono",
            "address": "localhost",
            "port": 55556
        }
    ]
}
        """)

    def _generate_csproj(self, project_dir: Path) -> None:
        """Generates a .csproj file for the given project and returns the path to it.

        :param project_dir: the path of the new project
        """
        self._generate_file(project_dir / f"{project_dir.name}.csproj", """
<!--
This file exists to make C# autocomplete and debugging work.

Custom libraries added in this file won't be used when compiling your code.
When using the Lean CLI to run algorithms, this csproj file is overwritten
to make your code compile against all the DLLs in the QuantConnect/Lean
Docker container. This container contains the following libraries besides
the System.* and QuantConnect.* libraries:
https://www.quantconnect.com/docs/key-concepts/supported-libraries

If you want to get autocomplete to work for any of the C# libraries listed
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
        <PackageReference Include="QuantConnect.Lean" Version="2.5.11072"/>
    </ItemGroup>
</Project>
        """)

    def _generate_rider_config(self, project_dir: Path) -> None:
        """Generates C# debugging configuration for Rider.

        :param project_dir: the directory of the new project
        """
        workspace_xml = """
<?xml version="1.0" encoding="UTF-8"?>
<project version="4">
  <component name="RunManager">
    <configuration name="Debug with Lean CLI" type="ConnectRemote" factoryName="Mono Remote" show_console_on_std_err="false" show_console_on_std_out="false" port="55556" address="localhost">
      <option name="allowRunningInParallel" value="false" />
      <option name="listenPortForConnections" value="false" />
      <option name="selectedOptions">
        <list />
      </option>
      <method v="2" />
    </configuration>
  </component>
</project>
        """

        self._generate_file(project_dir / ".idea" / f".idea.{project_dir.name}" / ".idea" / "workspace.xml",
                            workspace_xml)
        self._generate_file(project_dir / ".idea" / f".idea.{project_dir.name}.dir" / ".idea" / "workspace.xml",
                            workspace_xml)

    def _generate_file(self, file: Path, content: str) -> None:
        """Writes to a file, which is created if it doesn't exist yet, and normalized the content before doing so.

        :param file: the file to write to
        :param content: the content to write to the file
        """
        file.parent.mkdir(parents=True, exist_ok=True)
        with file.open("w+", encoding="utf-8") as file:
            file.write(content.strip() + "\n")
