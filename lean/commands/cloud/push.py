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
from lean.components.util.encryption_helper import get_project_key_hash
from lean.models.encryption import ActionType

@command(cls=LeanCommand)
@option("--project",
        type=PathParameter(exists=True, file_okay=False, dir_okay=True),
        help="Path to the local project to push (all local projects if not specified)")
@option("--encrypt",
        is_flag=True, default=False,
        help="Encrypt your cloud files with a key")
@option("--decrypt",
        is_flag=True, default=False,
        help="Decrypt your cloud files with a key")
@option("--key",
              type=PathParameter(exists=True, file_okay=True, dir_okay=False),
              help="Path to the encryption key to use")
def push(project: Optional[Path], encrypt: Optional[bool], decrypt: Optional[bool], key: Optional[Path]) -> None:
    """Push local projects to QuantConnect.

    This command overrides the content of cloud files with the content of their respective local counterparts.

    This command will delete cloud files which don't have a local counterpart.
    """
    push_manager = container.push_manager
    encryption_key_id = None
    encryption_action = None

    if encrypt and decrypt:
        raise RuntimeError(f"Cannot encrypt and decrypt at the same time.")
    if key is None and (encrypt or decrypt):
        raise RuntimeError(f"Encryption key is required when encrypting or decrypting.")

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
            # lets check if the given key is registered with the cloud
            organization_id = container.organization_manager.try_get_working_organization_id()
            available_encryption_keys = container.api_client.encryption_keys.list(organization_id)['keys']
            encryption_key_id = get_project_key_hash(key)
            if (not any(found_key for found_key in available_encryption_keys if found_key['hash'] == encryption_key_id)):
                raise RuntimeError(f"Given encryption key is not registered with the cloud.")
        
        push_manager.push_project(project, encryption_action, key)
    else:
        if key is not None:
            raise RuntimeError(f"Encryption key can only be specified when pushing a single project.")
        projects_to_push = [p.parent for p in Path.cwd().rglob(PROJECT_CONFIG_FILE_NAME)]
        push_manager.push_projects(projects_to_push, encryption_action, key)
