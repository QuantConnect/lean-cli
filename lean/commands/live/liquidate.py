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
from typing import Optional
from click import command, argument, option
from lean.click import LeanCommand, PathParameter
from lean.commands.live.live import get_result, send_command


@command(cls=LeanCommand, requires_lean_config=True, requires_docker=True)
@argument("project", type=PathParameter(exists=True, file_okay=True, dir_okay=True))
@option("--ticker", type=str, help="The ticker of the symbol to liquidate")
@option("--market", type=str, help="The market of the symbol to liquidate")
@option("--security-type", type=str, default=0, help="The security type of the symbol to liquidate")
def liquidate(project: Path,
              ticker: Optional[str],
              market: Optional[str],
              security_type: Optional[str]) -> None:
    """
    Liquidate the given symbol from the latest deployment of the given project.
    """
    from uuid import uuid4
    command_id = uuid4().hex

    data = {
        "$type": "QuantConnect.Commands.LiquidateCommand, QuantConnect.Common",
        "Id": command_id,
        "Ticker": ticker,
        "Market": market,
        "SecurityType": security_type
    }

    docker_container_name = send_command(project, data)
    get_result(command_id, docker_container_name)
