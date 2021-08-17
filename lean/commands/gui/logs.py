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

import click

from lean.click import LeanCommand
from lean.constants import LOCAL_GUI_CONTAINER_NAME
from lean.container import container


@click.command(cls=LeanCommand, requires_docker=True)
@click.option("--follow", "-f",
              is_flag=True,
              default=False,
              help="Update the logs in real-time while the GUI is running")
def logs(follow: bool) -> None:
    """See the logs of the local GUI."""
    docker_manager = container.docker_manager()

    if docker_manager.get_container_by_name(LOCAL_GUI_CONTAINER_NAME) is None:
        raise RuntimeError("The local GUI container does not exist, you can start it using `lean gui start`")

    docker_manager.show_logs(LOCAL_GUI_CONTAINER_NAME, follow)
