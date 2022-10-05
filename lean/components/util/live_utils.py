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
from datetime import datetime
import json
from pathlib import Path
import pytz
import os
from typing import Any, Dict, List
from lean.components.api.api_client import APIClient
from lean.components.util.logger import Logger
from lean.models.brokerages.cloud import all_cloud_brokerages
from lean.models.brokerages.local import all_local_brokerages, all_local_data_feeds
from lean.models.data_providers import all_data_providers
from lean.models.json_module import LiveCashBalanceInput
from lean.models.configuration import Configuration, InfoConfiguration, InternalInputUserInput
from lean.models.lean_config_configurer import LeanConfigConfigurer

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
                if (config._id in config_with_module_id 
                    and config_with_module_id[config._id] == module._id):
                    # config of same module
                    continue
                else:
                    raise ValueError(f'Options names should be unique. Duplicate key present: {config._id}')
            run_options[config._id] = config
            config_with_module_id[config._id] = module._id
    return list(run_options.values())


def get_latest_cash_state(api_client: APIClient, project_id: str, project_name: Path) -> List[Dict[str, Any]]:
    cloud_deployment_list = api_client.get("live/read")
    cloud_deployment_time = [datetime.strptime(instance["launched"], "%Y-%m-%d %H:%M:%S").astimezone(pytz.UTC) for instance in cloud_deployment_list["live"] 
                             if instance["projectId"] == project_id]
    cloud_last_time = sorted(cloud_deployment_time, reverse = True)[0] if cloud_deployment_time else pytz.utc.localize(datetime.min)
    
    local_last_time = pytz.utc.localize(datetime.min)
    live_deployment_path = f"{project_name}/live"
    if os.path.isdir(live_deployment_path):
        local_deployment_time = [datetime.strptime(subdir, "%Y-%m-%d_%H-%M-%S").astimezone().astimezone(pytz.UTC) for subdir in os.listdir(live_deployment_path)]
        if local_deployment_time:
            local_last_time = sorted(local_deployment_time, reverse = True)[0]
    
    if cloud_last_time > local_last_time:
        last_state = api_client.get("live/read/portfolio", {"projectId": project_id})
        previous_cash_state = last_state["portfolio"]["cash"] if last_state and "cash" in last_state["portfolio"] else None
    elif cloud_last_time < local_last_time:
        previous_state_file = get_state_json("live")
        if not previous_state_file:
            return None
        previous_portfolio_state = json.loads(open(previous_state_file).read())
        previous_cash_state = previous_portfolio_state["Cash"] if previous_portfolio_state else None
    else:
        return None
    
    return previous_cash_state


def configure_initial_cash_balance(logger: Logger, cash_input_option: LiveCashBalanceInput, live_cash_balance: str, previous_cash_state: List[Dict[str, Any]])\
    -> List[Dict[str, float]]:
    """Interactively configures the intial cash balance.

    :param logger: the logger to use
    :param cash_input_option: if the initial cash balance setting is optional/required
    :param live_cash_balance: the initial cash balance option input
    :param previous_cash_state: the dictionary containing cash balance in previous portfolio state
    :return: the list of dictionary containing intial currency and amount information
    """
    cash_list = []
    previous_cash_balance = []
    if previous_cash_state:
        for cash_state in previous_cash_state.values():
            currency = cash_state["Symbol"]
            amount = cash_state["Amount"]
            previous_cash_balance.append({"currency": currency, "amount": amount})
    
    if live_cash_balance is not None and live_cash_balance != "":
        for cash_pair in live_cash_balance.split(","):
            currency, amount = cash_pair.split(":")
            cash_list.append({"currency": currency, "amount": float(amount)})
            
    elif (cash_input_option == LiveCashBalanceInput.Required and not previous_cash_balance)\
    or click.confirm(f"""Previous cash balance: {previous_cash_balance}
Do you want to set a different initial cash balance?""", default=False):
        continue_adding = True
    
        while continue_adding:
            logger.info("Setting initial cash balance...")
            currency = click.prompt("Currency")
            amount = click.prompt("Amount", type=float)
            cash_list.append({"currency": currency, "amount": amount})
            logger.info(f"Cash balance: {cash_list}")
            
            if not click.confirm("Do you want to add more currency?", default=False):
                continue_adding = False
                
    else:
        cash_list = previous_cash_balance
            
    return cash_list


def _filter_json_name_backtest(file: Path) -> bool:
    return not file.name.endswith("-order-events.json") and not file.name.endswith("alpha-results.json")


def _filter_json_name_live(file: Path) -> bool:
    return file.name.replace("L-", "", 1).replace(".json", "").isdigit()    # The json should have name like "L-1234567890.json"


def get_state_json(environment: str) -> str:
    json_files = list(Path.cwd().rglob(f"{environment}/*/*.json"))
    name_filter = _filter_json_name_backtest if environment == "backtests" else _filter_json_name_live
    filtered_json_files = [f for f in json_files if name_filter(f)]

    if len(filtered_json_files) == 0:
        return None

    return sorted(filtered_json_files, key=lambda f: f.stat().st_mtime, reverse=True)[0]