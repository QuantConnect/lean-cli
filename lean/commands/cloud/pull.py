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

from lean.click import LeanCommand
from lean.container import container
from lean.models.api import QCProject
from lean.models.utils import LeanLibraryReference


def _add_local_library_references_to_project(project: QCProject, cloud_libraries: List[QCProject]) -> None:
    logger = container.logger()
    library_manager = container.library_manager()

    if len(cloud_libraries) > 0:
        logger.info(f"Adding/updating local library references to project {project.name}")

    cwd = Path.cwd()
    project_dir = cwd / project.name
    for i, library in enumerate(cloud_libraries, start=1):
        logger.info(f"[{i}/{len(cloud_libraries)}] "
                    f"Adding/updating local library {library.name} reference to project {project.name}")
        library_manager.add_lean_library_to_project(project_dir, cwd / library.name, False)


def _remove_local_library_references_from_project(project: QCProject, cloud_libraries: List[QCProject]) -> None:
    logger = container.logger()
    library_manager = container.library_manager()

    project_dir = Path.cwd() / project.name
    project_config = container.project_config_manager().get_project_config(project_dir)
    local_libraries = project_config.get("libraries", [])
    cloud_library_paths = [Path(library.name) for library in cloud_libraries]
    libraries_to_remove = [LeanLibraryReference(**library_reference)
                           for library_reference in local_libraries
                           if Path(library_reference["path"]) not in cloud_library_paths]

    if len(libraries_to_remove) > 0:
        logger.info(f"Removing local library references from project {project.name}")

    for i, library_reference in enumerate(libraries_to_remove, start=1):
        logger.info(f"[{i}/{len(libraries_to_remove)}] "
                    f"Removing local library {library_reference.name} reference from project {project.name}")
        library_manager.remove_lean_library_from_project(project_dir, Path.cwd() / library_reference.path, False)


def _update_local_library_references(projects: List[QCProject]) -> None:
    for project in projects:
        cloud_libraries = [library
                           for library_id in project.libraries
                           for library in projects if library.projectId == library_id]

        # Add cloud library references to local config
        _add_local_library_references_to_project(project, cloud_libraries)

        # Remove library references locally if they were removed in the cloud
        _remove_local_library_references_from_project(project, cloud_libraries)


@click.command(cls=LeanCommand)
@click.option("--project", type=str, help="Name or id of the project to pull (all cloud projects if not specified)")
@click.option("--pull-bootcamp", is_flag=True, default=False, help="Pull Boot Camp projects (disabled by default)")
def pull(project: Optional[str], pull_bootcamp: bool) -> None:
    """Pull projects from QuantConnect to the local drive.

    This command overrides the content of local files with the content of their respective counterparts in the cloud.

    This command will not delete local files for which there is no counterpart in the cloud.
    """
    # Parse which projects need to be pulled
    project_id = None
    if project is not None:
        try:
            project_id = int(project)
        except ValueError:
            pass

    api_client = container.api_client()
    all_projects = api_client.projects.get_all()
    project_manager = container.project_manager()
    projects_to_pull = project_manager.get_projects_by_name_or_id(all_projects, project_id or project)

    if project is None and not pull_bootcamp:
        projects_to_pull = [p for p in projects_to_pull if not p.name.startswith("Boot Camp/")]

    pull_manager = container.pull_manager()
    pull_manager.pull_projects(projects_to_pull)

    _update_local_library_references(projects_to_pull)
