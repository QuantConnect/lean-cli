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

