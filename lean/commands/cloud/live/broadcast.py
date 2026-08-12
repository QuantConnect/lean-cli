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

from lean.container import container
from click import command, option
from lean.click import LeanCommand


@command(cls=LeanCommand, name="broadcast")
@option("--data", type=str, required=True,
        help="The command to send, 'str' representation of a 'dict' e.g. "
             "\"{ \\\"target\\\": \\\"BTCUSD\\\", \\\"$type\\\":\\\"MyCommand\\\" }\"")
@option("--organization", type=str,
        help="The name or id of the organization to broadcast the command to, "
             "defaults to the organization of the current Lean CLI directory")
@option("--exclude-project", type=str,
        help="The name or id of the project to exclude from the broadcast, by default all projects are included")
def broadcast(data: str, organization: Optional[str], exclude_project: Optional[str]) -> None:
    """
    Broadcast a command to all running cloud live trading projects in an organization.
    """
    data = eval(data)

    logger = container.logger
    api_client = container.api_client

    if organization is not None:
        from lean.commands.init import _get_organization_id
        organization_id, _ = _get_organization_id(organization)
    else:
        organization_id = container.organization_manager.try_get_working_organization_id()

    exclude_project_id = None
    if exclude_project is not None:
        cloud_project_manager = container.cloud_project_manager
        exclude_project_id = cloud_project_manager.get_cloud_project(exclude_project, False).projectId

    logger.info(f"cloud.live.broadcast(): broadcasting command.")
    response = api_client.live.broadcast_command(organization_id, data, exclude_project_id)
    if response.success:
        logger.info(f"cloud.live.broadcast(): command broadcasted successfully.")
    else:
        raise Exception("cloud.live.broadcast(): Failed: to broadcast the command successfully.")
