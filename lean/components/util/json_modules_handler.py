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
from lean.components.util.logger import Logger
from lean.models.json_module import JsonModule
from lean.models.logger import Option


def build_and_configure_modules(target_modules: List[str], module_list: List[JsonModule], organization_id: str,
                                lean_config: Dict[str, Any], properties: Dict[str, Any], logger: Logger,
                                environment_name: str, module_version: str):
    """Builds and configures the given modules

    :param target_modules: the requested modules
    :param module_list: the available modules
    :param organization_id: the organization id
    :param lean_config: the current lean configs
    :param properties: the user provided arguments
    :param logger: the logger instance
    :param environment_name: the environment name to use
    :param module_version: The version of the module to install. If not provided, the latest version will be installed.
    """
    for target_module_name in target_modules:
        module = non_interactive_config_build_for_name(lean_config, target_module_name, module_list, properties,
                                                       logger, environment_name)
        # Ensures extra modules (not brokerage or data feeds) are installed.
        module.ensure_module_installed(organization_id, module_version)
        lean_config["environments"][environment_name].update(module.get_settings())


def non_interactive_config_build_for_name(lean_config: Dict[str, Any], target_module_name: str,
                                          module_list: List[JsonModule], properties: Dict[str, Any], logger: Logger,
                                          environment_name: str = None) -> JsonModule:
    return config_build_for_name(lean_config, target_module_name, module_list, properties, logger, interactive=False,
                                 environment_name=environment_name)


def find_module(target_module_name: str, module_list: List[JsonModule], logger: Logger) -> JsonModule:
    target_module: JsonModule = None
    # because we compare str we normalize everything to lower case
    target_module_name = target_module_name.lower()
    module_class_name = target_module_name.rfind('.')
    for module in module_list:
        # we search in the modules name and id
        module_id = module.get_id().lower()
        module_name = module.get_name().lower()

        if module_id == target_module_name or module_name == target_module_name:
            target_module = module
            break
        else:
            if (module_class_name != -1 and module_id == target_module_name[module_class_name + 1:]
                    or module_name == target_module_name[module_class_name + 1:]):
                target_module = module
                break

    if not target_module:
        for module in module_list:
            # we search in the modules configuration values, this is for when the user provides an environment
            if (module.is_value_in_config(target_module_name)
               or module_class_name != -1 and module.is_value_in_config(target_module_name[module_class_name + 1:])):
                target_module = module
        if not target_module:
            raise RuntimeError(f"""Failed to resolve module for name: '{target_module_name}'""")
    logger.debug(f'Found module \'{target_module_name}\' from given name')
    return target_module


def config_build_for_name(lean_config: Dict[str, Any], target_module_name: str, module_list: List[JsonModule],
                          properties: Dict[str, Any], logger: Logger, interactive: bool,
                          environment_name: str = None) -> JsonModule:
    target_module = find_module(target_module_name, module_list, logger)
    target_module.config_build(lean_config, logger, interactive=interactive, properties=properties,
                               environment_name=environment_name)
    _update_settings(logger, environment_name, target_module, lean_config)
    return target_module


def interactive_config_build(lean_config: Dict[str, Any], models: [JsonModule], logger: Logger,
                             user_provided_options: Dict[str, Any], show_secrets: bool, select_message: str,
                             multiple: bool, environment_name: str = None) -> [JsonModule]:
    """Interactively configures the brokerage to use.

    :param lean_config: the LEAN configuration that should be used
    :param models: the modules to choose from
    :param logger: the logger to use
    :param user_provided_options: the dictionary containing user provided options
    :param show_secrets: whether to show secrets on input
    :param select_message: the user facing selection message
    :param multiple: true if multiple selections are allowed
    :param environment_name: the target environment name
    :return: the brokerage the user configured
    """
    options = [Option(id=b, label=b.get_name()) for b in models]

    modules: [JsonModule] = []
    if multiple:
        modules = logger.prompt_list(select_message, options, multiple=True)
    else:
        module = logger.prompt_list(select_message, options, multiple=False)
        modules.append(module)

    for module in modules:
        module.config_build(lean_config, logger, interactive=True, properties=user_provided_options,
                            hide_input=not show_secrets, environment_name=environment_name)
        _update_settings(logger, environment_name, module, lean_config)
    if multiple:
        return modules
    return modules[-1]


def _update_settings(logger: Logger, environment_name: str, module: JsonModule,
                     lean_config: Dict[str, Any]) -> None:
    settings = module.get_settings()
    logger.debug(f'_update_settings({module}): Settings: {settings}')

    if environment_name:
        if "environments" not in lean_config:
            lean_config["environments"] = {}
        if environment_name not in lean_config["environments"]:
            lean_config["environments"][environment_name] = {}
        target = lean_config["environments"][environment_name]
    else:
        target = lean_config

    for key, value in settings.items():
        if key in target:
            from json import loads
            if isinstance(target[key], str) and target[key].startswith("["):
                # it already exists, and it's an array we need to merge
                logger.debug(f'_update_settings({module}): target[key]: {target[key]}')
                existing_value = loads(target[key])
                if value.startswith("["):
                    # the new value is also an array, merge them
                    existing_value = existing_value + loads(value)
                else:
                    existing_value.append(value)
                # guarantee order but uniqueness
                target[key] = list(dict.fromkeys(existing_value).keys())
            elif isinstance(target[key], list):
                # guarantee order but uniqueness
                target[key] = list(dict.fromkeys(target[key] + loads(value)).keys())
            else:
                target[key] = value
        else:
            target[key] = value

