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


from lean.container import container
from click import command, argument, option
from lean.click import LeanCommand


@command(cls=LeanCommand)
@argument("project", type=str)
@option("--data", type=str, help="The command to send, 'str' representation of a 'dict' e.g. "
                                 "\"{ \\\"target\\\": \\\"BTCUSD\\\", \\\"$type\\\":\\\"MyCommand\\\" }\"")
def command(project: str, data: str) -> None:
    """
    Send a command to a running cloud live trading project.
    """
    data = eval(data)

    logger = container.logger
    api_client = container.api_client

    cloud_project_manager = container.cloud_project_manager
    cloud_project = cloud_project_manager.get_cloud_project(project, False)
    logger.info(f"cloud.live.command(): sending command.")
    response = api_client.live.command_create(cloud_project.projectId, data)
    if response.success:
        logger.info(f"cloud.live.command(): command executed successfully.")
    else:
        raise Exception("cloud.live.command(): Failed: to execute the command successfully.")

