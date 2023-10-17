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

from typing import Optional
from pathlib import Path
from click import command, option

from lean.click import LeanCommand, PathParameter
from lean.container import container
from lean.models.encryption import ActionType

@command(cls=LeanCommand)
@option("--project", type=str, help="Name or id of the project to pull (all cloud projects if not specified)")
@option("--pull-bootcamp", is_flag=True, default=False, help="Pull Boot Camp projects (disabled by default)")
@option("--encrypt",
        is_flag=True, default=False,
        help="Pull your cloud files and encrypt them before saving on your local drive")
@option("--decrypt",
        is_flag=True, default=False,
        help="Pull your cloud files and decrypt them before saving on your local drive")
@option("--key",
              type=PathParameter(exists=True, file_okay=True, dir_okay=False),
              help="Path to the encryption key to use")
def pull(project: Optional[str], pull_bootcamp: bool, encrypt: Optional[bool], decrypt: Optional[bool], key: Optional[Path]) -> None:
    """Pull projects from QuantConnect to the local drive.

    This command overrides the content of local files with the content of their respective counterparts in the cloud.

    This command will not delete local files for which there is no counterpart in the cloud.
    """

    encryption_action = None

    from lean.components.util.encryption_helper import validate_user_inputs_for_cloud_push_pull_commands
    validate_user_inputs_for_cloud_push_pull_commands(encrypt, decrypt, key)
    
    if encrypt:
        encryption_action = ActionType.ENCRYPT
    if decrypt:
        encryption_action = ActionType.DECRYPT

    # Parse which projects need to be pulled
    project_id = None
    project_name = None
    if project is not None:
        try:
            project_id = int(project)
        except ValueError:
            # We treat it as a name rather than an id
            project_name = project

    api_client = container.api_client
    projects_to_pull = []
    all_projects = None

    organization_id = container.organization_manager.try_get_working_organization_id()

    if project_id is not None:
        projects_to_pull.append(api_client.projects.get(project_id, organization_id))
    else:
        all_projects = api_client.projects.get_all(organization_id)
        project_manager = container.project_manager
        projects_to_pull = project_manager.get_projects_by_name_or_id(all_projects, project_name)

    if project is None and not pull_bootcamp:
        projects_to_pull = [p for p in projects_to_pull if not p.name.startswith("Boot Camp/")]

    if key is not None and len(projects_to_pull) > 1:
        raise RuntimeError(f"Cannot encrypt or decrypt more than one project at a time.")

    # the encryption key info is available when reading the project individually from API
    projects_to_pull = [api_client.projects.get(project.projectId, project.organizationId) if project.encrypted == True else project for project in projects_to_pull]

    pull_manager = container.pull_manager
    pull_manager.pull_projects(projects_to_pull, all_projects, encryption_action, key)
