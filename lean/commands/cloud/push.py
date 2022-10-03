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
from typing import Optional, List

import click

from lean.click import LeanCommand, PathParameter
from lean.constants import PROJECT_CONFIG_FILE_NAME
from lean.container import container
from lean.models.api import QCProject
from lean.models.utils import LeanLibraryReference


def _get_cloud_project(project: Path, cloud_projects: List[QCProject]) -> QCProject:
    lean_config_manager = container.lean_config_manager()
    lean_cli_root_dir = lean_config_manager.get_cli_root_directory()
    project_relative_path = project.relative_to(lean_cli_root_dir)
    cloud_project = [cloud_project for cloud_project in cloud_projects
                     if Path(cloud_project.name) == project_relative_path][0]

    return cloud_project


def _get_local_libraries_cloud_ids(project_dir: Path) -> List[int]:
    project_config_manager = container.project_config_manager()
    project_config = project_config_manager.get_project_config(project_dir)

    lean_config_manager = container.lean_config_manager()
    lean_cli_root_dir = lean_config_manager.get_cli_root_directory()

    libraries_in_config = project_config.get("libraries", [])
    library_paths = [lean_cli_root_dir / LeanLibraryReference(**library).path for library in libraries_in_config]

    local_libraries_cloud_ids = [int(project_config_manager.get_project_config(path).get("cloud-id", None))
                                 for path in library_paths]

    return local_libraries_cloud_ids


def _get_library_name(library_cloud_id: int, cloud_projects: List[QCProject]) -> str:
    return [project.name for project in cloud_projects if project.projectId == library_cloud_id][0]


def _add_new_libraries(project: QCProject,
                       local_libraries_cloud_ids: List[int],
                       cloud_projects: List[QCProject]) -> None:
    logger = container.logger()
    api_client = container.api_client()
    libraries_to_add = [library_id for library_id in local_libraries_cloud_ids if library_id not in project.libraries]

    if len(libraries_to_add) > 0:
        logger.info(f"Adding libraries to project {project.name} in the cloud")

    for i, library_cloud_id in enumerate(libraries_to_add, start=1):
        library_name = _get_library_name(library_cloud_id, cloud_projects)
        logger.info(f"[{i}/{len(libraries_to_add)}] "
                    f"Adding library {library_name} to project {project.name} in the cloud")
        api_client.projects.add_library(project.projectId, library_cloud_id)


def _remove_outdated_libraries(project: QCProject,
                               local_libraries_cloud_ids: List[int],
                               cloud_projects: List[QCProject]) -> None:
    logger = container.logger()
    api_client = container.api_client()
    libraries_to_remove = [library_id for library_id in project.libraries
                           if library_id not in local_libraries_cloud_ids]

    if len(libraries_to_remove) > 0:
        logger.info(f"Removing libraries from project {project.name} in the cloud")

    for i, library_cloud_id in enumerate(libraries_to_remove, start=1):
        library_name = _get_library_name(library_cloud_id, cloud_projects)
        logger.info(f"[{i}/{len(libraries_to_remove)}] "
                    f"Removing library {library_name} from project {project.name} in the cloud")
        api_client.projects.delete_library(project.projectId, library_cloud_id)


def _update_cloud_library_references(projects: List[Path]) -> None:
    api_client = container.api_client()
    cloud_projects = api_client.projects.get_all()

    for project in projects:
        cloud_project = _get_cloud_project(project, cloud_projects)
        local_libraries_cloud_ids = _get_local_libraries_cloud_ids(project)

        _add_new_libraries(cloud_project, local_libraries_cloud_ids, cloud_projects)
        _remove_outdated_libraries(cloud_project, local_libraries_cloud_ids, cloud_projects)


def _get_libraries_to_push(project_dir: Path, seen_projects: List[Path] = None) -> List[Path]:
    if seen_projects is None:
        seen_projects = [project_dir]

    project_config_manager = container.project_config_manager()
    project_config = project_config_manager.get_project_config(project_dir)
    libraries_in_config = project_config.get("libraries", [])
    libraries = [LeanLibraryReference(**library).path.expanduser().resolve() for library in libraries_in_config]

    referenced_libraries = []
    for library_path in libraries:
        # Avoid infinite recursion
        if library_path in seen_projects:
            continue

        seen_projects.append(library_path)
        referenced_libraries.extend(_get_libraries_to_push(library_path, seen_projects))

    libraries.extend(referenced_libraries)

    return list(dict.fromkeys(libraries))


@click.command(cls=LeanCommand)
@click.option("--project",
              type=PathParameter(exists=True, file_okay=False, dir_okay=True),
              help="Path to the local project to push (all local projects if not specified)")
@click.option("--organization-id",
              type=str,
              help="ID of the organization where the project will be created in. This is ignored if the project has "
                   "already been created in the cloud")
def push(project: Optional[Path], organization_id: Optional[str]) -> None:
    """Push local projects to QuantConnect.

    This command overrides the content of cloud files with the content of their respective local counterparts.

    This command will delete cloud files which don't have a local counterpart.
    """
    # Parse which projects need to be pushed
    if project is not None:
        project_config_manager = container.project_config_manager()
        project_config = project_config_manager.get_project_config(project)
        if not project_config.file.exists():
            raise RuntimeError(f"'{project}' is not a Lean project")

        projects_to_push = [project, *_get_libraries_to_push(project)]
    else:
        projects_to_push = [p.parent for p in Path.cwd().rglob(PROJECT_CONFIG_FILE_NAME)]

    push_manager = container.push_manager()
    push_manager.push_projects(projects_to_push, organization_id)

    _update_cloud_library_references(projects_to_push)
