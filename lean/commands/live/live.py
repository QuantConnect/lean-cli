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

from typing import Any, Dict
from click import group
from lean.components.util.click_group_default_command import DefaultCommandGroup
from lean.constants import COMMAND_FILE_BASENAME, COMMAND_RESULT_FILE_BASENAME
from pathlib import Path
from lean.container import container


@group(cls=DefaultCommandGroup)
def live() -> None:
    """Interact with the local machine."""
    # This method is intentionally empty
    # It is used as the command group for all `lean cloud <command>` commands
    pass


def get_command_file_name() -> str:
    from time import time

    return Path(f'{COMMAND_FILE_BASENAME}-{int(time())}.json')


def get_result_file_name(command_id: str) -> str:
    return Path(f'{COMMAND_RESULT_FILE_BASENAME}-{command_id}.json')


def send_command(project: Path, data: Dict[str, Any]) -> str:
    """send command to the running container of the given project.

    :param project: the project path
    :param data: the data to send to the container
    :return: the name of the running docker container of the given project
    """
    from inspect import stack
    logger = container.logger
    live_dir = container.project_config_manager.get_latest_live_directory(project)
    docker_container_name = container.output_config_manager.get_container_name(Path(live_dir))
    file_name = get_command_file_name()
    logger.info(
        f"live.send_command(): {stack()[1].function} - sending command.")
    container.docker_manager.write_to_file(
        docker_container_name, file_name, data)
    return docker_container_name


def get_result(command_id: str, docker_container_name: str, container_running_required: bool = True,
               interval: int = 1, timeout: int = 30) -> None:
    """Get the result of a command.

    :param command_id: command id
    :param docker_container_name: docker container name
    :param container_running_required: should the container be alive after command execution, defaults to True
    :param interval: interval to sleep before retrying, defaults to 1
    :param timeout: time to stop trying to check for result file, defaults to 30
    :raises Exception: When the command is not executed successfully
    """
    from inspect import stack
    logger = container.logger
    logger.info(
        f"live.get_result(): {stack()[1].function} -  waiting for results...")
    result_file_path = get_result_file_name(command_id)
    result = container.docker_manager.read_from_file(
        docker_container_name, result_file_path, interval, timeout)
    if "success" in result and result["success"]:
        logger.info(
            f"live.get_result(): {stack()[1].function} - Success: The command was executed successfully")
    elif "container-running" in result and not result["container-running"]:
        if container_running_required:
            raise Exception(
                f"live.get_result(): {stack()[1].function} - Failed: The container is not running")
        else:
            logger.info(
                f"live.get_result(): {stack()[1].function} - Success: The command was executed successfully")
    else:
        raise Exception((f"live.get_result(): {stack()[1].function} - "
                        + f"Failed: to execute the command successfully. {result['error']}"))
