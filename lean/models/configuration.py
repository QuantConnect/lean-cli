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
import re
from typing import Any, Dict, Optional
import click
import abc
from lean.components.util.logger import Logger
from lean.click import PathParameter
        
class RegexOptionCondition():

    def __init__(self, condition_object: Dict[str, Any]):
        self._type = condition_object["type"]
        self._pattern = str(condition_object["pattern"])
        self._dependent_config_id = condition_object["dependent-config-id"]

    def check(self, target_value: str) -> bool:
        return len(re.findall(self._pattern, target_value, re.I)) > 0

class ConditionalValueOption():

    def __init__(self, option_object: Dict[str, Any]):
        self._value = option_object["value"]
        self._condition = RegexOptionCondition(option_object["condition"])

class Configuration(abc.ABC):
    def __init__(self, config_json_object):
        self._name = config_json_object["Name"]
        self._config_type = config_json_object["Type"]
        self._value = config_json_object["Value"]
        self._filter = Filter(config_json_object["Environment"])
        self._is_type_configurations_env = type(self) is ConfigurationsEnvConfiguration
        self._is_type_trading_env = type(self) is TradingEnvConfiguration
        self._log_message = None
        if "Log-message" in config_json_object.keys():
            self._log_message = config_json_object["Log-message"]

    @abc.abstractmethod
    def is_required_from_user(self):
        return NotImplemented()

    def factory(config_json_object):
        if config_json_object["Type"] in ["info" , "configurations-env"]:
            return InfoConfiguration.factory(config_json_object)
        elif config_json_object["Type"] in ["input","internal-input"]:
            return UserInputConfiguration.factory(config_json_object)
        elif config_json_object["Type"] in ["filter-env" , "trading-env"]:
            return BrokerageEnvConfiguration.factory(config_json_object)
        else:
            raise(f'Undefined input method type {config_json_object["Type"]}')

class Filter():
    def __init__(self, filter_environments):
        self._options = filter_environments

class InfoConfiguration(Configuration):
    def __init__(self, config_json_object):
        super().__init__(config_json_object)

    def factory(config_json_object):
        if config_json_object["Type"] == "configurations-env":
            return ConfigurationsEnvConfiguration(config_json_object)
        else:
            return InfoConfiguration(config_json_object)

    def is_required_from_user(self):
        return False
 
class ConfigurationsEnvConfiguration(InfoConfiguration):
    def __init__(self, config_json_object):
        super().__init__(config_json_object)
        self._env_and_values = {env_obj["Name"]:env_obj["Value"] for env_obj in self._value}

class UserInputConfiguration(Configuration, abc.ABC):
    def __init__(self, config_json_object):
        super().__init__(config_json_object)
        self._input_method = config_json_object["Input-method"]
        self._input_data = config_json_object["Input-data"]
        self._help = config_json_object["Help"]
        self._input_default = None
        self._cloud_name = None
        if "Input-default" in config_json_object.keys():
            self._input_default = config_json_object["Input-default"]
        if "Cloud-Name" in config_json_object.keys():
            self._cloud_name = config_json_object["Cloud-Name"]

    @abc.abstractmethod
    def AskUserForInput(self, default_value):
        return NotImplemented()

    def factory(config_json_object):
        # Check "Type" before "Input-method"
        if config_json_object["Type"] == "internal-input":
            return InternalInputUserInput(config_json_object)
        if config_json_object["Input-method"] == "prompt":
            return PromptUserInput(config_json_object)
        elif config_json_object["Input-method"] == "choice":
            return ChoiceUserInput(config_json_object)
        elif config_json_object["Input-method"] == "confirm":
            return ConfirmUserInput(config_json_object)
        elif config_json_object["Input-method"] == "prompt-password":
            return PromptPasswordUserInput(config_json_object)
        elif config_json_object["Input-method"] == "path-parameter":
            return PathParameterUserInput(config_json_object)

    def is_required_from_user(self):
        return True

class InternalInputUserInput(UserInputConfiguration):

    def __init__(self, config_json_object):
        super().__init__(config_json_object)
        value_options = [ConditionalValueOption(value_option) for value_option in config_json_object["Value-options"]]
        self._value_options = value_options

    def AskUserForInput(self, default_value, logger: Logger):
        raise ValueError(f'user input not allowed with {self.__class__.__name__}')

class PromptUserInput(UserInputConfiguration):
    map_to_types = {
        "string": str,
        "boolean": bool,
        "integer": int
    }

    def __init__(self, config_json_object):
        super().__init__(config_json_object)
        self._input_type = "string"
        if "Input-type" in config_json_object.keys():
            self._input_type = config_json_object["Input-type"]

    def AskUserForInput(self, default_value, logger: Logger):
        return click.prompt(self._input_data, default_value, type=self.get_input_type())

    def get_input_type(self):
        return self.map_to_types.get(self._input_type, self._input_type)

class ChoiceUserInput(UserInputConfiguration):
    def __init__(self, config_json_object):
        super().__init__(config_json_object)
        if "Input-choices" in config_json_object.keys():
            self._choices = config_json_object["Input-choices"]
        else:
            self._choices = []

    def AskUserForInput(self, default_value, logger: Logger):
        return click.prompt(
                    self._input_data,
                    default_value,
                    type=click.Choice(self._choices, case_sensitive=False)
                )

class PathParameterUserInput(UserInputConfiguration):
    def __init__(self, config_json_object):
        super().__init__(config_json_object)

    def AskUserForInput(self, default_value, logger: Logger):

        default_binary = None
        if default_value is not None:
            default_binary = Path(default_value)
        elif self._input_default is not None and Path(self._input_default).is_file():
            default_binary = Path(self._input_default)
        value = click.prompt(self._input_data,
                    type=PathParameter(exists=True, file_okay=True, dir_okay=False),
                    default=default_binary
                )
        if not value:
            str(value).replace("\\", "/")
        return value

class ConfirmUserInput(UserInputConfiguration):
    def __init__(self, config_json_object):
        super().__init__(config_json_object)

    def AskUserForInput(self, default_value, logger: Logger):
        return click.confirm(self._input_data)

class PromptPasswordUserInput(UserInputConfiguration):
    def __init__(self, config_json_object):
        super().__init__(config_json_object)

    def AskUserForInput(self, default_value, logger: Logger):
        return logger.prompt_password(self._input_data, default_value)


class BrokerageEnvConfiguration(PromptUserInput, ChoiceUserInput, ConfirmUserInput):
    def __init__(self, config_json_object):
        super().__init__(config_json_object)
    
    def factory(config_json_object):
        if config_json_object["Type"] == "trading-env":
            return TradingEnvConfiguration(config_json_object)
        elif config_json_object["Type"] == "filter-env":
            return FilterEnvConfiguration(config_json_object)
        else:
            raise(f'Undefined input method type {config_json_object["Type"]}')

    def AskUserForInput(self, default_value, logger: Logger):
        if self._input_method == "confirm":
            return ConfirmUserInput.AskUserForInput(self, default_value, logger)
        elif self._input_method == "choice":
            return ChoiceUserInput.AskUserForInput(self, default_value, logger)
        elif self._input_method == "prompt":
            return PromptUserInput.AskUserForInput(self, default_value, logger)
        else:
            raise(f"Undefined input method type {self._input_method}")
    

class TradingEnvConfiguration(BrokerageEnvConfiguration):
    def __init__(self, config_json_object):
        super().__init__(config_json_object)
    
    def AskUserForInput(self, default_value, logger: Logger):
        if self._input_method == "confirm":
            raise ValueError(f'input method -- {self._input_method} is not allowed with {self.__class__.__name__}')
        else:
            return BrokerageEnvConfiguration.AskUserForInput(self, default_value, logger)

class FilterEnvConfiguration(BrokerageEnvConfiguration):
    def __init__(self, config_json_object):
        super().__init__(config_json_object)