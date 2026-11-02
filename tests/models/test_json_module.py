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

from json import loads
from pathlib import Path
from typing import Any, Dict
from unittest import mock

import pytest
from click import Command, Context, command, echo
from click.testing import CliRunner

from lean.constants import MODULE_BROKERAGE, MODULE_CLI_PLATFORM
from lean.container import container
from lean.models.api import QCAuth0Authorization
from lean.models.json_module import JsonModule
from tests.models.test_configuration import TIME_REGEX, TIME_REGEX_MESSAGE
from tests.test_helpers import create_fake_lean_cli_directory


def create_module(regex: bool = True) -> JsonModule:
    configuration = {
        "id": "my-time",
        "type": "input",
        "input-method": "prompt",
        "prompt-info": "My time"
    }
    if regex:
        configuration["input-regex"] = TIME_REGEX
        configuration["input-regex-message"] = TIME_REGEX_MESSAGE

    return JsonModule({
        "id": "MyBrokerage",
        "display-id": "My Brokerage",
        "configurations": [configuration]
    }, MODULE_BROKERAGE, MODULE_CLI_PLATFORM)


def build_config(lean_config: Dict[str, Any], interactive: bool = False, regex: bool = True) -> JsonModule:
    # config_build() reads the options the user passed from the click context
    with Context(Command("test")):
        return create_module(regex).config_build(lean_config, container.logger, interactive=interactive)


def test_config_build_accepts_lean_config_value_matching_the_regex() -> None:
    module = build_config({"my-time": "21:00:00"})

    assert module.get_config_value_from_name("my-time") == "21:00:00"


@pytest.mark.parametrize("value", ["23:30:01", "23:50:00", "21:00", "invalid"])
def test_config_build_raises_when_lean_config_value_does_not_match_the_regex(value: str) -> None:
    # values read from the Lean config don't go through click, they are validated by config_build()
    with pytest.raises(RuntimeError) as error:
        build_config({"my-time": value})

    assert "Invalid value for 'my-time'" in str(error.value)
    assert TIME_REGEX_MESSAGE in str(error.value)


@pytest.mark.parametrize("lean_config", [{}, {"my-time": ""}])
def test_config_build_reports_the_missing_option_when_there_is_no_value_to_validate(lean_config) -> None:
    # an empty value is not an unsupported one, the user simply didn't provide it
    with pytest.raises(RuntimeError) as error:
        build_config(lean_config)

    assert "You are missing the following option: --my-time" in str(error.value)


def test_config_build_prompts_again_when_lean_config_value_does_not_match_the_regex() -> None:
    create_fake_lean_cli_directory()

    @command()
    def test_command():
        module = build_config({"my-time": "23:50:00"}, interactive=True)
        echo(f"value: {module.get_config_value_from_name('my-time')}")

    # the first answer isn't supported either, so the user is asked once more
    result = CliRunner().invoke(test_command, input="21:00\n22:00:00\n")

    assert result.exit_code == 0
    assert TIME_REGEX_MESSAGE in result.output
    assert "value: 22:00:00" in result.output

    # the value the user provided replaces the unsupported one in the Lean config
    assert loads((Path.cwd() / "lean.json").read_text(encoding="utf-8"))["my-time"] == "22:00:00"


@pytest.mark.parametrize("value", ["23:50:00", "21:00", "invalid"])
def test_config_build_accepts_any_lean_config_value_when_the_module_has_no_regex(value: str) -> None:
    # the regex is optional, modules json files which don't describe one behave like they did before
    module = build_config({"my-time": value}, regex=False)

    assert module.get_config_value_from_name("my-time") == value


def create_oauth_module(module_id: str, display_id: str) -> JsonModule:
    return JsonModule({
        "id": module_id,
        "display-id": display_id,
        "configurations": [
            {
                "id": "my-oauth-token",
                "type": "oauth-token",
                "require-user-name": True,
                "value": "Yes"
            },
            {
                "id": "my-user-name",
                "type": "input",
                "input-method": "prompt",
                "prompt-info": "Username"
            },
            {
                "id": "my-account",
                "type": "input",
                "input-method": "choice",
                "prompt-info": "Account",
                "filters": [{"condition": {"dependent-config-id": "my-oauth-token",
                                           "pattern": "^(?!\\s*$).+",
                                           "type": "regex"}}]
            },
            {
                "id": "my-linked-account",
                "type": "internal-input",
                "alias-of": "my-user-name"
            }
        ]
    }, MODULE_BROKERAGE, MODULE_CLI_PLATFORM)


@pytest.mark.parametrize("module_id,display_id,expected_read_brokerage_id",
                         [("MyBrokerage", "My Brokerage", "my brokerage"),
                          ("InteractiveBrokersFixBrokerage", "InteractiveBrokersFix", "InteractiveBrokersFixBrokerage")])
def test_config_build_reads_the_authorization_under_the_brokerage_id_of_the_module(module_id: str, display_id: str,
                                                                                  expected_read_brokerage_id: str) -> None:
    api_client = mock.Mock()
    api_client.auth0.read.return_value = QCAuth0Authorization(
        authorization={"my-refresh-token": "token", "accounts": [{"id": "U1234567", "name": "U1234567 : Me"}]})
    container.api_client = api_client

    with Context(Command("test")):
        module = create_oauth_module(module_id, display_id).config_build(
            {"project-id": 123, "my-user-name": "someuser", "my-account": "U1234567"}, container.logger,
            interactive=False)

    api_client.auth0.read.assert_called_once_with(expected_read_brokerage_id, user_name="someuser")
    api_client.auth0.authorize.assert_not_called()
    settings = module.get_settings()
    assert settings["my-refresh-token"] == "token"
    assert settings["my-user-name"] == "someuser"
    assert settings["my-account"] == "U1234567"
    assert settings["my-linked-account"] == "someuser"


@pytest.mark.parametrize("module_id,display_id,expected_authorize_brokerage_id",
                         [("MyBrokerage", "My Brokerage", "my brokerage"),
                          ("InteractiveBrokersFixBrokerage", "InteractiveBrokersFix", "interactivebrokers")])
def test_config_build_authorizes_under_the_login_brokerage_id_of_the_module(module_id: str, display_id: str,
                                                                           expected_authorize_brokerage_id: str) -> None:
    api_client = mock.Mock()
    stored_authorization = QCAuth0Authorization(
        authorization={"my-refresh-token": "token", "accounts": [{"id": "U1234567", "name": "U1234567 : Me"}]})
    api_client.auth0.read.side_effect = [QCAuth0Authorization(authorization=None), stored_authorization]
    container.api_client = api_client

    with mock.patch("time.sleep"), Context(Command("test")):
        create_oauth_module(module_id, display_id).config_build(
            {"project-id": 123, "my-user-name": "someuser", "my-account": "U1234567"}, container.logger,
            interactive=False)

    api_client.auth0.authorize.assert_called_once_with(expected_authorize_brokerage_id, container.logger, 123, False,
                                                      user_name="someuser")


def test_get_settings_names_the_alias_of_target_when_it_is_not_a_configuration() -> None:
    module = JsonModule({
        "id": "MyBrokerage",
        "display-id": "My Brokerage",
        "configurations": [{"id": "my-linked-account", "type": "internal-input", "alias-of": "my-username"}]
    }, MODULE_BROKERAGE, MODULE_CLI_PLATFORM)

    with pytest.raises(ValueError, match='"my-linked-account" is an alias of "my-username"'):
        module.get_settings()
