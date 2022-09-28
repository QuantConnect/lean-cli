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
from pathlib import Path
from typing import Any, Dict, List
from lean.components.util.logger import Logger
from lean.models.brokerages.cloud import all_cloud_brokerages
from lean.models.brokerages.local import all_local_brokerages, all_local_data_feeds
from lean.models.data_providers import all_data_providers
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


def _configure_initial_cash_balance(logger: Logger, live_cash_balance: str, previous_cash_state: List[Dict[str, Any]]) -> List[Dict[str, float]]:
    """Interactively configures the intial cash balance.

    :param logger: the logger to use
    :param live_cash_balance: the initial cash balance option input
    :param previous_cash_state: the dictionary containing cash balance in previous portfolio state
    :return: the list of dictionary containing intial currency and amount information
    """
    cash_list = []
    previous_cash_balance = []
    for cash_state in previous_cash_state.values():
        currency = cash_state["Symbol"]
        amount = cash_state["Amount"]
        previous_cash_balance.append({"currency": currency, "amount": amount})
    
    if live_cash_balance is not None and live_cash_balance != "":
        for cash_pair in live_cash_balance.split(","):
            currency, amount = cash_pair.split(":")
            cash_list.append({"currency": currency, "amount": float(amount)})
        
    elif click.confirm(f"Do you want to set initial cash balance? {previous_cash_balance}", default=False):
        continue_adding = True
    
        while continue_adding:
            currency = click.prompt("Currency")
            amount = click.prompt("Amount", type=float)
            cash_list.append({"currency": currency, "amount": amount})
            logger.info(f"Cash balance: {cash_list}")
            
            if not click.confirm("Do you want to add other currency?", default=False):
                continue_adding = False
                
    else:
        cash_list = previous_cash_balance
            
    return cash_list


def get_state_json(environment: str):
    backtest_json_files = list(Path.cwd().rglob(f"{environment}/*/*.json"))
    result_json_files = [f for f in backtest_json_files if
                            not f.name.endswith("-order-events.json") and not f.name.endswith("alpha-results.json") and not f.name.endswith("minute.json")]

    if len(result_json_files) == 0:
        return None

    return sorted(result_json_files, key=lambda f: f.stat().st_mtime, reverse=True)[0]