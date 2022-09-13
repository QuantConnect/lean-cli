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
from lean.click import LeanCommand, PathParameter
from lean.container import container


@click.command(cls=LeanCommand)
@click.argument("path", type=PathParameter(exists=True, file_okay=False, dir_okay=True))
def delete_project(path: Path) -> None:
    """Delete a project both locally and in remotely, if there is a counterpart in the cloud.
    """
    # Remove project from cloud
    project_config = container.project_config_manager().get_project_config(path)
    cloud_id = project_config.get("cloud-id")
    if cloud_id is not None:
        api_client = container.api_client()
        api_client.projects.delete(cloud_id)

    # Remove project locally
    project_manager = container.project_manager()
    project_manager.delete_project(path)

    logger = container.logger()
    logger.info(f"Successfully deleted project '{path}'")
