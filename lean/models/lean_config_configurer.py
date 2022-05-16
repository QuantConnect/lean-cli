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

import abc
import pathlib
from typing import Any, Dict, List, Optional
from lean.container import container
from lean.models.json_module import JsonModule
from lean.models.configuration import InternalInputUserInput

class LeanConfigConfigurer(JsonModule, abc.ABC):
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
        if self._is_installed_and_build:
            return 
        self.ensure_module_installed()

        for environment_config in self.get_configurations_env_values_from_name(environment_name):
            environment_config_name = environment_config["Name"]
            if self.__class__.__name__ == 'DataFeed' and environment_config_name in ["live-mode-brokerage", "transaction-handler"]:
                continue
            lean_config["environments"][environment_name][environment_config_name] = environment_config["Value"]

    def configure_credentials(self, lean_config: Dict[str, Any]) -> None:
        """Configures the credentials in the Lean config for this brokerage and saves them persistently to disk.
        :param lean_config: the Lean configuration dict to write to
        """
        if self._is_installed_and_build:
            return
        if self._installs:
            lean_config["job-organization-id"] = self.get_organzation_id()
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
                            raise ValueError(f'No condtion matched among present options for {configuration._name}')
            else:
                value = configuration._value
            if type(value) == pathlib.WindowsPath:
                value = str(value).replace("\\", "/")
            lean_config[configuration._name] = value
        self._save_properties(lean_config, self.get_required_properties())

    def ensure_module_installed(self) -> None:
        if not self._is_module_installed and self._installs:
            container.module_manager().install_module(self._product_id, self.get_organzation_id())
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
        container.lean_config_manager().set_properties({key: lean_config[key] for key in properties})