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
@option("--ticker", type=str, required=True, help="The ticker of the symbol to be submitted")
@option("--market", type=str, required=True, help="The market of the symbol to be submitted")
@option("--security-type", required=True, type=str, help="The security type of the symbol to be submitted")
@option("--order-type", type=str, required=True, help="The order type to be submitted")
@option("--quantity", type=DECIMAL, required=True, help="The number of units to be ordered (directional)")
@option("--limit-price", type=DECIMAL, default=0.0, help="The limit price of the order be submitted")
@option("--stop-price", type=DECIMAL, default=0.0, help="The stop price of the order to be submitted")
@option("--tag", type=str, help="The tag to be attached to the order")
def submit_order(project: Path,
                 ticker: str,
                 market: str,
                 security_type: str,
                 order_type: str,
                 quantity: DECIMAL,
                 limit_price: Optional[DECIMAL],
                 stop_price: Optional[DECIMAL],
                 tag: Optional[str]) -> None:
    """
    Represents a command to submit an order to the algorithm.
    """
    from uuid import uuid4
    command_id = uuid4().hex

    data = {
        "$type": "QuantConnect.Commands.OrderCommand, QuantConnect.Common",
        "Id": command_id,
        "Ticker": ticker,
        "Market": market,
        "SecurityType": security_type,
        "OrderType": order_type,
        "Quantity": quantity,
        "LimitPrice": limit_price,
        "StopPrice": stop_price,
        "Tag": tag
    }

    docker_container_name = send_command(project, data)
    get_result(command_id, docker_container_name)
