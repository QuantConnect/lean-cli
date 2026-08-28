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

import pytest
from click.types import INT, StringParamType

from lean.click import CaseInsensitiveChoice, PathParameter, RegexParameter
from lean.models.click_options import get_click_option_type
from lean.models.configuration import Configuration

# The regex the modules json uses for ib-weekly-restart-utc-time,
# Interactive Brokers doesn't support weekly restart times later than 23:30 UTC
TIME_REGEX = r"^(?:(?:[01][0-9]|2[0-2]):[0-5][0-9]:[0-5][0-9]|23:(?:[0-2][0-9]:[0-5][0-9]|30:00))$"
TIME_REGEX_MESSAGE = "must be a UTC time in hh:mm:ss format, no later than 23:30:00"


def create_configuration(**properties) -> Configuration:
    return Configuration.factory({
        "id": "my-time",
        "type": "input",
        "input-method": "prompt",
        "prompt-info": "My time",
        **properties
    })


def test_validate_returns_value_when_modules_json_has_no_regex() -> None:
    configuration = create_configuration()

    assert configuration.validate("this is not a time") == "this is not a time"


@pytest.mark.parametrize("value", ["00:00:00", "21:00:00", "23:29:59", "23:30:00"])
def test_validate_returns_value_when_it_matches_the_regex(value: str) -> None:
    configuration = create_configuration(**{"input-regex": TIME_REGEX, "input-regex-message": TIME_REGEX_MESSAGE})

    assert configuration.validate(value) == value


@pytest.mark.parametrize("value", ["23:30:01", "23:50:00", "21:00", "25:00:00", "invalid"])
def test_validate_raises_when_value_does_not_match_the_regex(value: str) -> None:
    configuration = create_configuration(**{"input-regex": TIME_REGEX, "input-regex-message": TIME_REGEX_MESSAGE})

    with pytest.raises(RuntimeError) as error:
        configuration.validate(value)

    assert f"Invalid value for 'my-time'" in str(error.value)
    assert value in str(error.value)
    assert TIME_REGEX_MESSAGE in str(error.value)


@pytest.mark.parametrize("value", [None, ""])
def test_validate_returns_the_value_when_there_is_nothing_to_validate(value) -> None:
    # an empty value means the user didn't provide one, config_build() reports it as a missing option
    configuration = create_configuration(**{"input-regex": TIME_REGEX})

    assert configuration.validate(value) == value


def test_get_input_type_returns_the_regex_type_when_modules_json_has_a_regex() -> None:
    configuration = create_configuration(**{"input-type": "integer", "input-regex": TIME_REGEX})

    input_type = configuration.get_input_type()

    # the regex is added to the type of the configuration, it doesn't replace it
    assert isinstance(input_type, RegexParameter)
    assert input_type._inner_type is INT


def test_get_input_type_returns_the_mapped_type_when_modules_json_has_no_regex() -> None:
    configuration = create_configuration(**{"input-type": "integer"})

    assert configuration.get_input_type() is int


@pytest.mark.parametrize("input_method,inner_type", [("prompt", StringParamType),
                                                    ("prompt-password", StringParamType),
                                                    ("path-parameter", PathParameter)])
def test_get_click_option_type_adds_the_regex_to_the_type_of_the_input_method(input_method: str, inner_type) -> None:
    configuration = create_configuration(**{"input-method": input_method, "input-regex": TIME_REGEX})

    option_type = get_click_option_type(configuration)

    # the regex is added to the type of the input method, it doesn't replace it
    assert isinstance(option_type, RegexParameter)
    assert isinstance(option_type._inner_type, inner_type)


def test_get_click_option_type_keeps_the_integer_type_of_a_prompt() -> None:
    configuration = create_configuration(**{"input-type": "integer", "input-regex": TIME_REGEX})

    assert get_click_option_type(configuration)._inner_type is INT


def test_regex_is_ignored_for_a_choice_input() -> None:
    # the choices already describe the values the configuration accepts
    configuration = create_configuration(**{"input-method": "choice",
                                            "input-choices": ["morning", "evening"],
                                            "input-regex": TIME_REGEX})

    assert isinstance(get_click_option_type(configuration), CaseInsensitiveChoice)
    assert configuration.validate("morning") == "morning"


def test_regex_is_ignored_for_a_confirm_input() -> None:
    configuration = create_configuration(**{"input-method": "confirm", "input-regex": TIME_REGEX})

    assert get_click_option_type(configuration) is bool
    assert configuration.validate(True) is True


def test_regex_is_not_added_for_configurations_without_one() -> None:
    configuration = create_configuration(**{"input-method": "prompt-password"})

    assert configuration.wrap_with_regex(str) is str
    assert get_click_option_type(configuration) is str
