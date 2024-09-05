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
from click import command, option, argument

from lean.click import LeanCommand, PathParameter
from lean.container import container


@command(cls=LeanCommand)
@argument("project", type=PathParameter(exists=True, file_okay=False, dir_okay=True))
@option("--key",
              type=PathParameter(exists=True, file_okay=True, dir_okay=False),
              help="Path to the decryption key to use")
def decrypt(project: Path,
            key: Optional[Path]) -> None:
    """Decrypt your local project using the specified decryption key."""
    
    logger = container.logger
    project_manager = container.project_manager
    project_config_manager = container.project_config_manager
    project_config = project_config_manager.get_project_config(project)

    # Check if the project is already decrypted
    if not project_config.get("encrypted", False):
        logger.info(f"Successfully decrypted project {project}")
        return

    decryption_key: Path = project_config.get('encryption-key-path', None)
    from lean.components.util.encryption_helper import get_and_validate_user_input_encryption_key
    decryption_key = get_and_validate_user_input_encryption_key(key, decryption_key)

    organization_id = container.organization_manager.try_get_working_organization_id()

    source_files = project_manager.get_source_files(project)
    try:
        from lean.components.util.encryption_helper import get_decrypted_file_content_for_local_project
        decrypted_data = get_decrypted_file_content_for_local_project(project,
                                source_files, decryption_key, project_config_manager, organization_id)
    except Exception as e:
        raise RuntimeError(f"Could not decrypt project {project}: {e}")

    for file, decrypted in zip(source_files, decrypted_data):
        with open(file, 'w', encoding="utf-8") as f:
            f.write(decrypted)

    # Mark the project as decrypted
    project_config.set('encrypted', False)
    project_config.delete('encryption-key-path')
    logger.info(f"Successfully decrypted project {project}")
