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

from click import prompt, confirm

from pathlib import Path
from typing import Any, Dict, List, Optional
from lean.components.api.api_client import APIClient
from lean.components.util.logger import Logger
from lean.models.json_module import LiveInitialStateInput, JsonModule
from collections import UserDict


class InsensitiveCaseDict(UserDict):
    def __getitem__(self, key: Any) -> Any:
        if type(key) is str:
            return super().__getitem__(key.lower())
        return super().__getitem__(key)

    def __setitem__(self, key: Any, item: Any) -> Any:
        if type(key) is str:
            self.data[key.lower()] = item
            return
        self.data[key] = item


def _get_last_portfolio(api_client: APIClient, project_id: str, project_name: Path) -> List[Dict[str, Any]]:
    from pytz import utc, UTC
    from os import listdir, path
    from json import loads
    from datetime import datetime

    cloud_last_time = utc.localize(datetime.min)
    if project_id:
        cloud_deployment = api_client.get("live/read", {"projectId": project_id})
        if cloud_deployment["success"] and cloud_deployment["status"] != "Undefined":
            if cloud_deployment["stopped"] is not None:
                cloud_last_time = datetime.strptime(cloud_deployment["stopped"], "%Y-%m-%d %H:%M:%S")
            else:
                cloud_last_time = datetime.strptime(cloud_deployment["launched"], "%Y-%m-%d %H:%M:%S")
    cloud_last_time = datetime(cloud_last_time.year, cloud_last_time.month,
                               cloud_last_time.day, cloud_last_time.hour,
                               cloud_last_time.minute,
                               cloud_last_time.second,
                               tzinfo=UTC)

    local_last_time = utc.localize(datetime.min)
    live_deployment_path = f"{project_name}/live"
    if path.isdir(live_deployment_path):
        local_deployment_time = [datetime.strptime(subdir, "%Y-%m-%d_%H-%M-%S").astimezone().astimezone(UTC) for subdir in listdir(live_deployment_path)]
        if local_deployment_time:
            local_last_time = sorted(local_deployment_time, reverse = True)[0]

    if cloud_last_time > local_last_time:
        last_state = api_client.get("live/portfolio/read", {"projectId": project_id})
        previous_portfolio_state = last_state["portfolio"]
    elif cloud_last_time < local_last_time:
        from lean.container import container
        output_directory = container.output_config_manager.get_latest_output_directory("live")
        if not output_directory:
            return None
        previous_state_file = get_latest_result_json_file(output_directory, True)
        if not previous_state_file:
            return None
        previous_portfolio_state = {x.lower(): y for x, y in loads(open(previous_state_file, "r", encoding="utf-8").read()).items()}
    else:
        return None

    return previous_portfolio_state


def get_last_portfolio_cash_holdings(api_client: APIClient, brokerage_instance: JsonModule, project_id: int, project: str):
    """Interactively obtain the portfolio state from the latest live deployment (both cloud/local)

    :param api_client: the api instance
    :param brokerage_instance: the brokerage
    :param project_id: the cloud id of the project
    :param project: the name of the project
    :return: the options of initial cash/holdings setting, and the latest portfolio cash/holdings from the last deployment
    """
    from lean.container import container
    last_cash = {}
    last_holdings = {}
    container.logger.debug(f'brokerage_instance: {brokerage_instance}')
    cash_balance_option = brokerage_instance._initial_cash_balance
    holdings_option = brokerage_instance._initial_holdings
    container.logger.debug(f'cash_balance_option: {cash_balance_option}')
    container.logger.debug(f'holdings_option: {holdings_option}')
    if cash_balance_option != LiveInitialStateInput.NotSupported or holdings_option != LiveInitialStateInput.NotSupported:
        last_portfolio = _get_last_portfolio(api_client, project_id, project)
        if last_portfolio is not None:
            if "cash" in last_portfolio:
                for key, value in last_portfolio["cash"].items():
                    last_cash[key] = InsensitiveCaseDict(value)
            if "holdings" in last_portfolio:
                for key, value in last_portfolio["holdings"].items():
                    new_dic = InsensitiveCaseDict(value)
                    new_dic["averagePrice"] = new_dic.get("averagePrice", new_dic.get("a",  0))
                    new_dic["quantity"] = new_dic.get("quantity", new_dic.get("q",  0))
                    new_dic["symbol"] = InsensitiveCaseDict(
                        new_dic.get("symbol", { "ID": key, "Value": key.split(' ')[0]}))
                    last_holdings[key] = new_dic
        else:
            last_cash = None
            last_holdings = None
    return cash_balance_option, holdings_option, last_cash, last_holdings


def _configure_initial_cash_interactively(logger: Logger, cash_input_option: LiveInitialStateInput, previous_cash_state: Dict[str, Any]) -> List[Dict[str, float]]:
    cash_list = []
    previous_cash_balance = []
    if previous_cash_state:
        for cash_state in previous_cash_state.values():
            currency = cash_state["Symbol"]
            amount = cash_state["Amount"]
            previous_cash_balance.append({"currency": currency, "amount": amount})

    if cash_input_option == LiveInitialStateInput.Required or confirm("Do you want to set the initial cash balance?", default=False):
        if confirm(f"Do you want to use the last cash balance? {previous_cash_balance}", default=False):
            return previous_cash_balance

        continue_adding = True
        while continue_adding:
            logger.info("Setting initial cash balance...")
            currency = prompt("Currency")
            amount = prompt("Amount", type=float)
            cash_list.append({"currency": currency, "amount": amount})

            logger.info(f"Cash balance: {cash_list}")
            if not confirm("Do you want to add more currency?", default=False):
                continue_adding = False
        return cash_list

    else:
        return []


def configure_initial_cash_balance(logger: Logger, cash_input_option: LiveInitialStateInput, live_cash_balance: str, previous_cash_state: Dict[str, Any])\
    -> List[Dict[str, float]]:
    """Interactively configures the intial cash balance.

    :param logger: the logger to use
    :param cash_input_option: if the initial cash balance setting is optional/required
    :param live_cash_balance: the initial cash balance option input
    :param previous_cash_state: the dictionary containing cash balance in previous portfolio state
    :return: the list of dictionary containing intial currency and amount information
    """
    cash_list = []
    if live_cash_balance or cash_input_option != LiveInitialStateInput.Required:
        for cash_pair in [x for x in live_cash_balance.split(",") if x]:
            currency, amount = cash_pair.split(":")
            cash_list.append({"currency": currency, "amount": float(amount)})
        return cash_list
    else:
        return _configure_initial_cash_interactively(logger, cash_input_option, previous_cash_state)


def _configure_initial_holdings_interactively(logger: Logger, holdings_option: LiveInitialStateInput, previous_holdings: Dict[str, Any]) -> List[Dict[str, float]]:
    holdings = []
    last_holdings = []
    if previous_holdings:
        for holding in previous_holdings.values():
            symbol = holding["Symbol"]
            quantity = int(holding["Quantity"])
            avg_price = float(holding["AveragePrice"])
            last_holdings.append({"symbol": symbol["Value"], "symbolId": symbol["ID"], "quantity": quantity, "averagePrice": avg_price})

    if holdings_option == LiveInitialStateInput.Required or confirm("Do you want to set the initial portfolio holdings?", default=False):
        if confirm(f"Do you want to use the last portfolio holdings? {last_holdings}", default=False):
            return last_holdings

        continue_adding = True
        while continue_adding:
            logger.info("Setting custom initial portfolio holdings...")
            symbol = prompt("Symbol")
            symbol_id = prompt("Symbol ID")
            quantity = prompt("Quantity", type=int)
            avg_price = prompt("Average Price", type=float)
            holdings.append({"symbol": symbol, "symbolId": symbol_id, "quantity": quantity, "averagePrice": avg_price})

            logger.info(f"Portfolio Holdings: {holdings}")
            if not confirm("Do you want to add more holdings?", default=False):
                continue_adding = False
        return holdings

    else:
        return []


def configure_initial_holdings(logger: Logger, holdings_option: LiveInitialStateInput, live_holdings: str, previous_holdings: Dict[str, Any])\
    -> List[Dict[str, float]]:
    """Interactively configures the intial portfolio holdings.

    :param logger: the logger to use
    :param holdings_option: if the initial portfolio holdings setting is optional/required
    :param live_holdings: the initial portfolio holdings option input
    :param previous_holdings: the dictionary containing portfolio holdings in previous portfolio state
    :return: the list of dictionary containing intial symbol, symbol id, quantity, and average price information
    """
    holdings = []
    if live_holdings or holdings_option != LiveInitialStateInput.Required:
        for holding in [x for x in live_holdings.split(",") if x]:
            symbol, symbol_id, quantity, avg_price = holding.split(":")
            holdings.append({"symbol": symbol, "symbolId": symbol_id, "quantity": int(quantity), "averagePrice": float(avg_price)})
        return holdings
    else:
        return _configure_initial_holdings_interactively(logger, holdings_option, previous_holdings)


def get_latest_result_json_file(output_directory: Path, is_live_trading: bool = False) -> Optional[Path]:
    from lean.container import container

    output_config_manager = container.output_config_manager
    output_id = output_config_manager.get_output_id(output_directory)

    if output_id is None:
        return None

    prefix = ""
    if is_live_trading:
        prefix = "L-"

    result_file = output_directory / f"{prefix}{output_id}.json"
    if not result_file.exists():
        return None

    return result_file
