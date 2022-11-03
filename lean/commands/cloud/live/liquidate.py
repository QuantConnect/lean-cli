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


from click import command, argument
from lean.click import LeanCommand
from lean.container import container


@command(cls=LeanCommand)
@argument("project", type=str)
def liquidate(project: str) -> None:
    """
    Stops live trading and liquidates existing positions for a certain project.
    """
    logger = container.logger
    api_client = container.api_client

    cloud_project_manager = container.cloud_project_manager
    cloud_project = cloud_project_manager.get_cloud_project(project, False)
    logger.info(f"cloud.live.liquidate(): sending command.")
    response = api_client.live.liquidate_and_stop(cloud_project.projectId)
    if response.success:
        logger.info(f"cloud.live.liquidate(): command executed successfully.")
    else:
        raise Exception("cloud.live.liquidate(): Failed: to execute the command successfully.")
