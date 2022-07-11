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

from typing import Any, Dict, List, Type
from lean.components.util.logger import Logger
from lean.container import container
from lean.models.logger import Option
from lean.models.configuration import BrokerageEnvConfiguration, Configuration, InternalInputUserInput
import copy
import abc


class JsonModule(abc.ABC):
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
        self._is_installed_and_build: bool = False

    def sort_configs(self) -> List[Configuration]:
        sorted_configs = []
        brokerage_configs = []
        organization_config = []
        for config in self._lean_configs:
            if isinstance(config, BrokerageEnvConfiguration):
                brokerage_configs.append(config)
            elif config.is_type_organization_id:
                organization_config.append(config)
            else:
                sorted_configs.append(config)
        return organization_config + brokerage_configs + sorted_configs

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

    def get_organzation_id(self) -> str:
        [organization_id] = [
            config._value for config in self._lean_configs if config.is_type_organization_id]
        return organization_id

    def update_value_for_given_config(self, target_name: str, value: Any) -> None:
        [idx] = [i for i in range(len(self._lean_configs))
                 if self._lean_configs[i]._id == target_name]
        self._lean_configs[idx]._value = value

    def get_config_value_from_name(self, target_name: str) -> str:
        [idx] = [i for i in range(len(self._lean_configs))
                 if self._lean_configs[i]._id == target_name]
        return self._lean_configs[idx]._value

    def get_non_user_required_properties(self) -> List[Configuration]:
        return [config._id for config in self._lean_configs if not config._is_required_from_user and not
                config._is_type_configurations_env and self.check_if_config_passes_filters(config)]

    def get_required_properties(self, filters: List[Type[Configuration]] = []) -> List[str]:
        return [config._id for config in self.get_required_configs(filters)]

    def get_required_configs(self, filters: List[Type[Configuration]] = []) -> List[Configuration]:
        required_configs = [copy.copy(config) for config in self._lean_configs if config._is_required_from_user
                            and type(config) not in filters
                            and self.check_if_config_passes_filters(config)]
        return required_configs

    def get_essential_properties(self) -> List[str]:
        return [config._id for config in self.get_essential_configs()]

    def get_essential_configs(self) -> List[Configuration]:
        return [copy.copy(config) for config in self._lean_configs if isinstance(config, BrokerageEnvConfiguration)]

    def get_all_input_configs(self, filters: List[Type[Configuration]] = []) -> List[Configuration]:
        return [copy.copy(config) for config in self._lean_configs if config._is_required_from_user
                if type(config) not in filters
                and self.check_if_config_passes_module_filter(config)]

    def _convert_lean_key_to_variable(self, lean_key: str) -> str:
        """Replaces hyphens with underscore to follow python naming convention.

        :param lean_key: string that uses hyphnes as separator. Used in lean config
        """
        return lean_key.replace('-', '_')

    def _convert_variable_to_lean_key(self, variable_key: str) -> str:
        """Replaces underscore with hyphens to follow lean config naming convention.

        :param variable_key: string that uses underscore as separator as per python convention.
        """
        return variable_key.replace('_', '-')

    def build(self, lean_config: Dict[str, Any], logger: Logger) -> 'JsonModule':
        """Builds a new instance of this class, prompting the user for input when necessary.

        :param lean_config: the Lean configuration dict to read defaults from
        :param logger: the logger to use
        :return: a LeanConfigConfigurer instance containing all the details needed to configure the Lean config
        """
        if self._is_installed_and_build:
            return self
        logger.info(f'Configure credentials for {self._display_name}')
        for configuration in self._lean_configs:
            if not self.check_if_config_passes_filters(configuration):
                continue
            if not configuration._is_required_from_user:
                continue
            if type(configuration) is InternalInputUserInput:
                continue
            if configuration._log_message is not None:
                logger.info(configuration._log_message.strip())
            if configuration.is_type_organization_id:
                api_client = container.api_client()
                organizations = api_client.organizations.get_all()
                options = [Option(id=organization.id, label=organization.name)
                           for organization in organizations]
                organization_id = logger.prompt_list(
                    "Select the organization with the {} module subscription".format(
                        self.get_name()),
                    options
                )
                user_choice = organization_id
            else:
                default_value = None
                # TODO: use type(class) equality instead of class name (str)
                if self.__class__.__name__ != 'CloudBrokerage':
                    default_value = self._get_default(lean_config, configuration._id)
                user_choice = configuration.AskUserForInput(default_value, logger)
            self.update_value_for_given_config(
                configuration._id, user_choice)

        return self
