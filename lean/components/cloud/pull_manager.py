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

import traceback
from pathlib import Path
from typing import List, Optional, Tuple

from lean.components.api.api_client import APIClient
from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.util.library_manager import LibraryManager
from lean.components.util.logger import Logger
from lean.components.util.platform_manager import PlatformManager
from lean.components.util.project_manager import ProjectManager
from lean.models.api import QCProject, QCLanguage
from lean.models.utils import LeanLibraryReference


class PullManager:
    """The PullManager class is responsible for synchronizing cloud projects to the local drive."""

    def __init__(self,
                 logger: Logger,
                 api_client: APIClient,
                 project_manager: ProjectManager,
                 project_config_manager: ProjectConfigManager,
                 library_manager: LibraryManager,
                 platform_manager: PlatformManager) -> None:
        """Creates a new PullManager instance.

        :param logger: the logger to use when printing messages
        :param api_client: the APIClient instance to use when communicating with the cloud
        :param project_manager: the ProjectManager instance to use when creating new projects
        :param project_config_manager: the ProjectConfigManager instance to use
        :param library_manager: the LibraryManager instance to use when updating library references
        :param platform_manager: the PlatformManager used when checking which operating system is in use
        """
        self._logger = logger
        self._api_client = api_client
        self._project_manager = project_manager
        self._project_config_manager = project_config_manager
        self._library_manager = library_manager
        self._platform_manager = platform_manager
        self._last_file = None

    def _get_libraries(self, project: QCProject, seen_projects: List[int] = None) -> List[QCProject]:
        if seen_projects is None:
            seen_projects = [project.projectId]

        libraries = []
        for library_id in project.libraries:
            if library_id in seen_projects:
                continue
            seen_projects.append(library_id)
            library = self._api_client.projects.get(library_id)
            libraries.append(library)
            libraries.extend(self._get_libraries(library, seen_projects))

        return libraries

    def pull_projects(self, projects_to_pull: List[QCProject], all_cloud_projects: Optional[List[QCProject]]) -> None:
        """Pulls the given projects from the cloud to the local drive.

        This will also pull libraries referenced by the project.

        :param projects_to_pull: the cloud projects that need to be pulled
        :param all_cloud_projects: all the projects available in the cloud
        """
        if all_cloud_projects is not None:
            projects_to_pull.extend(self._project_manager.get_cloud_projects_libraries(all_cloud_projects,
                                                                                       projects_to_pull))
        else:
            for project in projects_to_pull:
                projects_to_pull.extend(self._get_libraries(project, [p.projectId for p in projects_to_pull]))

        projects_to_pull = sorted(projects_to_pull, key=lambda p: p.name)
        projects_with_paths = []

        for index, project in enumerate(projects_to_pull, start=1):
            try:
                self._logger.info(f"[{index}/{len(projects_to_pull)}] Pulling '{project.name}'")
                projects_with_paths.append((project, self._pull_project(project)))
            except Exception as ex:
                self._logger.debug(traceback.format_exc().strip())
                if self._last_file is not None:
                    self._logger.warn(
                        f"Cannot pull '{project.name}' (id {project.projectId}, failed on {self._last_file}): {ex}")
                else:
                    self._logger.warn(f"Cannot pull '{project.name}' (id {project.projectId}): {ex}")

        self._update_local_library_references(projects_with_paths)

    def _pull_project(self, project: QCProject) -> Path:
        """Pulls a single project from the cloud to the local drive.

        Raises an error with a descriptive message if the project cannot be pulled.

        :param project: the cloud project to pull
        :return the actual local path of the project
        """
        local_project_path = self.get_local_project_path(project)

        # Pull the cloud files to the local drive
        self._pull_files(project, local_project_path)

        # Update the local project config with the latest details
        project_config = self._project_config_manager.get_project_config(local_project_path)
        project_config.set("cloud-id", project.projectId)
        project_config.set("algorithm-language", project.language.name)
        project_config.set("parameters", {parameter.key: parameter.value for parameter in project.parameters})
        project_config.set("description", project.description)
        project_config.set("organization-id", project.organizationId)
        project_config.set("python-venv", project.leanEnvironment)

        if not project.leanPinnedToMaster:
            project_config.set("lean-engine", project.leanVersionId)
        else:
            project_config.delete("lean-engine")

        return local_project_path

    def _pull_files(self, project: QCProject, local_project_path: Path) -> None:
        """Pull the files of a single project.

        :param project: the cloud project of which the files need to be pulled
        :param local_project_path: the path to the local project directory
        """
        if not local_project_path.exists():
            self._project_manager.create_new_project(local_project_path, project.language)

        for cloud_file in self._api_client.files.get_all(project.projectId):
            self._last_file = cloud_file.name

            if cloud_file.isLibrary:
                continue

            local_file_path = local_project_path / cloud_file.name

            # Skip if the local file already exists with the correct content
            if local_file_path.exists():
                if local_file_path.read_text(encoding="utf-8").strip() == cloud_file.content.strip():
                    self._project_manager.update_last_modified_time(local_file_path, cloud_file.modified)
                    continue

            local_file_path.parent.mkdir(parents=True, exist_ok=True)
            with local_file_path.open("w+", encoding="utf-8") as local_file:
                if cloud_file.content != "" and not cloud_file.content.endswith("\n"):
                    local_file.write(cloud_file.content + "\n")
                else:
                    local_file.write(cloud_file.content)

            self._project_manager.update_last_modified_time(local_file_path, cloud_file.modified)
            self._logger.info(f"Successfully pulled '{project.name}/{cloud_file.name}'")

        self._last_file = None
        self._project_manager.update_last_modified_time(local_project_path, project.modified)

    def get_local_project_path(self, project: QCProject) -> Path:
        """Returns the local path where a certain cloud project should be stored.

        If two cloud projects are named "Project", they are pulled to ./Project and ./Project 2.

        :param project: the cloud project to get the project path of
        :return: the path to the local project directory
        """
        local_path = self._format_local_path(project.name)

        current_index = 1
        while True:
            path_suffix = "" if current_index == 1 else f" {current_index}"
            current_path = Path.cwd() / (local_path + path_suffix)

            if not current_path.exists():
                return current_path

            current_project_config = self._project_config_manager.get_project_config(current_path)
            if current_project_config.get("cloud-id") == project.projectId:
                return current_path

            current_index += 1

    def _format_local_path(self, cloud_path: str) -> str:
        """Converts the given cloud path into a local path which is valid for the current operating system.

        :param cloud_path: the path of the project in the cloud
        :return: the converted cloud_path so that it is valid locally
        """
        # Remove forbidden characters and OS-specific path separator that are not path separators on QuantConnect
        if self._platform_manager.is_host_windows():
            # Windows, \":*?"<>| are forbidden
            # Windows, \ is a path separator, but \ is not a path separator on QuantConnect
            forbidden_characters = ["\\", ":", "*", "?", '"', "<", ">", "|"]
        elif self._platform_manager.is_host_macos():
            # macOS, : is a path separator, but : is not a path separator on QuantConnect
            forbidden_characters = [":"]
        else:
            # Linux, no forbidden characters
            forbidden_characters = []

        for forbidden_character in forbidden_characters:
            cloud_path = cloud_path.replace(forbidden_character, " ")

        # On Windows we need to ensure each path component is valid
        if self._platform_manager.is_host_windows():
            new_components = []

            for component in cloud_path.split("/"):
                # Some names are reserved
                for reserved_name in ["CON", "PRN", "AUX", "NUL",
                                      "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
                                      "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"]:
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

    def _add_local_library_references_to_project(self, project_dir: Path, cloud_libraries_paths: List[Path]) -> None:
        if len(cloud_libraries_paths) > 0:
            self._logger.info(f"Adding/updating local library references to project {project_dir.name}")

        for i, library_dir in enumerate(cloud_libraries_paths, start=1):
            self._logger.info(f"[{i}/{len(cloud_libraries_paths)}] Adding/updating local library "
                              f"{library_dir.name} reference to project {project_dir.name}")
            # Add library references without restoring. It will be done after all lib references have been updated
            self._library_manager.add_lean_library_to_project(project_dir, library_dir, True)

    def _remove_local_library_references_from_project(self,
                                                      project_dir: Path,
                                                      cloud_libraries_paths: List[Path]) -> None:

        project_config = self._project_config_manager.get_project_config(project_dir)
        local_libraries = project_config.get("libraries", [])
        cloud_library_relative_paths = [library_dir.relative_to(Path.cwd()) for library_dir in cloud_libraries_paths]
        libraries_to_remove = [LeanLibraryReference(**library_reference)
                               for library_reference in local_libraries
                               if Path(library_reference["path"]) not in cloud_library_relative_paths]

        if len(libraries_to_remove) > 0:
            self._logger.info(f"Removing local library references from project {project_dir.name}")

        for i, library_reference in enumerate(libraries_to_remove, start=1):
            self._logger.info(f"[{i}/{len(libraries_to_remove)}] Removing local library "
                              f"{library_reference.name} reference from project {project_dir.name}")
            # Remove library references without restoring. It will be done after all lib references have been updated
            self._library_manager.remove_lean_library_from_project(project_dir,
                                                                   Path.cwd() / library_reference.path,
                                                                   True)

    def _update_local_library_references(self, projects: List[Tuple[QCProject, Path]]) -> None:
        for project, path in projects:
            cloud_libraries_paths = [library_path for library, library_path in projects
                                     if library.projectId in project.libraries]

            # Add cloud library references to local config
            self._add_local_library_references_to_project(path, cloud_libraries_paths)

            # Remove library references locally if they were removed in the cloud
            self._remove_local_library_references_from_project(path, cloud_libraries_paths)

            # Restore the project to automatically enable local auto-complete
            self._restore_project(project, path)

    def _restore_project(self, project: QCProject, project_dir: Path) -> None:
        if project.language != QCLanguage.CSharp:
            return

        project_csproj_file = self._project_manager.get_csproj_file_path(project_dir)
        original_csproj_content = project_csproj_file.read_text(encoding="utf-8")
        self._project_manager.try_restore_csharp_project(project_csproj_file, original_csproj_content, False)
