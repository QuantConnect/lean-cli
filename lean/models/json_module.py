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
from lean.constants import MODULE_TYPE, MODULE_PLATFORM, MODULE_CLI_PLATFORM
from lean.container import container
from lean.models.configuration import BrokerageEnvConfiguration, Configuration, InternalInputUserInput, \
    PathParameterUserInput
from copy import copy
from abc import ABC

_logged_messages = set()


class JsonModule(ABC):
    """The JsonModule class is the base class extended for all json modules."""

    def __init__(self, json_module_data: Dict[str, Any], module_type: str, platform: str) -> None:
        self._module_type: str = module_type
        self._platform: str = platform
        self._product_id: int = json_module_data["product-id"] if "product-id" in json_module_data else 0
        self._id: str = json_module_data["id"]
        self._display_name: str = json_module_data["display-id"]
        self._specifications_url: str = json_module_data["specifications"] if "specifications" in json_module_data else None
        self._installs: bool = json_module_data["installs"] if ("installs" in json_module_data
                                                                and platform == MODULE_CLI_PLATFORM) else False
        self._lean_configs: List[Configuration] = []
        for config in json_module_data["configurations"]:
            self._lean_configs.append(Configuration.factory(config))
        self._lean_configs = self.sort_configs()
        self._is_module_installed: bool = False
        self._initial_cash_balance: LiveInitialStateInput = LiveInitialStateInput(
            json_module_data["live-cash-balance-state"]) \
            if "live-cash-balance-state" in json_module_data \
            else None
        self._initial_holdings: LiveInitialStateInput = LiveInitialStateInput(json_module_data["live-holdings-state"]) \
            if "live-holdings-state" in json_module_data \
            else False
        self._minimum_seat = json_module_data["minimum-seat"] if "minimum-seat" in json_module_data else None

    def get_id(self):
        return self._id

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

    def _check_if_config_passes_filters(self, config: Configuration, all_for_platform_type: bool) -> bool:
        for condition in config._filter._conditions:
            if condition._dependent_config_id == MODULE_TYPE:
                target_value = self._module_type
            elif condition._dependent_config_id == MODULE_PLATFORM:
                target_value = self._platform
            else:
                if all_for_platform_type:
                    # skip, we want all configurations that match type and platform, for help
                    continue
                target_value = self.get_config_value_from_name(condition._dependent_config_id)
            if not target_value or not condition.check(target_value):
                return False
        return True

    def get_config_value_from_name(self, target_name: str) -> str:
        [idx] = [i for i in range(len(self._lean_configs))
                 if self._lean_configs[i]._id == target_name]
        return self._lean_configs[idx]._value

    def is_value_in_config(self, searched_value: str) -> bool:
        searched_value = searched_value.lower()
        for i in range(len(self._lean_configs)):
            value = self._lean_configs[i]._value
            if isinstance(value, str):
                value = value.lower()
            if isinstance(value, list):
                value = [x.lower() for x in value]

            if searched_value in value:
                return True
        return False

    def get_settings(self) -> Dict[str, str]:
        settings: Dict[str, str] = {"id": self._id}

        # we build these after the rest, because they might depend on their values
        for config in self._lean_configs:
            if type(config) is InternalInputUserInput:
                if config._is_conditional:
                    for option in config._value_options:
                        if option._condition.check(self.get_config_value_from_name(option._condition._dependent_config_id)):
                            config._value = option._value
                            break
                    if not config._value:
                        options_to_log = set([(opt._condition._dependent_config_id,
                                               self.get_config_value_from_name(opt._condition._dependent_config_id))
                                              for opt in config._value_options])
                        raise ValueError(
                            f'No condition matched among present options for "{config._id}". '
                            f'Please review ' +
                            ', '.join([f'"{x[0]}"' for x in options_to_log]) +
                            f' given value{"s" if len(options_to_log) > 1 else ""} ' +
                            ', '.join([f'"{x[1]}"' for x in options_to_log]))

        for configuration in self._lean_configs:
            if not self._check_if_config_passes_filters(configuration, all_for_platform_type=False):
                continue
            settings[configuration._id] = str(configuration._value).replace("\\", "/")

        return settings

    def get_all_input_configs(self, filters: List[Type[Configuration]] = []) -> List[Configuration]:
        return [copy(config) for config in self._lean_configs if config._is_required_from_user
                if type(config) not in filters
                and self._check_if_config_passes_filters(config, all_for_platform_type=True)]

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

    def config_build(self,
                     lean_config: Dict[str, Any],
                     logger: Logger,
                     interactive: bool,
                     properties: Dict[str, Any] = {},
                     hide_input: bool = False,
                     environment_name: str = None) -> 'JsonModule':
        """Builds a new instance of this class, prompting the user for input when necessary.

        :param lean_config: the Lean configuration dict to read defaults from
        :param logger: the logger to use
        :param interactive: true if running in interactive mode
        :param properties: the properties that passed as options
        :param hide_input: whether to hide secrets inputs
        :param environment_name: the target environment name
        :return: self
        """
        logger.debug(f'Configuring {self._display_name}')

        # filter properties that were not passed as command line arguments,
        # so that we prompt the user for them only when they don't have a value in the Lean config
        context = get_current_context()
        user_provided_options = {k: v for k, v in properties.items()
                                 if context.get_parameter_source(k) == ParameterSource.COMMANDLINE}

        missing_options = []
        for configuration in self._lean_configs:
            if not self._check_if_config_passes_filters(configuration, all_for_platform_type=False):
                continue
            if not configuration._is_required_from_user:
                continue
            # Let's log messages for internal input configurations as well
            if configuration._log_message is not None:
                log_message = configuration._log_message.strip()
                if log_message and log_message not in _logged_messages:
                    logger.info(log_message)
                    # make sure we log these messages once, we could use the same module for different functionalities
                    _logged_messages.add(log_message)
            if type(configuration) is InternalInputUserInput:
                continue

            property_name = self.convert_lean_key_to_variable(configuration._id)
            # Only ask for user input if the config wasn't given as an option
            if property_name in user_provided_options and user_provided_options[property_name]:
                user_choice = user_provided_options[property_name]
                logger.debug(
                    f'JsonModule({self._display_name}): user provided \'{user_choice}\' for \'{property_name}\'')
            else:
                logger.debug(f'JsonModule({self._display_name}): Configuration not provided \'{configuration._id}\'')
                user_choice = self.get_default(lean_config, configuration._id, environment_name, logger)

                # There's no value in the lean config, let's use the module default value instead and prompt the user
                # NOTE: using "not" instead of "is None" because the default value can be false,
                #       in which case we still want to prompt the user.
                if not user_choice:
                    if interactive:
                        default_value = configuration._input_default
                        user_choice = configuration.ask_user_for_input(default_value, logger, hide_input=hide_input)

                        if not isinstance(configuration, BrokerageEnvConfiguration):
                            self._save_property({f"{configuration._id}": user_choice})
                    else:
                        if configuration._input_default != None and configuration._optional:
                            # if optional and we have a default input value and the user didn't provider it we use it
                            user_choice = configuration._input_default
                        else:
                            missing_options.append(f"--{configuration._id}")

            configuration._value = user_choice

        if len(missing_options) > 0:
            raise RuntimeError(f"""You are missing the following option{"s" if len(missing_options) > 1 else ""}: {', '
                               .join(missing_options)}""".strip())
        return self

    def get_paths_to_mount(self) -> Dict[str, str]:
        return {config._id: config._value
                for config in self._lean_configs
                if (isinstance(config, PathParameterUserInput)
                    and self._check_if_config_passes_filters(config, all_for_platform_type=False))}

    def ensure_module_installed(self, organization_id: str) -> None:
        if not self._is_module_installed and self._installs:
            container.logger.debug(f"JsonModule.ensure_module_installed(): installing module {self}: {self._product_id}")
            container.module_manager.install_module(
                self._product_id, organization_id)
            self._is_module_installed = True

    def get_default(self, lean_config: Dict[str, Any], key: str, environment_name: str, logger: Logger):
        user_choice = None
        if lean_config is not None:
            if (environment_name and "environments" in lean_config and environment_name in lean_config["environments"]
                    and key in lean_config["environments"][environment_name]):
                user_choice = lean_config["environments"][environment_name][key]
                logger.debug(f'JsonModule({self._display_name}): found \'{user_choice}\' for \'{key}\', in environment')
            elif key in lean_config:
                user_choice = lean_config[key]
                logger.debug(f'JsonModule({self._display_name}): found \'{user_choice}\' for \'{key}\'')
        return user_choice

    def __repr__(self):
        return self.get_name()

    def _save_property(self, settings: Dict[str, Any]):
        from lean.container import container
        container.lean_config_manager.set_properties(settings)

    @property
    def specifications_url(self):
        return self._specifications_url


class LiveInitialStateInput(str, Enum):
    Required = "required"
    Optional = "optional"
    NotSupported = "not-supported"
