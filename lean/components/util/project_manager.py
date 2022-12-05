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

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Union, Tuple
from lean.components import reserved_names
from lean.components.config.lean_config_manager import LeanConfigManager
from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.util.logger import Logger
from lean.components.util.path_manager import PathManager
from lean.components.util.platform_manager import PlatformManager
from lean.components.util.xml_manager import XMLManager
from lean.constants import PROJECT_CONFIG_FILE_NAME
from lean.models.api import QCLanguage, QCProject, QCProjectLibrary
from lean.models.utils import LeanLibraryReference

class ProjectManager:
    """The ProjectManager class provides utilities for handling a single project."""

    def __init__(self,
                 logger: Logger,
                 project_config_manager: ProjectConfigManager,
                 lean_config_manager: LeanConfigManager,
                 path_manager: PathManager,
                 xml_manager: XMLManager,
                 platform_manager: PlatformManager) -> None:
        """Creates a new ProjectManager instance.

        :param logger: the logger to use to log messages with
        :param project_config_manager: the ProjectConfigManager to use when creating new projects
        :param lean_config_manager: the LeanConfigManager to get the CLI root directory from
        :param path_manager: the path manager to use to handle library paths
        :param xml_manager: the XMLManager to use when working with XML
        :param platform_manager: the PlatformManager used when checking which operating system is in use
        """
        self._logger = logger
        self._project_config_manager = project_config_manager
        self._lean_config_manager = lean_config_manager
        self._path_manager = path_manager
        self._xml_manager = xml_manager
        self._platform_manager = platform_manager

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

    def get_project_by_id(self, local_id: int) -> Path:
        """Finds a project by its local id.

        Raises an error if a project with the given local id cannot be found.

        :param local_id: the local id of the project
        :return: the path to the directory containing the project with the given local id
        """
        directories = [self._lean_config_manager.get_cli_root_directory()]
        while len(directories) > 0:
            directory = directories.pop(0)

            config_file = directory / PROJECT_CONFIG_FILE_NAME
            if config_file.is_file():
                if self._project_config_manager.get_local_id(directory) == local_id:
                    return directory
            else:
                directories.extend(d for d in directory.iterdir() if d.is_dir())

        raise RuntimeError(f"Project with local id '{local_id}' does not exist")

    def try_get_project_path_by_cloud_id(self, cloud_id: int) -> Path:
        """Finds a project by its cloud id.

        Raises an error if a project with the given cloud id cannot be found.

        :param cloud_id: the cloud id of the project
        :return: the path to the directory containing the project with the given cloud id
        """
        directories = [self._lean_config_manager.get_cli_root_directory()]
        while len(directories) > 0:
            directory = directories.pop(0)

            try:
                project_config = self._project_config_manager.get_project_config(directory)
            except:
                continue
            if project_config and project_config.get("cloud-id", None) == cloud_id:
                return directory
            else:
                directories.extend(d for d in directory.iterdir() if d.is_dir())

        return False

    def get_source_files(self, directory: Path) -> List[Path]:
        """Returns the paths of all the source files in a directory.

        :param directory: the path to the directory to get the source files of
        :return: the list of source files in the given project directory
        """
        source_files = []

        for obj in directory.iterdir():
            if obj.is_dir():
                if obj.name in ["bin", "obj", ".ipynb_checkpoints", "backtests", "live", "optimizations"]:
                    continue

                source_files.extend(self.get_source_files(obj))

            if obj.suffix not in [".py", ".cs", ".ipynb"]:
                continue

            source_files.append(obj)

        return source_files

    def update_last_modified_time(self, local_file_path: Path, cloud_timestamp: datetime) -> None:
        """Updates the last modified time of a local path to that of the cloud counterpart.

        :param local_file_path: the path to the local file to update the last modified time of
        :param cloud_timestamp: the last modified time of the counterpart of the local file in the cloud
        """
        from os import utime
        from datetime import timezone

        # Timestamps are stored in UTC in the cloud, but utime() requires them in the local timezone
        time = cloud_timestamp.replace(tzinfo=timezone.utc).astimezone(tz=None)
        time = round(time.timestamp() * 1e9)
        utime(local_file_path, ns=(time, time))

    def copy_code(self, project_dir: Path, output_dir: Path) -> None:
        """Copies the source code of a project to another directory.

        :param project_dir: the directory of the project
        :param output_dir: the directory to copy the code to
        """
        from shutil import copyfile

        output_dir.mkdir(parents=True, exist_ok=True)

        for source_file in self.get_source_files(project_dir):
            target_file = output_dir / source_file.relative_to(project_dir)
            target_file.parent.mkdir(parents=True, exist_ok=True)
            copyfile(source_file, target_file)

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
            self._generate_python_library_projects_config()
            self._generate_vscode_python_config(project_dir)
            self._generate_pycharm_config(project_dir)
        else:
            self._generate_vscode_csharp_config(project_dir)
            self._generate_csproj(project_dir)
            self.generate_rider_config()

    def delete_project(self, project_dir: Path) -> None:
        """Deletes a project directory.

        Raises an error if the project directory does not exist.

        :param project_dir: the directory of the project to delete
        """
        from shutil import rmtree
        try:
            rmtree(project_dir)
        except FileNotFoundError:
            raise RuntimeError(f"Failed to delete project. Could not find the specified path {project_dir}.")


    def get_local_project_path(self, project_name: str, cloud_id: Optional[int] = None, local_id: Optional[int] = None) -> Path:
        """Returns the local path where a certain cloud project should be stored.

        If two cloud projects are named "Project", they are pulled to ./Project and ./Project 2.

        If you push a project with unsupported cloud name, a supported project name would be assigned.

        :param project_name: the cloud project to get the project path of
        :param cloud_id: the cloud project to get the project path of
        :param local_id: the cloud project to get the project path of
        :return: the path to the local project directory
        """

        if cloud_id is not None and local_id is not None:
            raise ValueError("Cannot specify both cloud_id and local_id")

        if cloud_id is None and local_id is None:
            raise ValueError("Must specify either cloud_id or local_id")

        local_path = self._format_local_path(project_name)

        current_index = 1
        while True:
            path_suffix = "" if current_index == 1 else f" {current_index}"
            current_path = Path.cwd() / (local_path + path_suffix)

            if not current_path.exists():
                return current_path

            if cloud_id is not None:
                current_project_config = self._project_config_manager.get_project_config(current_path)
                if current_project_config.get("cloud-id") == cloud_id:
                    return current_path

            if local_id is not None:
                current_project_config = self._project_config_manager.get_project_config(current_path)
                if current_project_config.get("local-id") == local_id:
                    return current_path

            current_index += 1

    def rename_project_and_contents(self, old_path: Path, new_path: Path,) -> None:
        """Renames a project and updates the project config.

        :param old_path: the local project to rename
        :param new_path: the new path of the project
        """
        if not old_path.exists():
            raise RuntimeError(f"Failed to rename project. Could not find the specified path {old_path}.")
        if old_path == new_path:
            return
        from shutil import move
        move(old_path, new_path)
        self._rename_csproj_file(new_path)

    def get_projects_by_name_or_id(self, cloud_projects: List[QCProject],
                                   project: Optional[Union[str, int]]) -> List[QCProject]:
        """Returns a list of all the projects in the cloud that match the given name or id.

        :param cloud_projects: all projects fetched from the cloud
        :param project: the name or id of the project
        :return: a list of all the projects in the cloud that match the given name or id
        """
        search_by_id = isinstance(project, int)

        if project is not None:
            project_path = Path(project).as_posix() if not search_by_id else None
            projects = [cloud_project for cloud_project in cloud_projects
                        if (search_by_id and cloud_project.projectId == project or
                            not search_by_id and Path(cloud_project.name).as_posix() == project_path)]

            if len(projects) == 0:
                raise RuntimeError("No project with the given name or id exists in the cloud")
        else:
            projects = cloud_projects

        return projects

    def get_project_libraries(self, project_dir: Path) -> List[Path]:
        """Returns a list of all the libraries referenced by the given project.

        It will also recursively get all the libraries referenced by each library.

        :param project_dir: Path to the project
        :return List of all the libraries referenced by the given project
        """
        return self._get_project_libraries(project_dir)

    def _get_project_libraries(self, project_dir: Path, seen_projects: List[Path] = None) -> List[Path]:
        """Returns a list of all the libraries referenced by the given project.

        This is a helper method to recurse the libraries and get their dependencies as well.

        :param project_dir: Path to the project
        :param seen_projects: List of paths already seen, which serves as recursion stop criteria
        :return List of all the libraries referenced by the given project
        """
        if seen_projects is None:
            seen_projects = [project_dir]

        project_config = self._project_config_manager.get_project_config(project_dir)
        libraries_in_config = project_config.get("libraries", [])
        libraries = [LeanLibraryReference(**library).path.expanduser().resolve() for library in libraries_in_config]
        referenced_libraries = []

        for library_path in libraries:
            # Avoid infinite recursion
            if library_path in seen_projects:
                continue

            seen_projects.append(library_path)
            referenced_libraries.extend(self._get_project_libraries(library_path, seen_projects))
            referenced_libraries.append(library_path)

        return referenced_libraries

    def restore_csharp_project(self, csproj_file: Path, no_local: bool) -> None:
        """Restores a C# project if requested with the no_local flag and if dotnet is on the user's PATH.

        :param csproj_file: Path to the project's csproj file
        :param no_local: Whether restoring the packages locally must be skipped
        """
        from shutil import which
        from subprocess import run, STDOUT, PIPE
        from lean.models.errors import MoreInfoError

        if no_local:
            return

        if which("dotnet") is None:
            self._logger.info(f"Project {csproj_file.parent} will not be restored because dotnet was not found in PATH")
            return

        project_dir = csproj_file.parent
        self._logger.info(f"Restoring packages in '{self._path_manager.get_relative_path(project_dir)}' "
                          f"to provide local autocomplete")

        process = run(["dotnet", "restore", str(csproj_file)], cwd=project_dir, stdout=PIPE, stderr=STDOUT, text=True)
        self._logger.debug(process.stdout)

        if process.returncode != 0:
            raise RuntimeWarning("Something went wrong while restoring packages. "
                                 "You might be missing the .NET Core SDK in your dotnet installation. "
                                 "Local autocomplete functionality might be limited.")

        self._logger.info("Restored successfully")

    def try_restore_csharp_project(self, csproj_file: Path,
                                   original_csproj_content: Optional[str] = None,
                                   no_local: bool = False) -> None:
        """Restores a C# project if requested with the no_local flag and if dotnet is on the user's PATH.

        :param csproj_file: Path to the project's csproj file
        :param original_csproj_content: The original csproj file content
        :param no_local: Whether restoring the packages locally must be skipped
        """
        try:
            self.restore_csharp_project(csproj_file, no_local)
        except RuntimeWarning as e:
            if original_csproj_content is not None:
                self._logger.info(f"Reverting the changes to '{self._path_manager.get_relative_path(csproj_file)}'")
                csproj_file.write_text(original_csproj_content, encoding="utf-8")
            raise e


    def _format_local_path(self, cloud_path: str) -> str:
        """Converts the given cloud path into a local path which is valid for the current operating system.

        :param cloud_path: the path of the project in the cloud
        :return: the converted cloud_path so that it is valid locally
        """
        # Remove forbidden characters and OS-specific path separator that are not path separators on QuantConnect
        # Windows, \":*?"<>| are forbidden
        # Windows, \ is a path separator, but \ is not a path separator on QuantConnect
        # We follow the rules of windows for every OS

        for character in cloud_path:
            if self._path_manager.is_name_valid(character):
                continue
            cloud_path = cloud_path.replace(character, " ")

        # On Windows we need to ensure each path component is valid
        # We follow the rules of windows for every OS
        new_components = []

        for component in cloud_path.split("/"):
            # Some names are reserved
            for reserved_name in reserved_names:
                # If the component is a reserved name, we add an underscore to it so it can be used
                if component.upper() == reserved_name:
                    component += "_"

            # Components cannot start or end with a space
            component = component.strip(" ")

            # Components cannot end with a period
            component = component.rstrip(".")

            new_components.append(component)

        cloud_path = "/".join(new_components)

        return cloud_path


    def _generate_python_library_projects_config(self) -> None:
        """Generates the required configuration to enable autocomplete on Python library projects."""
        try:
            cli_root_dir = self._lean_config_manager.get_cli_root_directory()
        except:
            return
        from site import ENABLE_USER_SITE, getusersitepackages, getsitepackages

        library_dir = cli_root_dir / "Library"
        if not library_dir.is_dir():
            return

        if ENABLE_USER_SITE:
            site_packages_dir = getusersitepackages()
        else:
            site_packages_dir = getsitepackages()[0]

        self._generate_file(Path(site_packages_dir) / "lean-cli.pth", str(library_dir))

    def _generate_vscode_python_config(self, project_dir: Path) -> None:
        """Generates Python interpreter configuration and Python debugging configuration for VS Code.

        :param project_dir: the directory of the new project
        """
        from sys import executable
        from json import dumps

        self._generate_file(project_dir / ".vscode" / "settings.json", dumps({
            "python.pythonPath": executable,
            "python.languageServer": "Pylance"
        }, indent=4))

        launch_config = {
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

        try:
            library_dir = self._lean_config_manager.get_cli_root_directory() / "Library"
            launch_config["configurations"][0]["pathMappings"].append({
                "localRoot": str(library_dir),
                "remoteRoot": "/Library"
            })
        except:
            pass

        self._generate_file(project_dir / ".vscode" / "launch.json", dumps(launch_config, indent=4))

    def _generate_pycharm_config(self, project_dir: Path) -> None:
        """Generates Python interpreter configuration and Python debugging configuration for PyCharm.

        :param project_dir: the directory of the new project
        """
        from os import path

        # Generate Python JDK entry for PyCharm Professional and PyCharm Community
        for editor in ["PyCharm", "PyCharmCE"]:
            for directory in self._get_jetbrains_config_dirs(editor):
                self._generate_pycharm_jdk_entry(directory)

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

        try:
            library_dir = self._lean_config_manager.get_cli_root_directory() / "Library"
            library_dir = f"$PROJECT_DIR$/{path.relpath(library_dir, project_dir)}".replace("\\", "/")
            library_mapping = f'<mapping local-root="{library_dir}" remote-root="/Library" />'
        except:
            library_mapping = ""

        self._generate_file(project_dir / ".idea" / "workspace.xml", f"""
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
            {library_mapping}
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

    def _generate_pycharm_jdk_entry(self, pycharm_config_dir: Path) -> None:
        """Generates a "Lean CLI" Python JDK entry to PyCharm's internal JDK table.

        When we generate PyCharm's .idea directory we want to tell PyCharm where the Python interpreter is located.
        PyCharm stores this bit of configuration globally, so we find the global location and update it to our needs.

        If PyCharm is not installed yet, we create the configuration anyways.
        Once the user installs PyCharm, it will then automatically pick up the configuration we created in the past.

        :param pycharm_config_dir: the path to the global configuration directory of a PyCharm edition
        """
        from sys import path, executable, version_info
        # Parse the file containing PyCharm's internal table of Python interpreters
        jdk_table_file = pycharm_config_dir / "options" / "jdk.table.xml"
        if jdk_table_file.exists():
            root = self._xml_manager.parse(jdk_table_file.read_text(encoding="utf-8"))
        else:
            root = self._xml_manager.parse("""
<application>
  <component name="ProjectJdkTable">
  </component>
</application>
            """)

        # Don't do anything if the Lean CLI interpreter entry already exists
        if root.find(".//jdk/name[@value='Lean CLI']") is not None:
            return

        # Add the new JDK entry to the XML tree
        classpath_entries = [Path(p).as_posix() for p in path if p != "" and not p.endswith(".zip")]
        classpath_entries = [f'<root url="{p}" type="simple" />' for p in classpath_entries]
        classpath_entries = "\n".join(classpath_entries)

        component_element = root.find(".//component[@name='ProjectJdkTable']")
        component_element.append(self._xml_manager.parse(f"""
<jdk version="2">
  <name value="Lean CLI" />
  <type value="Python SDK" />
  <version value="Python {version_info.major}.{version_info.minor}.{version_info.micro}" />
  <homePath value="{Path(executable).as_posix()}" />
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
        self._generate_file(jdk_table_file, self._xml_manager.to_string(root))

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
            "type": "coreclr",
            "processId": "1",
            "pipeTransport": {
                "pipeCwd": "${workspaceRoot}",
                "pipeProgram": "docker",
                "pipeArgs": ["exec", "-i", "lean_cli_vsdbg"],
                "debuggerPath": "/root/vsdbg/vsdbg",
                "quoteArgs": false
            },
            "logging": {
                "moduleLoad": false
            }
        }
    ]
}
        """)

    def _generate_csproj(self, project_dir: Path) -> None:
        """Generates a .csproj file for the given project and returns the path to it.

        :param project_dir: the path of the new project
        """
        self._generate_file(project_dir / f"{project_dir.name}.csproj", self.get_csproj_file_default_content())

    def generate_rider_config(self) -> None:
        """Generates C# debugging configuration for Rider."""
        from pkg_resources import resource_string

        ssh_dir = Path("~/.lean/ssh").expanduser()

        # Add SSH keys to .lean/ssh if necessary
        if not ssh_dir.exists():
            ssh_dir.mkdir(parents=True)
            for name in ["key", "key.pub", "README.md"]:
                with (ssh_dir / name).open("wb+") as file:
                    file.write(resource_string("lean", f"ssh/{name}"))

        # Find Rider's global configuration directory
        for directory in self._get_jetbrains_config_dirs("Rider"):
            self._generate_rider_debugger_entry(directory, ssh_dir)

    def _generate_rider_debugger_entry(self, rider_config_dir: Path, ssh_dir: Path) -> None:
        """Generates a "root@localhost:2222" remote debugger entry to Rider's internal debugger configuration.

        If Rider is not installed yet, we create the configuration anyways.
        Once the user installs Rider, it will then automatically pick up the configuration we created in the past.

        :param rider_config_dir: the path to the global configuration directory of a Rider edition
        :param ssh_dir: the path to the directory containing the SSH keys
        """
        # Parse the file containing Rider's internal list of remote hosts
        debugger_file = rider_config_dir / "options" / "debugger.xml"
        if debugger_file.exists():
            root = self._xml_manager.parse(debugger_file.read_text(encoding="utf-8"))
        else:
            root = self._xml_manager.parse("""
<application>
    <component name="XDebuggerSettings">
    </component>
</application>
            """)

        component_element = root.find(".//component[@name='XDebuggerSettings']")

        if root.find(".//debuggers") is None:
            component_element.append(self._xml_manager.parse("<debuggers></debuggers>"))
        debuggers = root.find(".//debuggers")

        if debuggers.find(".//debugger[@id='dotnet_debugger']") is None:
            debuggers.append(self._xml_manager.parse('<debugger id="dotnet_debugger"></debugger>'))
        dotnet_debugger = debuggers.find(".//debugger[@id='dotnet_debugger']")

        if dotnet_debugger.find(".//configuration") is None:
            dotnet_debugger.append(self._xml_manager.parse("<configuration></configuration>"))
        configuration = dotnet_debugger.find(".//configuration")

        if configuration.find(".//option[@name='sshCredentials']") is None:
            configuration.append(self._xml_manager.parse('<option name="sshCredentials"></option>'))
        ssh_credentials = configuration.find(".//option[@name='sshCredentials']")

        required_value = f"&lt;credentials HOST=&quot;localhost&quot; PORT=&quot;2222&quot; USERNAME=&quot;root&quot; PRIVATE_KEY_FILE=&quot;{ssh_dir.as_posix()}/key&quot; USE_KEY_PAIR=&quot;true&quot; USE_AUTH_AGENT=&quot;false&quot; /&gt;"

        # Don't do anything if the required entry already exists
        for option in ssh_credentials.findall(f".//option"):
            if option.get("value") == required_value.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"'):
                return

        # Add the new entry to the XML tree
        ssh_credentials.append(self._xml_manager.parse(f'<option value="{required_value}"/>'))

        # Save the modified XML tree
        self._generate_file(debugger_file, self._xml_manager.to_string(root))

    def _rename_csproj_file(self, project_path: Path) -> None:
        """Renames the csproj file in the project to name the project name.

        :param project_path: the local project path
        """
        csproj_file = next(project_path.glob("*.csproj"), None)
        if not csproj_file:
            return
        new_csproj_file = project_path / f'{project_path.name}.csproj'
        if new_csproj_file.exists():
            return
        from shutil import move
        move(csproj_file, new_csproj_file)

    def _generate_file(self, file: Path, content: str) -> None:
        """Writes to a file, which is created if it doesn't exist yet, and normalized the content before doing so.

        :param file: the file to write to
        :param content: the content to write to the file
        """
        file.parent.mkdir(parents=True, exist_ok=True)
        with file.open("w+", encoding="utf-8") as file:
            file.write(content.strip() + "\n")

    def _get_jetbrains_config_dirs(self, editor_name: str) -> List[Path]:
        """Returns the paths to the global configuration directories for all installed editions of a JetBrains IDE.

        :param editor_name: the name of the JetBrains IDE
        :return: the paths to the directories holding the global configuration for the specified IDE
        """
        # Find JetBrains' root directory containing the global configuration directories for all installed IDEs
        # See https://www.jetbrains.com/help/pycharm/project-and-ide-settings.html#ide_settings
        if self._platform_manager.is_host_windows():
            root_dir = Path("~/AppData/Roaming/JetBrains").expanduser()
        elif self._platform_manager.is_host_macos():
            root_dir = Path("~/Library/Application Support/JetBrains").expanduser()
        else:
            root_dir = Path("~/.config/JetBrains").expanduser()

        if not root_dir.exists():
            root_dir.mkdir(parents=True)

        # Find the global config directories for the given IDE
        directories = []

        for path in root_dir.iterdir():
            if not path.is_dir() or not path.name.startswith(editor_name):
                continue

            suffix = path.name.replace(editor_name, "")
            if len(suffix) > 0 and not suffix[0].isdigit():
                continue

            directories.append(path)

        if len(directories) == 0:
            directories.append(root_dir / editor_name)

        return directories

    def get_cloud_project_libraries(self,
                                    cloud_projects: List[QCProject],
                                    project: QCProject,
                                    seen_libraries: List[int] = None) -> Tuple[List[QCProject], List[QCProjectLibrary]]:
        """Gets the libraries referenced by the project and its dependencies from the given cloud projects.

        It recursively gets every Lean CLI library referenced by the project
        and the ones referenced by those libraries as well.

        :param cloud_projects: the cloud projects list to search in.
        :param project: the starting point for the libraries gathering.
        :param seen_libraries: list of seen library IDs to avoid infinite recursion.

        :return: two lists including the libraries referenced by the project.
            The first one containing the library projects that could be fetched and
            the second list containing the libraries that could not be fetched because the user has no access to them.
        """
        if seen_libraries is None:
            seen_libraries = []

        libraries = [cloud_project
                     for library in project.libraries
                     for cloud_project in cloud_projects if cloud_project.projectId == library.projectId]

        libraries_ids = [library.projectId for library in libraries]
        libraries_not_found = [library for library in project.libraries if library.projectId not in libraries_ids]

        referenced_libraries = []
        for library in libraries:
            # Avoid infinite recursion
            if library.projectId in seen_libraries:
                continue

            seen_libraries.append(library.projectId)
            libs, libs_not_found = self.get_cloud_project_libraries(cloud_projects, library, seen_libraries)
            referenced_libraries.extend(libs)
            libraries_not_found.extend(libs_not_found)

        libraries.extend(referenced_libraries)

        return list(set(libraries)), list(set(libraries_not_found))

    def get_cloud_projects_libraries(self,
                                     cloud_projects: List[QCProject],
                                     projects: List[QCProject],
                                     seen_projects: List[int] = None) -> Tuple[List[QCProject], List[QCProjectLibrary]]:
        """Gets the libraries referenced by the passed projects and its dependencies from the given cloud projects.

        It recursively gets every Lean CLI library referenced by the passed projects
        and the ones referenced by those libraries as well.

        :param cloud_projects: the cloud projects list to search in.
        :param projects: the starting point list of projects for the libraries gathering.
        :param seen_projects: list of seen project IDs to avoid infinite recursion.

        :return: two lists including the libraries referenced by the projects.
            The first one containing the library projects that could be fetched and
            the second list containing the libraries that could not be fetched because the user has no access to them.
        """
        if seen_projects is None:
            seen_projects = [project.projectId for project in projects]

        libraries = []
        libraries_not_found = []
        for project in projects:
            libs, libs_not_found = self.get_cloud_project_libraries(cloud_projects, project, seen_projects)
            libraries.extend(libs)
            libraries_not_found.extend(libs_not_found)

        return list(set(libraries)), list(set(libraries_not_found))

    @staticmethod
    def get_csproj_file_default_content() -> str:
        return """
<Project Sdk="Microsoft.NET.Sdk">
    <PropertyGroup>
        <Configuration Condition=" '$(Configuration)' == '' ">Debug</Configuration>
        <Platform Condition=" '$(Platform)' == '' ">AnyCPU</Platform>
        <TargetFramework>net6.0</TargetFramework>
        <OutputPath>bin/$(Configuration)</OutputPath>
        <AppendTargetFrameworkToOutputPath>false</AppendTargetFrameworkToOutputPath>
        <DefaultItemExcludes>$(DefaultItemExcludes);backtests/*/code/**;live/*/code/**;optimizations/*/code/**</DefaultItemExcludes>
        <NoWarn>CS0618</NoWarn>
    </PropertyGroup>
    <ItemGroup>
        <PackageReference Include="QuantConnect.Lean" Version="2.5.*"/>
        <PackageReference Include="QuantConnect.DataSource.Libraries" Version="2.5.*"/>
    </ItemGroup>
</Project>
        """

    @staticmethod
    def get_csproj_file_path(project_dir: Path) -> Path:
        """Gets the path to the csproj file in the project directory.

        :param project_dir: Path to the project directory
        :return: Path to the csproj file in the project directory
        """
        return next((p for p in project_dir.iterdir() if p.name.endswith(".csproj")), None)
