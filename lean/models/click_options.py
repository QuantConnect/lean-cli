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


from typing import List, Dict
from click import option, Choice
from lean.click import PathParameter
from lean.models.cli import cli_brokerages, cli_data_downloaders, cli_data_queue_handlers
from lean.models.cloud import cloud_brokerages, cloud_data_queue_handlers
from lean.models.configuration import Configuration, InfoConfiguration, InternalInputUserInput


def get_configs_for_options(env: str) -> List[Configuration]:
    if env == "live-cloud":
        brokerage = cloud_brokerages + cloud_data_queue_handlers
    elif env == "live-cli":
        brokerage = cli_brokerages + cli_data_queue_handlers + cli_data_downloaders
    elif env == "backtest":
        brokerage = cli_data_downloaders
    elif env == "research":
        brokerage = cli_data_downloaders
    elif env == "download":
        brokerage = cli_data_downloaders
    else:
        raise ValueError("Acceptable values for 'env' are: 'live-cloud', 'live-cli', 'backtest', 'research'")

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


def get_click_option_type(configuration: Configuration):
    # get type should be a method of configurations class itself.
    # TODO: handle input can inherit type prompt.
    if configuration._config_type == "internal-input":
        return str
    if configuration._input_method == "confirm":
        return bool
    elif configuration._input_method == "choice":
        # Skip validation if no predefined choices in config and user provided input manually
        if not configuration._choices:
            return str
        return Choice(configuration._choices, case_sensitive=False)
    elif configuration._input_method == "prompt":
        return configuration.get_input_type()
    elif configuration._input_method == "prompt-password":
        return str
    elif configuration._input_method == "path-parameter":
        return PathParameter(exists=False, file_okay=True, dir_okay=False)


def get_attribute_type(configuration: Configuration):
    # get type should be a method of configurations class itself.
    # TODO: handle input can inherit type prompt.
    if configuration._config_type == "internal-input":
        return str
    if configuration._input_method == "confirm":
        return bool
    elif configuration._input_method == "choice":
        return str
    elif configuration._input_method == "prompt":
        return configuration.get_input_type()
    elif configuration._input_method == "prompt-password":
        return str
    elif configuration._input_method == "path-parameter":
        return str


def get_options_attributes(configuration: Configuration, default_lean_config_key=None):
    options_attributes = {
        "type": get_click_option_type(configuration),
        "help": configuration._help
    }
    return options_attributes


def get_default_key(configuration: Configuration):
    return configuration._id


def options_from_json(configurations: List[Configuration]):

    def decorator(f):
        for configuration in reversed(configurations):
            long = configuration._id
            name = str(configuration._id).replace('-', '_')
            param_decls = (
                '--' + long,
                name)
            attrs = get_options_attributes(
                configuration, get_default_key(configuration))
            option(*param_decls, **attrs)(f)
        return f
    return decorator
