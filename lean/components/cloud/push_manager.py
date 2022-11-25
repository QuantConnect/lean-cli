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
from typing import List, Dict

from lean.components.api.api_client import APIClient
from lean.components.config.project_config_manager import ProjectConfigManager
from lean.components.util.logger import Logger
from lean.components.util.organization_manager import OrganizationManager
from lean.components.util.project_manager import ProjectManager
from lean.models.api import QCLanguage, QCProject
from lean.models.utils import LeanLibraryReference

class PushManager:
    """The PushManager class is responsible for synchronizing local projects to the cloud."""

    def __init__(self,
                 logger: Logger,
                 api_client: APIClient,
                 project_manager: ProjectManager,
                 project_config_manager: ProjectConfigManager,
                 organization_manager: OrganizationManager) -> None:
        """Creates a new PushManager instance.

        :param logger: the logger to use when printing messages
        :param api_client: the APIClient instance to use when communicating with the cloud
        :param project_manager: the ProjectManager to use when looking for certain projects
        :param project_config_manager: the ProjectConfigManager instance to use
        """
        self._logger = logger
        self._api_client = api_client
        self._project_manager = project_manager
        self._project_config_manager = project_config_manager
        self._organization_manager = organization_manager
        self._cloud_projects = []

    def push_project(self, project: Path) -> None:
        """Pushes the given project from the local drive to the cloud.

        It will also push every library referenced by the project and add or remove references.

        :param project: path to the directory containing the local project that needs to be pushed
        """
        libraries = self._project_manager.get_project_libraries(project)
        self.push_projects(libraries + [project])

    def push_projects(self, projects_to_push: List[Path]) -> None:
        """Pushes the given projects from the local drive to the cloud.

        It will also push every library referenced by each project and add or remove references.

        :param projects_to_push: a list of directories containing the local projects that need to be pushed
        """
        if len(projects_to_push) == 0:
            return

        organization_id = self._organization_manager.try_get_working_organization_id()

        for index, path in enumerate(projects_to_push, start=1):
            relative_path = path.relative_to(Path.cwd())
            try:
                self._logger.info(f"[{index}/{len(projects_to_push)}] Pushing '{relative_path}'")
                self._push_project(path, organization_id)
            except Exception as ex:
                from traceback import format_exc
                self._logger.debug(format_exc().strip())
                self._logger.warn(f"Cannot push '{relative_path}': {ex}")

    def _get_local_libraries_cloud_ids(self, project_dir: Path) -> List[int]:
        project_config = self._project_config_manager.get_project_config(project_dir)

        libraries_in_config = project_config.get("libraries", [])
        library_paths = [LeanLibraryReference(**library).path.expanduser().resolve() for library in libraries_in_config]

        local_libraries_cloud_ids = [int(self._project_config_manager.get_project_config(path).get("cloud-id", None))
                                     for path in library_paths]

        return local_libraries_cloud_ids

    def _push_project(self, project_path: Path, organization_id: str, suggested_rename_path: Path = None) -> None:
        """Pushes a single local project to the cloud.

        Raises an error with a descriptive message if the project cannot be pushed.

        :param project_path: the local project to push
        :param organization_id: the id of the organization to push the project to
        :param suggested_rename_path: the path to move the project to.
        """
        
        project_name = project_path.relative_to(Path.cwd()).as_posix()

        potential_new_name = project_name
        if suggested_rename_path and suggested_rename_path != project_path:
            potential_new_name = suggested_rename_path.relative_to(Path.cwd()).as_posix()
            

        project_config = self._project_config_manager.get_project_config(project_path)
        cloud_id = project_config.get("cloud-id")

        # check if project name is valid or if rename is required
        if cloud_id is not None:
            expected_correct_project_path = self._project_manager.get_local_project_path(potential_new_name, cloud_id)
        else:
            local_id = self._project_config_manager.get_local_id(project_path)
            expected_correct_project_path = self._project_manager.get_local_project_path(potential_new_name, None, local_id)
        if expected_correct_project_path != project_path:
            # rename project
            valid_project_name = expected_correct_project_path.relative_to(Path.cwd()).as_posix()
            self._logger.info(f"Renaming '{project_name}' to '{valid_project_name}'")
            self._project_manager.rename_project_and_contents(project_path, expected_correct_project_path)
            project_path = expected_correct_project_path
            project_name = valid_project_name
            project_config = self._project_config_manager.get_project_config(project_path)

        # Find the cloud project to push the files to
        if cloud_id is not None:
            # Project has cloud id which matches cloud project, update cloud project
            cloud_project = self._get_cloud_project(cloud_id, organization_id)
        else:
            # Project has invalid cloud id or no cloud id at all, create new cloud project
            cloud_project = self._api_client.projects.create(project_name,
                                                             QCLanguage[project_config.get("algorithm-language")],
                                                             organization_id)
            project_config.set("cloud-id", cloud_project.projectId)
            project_config.set("organization-id", cloud_project.organizationId)

            if cloud_project.name != project_name:
                # cloud project name was changed. Repeat steps to validate the new name locally.
                self._logger.info(f"Received new name '{cloud_project.name}' for project '{project_name}' from QuantConnect.com")
                self._push_project(project_path, organization_id, Path.cwd() / cloud_project.name)
                return

            self._cloud_projects.append(cloud_project)
            organization_message_part = f" in organization '{organization_id}'" if organization_id is not None else ""
            self._logger.info(f"Successfully created cloud project '{cloud_project.name}'{organization_message_part}")

        # Finalize pushing by updating locally modified metadata, files and libraries
        self._push_metadata(project_path, cloud_project)

    def _get_files(self, project: Path) -> List[Dict[str, str]]:
        """Pushes the files of a local project to the cloud.

        :param project: the local project to push the files of
        """
        paths = self._project_manager.get_source_files(project)
        files = []

        for path in paths:
            relative_path = path.relative_to(project).as_posix()
            if "bin/" in relative_path and "obj/" in relative_path and ".ipynb_checkpoints/" in relative_path:
                continue

            files.append({
                'name': relative_path,
                'content': path.read_text(encoding="utf-8")
            })

        return files

    def _push_metadata(self, project: Path, cloud_project: QCProject) -> None:
        """Pushes local project description and parameters to the cloud.

        Does nothing if the cloud is already up-to-date.

        :param project: the local project to push the parameters of
        :param cloud_project: the cloud project to push the parameters to
        """
        project_config = self._project_config_manager.get_project_config(project)

        local_description = project_config.get("description", "")
        cloud_description = cloud_project.description

        local_parameters = project_config.get("parameters", {})
        cloud_parameters = {parameter.key: parameter.value for parameter in cloud_project.parameters}

        # Use latest (-1) by default
        local_lean_version = int(project_config.get("lean-engine", "-1"))
        cloud_lean_version = cloud_project.leanVersionId

        local_lean_venv = project_config.get("python-venv", None)
        cloud_lean_venv = cloud_project.leanEnvironment

        update_args = {}

        expected_correct_project_name = project.relative_to(Path.cwd()).as_posix()

        # update project name in cloud in case it was incorrect and renamed locally otherwise update the same name
        update_args["name"] = expected_correct_project_name
        if cloud_project.name != expected_correct_project_name:
            self._logger.info(f"Renaming project in cloud from '{cloud_project.name}' to '{expected_correct_project_name}'")

        if local_description != cloud_description:
            update_args["description"] = local_description

        if local_parameters != cloud_parameters:
            update_args["parameters"] = local_parameters

        if (local_lean_version != cloud_lean_version and
           (local_lean_version != -1 or not cloud_project.leanPinnedToMaster)):
            update_args["lean_engine"] = local_lean_version

        # Initially, python-venv is not defined in the config and the default one will be used.
        # After it is changed, in order to use the default one again, it must not be removed from the config,
        # but it should be set to the default env id explicitly instead.
        if local_lean_venv is not None and local_lean_venv != cloud_lean_venv:
            update_args["python_venv"] = local_lean_venv

        update_args["files"] = self._get_files(project)
        update_args["libraries"] = self._get_local_libraries_cloud_ids(project)

        if update_args != {}:
            self._api_client.projects.update(cloud_project.projectId, **update_args)

            updated_keys = list(update_args)
            if len(updated_keys) == 1:
                updated_keys_str = updated_keys[0]
            elif len(updated_keys) == 2:
                updated_keys_str = " and ".join(updated_keys)
            else:
                updated_keys_str = ", ".join(updated_keys[:-1]) + f", and {updated_keys[-1]}"
            self._logger.info(f"Successfully updated {updated_keys_str} for '{cloud_project.name}'")

    def _get_cloud_project(self, project_id: int, organization_id: str) -> QCProject:
        project = next(iter(p for p in self._cloud_projects if p.projectId == project_id), None)
        if project is None:
            project = self._api_client.projects.get(project_id, organization_id)
            self._cloud_projects.append(project)

        return project
