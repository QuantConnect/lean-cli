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
from typing import Any, Dict, List
from click import prompt, Choice
from abc import ABC, abstractmethod
from lean.components.util.logger import Logger
from lean.click import PathParameter


class BaseCondition(ABC):
    """Base condition class extended to all types of conditions"""

    def __init__(self, condition_object: Dict[str, str]):
        self._type: str = condition_object["type"]
        self._pattern: str = str(condition_object["pattern"])
        self._dependent_config_id: str = condition_object["dependent-config-id"]

    def factory(condition_object: Dict[str, str]) -> 'BaseCondition':
        """Creates an instance of the child classes.

        :param condition_object: the json object dict with condition info
        :raises ValueError: When the wrong condition type is provided
        :return: An instance of BaseCondition
        """
        if condition_object["type"] == "regex":
            return RegexCondition(condition_object)
        elif condition_object["type"] == "exact-match":
            return ExactMatchCondition(condition_object)
        else:
            raise ValueError(
                f'Undefined condition type {condition_object["type"]}')

    @abstractmethod
    def check(self, target_value: str) -> bool:
        """validates the condition against the provided values

        :param target_value: value to validate the condition against
        :return: True if the condition is valid otherwise False
        """
        raise NotImplementedError()


class ExactMatchCondition(BaseCondition):
    """This class is used when the condition needs to be evaluated with equality"""

    def check(self, target_value: str) -> bool:
        """validates the condition against the provided values

        :param target_value: value to validate the condition against
        :return: True if the condition is valid otherwise False
        """
        return self._pattern.casefold() == target_value.casefold()


class RegexCondition(BaseCondition):
    """This class is used when the condition needs to be evaluated using regex"""

    def check(self, target_value: str) -> bool:
        """validates the condition against the provided values

        :param target_value: value to validate the condition against
        :return: True if the condition is valid otherwise False
        """
        from re import findall, I
        return len(findall(self._pattern, target_value, I)) > 0


class ConditionalValueOption():
    """This class is used when mutliple values needs to be evaluated based on conditions."""

    def __init__(self, option_object: Dict[str, Any]):
        self._value: str = option_object["value"]
        self._condition: BaseCondition = BaseCondition.factory(
            option_object["condition"])


class Configuration(ABC):
    """Base configuration class extended to all types of configurations"""

    def __init__(self, config_json_object):
        self._id: str = config_json_object["id"]
        self._config_type: str = config_json_object["type"]
        self._value: str = config_json_object["value"]
        self._is_cloud_property: bool = "cloud-id" in config_json_object
        self._is_required_from_user = False
        self._save_persistently_in_lean = False
        self._is_type_configurations_env: bool = type(
            self) is ConfigurationsEnvConfiguration
        self._is_type_trading_env: bool = type(self) is TradingEnvConfiguration
        self._log_message: str = ""
        if "log-message" in config_json_object.keys():
            self._log_message = config_json_object["log-message"]
        if "filters" in config_json_object.keys():
            self._filter = Filter(config_json_object["filters"])
        else:
            self._filter = Filter([])

    def factory(config_json_object) -> 'Configuration':
        """Creates an instance of the child classes.

        :param config_json_object: the json object dict with configuration info
        :raises ValueError: When the wrong configuration type is provided.
        :return: An instance of Configuration.
        """

        if config_json_object["type"] in ["info", "configurations-env"]:
            return InfoConfiguration.factory(config_json_object)
        elif config_json_object["type"] in ["input", "internal-input"]:
            return UserInputConfiguration.factory(config_json_object)
        elif config_json_object["type"] == "filter-env":
            return BrokerageEnvConfiguration.factory(config_json_object)
        elif config_json_object["type"] == "trading-env":
            return TradingEnvConfiguration.factory(config_json_object)
        else:
            raise ValueError(
                f'Undefined input method type {config_json_object["type"]}')


class Filter():
    """This class handles the conditional filters added to configurations.
    """

    def __init__(self, filter_conditions):
        self._conditions: List[BaseCondition] = [BaseCondition.factory(
            condition["condition"]) for condition in filter_conditions]


class InfoConfiguration(Configuration):
    """Configuration class used for informational configurations.

    Doesn't support user prompt inputs.
    Values of this configuration isn't persistently saved in the Lean configuration.
    """

    def __init__(self, config_json_object):
        super().__init__(config_json_object)
        self._is_required_from_user = False

    def factory(config_json_object) -> 'InfoConfiguration':
        """Creates an instance of the child classes.

        :param config_json_object: the json object dict with configuration info
        :return: An instance of InfoConfiguration.
        """
        if config_json_object["type"] == "configurations-env":
            return ConfigurationsEnvConfiguration(config_json_object)
        else:
            return InfoConfiguration(config_json_object)


class ConfigurationsEnvConfiguration(InfoConfiguration):
    """Configuration class used for environment properties.

    Doesn't support user prompt inputs.
    Values of this configuration isn't persistently saved in the Lean configuration.
    """

    def __init__(self, config_json_object):
        super().__init__(config_json_object)
        self._env_and_values = {
            env_obj["name"]: env_obj["value"] for env_obj in self._value}


class UserInputConfiguration(Configuration, ABC):
    """Base class extended to all configuration class that requires input from user.

    Values are expected from the user via prompts.
    Values of this configuration is persistently saved in the Lean configuration,
    until specified explicitly.
    """

    def __init__(self, config_json_object):
        super().__init__(config_json_object)
        self._is_required_from_user = True
        self._save_persistently_in_lean = True
        self._input_method = self._prompt_info = self._help = ""
        self._input_default = self._cloud_id = None
        if "input-method" in config_json_object.keys():
            self._input_method = config_json_object["input-method"]
        if "prompt-info" in config_json_object.keys():
            self._prompt_info = config_json_object["prompt-info"]
        if "help" in config_json_object.keys():
            self._help = config_json_object["help"]
        if "input-default" in config_json_object.keys():
            self._input_default = config_json_object["input-default"]
        if "cloud-id" in config_json_object.keys():
            self._cloud_id = config_json_object["cloud-id"]
        if "save-persistently-in-lean" in config_json_object.keys():
            self._save_persistently_in_lean = config_json_object["save-persistently-in-lean"]

    @abstractmethod
    def ask_user_for_input(self, default_value, logger: Logger, hide_input: bool = False):
        """Prompts user to provide input while validating the type of input
        against the expected type

        :param default_value: The default to prompt to the user.
        :param logger: The instance of logger class.
        :param hide_input: Whether to hide the input
        :return: The value provided by the user.
        """
        return NotImplemented()

    def factory(config_json_object) -> 'UserInputConfiguration':
        """Creates an instance of the child classes.

        :param config_json_object: the json object dict with configuration info
        :return: An instance of UserInputConfiguration.
        """
        # NOTE: Check "Type" before "Input-method"
        if config_json_object["type"] == "internal-input":
            return InternalInputUserInput(config_json_object)
        if config_json_object["input-method"] == "prompt":
            return PromptUserInput(config_json_object)
        elif config_json_object["input-method"] == "choice":
            return ChoiceUserInput(config_json_object)
        elif config_json_object["input-method"] == "confirm":
            return ConfirmUserInput(config_json_object)
        elif config_json_object["input-method"] == "prompt-password":
            return PromptPasswordUserInput(config_json_object)
        elif config_json_object["input-method"] == "path-parameter":
            return PathParameterUserInput(config_json_object)


class InternalInputUserInput(UserInputConfiguration):
    """This class is used when configuratios are needed by LEAN config but the values
        are derived from other dependent configurations and not from user input."""

    def __init__(self, config_json_object):
        super().__init__(config_json_object)
        self._is_conditional: bool = False
        value_options: List[ConditionalValueOption] = []
        if "value-options" in config_json_object.keys():
            value_options = [ConditionalValueOption(
                value_option) for value_option in config_json_object["value-options"]]
            self._is_conditional = True
        self._value_options = value_options

    def ask_user_for_input(self, default_value, logger: Logger, hide_input: bool = False):
        """Prompts user to provide input while validating the type of input
        against the expected type

        :param default_value: The default to prompt to the user.
        :param logger: The instance of logger class.
        :param hide_input: Whether to hide the input (not used for this type of input, which is never hidden).
        :return: The value provided by the user.
        """
        raise ValueError(f'user input not allowed with {self.__class__.__name__}')


class PromptUserInput(UserInputConfiguration):
    map_to_types = {
        "string": str,
        "boolean": bool,
        "integer": int
    }

    def __init__(self, config_json_object):
        super().__init__(config_json_object)
        self._input_type: str = "string"
        if "input-type" in config_json_object.keys():
            self._input_type = config_json_object["input-type"]

    def ask_user_for_input(self, default_value, logger: Logger, hide_input: bool = False):
        """Prompts user to provide input while validating the type of input
        against the expected type

        :param default_value: The default to prompt to the user.
        :param logger: The instance of logger class.
        :param hide_input: Whether to hide the input (not used for this type of input, which is never hidden).
        :return: The value provided by the user.
        """
        return prompt(self._prompt_info, default_value, type=self.get_input_type())

    def get_input_type(self):
        return self.map_to_types.get(self._input_type, self._input_type)


class ChoiceUserInput(UserInputConfiguration):
    def __init__(self, config_json_object):
        super().__init__(config_json_object)
        self._choices: List[str] = []
        if "input-choices" in config_json_object.keys():
            self._choices = config_json_object["input-choices"]

    def ask_user_for_input(self, default_value, logger: Logger, hide_input: bool = False):
        """Prompts user to provide input while validating the type of input
        against the expected type

        :param default_value: The default to prompt to the user.
        :param logger: The instance of logger class.
        :param hide_input: Whether to hide the input (not used for this type of input, which is never hidden).
        :return: The value provided by the user.
        """
        return prompt(
            self._prompt_info,
            default_value,
            type=Choice(self._choices, case_sensitive=False)
        )


class PathParameterUserInput(UserInputConfiguration):
    def __init__(self, config_json_object):
        super().__init__(config_json_object)

    def ask_user_for_input(self, default_value, logger: Logger, hide_input: bool = False):
        """Prompts user to provide input while validating the type of input
        against the expected type

        :param default_value: The default to prompt to the user.
        :param logger: The instance of logger class.
        :param hide_input: Whether to hide the input (not used for this type of input, which is never hidden).
        :return: The value provided by the user.
        """

        default_binary = None
        if default_value is not None:
            default_binary = Path(default_value)
        elif self._input_default is not None and Path(self._input_default).is_file():
            default_binary = Path(self._input_default)
        else:
            default_binary = ""
        value = prompt(self._prompt_info,
                             default=default_binary,
                             type=PathParameter(
                                 exists=False, file_okay=True, dir_okay=False)
                             )
        return value


class ConfirmUserInput(UserInputConfiguration):
    def __init__(self, config_json_object):
        super().__init__(config_json_object)

    def ask_user_for_input(self, default_value, logger: Logger, hide_input: bool = False):
        """Prompts user to provide input while validating the type of input
        against the expected type

        :param default_value: The default to prompt to the user.
        :param logger: The instance of logger class.
        :param hide_input: Whether to hide the input (not used for this type of input, which is never hidden).
        :return: The value provided by the user.
        """
        return prompt(self._prompt_info, default_value, type=bool)


class PromptPasswordUserInput(UserInputConfiguration):
    def __init__(self, config_json_object):
        super().__init__(config_json_object)

    def ask_user_for_input(self, default_value, logger: Logger, hide_input: bool = True):
        """Prompts user to provide input while validating the type of input
        against the expected type

        :param default_value: The default to prompt to the user.
        :param logger: The instance of logger class.
        :param hide_input: Whether to hide the input
        :return: The value provided by the user.
        """
        return logger.prompt_password(self._prompt_info, default_value, hide_input=hide_input)


class BrokerageEnvConfiguration(PromptUserInput, ChoiceUserInput, ConfirmUserInput):
    """This class is base class extended by all classes that needs to add value to user filters"""

    def __init__(self, config_json_object):
        super().__init__(config_json_object)

    def factory(config_json_object) -> 'BrokerageEnvConfiguration':
        """Creates an instance of the child classes.

        :param config_json_object: the json object dict with configuration info
        :return: An instance of BrokerageEnvConfiguration
        """
        if config_json_object["type"] == "filter-env":
            return FilterEnvConfiguration(config_json_object)
        else:
            raise ValueError(
                f'Undefined input method type {config_json_object["type"]}')

    def ask_user_for_input(self, default_value, logger: Logger, hide_input: bool = False):
        """Prompts user to provide input while validating the type of input
        against the expected type

        :param default_value: The default to prompt to the user.
        :param logger: The instance of logger class.
        :param hide_input: Whether to hide the input (not used for this type of input, which is never hidden).
        :return: The value provided by the user.
        """
        if self._input_method == "confirm":
            return ConfirmUserInput.ask_user_for_input(self, default_value, logger)
        elif self._input_method == "choice":
            return ChoiceUserInput.ask_user_for_input(self, default_value, logger)
        elif self._input_method == "prompt":
            return PromptUserInput.ask_user_for_input(self, default_value, logger)
        else:
            raise ValueError(f"Undefined input method type {self._input_method}")


class TradingEnvConfiguration(PromptUserInput, ChoiceUserInput, ConfirmUserInput):
    """This class adds trading-mode/envirionment based user filters.

    Normalizes the value of envrionment values(live/paper) for cloud live.
    """

    def __init__(self, config_json_object):
        super().__init__(config_json_object)

    def factory(config_json_object) -> 'TradingEnvConfiguration':
        """Creates an instance of the child classes.

        :param config_json_object: the json object dict with configuration info
        :return: An instance of TradingEnvConfiguration.
        """
        if config_json_object["type"] == "trading-env":
            return TradingEnvConfiguration(config_json_object)
        else:
            raise ValueError(
                f'Undefined input method type {config_json_object["type"]}')

    def ask_user_for_input(self, default_value, logger: Logger, hide_input: bool = False):
        """Prompts user to provide input while validating the type of input
        against the expected type

        :param default_value: The default to prompt to the user.
        :param logger: The instance of logger class.
        :param hide_input: Whether to hide the input (not used for this type of input, which is never hidden).
        :return: The value provided by the user.
        """
        # NOTE: trading envrionment config should not use old boolean value as default
        if type(default_value) == bool:
            default_value = "paper" if default_value else "live"
        if self._input_method == "confirm":
            raise ValueError(
                f'input method -- {self._input_method} is not allowed with {self.__class__.__name__}')
        else:
            return BrokerageEnvConfiguration.ask_user_for_input(self, default_value, logger)


class FilterEnvConfiguration(BrokerageEnvConfiguration):
    """This class adds extra filters to user filters."""

    def __init__(self, config_json_object):
        super().__init__(config_json_object)
