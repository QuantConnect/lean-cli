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


from typing import Dict
import click
from lean.click import PathParameter
from lean.models.configuration import Configuration

def get_click_option_type(configuration):
        # get type should be a method of configurations class itself.
        # TODO: handle input can inherit type prompt.
        if configuration._config_type == "internal-input":
            return str
        if configuration._input_method == "confirm":
            return bool
        elif configuration._input_method == "choice":
            return click.Choice(configuration._choices, case_sensitive=False)
        elif configuration._input_method == "prompt":
            return configuration.get_input_type()
        elif configuration._input_method == "prompt-password":
            return str
        elif configuration._input_method == "path-parameter":
            return PathParameter(exists=True, file_okay=True, dir_okay=False)

def get_options_attributes(configuration: Configuration, default_value=None):
    options_attributes = {
        "type": get_click_option_type(configuration),
        "help": configuration._help 
    }
    if default_value and type(default_value) == options_attributes["type"]:
        options_attributes["default"] = default_value
    return options_attributes

def options_from_json(configurations: Dict[Configuration, str]):

    def decorator(f):
        for configuration, default_value in configurations.items():
            long = configuration._name
            name = str(configuration._name).replace('-','_')
            param_decls = (
                '--' + long,
                name) 
            attrs = get_options_attributes(configuration, default_value)
            click.option(*param_decls, **attrs)(f)
        return f
    return decorator