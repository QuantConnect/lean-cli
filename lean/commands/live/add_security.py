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
from lean.components.util.click_custom_parameters import DECIMAL

@command(cls=LeanCommand, requires_lean_config=True, requires_docker=True)
@argument("project", type=PathParameter(exists=True, file_okay=True, dir_okay=True))
@option("--ticker", type=str, required=True, help="The ticker of the symbol to add")
@option("--market", type=str, required=True, help="The market of the symbol to add")
@option("--security-type", type=str, required=True, help="The security type of the symbol to add")
@option("--resolution",
              type=str,
              default="Minute",
              help="The resolution of the symbol to add")
@option("--fill-data-forward",
              is_flag=True,
              default=True,
              help="The fill forward behavior, true to fill forward, false otherwise - defaults to true")
@option("--leverage",
              type=DECIMAL,
              default=0.0,
              help="The leverage for the security, defaults to 2 for equity, 50 for forex, and 1 for everything else")
@option("--extended-market-hours",
              is_flag=True,
              default=False,
              help="The extended market hours flag, true to allow pre/post market data, false for only in market data")
def add_security(project: Path,
                 ticker: str,
                 market: str,
                 security_type: str,
                 resolution: Optional[str],
                 fill_data_forward: Optional[bool],
                 leverage: Optional[DECIMAL],
                 extended_market_hours: Optional[bool]) -> None:
    """
    Represents a command to add a security to the algorithm.
    """
    from uuid import uuid4
    command_id = uuid4().hex

    data = {
        "$type": "QuantConnect.Commands.AddSecurityCommand, QuantConnect.Common",
        "Id": command_id,
        "Symbol": ticker,
        "Market": market,
        "SecurityType": security_type,
        "Resolution": resolution,
        "FillDataForward": fill_data_forward,
        "Leverage": leverage,
        "ExtendedMarketHours": extended_market_hours
    }

    docker_container_name = send_command(project, data)
    get_result(command_id, docker_container_name)
