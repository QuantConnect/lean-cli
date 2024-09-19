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
from click import command, argument, option
from lean.click import LeanCommand, PathParameter
from lean.commands.live.live import get_result, send_command


@command(cls=LeanCommand, requires_lean_config=True, requires_docker=True)
@argument("project", type=PathParameter(exists=True, file_okay=True, dir_okay=True))
@option("--data", type=str, help="The command to send, 'str' representation of a 'dict' e.g. "
                                 "\"{ \\\"target\\\": \\\"BTCUSD\\\", \\\"$type\\\":\\\"MyCommand\\\" }\"")
def command(project: Path,
            data: str) -> None:
    """
    Send a command to a local running live trading project.
    """
    data = eval(data)
    if "id" not in data:
        from uuid import uuid4
        data["id"] = uuid4().hex

    docker_container_name = send_command(project, data)
    get_result(data["id"], docker_container_name)

