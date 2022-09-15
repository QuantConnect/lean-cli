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

import click

from lean.click import LeanCommand
from lean.container import container


@click.command(cls=LeanCommand)
@click.argument("project", type=str)
def delete_project(project: str) -> None:
    """Delete a project locally and in the cloud if it exists.

    The project is selected by name or cloud id.
    """
    # Remove project from cloud
    api_client = container.api_client()
    all_projects = api_client.projects.get_all()
    project_manager = container.project_manager()
    logger = container.logger()

    project_id = None
    try:
        project_id = int(project)
    except ValueError:
        pass

    projects = []
    try:
        projects = project_manager.get_projects_by_name_or_id(all_projects, project_id or project)
    except RuntimeError:
        # If searching by id, we cannot try lo locate the project locally
        if project_id is not None:
            raise RuntimeError(f"The project with ID {project_id} was not found in the cloud.")

        # The project might only be local, look for the path
        logger.info(f"The project {project} was not found in the cloud. It will be removed locally if it exists.")

    full_project = next(iter(projects), None)

    if full_project is not None:
        api_client.projects.delete(full_project.projectId)

    # Remove project locally
    project_path = full_project.name if full_project is not None else project
    project_manager.delete_project(Path(project_path))

    logger.info(f"Successfully deleted project '{project_path}'")
