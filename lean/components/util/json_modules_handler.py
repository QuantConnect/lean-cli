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

from typing import Any, Dict, List
from lean.models.addon_modules.addon_module import AddonModule
from lean.models.addon_modules import all_addon_modules
from lean.components.util.logger import Logger
from lean.models.configuration import InternalInputUserInput
from lean.models.json_module import JsonModule
from lean.click import ensure_options

def build_and_configure_modules(modules: List[AddonModule], organization_id: str, lean_config: Dict[str, Any], logger: Logger, environment_name: str) -> Dict[str, Any]:
    """Capitalizes the given word.

    :param word: the word to capitalize
    :return: the word with the first letter capitalized (any other uppercase characters are preserved)
    """
    for given_module in modules:
        try:
            found_module = next((module for module in all_addon_modules if module.get_name().lower() == given_module.lower()), None)
            if found_module:
                found_module.build(lean_config, logger).configure(lean_config, environment_name)
                found_module.ensure_module_installed(organization_id)
            else:
                logger.error(f"Addon module '{given_module}' not found")
        except Exception as e:
            logger.error(f"Addon module '{given_module}' failed to configure: {e}")
    return lean_config

def get_and_build_module(target_module_name: str, module_list: List[JsonModule], properties: Dict[str, Any], logger: Logger):
    [target_module] = [module for module in module_list if module.get_name() == target_module_name]
    # update essential properties from brokerage to datafeed
    # needs to be updated before fetching required properties
    essential_properties = [target_module.convert_lean_key_to_variable(prop) for prop in target_module.get_essential_properties()]
    ensure_options(essential_properties)
    essential_properties_value = {target_module.convert_variable_to_lean_key(prop) : properties[prop] for prop in essential_properties}
    target_module.update_configs(essential_properties_value)
    logger.debug(f"json_module_handler.get_and_build_module(): non-interactive: essential_properties_value with module {target_module_name}: {essential_properties_value}")
    # now required properties can be fetched as per data/filter provider from essential properties
    required_properties: List[str] = []
    for config in target_module.get_required_configs([InternalInputUserInput]):
        required_properties.append(target_module.convert_lean_key_to_variable(config._id))
    ensure_options(required_properties)
    required_properties_value = {target_module.convert_variable_to_lean_key(prop) : properties[prop] for prop in required_properties}
    target_module.update_configs(required_properties_value)
    logger.debug(f"json_module_handler.get_and_build_module(): non-interactive: required_properties_value with module {target_module_name}: {required_properties_value}")
    return target_module
