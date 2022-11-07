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


from typing import Any, List
from click import option, Choice
from lean.click import PathParameter
from lean.models.configuration import Configuration


def get_click_option_type(configuration: Configuration):
    # get type should be a method of configurations class itself.
    # TODO: handle input can inherit type prompt.
    if configuration._config_type == "internal-input":
        return str
    if configuration._input_method == "confirm":
        return bool
    elif configuration._input_method == "choice":
        return Choice(configuration._choices, case_sensitive=False)
    elif configuration._input_method == "prompt":
        return configuration.get_input_type()
    elif configuration._input_method == "prompt-password":
        return str
    elif configuration._input_method == "path-parameter":
        return PathParameter(exists=False, file_okay=True, dir_okay=False)


def get_attribute_type(configuration: Configuration):
    # get type should be a method of configurations class itself.
    # TODO: handle input can inherit type prompt.
    if configuration._config_type == "internal-input":
        return str
    if configuration._input_method == "confirm":
        return bool
    elif configuration._input_method == "choice":
        return str
    elif configuration._input_method == "prompt":
        return configuration.get_input_type()
    elif configuration._input_method == "prompt-password":
        return str
    elif configuration._input_method == "path-parameter":
        return str


def get_the_correct_type_default_value(default_lean_config_key: str, default_input_value: str, expected_type: Any,
                                       choices: List[str] = None):
    from lean.commands.live.deploy import _get_default_value
    lean_value = _get_default_value(default_lean_config_key)
    if lean_value is None and default_input_value is not None:
        lean_value = default_input_value
    # This handles backwards compatibility for the old modules.json values.
    if lean_value is not None and type(lean_value) != expected_type and type(lean_value) == bool:
        if choices and "true" in choices and "false" in choices:
            # Backwards compatibility for zeroha-history-subscription.
            lean_value = "true" if lean_value else "false"
        else:
            # Backwards compatibility for tradier-use-sandbox
            lean_value = "paper" if lean_value else "live"
    return lean_value


def get_options_attributes(configuration: Configuration, default_lean_config_key=None):
    options_attributes = {
        "type": get_click_option_type(configuration),
        "help": configuration._help
    }
    default_input_value = configuration._input_default if configuration._is_required_from_user else None
    options_attributes["default"] = lambda: get_the_correct_type_default_value(
        default_lean_config_key, default_input_value, get_attribute_type(configuration),
        configuration._choices if configuration._input_method == "choice" else None)
    return options_attributes


def get_default_key(configuration: Configuration):
    return configuration._id


def options_from_json(configurations: List[Configuration]):

    def decorator(f):
        for configuration in reversed(configurations):
            long = configuration._id
            name = str(configuration._id).replace('-', '_')
            param_decls = (
                '--' + long,
                name)
            attrs = get_options_attributes(
                configuration, get_default_key(configuration))
            option(*param_decls, **attrs)(f)
        return f
    return decorator
