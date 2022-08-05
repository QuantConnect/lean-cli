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
import uuid
import click
from lean.click import LeanCommand, PathParameter
from lean.commands.live.live import get_result, send_command


@click.command(cls=LeanCommand, requires_lean_config=True, requires_docker=True)
@click.argument("project", type=PathParameter(exists=True, file_okay=True, dir_okay=True))
@click.option("--ticker", type=str, required=True, help="The ticker of the symbol to liquidate")
@click.option("--market", type=str, required=True, help="The market of the symbol to liquidate")
@click.option("--security-type", type=str, required=True, help="The security type of the symbol to liquidate")
@click.option("--resolution",
              type=str,
              default="Minute",
              help="The resolution of the symbol to liquidate")
@click.option("--fill-data-forward",
              is_flag=True,
              default=False,
              help="The ticker of the symbol to liquidate")
@click.option("--leverage",
              type=float,
              default=0.0,
              help="The market of the symbol to liquidate")
@click.option("--extended-market-hours",
              is_flag=True,
              default=True,
              help="The security type of the symbol to liquidate")
def add_security(project: Path,
                 ticker: str,
                 market: str,
                 security_type: str,
                 resolution: Optional[str],
                 fill_data_forward: Optional[bool],
                 leverage: Optional[float],
                 extended_market_hours: Optional[bool]) -> None:
    """
    Represents a command to add a security to the algorithm.
    """
    command_id = uuid.uuid4().hex

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

    try:
        docker_container_name = send_command(project, data)
    except Exception as e:
        raise Exception(
            f"add_security(): Failed to send the command, error: {e}")

    try:
        get_result(command_id, docker_container_name)
    except Exception as e:
        raise Exception(f"add_security(): Error: {e}")
