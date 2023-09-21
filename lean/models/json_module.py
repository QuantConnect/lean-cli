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

from enum import Enum
from typing import Any, Dict, List, Type

from click import get_current_context
from click.core import ParameterSource

from lean.components.util.logger import Logger
from lean.models.configuration import BrokerageEnvConfiguration, Configuration, InternalInputUserInput
from copy import copy
from abc import ABC


class JsonModule(ABC):
    """The JsonModule class is the base class extended for all json modules."""

    def __init__(self, json_module_data: Dict[str, Any]) -> None:
        self._type: List[str] = json_module_data["type"]
        self._product_id: int = json_module_data["product-id"]
        self._id: str = json_module_data["id"]
        self._display_name: str = json_module_data["display-id"]
        self._installs: bool = json_module_data["installs"]
        self._lean_configs: List[Configuration] = []
        for config in json_module_data["configurations"]:
            self._lean_configs.append(Configuration.factory(config))
        self._lean_configs = self.sort_configs()
        self._is_module_installed: bool = False
        self._initial_cash_balance: LiveInitialStateInput = LiveInitialStateInput(json_module_data["live-cash-balance-state"]) \
            if "live-cash-balance-state" in json_module_data \
            else None
        self._initial_holdings: LiveInitialStateInput = LiveInitialStateInput(json_module_data["live-holdings-state"]) \
            if "live-holdings-state" in json_module_data \
            else False
        self._minimum_seat = json_module_data["minimum-seat"] if "minimum-seat" in json_module_data else None

    def sort_configs(self) -> List[Configuration]:
        sorted_configs = []
        brokerage_configs = []
        for config in self._lean_configs:
            if isinstance(config, BrokerageEnvConfiguration):
                brokerage_configs.append(config)
            else:
                sorted_configs.append(config)
        return brokerage_configs + sorted_configs

    def get_name(self) -> str:
        """Returns the user-friendly name which users can identify this object by.

        :return: the user-friendly name to display to users
        """
        return self._display_name

    def check_if_config_passes_filters(self, config: Configuration) -> bool:
        for condition in config._filter._conditions:
            if condition._dependent_config_id == "module-type":
                target_value = self.__class__.__name__
            else:
                target_value = self.get_config_value_from_name(
                    condition._dependent_config_id)
            if not condition.check(target_value):
                return False
        return True

    def check_if_config_passes_module_filter(self, config: Configuration) -> bool:
        for condition in config._filter._conditions:
            if condition._dependent_config_id == "module-type":
                target_value = self.__class__.__name__
                if not condition.check(target_value):
                    return False
        return True

    def update_configs(self, key_and_values: Dict[str, str]):
        for key, value in key_and_values.items():
            self.update_value_for_given_config(key, value)

    def get_configurations_env_values_from_name(self, target_env: str) -> List[Dict[str, str]]:
        env_config_values = []
        [env_config] = [config for config in self._lean_configs if
                        config._is_type_configurations_env and self.check_if_config_passes_filters(
                            config)
                        ] or [None]
        if env_config is not None and target_env in env_config._env_and_values.keys():
            env_config_values = env_config._env_and_values[target_env]
        return env_config_values

    def get_config_from_type(self, config_type: Configuration) -> str:
        return [copy(config) for config in self._lean_configs if type(config) is config_type]

    def update_value_for_given_config(self, target_name: str, value: Any) -> None:
        [idx] = [i for i in range(len(self._lean_configs))
                 if self._lean_configs[i]._id == target_name]
        self._lean_configs[idx]._value = value

    def get_config_value_from_name(self, target_name: str) -> str:
        [idx] = [i for i in range(len(self._lean_configs))
                 if self._lean_configs[i]._id == target_name]
        return self._lean_configs[idx]._value

    def get_non_user_required_properties(self) -> List[str]:
        return [config._id for config in self._lean_configs if not config._is_required_from_user and not
                config._is_type_configurations_env and self.check_if_config_passes_filters(config)]

    def get_required_properties(self, filters: List[Type[Configuration]] = []) -> List[str]:
        return [config._id for config in self.get_required_configs(filters)]

    def get_required_configs(self, filters: List[Type[Configuration]] = []) -> List[Configuration]:
        required_configs = [copy(config) for config in self._lean_configs if config._is_required_from_user
                            and type(config) not in filters
                            and self.check_if_config_passes_filters(config)]
        return required_configs

    def get_persistent_save_properties(self, filters: List[Type[Configuration]] = []) -> List[str]:
        return [config._id for config in self.get_required_configs(filters) if config._save_persistently_in_lean]

    def get_essential_properties(self) -> List[str]:
        return [config._id for config in self.get_essential_configs()]

    def get_essential_configs(self) -> List[Configuration]:
        return [copy(config) for config in self._lean_configs if isinstance(config, BrokerageEnvConfiguration)]

    def get_all_input_configs(self, filters: List[Type[Configuration]] = []) -> List[Configuration]:
        return [copy(config) for config in self._lean_configs if config._is_required_from_user
                if type(config) not in filters
                and self.check_if_config_passes_module_filter(config)]

    def convert_lean_key_to_variable(self, lean_key: str) -> str:
        """Replaces hyphens with underscore to follow python naming convention.

        :param lean_key: string that uses hyphnes as separator. Used in lean config
        """
        return lean_key.replace('-', '_')

    def convert_variable_to_lean_key(self, variable_key: str) -> str:
        """Replaces underscore with hyphens to follow lean config naming convention.

        :param variable_key: string that uses underscore as separator as per python convention.
        """
        return variable_key.replace('_', '-')

    def build(self,
              lean_config: Dict[str, Any],
              logger: Logger,
              properties: Dict[str, Any] = {},
              hide_input: bool = False) -> 'JsonModule':
        """Builds a new instance of this class, prompting the user for input when necessary.

        :param lean_config: the Lean configuration dict to read defaults from
        :param logger: the logger to use
        :param properties: the properties that passed as options
        :param hide_input: whether to hide secrets inputs
        :return: a LeanConfigConfigurer instance containing all the details needed to configure the Lean config
        """
        logger.info(f'Configure credentials for {self._display_name}')
        for configuration in self._lean_configs:
            if not self.check_if_config_passes_filters(configuration):
                continue
            if not configuration._is_required_from_user:
                continue
            if self.__class__.__name__ == 'CloudBrokerage' and not configuration._is_cloud_property:
                continue
            # Lets log messages for internal input configurations as well
            if configuration._log_message is not None:
                log_message = configuration._log_message.strip()
                if log_message:
                    logger.info(log_message)
            if type(configuration) is InternalInputUserInput:
                continue

            # filter properties that were not passed as command line arguments,
            # so that we prompt the user for them only when they don't have a value in the Lean config
            context = get_current_context()
            user_provided_options = {k: v for k, v in properties.items()
                                     if context.get_parameter_source(k) == ParameterSource.COMMANDLINE}

            user_choice = None
            property_name = self.convert_lean_key_to_variable(configuration._id)
            # Only ask for user input if the config wasn't given as an option
            if property_name in user_provided_options and user_provided_options[property_name]:
                user_choice = user_provided_options[property_name]
            else:
                # Let's try to get the value from the lean config and use it as the user choice, without prompting
                # TODO: use type(class) equality instead of class name (str)
                if self.__class__.__name__ != 'CloudBrokerage':
                    user_choice = self._get_default(lean_config, configuration._id)
                # Try to get the values from lean config
                elif lean_config is not None and configuration._id in lean_config:
                    user_choice = lean_config[configuration._id]

                # There's no value in the lean config, let's use the module default value instead and prompt the user
                # NOTE: using "not" instead of "is None" because the default value can be false,
                #       in which case we still want to prompt the user.
                if not user_choice:
                    default_value = configuration._input_default
                    user_choice = configuration.ask_user_for_input(default_value, logger, hide_input=hide_input)

            self.update_value_for_given_config(configuration._id, user_choice)

        return self


class LiveInitialStateInput(str, Enum):
    Required = "required"
    Optional = "optional"
    NotSupported = "not-supported"
