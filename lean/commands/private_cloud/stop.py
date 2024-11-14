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
from lean.constants import PRIVATE_CLOUD
from lean.container import container


def get_private_cloud_containers(container_filter: [] = None):
    result = []
    if not container_filter:
        container_filter = [PRIVATE_CLOUD]
    for name in container_filter:
        for docker_container in container.docker_manager.get_containers_by_name(name, starts_with=True):
            result.append(docker_container)
    return result


def stop_command():
    logger = container.logger
    for docker_container in get_private_cloud_containers():
        logger.info(f'Stopping: {docker_container.name.lstrip("/")}')
        if docker_container:
            try:
                docker_container.kill()
            except:
                # might be restarting or not running
                pass
            try:
                docker_container.remove()
            except:
                # might be running with autoremove
                pass


@command(cls=LeanCommand, requires_docker=True, help="Stops a running private cloud")
def stop() -> None:
    stop_command()
