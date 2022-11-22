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

from lean.components.config.lean_config_manager import LeanConfigManager
from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.util.logger import Logger
from lean.components.util.path_manager import PathManager
from lean.components.util.project_manager import ProjectManager
from lean.components.util.xml_manager import XMLManager
from lean.models.utils import LeanLibraryReference


class LibraryManager:
    """The LibraryManager class provides utilities for handling a libraries."""

    def __init__(self,
                 logger: Logger,
                 project_manager: ProjectManager,
                 project_config_manager: ProjectConfigManager,
                 lean_config_manager: LeanConfigManager,
                 path_manager: PathManager,
                 xml_manager: XMLManager) -> None:
        """Creates a new LibraryManager instance.

        :param logger: the logger to use to log messages with
        :param project_manager: the ProjectManager to use when requesting project csproj file
        :param project_config_manager: the ProjectConfigManager to use to get project's config
        :param lean_config_manager: the LeanConfigManager to get the CLI root directory from
        :param path_manager: the path manager to use to handle library paths
        :param xml_manager: the XMLManager to use when working with XML
        """
        self._logger = logger
        self._project_manager = project_manager
        self._project_config_manager = project_config_manager
        self._lean_config_manager = lean_config_manager
        self._path_manager = path_manager
        self._xml_manager = xml_manager

    def is_lean_library(self, path: Path) -> bool:
        """Checks whether the library name is a Lean library path

        :param path: path to check whether it is a Lean library
        :return: true if the path is a Lean library path
        """
        relative_path = self._path_manager.get_relative_path(path, self._lean_config_manager.get_cli_root_directory())
        path_parts = relative_path.parts
        library_config = self._project_config_manager.get_project_config(path)
        library_language = library_config.get("algorithm-language", None)

        return (
            len(path_parts) > 0 and
            path_parts[0].lower() == "library" and
            relative_path.is_dir() and
            library_language is not None
        )

    def get_csharp_lean_library_path_for_csproj_file(self, project_dir: Path, library_dir: Path) -> str:
        """Gets the library path to be used for the project's .csproj file.

        The returned path is relative to the project directory so auto complete can be provided.

        :param project_dir: The path to the project directory
        :param library_dir: The path to the library directory
        :return The path to be used for the project's .csproj file
        """
        cli_root_dir = self._lean_config_manager.get_cli_root_directory()
        project_dir_relative_to_cli = self._path_manager.get_relative_path(project_dir, cli_root_dir)
        library_dir_relative_to_cli = self._path_manager.get_relative_path(library_dir, cli_root_dir)
        library_csproj_file = self._project_manager.get_csproj_file_path(library_dir_relative_to_cli)

        if library_csproj_file is None:
            return None

        return ("../" * len(project_dir_relative_to_cli.parts) / library_csproj_file).as_posix()

    def get_library_path_for_project_config_file(self, library_dir: Path) -> str:
        """Gets the library path to be used for the project's config.json file.

        :param library_dir: The path to the library directory
        :return The path to be used for the project's config.json file
        """
        lean_cli_root_dir = self._lean_config_manager.get_cli_root_directory()
        return self._path_manager.get_relative_path(library_dir, lean_cli_root_dir).as_posix()

    def add_lean_library_reference_to_project(self, project_dir: Path, library_dir: Path) -> bool:
        """Adds a Lean CLI library reference to a project.

        Adds the library path to the project's config.json

        :param project_dir: the path to the project directory
        :param library_dir: the path to the library directory
        :return: True if the library has already been added to the project, that is, if the reference already exists in
                 the project's config.json file. False if the library was added successfully.
        """
        project_config = self._project_config_manager.get_project_config(project_dir)
        project_libraries = project_config.get("libraries", [])
        library_relative_path = Path(self.get_library_path_for_project_config_file(library_dir))

        if any(LeanLibraryReference(**library).path == library_relative_path for library in project_libraries):
            return True

        library_config = self._project_config_manager.get_project_config(library_dir)
        library_libraries = library_config.get("libraries", [])
        project_relative_path = Path(self.get_library_path_for_project_config_file(project_dir))

        if any(LeanLibraryReference(**library).path == project_relative_path for library in library_libraries):
            raise RuntimeError("Circular dependency detected between "
                               f"{project_relative_path} and {library_relative_path}")

        from json import loads
        project_libraries.append(loads(LeanLibraryReference(
            name=library_dir.name,
            path=library_relative_path
        ).json()))
        project_config.set("libraries", project_libraries)

        return False

    def remove_lean_library_reference_from_project(self, project_dir: Path, library_dir: Path) -> None:
        """Removed a Lean CLI library reference from a project.

        Removes the library path from the project's config.json

        :param project_dir: the path to the project directory
        :param library_dir: the path to the C# library directory
        """
        library_relative_path = Path(self.get_library_path_for_project_config_file(library_dir))
        project_config = self._project_config_manager.get_project_config(project_dir)
        libraries = project_config.get("libraries", [])
        libraries = [library for library in libraries if LeanLibraryReference(**library).path != library_relative_path]
        project_config.set("libraries", libraries)

    def add_lean_library_to_csharp_project(self, project_dir: Path, library_dir: Path, no_local: bool) -> None:
        """Adds a Lean CLI C# library to the project's csproj file.

        It will add a reference to the library and restore the project if dotnet is the user's PATH.

        It will raise a RuntimeError if the library is a C# library and does not have a .csproj file.

        :param project_dir: Path to the project directory
        :param library_dir: Path to the library directory
        :param no_local: Whether restoring the packages locally must be skipped
        """
        already_added = self.add_lean_library_reference_to_project(project_dir, library_dir)
        # If the library was already referenced by the project,
        # do not proceed further with adding it to the .csproj file
        if already_added:
            self._logger.info(f"Library {library_dir.name} has already been added to the project {project_dir.name}")
            return

        library_config = self._project_config_manager.get_project_config(library_dir)
        library_language = library_config.get("algorithm-language", None)

        # Python library references are not added to .csproj file
        if library_language == 'Python':
            return

        library_csproj_file_path = self.get_csharp_lean_library_path_for_csproj_file(project_dir, library_dir)

        if library_csproj_file_path is None:
            raise RuntimeError(f"C# library {library_dir.name} does not contain a .csproj file")

        project_csproj_file = self._project_manager.get_csproj_file_path(project_dir)

        original_csproj_content = project_csproj_file.read_text(encoding="utf-8")
        self._add_csharp_project_to_csproj(project_csproj_file, library_csproj_file_path)
        self._project_manager.try_restore_csharp_project(project_csproj_file, original_csproj_content, no_local)

    def add_lean_library_to_python_project(self, project_dir: Path, library_dir: Path) -> None:
        """Adds a Lean CLI Python library to a Python project.

        :param project_dir: the path to the project directory
        :param library_dir: the path to the library directory
        """
        self.add_lean_library_reference_to_project(project_dir, library_dir)

    def add_lean_library_to_project(self, project_dir: Path, library_dir: Path, no_local: bool) -> None:
        """Adds a Lean CLI library to a project.

        :param project_dir: the path to the project directory
        :param library_dir: the path to the library directory
        :param no_local: whether restoring the packages locally must be skipped
        """
        project_language = self._get_project_language(project_dir)

        if project_language == "CSharp":
            self.add_lean_library_to_csharp_project(project_dir, library_dir, no_local)
        else:
            self.add_lean_library_to_python_project(project_dir, library_dir)

    def remove_lean_library_from_csharp_project(self, project_dir: Path, library_dir: Path, no_local: bool) -> None:
        """Removes a Lean CLI library from a C# project.

        Removes the library from the project's .csproj file,
        and restores the project if dotnet is on the user's PATH and no_local is False.

        :param project_dir: Path to the project directory
        :param library_dir: Path to the library directory
        :param no_local: Whether restoring the packages locally must be skipped
        """
        self.remove_lean_library_reference_from_project(project_dir, library_dir)

        library_config = self._project_config_manager.get_project_config(library_dir)
        library_language = library_config.get("algorithm-language", None)

        # Python library references are not added to .csproj file, so no need to remove
        if library_language == 'Python':
            return

        self._remove_project_reference_from_csharp_project(project_dir, library_dir, no_local)

    def remove_lean_library_from_python_project(self, project_dir: Path, library_dir: Path) -> None:
        """Removes a Lean CLI library from a Python project.

        :param project_dir: Path to the project directory
        :param library_dir: Path to the library directory
        """
        self.remove_lean_library_reference_from_project(project_dir, library_dir)

    def remove_lean_library_from_project(self, project_dir: Path, library_dir: Path, no_local: bool) -> None:
        """Removes a Lean CLI library from a project.

        Removes the library from the project's .csproj file,
        and restores the project if dotnet is on the user's PATH and no_local is False.

        :param project_dir: Path to the project directory
        :param library_dir: Path to the library directory
        :param no_local: Whether restoring the packages locally must be skipped
        """
        project_language = self._get_project_language(project_dir)

        if project_language == "CSharp":
            self.remove_lean_library_from_csharp_project(project_dir, library_dir, no_local)
        else:
            self.remove_lean_library_from_python_project(project_dir, library_dir)

    def _get_project_language(self, project_dir: Path) -> str:
        """Gets a project language.

        :param project_dir: Path to the project directory
        :return The project language
        """
        project_config = self._project_config_manager.get_project_config(project_dir)
        return project_config.get("algorithm-language", None)

    def _add_csharp_project_to_csproj(self, csproj_file: Path, library_csproj_path: str) -> None:
        """Adds a Lean CLI library project reference to a .csproj file.

        :param csproj_file: the path to the .csproj file
        :param library_csproj_path: the path to the library's .csproj file
        """
        from lxml import etree
        csproj_tree = self._xml_manager.parse(csproj_file.read_text(encoding="utf-8"))

        existing_project_reference = csproj_tree.find(f".//ProjectReference[@Include='{library_csproj_path}']")
        if existing_project_reference is None:
            last_item_group = csproj_tree.find(".//ItemGroup[last()]")
            if last_item_group is None:
                last_item_group = etree.SubElement(csproj_tree.find(".//Project"), "ItemGroup")

            last_item_group.append(etree.fromstring(f'<ProjectReference Include="{library_csproj_path}" />'))

        csproj_file.write_text(self._xml_manager.to_string(csproj_tree), encoding="utf-8")

    def _remove_project_reference_from_csharp_project(self, project_dir: Path, name: Path, no_local: bool) -> None:
        """Removes a Lean CLI C# library from a C# project.

        Removes the library from the project's .csproj file,
        and restores the project if dotnet is on the user's PATH and no_local is False.

        :param project_dir: the path to the project directory
        :param name: the path to the Lean CLI library to remove
        :param no_local: Whether restoring the packages locally must be skipped
        """
        from shutil import which
        from subprocess import run

        csproj_file = self._project_manager.get_csproj_file_path(project_dir)
        self._logger.info(f"Removing {name} from '{self._path_manager.get_relative_path(csproj_file)}'")

        csproj_tree = self._xml_manager.parse(csproj_file.read_text(encoding="utf-8"))

        library_reference = self.get_csharp_lean_library_path_for_csproj_file(project_dir, name)

        for package_reference in csproj_tree.findall('.//ProjectReference'):
            if package_reference.get("Include", "") == library_reference:
                package_reference.getparent().remove(package_reference)

        csproj_file.write_text(self._xml_manager.to_string(csproj_tree), encoding="utf-8")

        if not no_local and which("dotnet") is not None:
            self._logger.info(f"Restoring packages in '{self._path_manager.get_relative_path(project_dir)}'")

            process = run(["dotnet", "restore", str(csproj_file)], cwd=project_dir)

            if process.returncode != 0:
                raise RuntimeError(
                    "Something went wrong while restoring packages, see the logs above for more information")
