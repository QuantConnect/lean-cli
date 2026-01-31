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

from click import command

from lean.click import LeanCommand
from lean.container import container


@command(cls=LeanCommand, name="list")
def list_projects() -> None:
    """List all projects in the data server.

    This command lists all LEAN projects stored in the data server database.
    """
    logger = container.logger
    data_server_client = container.data_server_client

    if data_server_client is None:
        raise RuntimeError(
            "Data server is not configured. "
            "Please run 'lean login --url <data-server-url> --api-key <api-key>' first."
        )

    projects = data_server_client.list_projects()

    if not projects:
        logger.info("No projects found in the data server.")
        return

    logger.info(f"Found {len(projects)} project(s) in the data server:\n")

    for project in projects:
        logger.info(f"  {project.name}")
        logger.info(f"    ID: {project.id}")
        logger.info(f"    Language: {project.algorithm_language}")
        if project.description:
            logger.info(f"    Description: {project.description}")
        logger.info(f"    Created: {project.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info(f"    Updated: {project.updated_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info("")
