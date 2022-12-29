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

from abc import ABC

from typing import Any, Dict, List, Optional
from lean.container import container
from lean.models.json_module import JsonModule
from lean.models.configuration import InternalInputUserInput
from copy import copy

class LeanConfigConfigurer(JsonModule, ABC):
    """The LeanConfigConfigurer class is the base class extended by all classes that update the Lean config."""

    def configure(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        """Configures the Lean configuration for this brokerage.

        If the Lean configuration has been configured for this brokerage before, nothing will be changed.
        Non-environment changes are saved persistently to disk so they can be used as defaults later.

        :param lean_config: the configuration dict to write to
        :param environment_name: the name of the environment to configure
        """
        self._configure_environment(lean_config, environment_name)
        self.configure_credentials(lean_config)

    def _configure_environment(self, lean_config: Dict[str, Any], environment_name: str) -> None:
        """Configures the environment in the Lean config for this brokerage.
        :param lean_config: the Lean configuration dict to write to
        :param environment_name: the name of the environment to update
        """
        for environment_config in self.get_configurations_env_values_from_name(environment_name):
            environment_config_name = environment_config["name"]
            if self.__class__.__name__ == 'DataFeed':
                if environment_config_name == "data-queue-handler":
                    previous_value = []
                    if "data-queue-handler" in lean_config["environments"][environment_name]:
                        previous_value = copy(lean_config["environments"][environment_name][environment_config_name])
                    previous_value.append(environment_config["value"])
                    lean_config["environments"][environment_name][environment_config_name] = copy(previous_value)
            elif self.__class__.__name__ == 'LocalBrokerage':
                if environment_config_name != "data-queue-handler":
                    lean_config["environments"][environment_name][environment_config_name] = environment_config["value"]
            else:
                raise ValueError(f'{self.__class__.__name__} not valid for _configure_environment()')

    def configure_credentials(self, lean_config: Dict[str, Any]) -> None:
        """Configures the credentials in the Lean config for this brokerage and saves them persistently to disk.
        :param lean_config: the Lean configuration dict to write to
        """
        if self._installs:
            lean_config["job-organization-id"] = container.organization_manager.try_get_working_organization_id()
        for configuration in self._lean_configs:
            value = None
            if configuration._is_type_configurations_env:
                continue
            elif not self.check_if_config_passes_filters(configuration):
                continue
            elif type(configuration) is InternalInputUserInput:
                if not configuration._is_conditional:
                    value = configuration._value
                else:
                    for option in configuration._value_options:
                        if option._condition.check(self.get_config_value_from_name(option._condition._dependent_config_id)):
                            value = option._value
                            break
                    if not value:
                        options_to_log = set([(opt._condition._dependent_config_id,
                                               self.get_config_value_from_name(opt._condition._dependent_config_id))
                                              for opt in configuration._value_options])
                        raise ValueError(
                            f'No condition matched among present options for "{configuration._cloud_id}". '
                            f'Please review ' +
                            ', '.join([f'"{x[0]}"' for x in options_to_log]) +
                            f' given value{"s" if len(options_to_log) > 1 else ""} ' +
                            ', '.join([f'"{x[1]}"' for x in options_to_log]))
            else:
                value = configuration._value
            from pathlib import WindowsPath, PosixPath
            if type(value) == WindowsPath or type(value) == PosixPath:
                value = str(value).replace("\\", "/")
            lean_config[configuration._id] = value
        container.logger.debug(f"LeanConfigConfigurer.ensure_module_installed(): _save_properties for module {self._id}: {self.get_persistent_save_properties()}")
        self._save_properties(lean_config, self.get_persistent_save_properties())

    def ensure_module_installed(self, organization_id: str) -> None:
        if not self._is_module_installed and self._installs:
            container.logger.debug(f"LeanConfigConfigurer.ensure_module_installed(): installing module for module {self._id}: {self._product_id}")
            container.module_manager.install_module(
                self._product_id, organization_id)
            self._is_module_installed = True

    def _get_default(cls, lean_config: Dict[str, Any], key: str) -> Optional[Any]:
        """Returns the default value for a property based on the current Lean configuration.

        :param lean_config: the current Lean configuration
        :param key: the name of the property
        :return: the default value for the property, or None if there is none
        """
        if key not in lean_config or lean_config[key] == "":
            return None

        return lean_config[key]

    def _save_properties(self, lean_config: Dict[str, Any], properties: List[str]) -> None:
        """Persistently save properties in the Lean configuration.

        :param lean_config: the dict containing all properties
        :param properties: the names of the properties to save persistently
        """
        from lean.container import container
        container.lean_config_manager.set_properties(
            {key: lean_config[key] for key in properties})
