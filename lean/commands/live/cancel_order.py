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
import uuid
import click
from lean.click import LeanCommand, PathParameter
from lean.container import container
from lean.constants import COMMANDS_FILE_PATH, COMMAND_FILE_BASENAME, COMMAND_RESULT_FILE_BASENAME
import time


@click.command(cls=LeanCommand, requires_lean_config=True, requires_docker=True)
@click.argument("project", type=PathParameter(exists=True, file_okay=True, dir_okay=True))
@click.option("--order-id",
              type=str,
              required=True,
              help="The order id to be cancelled")
def cancel_order(project: Path,
              order_id: str) -> None:
    """
    Represents a command to cancel a specific order by id.
    """
    logger = container.logger()
    live_dir = container.project_config_manager().get_latest_live_directory(project)
    docker_container_name = container.output_config_manager(
    ).get_container_name(Path(live_dir))
    command_id = uuid.uuid4().hex
    data = {
            "$type": "QuantConnect.Commands.CancelOrderCommand, QuantConnect.Common",
            "Id": command_id,
            "OrderId": order_id
        }
    file_name = COMMANDS_FILE_PATH / f'{COMMAND_FILE_BASENAME}-{int(time.time())}.json'
    try:
        logger.info(
            f"cancel_order(): sending command.")
        container.docker_manager().write_to_file(
            docker_container_name, file_name, data)
    except Exception as e:
        logger.error(f"cancel_order(): Failed to send the command, error: {e}")
        return
    # Check for result
    logger.info("cancel_order(): waiting for results...")
    result_file_path = COMMANDS_FILE_PATH / f'{COMMAND_RESULT_FILE_BASENAME}-{command_id}.json'
    result = container.docker_manager().read_from_file(
        docker_container_name, result_file_path)
    if "success" in result and result["success"]:
        logger.info(
            "cancel_order(): Success: The command was executed successfully")
    elif "container-running" in result and not result["container-running"]:
        logger.info("liquidate(): Failed: The container is not running")
    else:
        logger.info(
            f"cancel_order(): Failed: to execute the command successfully. {result['error']}")
