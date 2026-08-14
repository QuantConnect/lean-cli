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

from lean.click import RegexParameter
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


def test_validate_returns_none_when_there_is_no_value_to_validate() -> None:
    configuration = create_configuration(**{"input-regex": TIME_REGEX})

    assert configuration.validate(None) is None


def test_get_input_type_returns_the_regex_type_when_modules_json_has_a_regex() -> None:
    configuration = create_configuration(**{"input-type": "string", "input-regex": TIME_REGEX})

    assert isinstance(configuration.get_input_type(), RegexParameter)


def test_get_input_type_returns_the_mapped_type_when_modules_json_has_no_regex() -> None:
    configuration = create_configuration(**{"input-type": "integer"})

    assert configuration.get_input_type() is int


@pytest.mark.parametrize("input_method", ["prompt", "prompt-password", "path-parameter", "choice"])
def test_get_click_option_type_returns_the_regex_type_for_all_input_methods(input_method: str) -> None:
    configuration = create_configuration(**{"input-method": input_method, "input-regex": TIME_REGEX})

    assert get_click_option_type(configuration) is configuration.get_regex_type()


def test_regex_is_not_validated_for_configurations_without_one() -> None:
    configuration = create_configuration(**{"input-method": "prompt-password"})

    assert configuration.get_regex_type() is None
    assert get_click_option_type(configuration) is str
