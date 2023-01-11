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
from lean.models.brokerages.cloud import all_cloud_brokerages
from lean.models.brokerages.local import all_local_brokerages, all_local_data_feeds
from lean.models.data_providers import all_data_providers
from lean.models.json_module import LiveInitialStateInput, JsonModule
from lean.models.configuration import Configuration, InfoConfiguration, InternalInputUserInput

def _get_configs_for_options(env: str) -> List[Configuration]:
    if env == "cloud":
        brokerage = all_cloud_brokerages
    elif env == "local":
        brokerage = all_local_brokerages + all_local_data_feeds + all_data_providers
    else:
        raise ValueError("Only 'cloud' and 'local' are accepted for the argument 'env'")

    run_options: Dict[str, Configuration] = {}
    config_with_module_id: Dict[str, str] = {}
    for module in brokerage:
        for config in module.get_all_input_configs([InternalInputUserInput, InfoConfiguration]):
            if config._id in run_options:
                if config._id in config_with_module_id and config_with_module_id[config._id] == module._id:
                    continue
                else:
                    raise ValueError(f'Options names should be unique. Duplicate key present: {config._id}')
            run_options[config._id] = config
            config_with_module_id[config._id] = module._id
    return list(run_options.values())


def _get_last_portfolio(api_client: APIClient, project_id: str, project_name: Path) -> List[Dict[str, Any]]:
    from pytz import utc, UTC
    from os import listdir, path
    from json import loads
    from datetime import datetime

    cloud_deployment_list = api_client.get("live/read")
    cloud_deployment_time = [datetime.strptime(instance["launched"], "%Y-%m-%d %H:%M:%S").astimezone(UTC) for instance in cloud_deployment_list["live"]
                             if instance["projectId"] == project_id]
    cloud_last_time = sorted(cloud_deployment_time, reverse = True)[0] if cloud_deployment_time else utc.localize(datetime.min)

    local_last_time = utc.localize(datetime.min)
    live_deployment_path = f"{project_name}/live"
    if path.isdir(live_deployment_path):
        local_deployment_time = [datetime.strptime(subdir, "%Y-%m-%d_%H-%M-%S").astimezone().astimezone(UTC) for subdir in listdir(live_deployment_path)]
        if local_deployment_time:
            local_last_time = sorted(local_deployment_time, reverse = True)[0]

    if cloud_last_time > local_last_time:
        last_state = api_client.get("live/read/portfolio", {"projectId": project_id})
        previous_portfolio_state = last_state["portfolio"]
    elif cloud_last_time < local_last_time:
        from lean.container import container
        output_directory = container.output_config_manager.get_latest_output_directory("live")
        if not output_directory:
            return None
        previous_state_file = get_latest_result_json_file(output_directory)
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
    last_cash = []
    last_holdings = []
    cash_balance_option = brokerage_instance._initial_cash_balance
    holdings_option = brokerage_instance._initial_holdings
    if cash_balance_option != LiveInitialStateInput.NotSupported or holdings_option != LiveInitialStateInput.NotSupported:
        last_portfolio = _get_last_portfolio(api_client, project_id, project)
        last_cash = last_portfolio["cash"] if last_portfolio else None
        last_holdings = last_portfolio["holdings"] if last_portfolio else None
    return cash_balance_option, holdings_option, last_cash, last_holdings


def _configure_initial_cash_interactively(logger: Logger, cash_input_option: LiveInitialStateInput, previous_cash_state: List[Dict[str, Any]]) -> List[Dict[str, float]]:
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


def configure_initial_cash_balance(logger: Logger, cash_input_option: LiveInitialStateInput, live_cash_balance: str, previous_cash_state: List[Dict[str, Any]])\
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


def _configure_initial_holdings_interactively(logger: Logger, holdings_option: LiveInitialStateInput, previous_holdings: List[Dict[str, Any]]) -> List[Dict[str, float]]:
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


def configure_initial_holdings(logger: Logger, holdings_option: LiveInitialStateInput, live_holdings: str, previous_holdings: List[Dict[str, Any]])\
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


def get_latest_result_json_file(output_directory: Path) -> Optional[Path]:
    from lean.container import container

    output_config_manager = container.output_config_manager
    output_id = output_config_manager.get_output_id(output_directory)

    if output_id is None:
        return None

    result_file = output_directory / f"{output_id}.json"
    if not result_file.exists():
        return None

    return result_file
