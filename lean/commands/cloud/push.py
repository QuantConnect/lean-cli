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
from typing import Optional

from click import command, option

from lean.click import LeanCommand, PathParameter
from lean.constants import PROJECT_CONFIG_FILE_NAME
from lean.container import container
from lean.models.encryption import ActionType

@command(cls=LeanCommand)
@option("--project",
        type=PathParameter(exists=True, file_okay=False, dir_okay=True),
        help="Path to the local project to push (all local projects if not specified)")
@option("--encrypt",
        is_flag=True, default=False,
        help="Push your local files and encrypt them before saving on the cloud")
@option("--decrypt",
        is_flag=True, default=False,
        help="Push your local files and decrypt them before saving on the cloud")
@option("--key",
              type=PathParameter(exists=True, file_okay=True, dir_okay=False),
              help="Path to the encryption key to use")
def push(project: Optional[Path], encrypt: Optional[bool], decrypt: Optional[bool], key: Optional[Path]) -> None:
    """Push local projects to QuantConnect.

    This command overrides the content of cloud files with the content of their respective local counterparts.

    This command will delete cloud files which don't have a local counterpart.
    """
    push_manager = container.push_manager
    encryption_action = None

    from lean.components.util.encryption_helper import validate_user_inputs_for_cloud_push_pull_commands
    validate_user_inputs_for_cloud_push_pull_commands(encrypt, decrypt, key)

    if encrypt:
        encryption_action = ActionType.ENCRYPT
    if decrypt:
        encryption_action = ActionType.DECRYPT

    # Parse which projects need to be pushed
    if project is not None:
        project_config_manager = container.project_config_manager
        project_config = project_config_manager.get_project_config(project)
        if not project_config.file.exists():
            raise RuntimeError(f"'{project}' is not a Lean project")

        if encrypt and key is not None:
            from lean.components.util.encryption_helper import validate_encryption_key_registered_with_cloud
            validate_encryption_key_registered_with_cloud(key, container.organization_manager, container.api_client) 

        push_manager.push_project(project, encryption_action, key)
    else:
        if key is not None:
            raise RuntimeError(f"Encryption key can only be specified when pushing a single project.")
        projects_to_push = [p.parent for p in Path.cwd().rglob(PROJECT_CONFIG_FILE_NAME)]
        push_manager.push_projects(projects_to_push, [], encryption_action, key)
