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
from unittest import mock
from unittest.mock import MagicMock

import pytest

from lean.components.util.json_modules_handler import find_module
from lean.constants import MODULE_CLI_PLATFORM, MODULE_BROKERAGE
from lean.models.json_module import JsonModule
from tests.conftest import initialize_container
from tests.test_helpers import create_fake_lean_cli_directory


_SCHWAB_LIKE_MODULE_DATA = {
    "id": "test-brokerage",
    "display-id": "TestBrokerage",
    "configurations": [
        {
            "id": "test-oauth-token",
            "type": "oauth-token"
        },
        {
            "id": "test-account-number",
            "type": "input",
            "input-method": "choice",
            "prompt-info": "Select account",
            "filters": [
                {
                    "condition": {
                        "dependent-config-id": "test-oauth-token",
                        "pattern": "^(?!\\s*$).+",
                        "type": "regex"
                    }
                }
            ]
        }
    ]
}


@pytest.mark.parametrize("id,display,search_name", [("ads", "binAnce", "BiNAnce"),
                                                    ("binAnce", "a", "BiNAnce"),
                                                    ("ads", "binAnce", "QC.Brokerage.Binance.BiNAnce"),
                                                    ("binAnce", "a", "QC.Brokerage.Binance.BiNAnce")])
def test_finds_module_case_insensitive_name(id: str, display: str, search_name: str) -> None:
    create_fake_lean_cli_directory()

    module = JsonModule({"id": id, "configurations": [], "display-id": display},
                        MODULE_BROKERAGE, MODULE_CLI_PLATFORM)
    result = find_module(search_name, [module], MagicMock())
    assert result == module


@pytest.mark.parametrize("searching,expected", [("ads", False),
                                                ("BinanceFuturesBrokerage", True)])
def test_is_value_in_config(searching: str, expected: bool) -> None:
    module = JsonModule({"id": "asd", "configurations": [
        {
            "id": "live-mode-brokerage",
            "type": "info",
            "value": "BinanceFuturesBrokerage"
        }
    ], "display-id": "OUS"}, MODULE_BROKERAGE, MODULE_CLI_PLATFORM)

    result = module.is_value_in_config(searching)

    assert expected == result


def test_get_user_name_returns_none_when_not_required() -> None:
    module = JsonModule({"id": "test", "configurations": [], "display-id": "Test"},
                        MODULE_BROKERAGE, MODULE_CLI_PLATFORM)
    result = module.get_user_name({}, mock.Mock(), {}, require_user_name=False,
                                  interactive=False)
    assert result is None


def test_get_user_name_from_user_provided_options() -> None:
    module = JsonModule({"id": "test", "configurations": [], "display-id": "Test"},
                        MODULE_BROKERAGE, MODULE_CLI_PLATFORM)
    config = mock.Mock()
    config._id = "charles-schwab-oauth-token"
    result = module.get_user_name({}, config,
                                  {"charles_schwab_user_name": "cli_login"},
                                  require_user_name=True, interactive=False)
    assert result == "cli_login"


def test_get_user_name_from_lean_config() -> None:
    module = JsonModule({"id": "test", "configurations": [], "display-id": "Test"},
                        MODULE_BROKERAGE, MODULE_CLI_PLATFORM)
    config = mock.Mock()
    config._id = "charles-schwab-oauth-token"
    lean_config = {"charles-schwab-user-name": "saved_login"}
    result = module.get_user_name(lean_config, config, {}, require_user_name=True, interactive=False)
    assert result == "saved_login"


def test_get_user_name_prompts_and_saves_to_lean_config() -> None:
    module = JsonModule({"id": "test", "configurations": [], "display-id": "Test"},
                        MODULE_BROKERAGE, MODULE_CLI_PLATFORM)
    config = mock.Mock()
    config._id = "charles-schwab-oauth-token"
    lean_config = {}
    with mock.patch("click.prompt", return_value="prompted_login") as mock_prompt:
        result = module.get_user_name(lean_config, config, {}, require_user_name=True, interactive=True)
    assert result == "prompted_login"
    assert lean_config["charles-schwab-user-name"] == "prompted_login"
    mock_prompt.assert_called_once()


def test_config_build_prompts_when_lean_config_has_stale_account() -> None:
    create_fake_lean_cli_directory()
    initialize_container()

    module = JsonModule(_SCHWAB_LIKE_MODULE_DATA, MODULE_BROKERAGE, MODULE_CLI_PLATFORM)

    lean_config = {"project-id": 123, "test-account-number": "89630725"}  # stale — not returned by API

    mock_auth = mock.MagicMock()
    mock_auth.get_authorization_config_without_account.return_value = {"token": "abc"}
    mock_auth.get_account_ids.return_value = ["60102549"]

    with mock.patch("lean.models.json_module.get_current_context") as mock_ctx, \
         mock.patch("lean.models.json_module.get_authorization", return_value=mock_auth), \
         mock.patch("lean.models.configuration.prompt", return_value="60102549") as mock_prompt, \
         mock.patch.object(module, "_save_property"):
        mock_ctx.return_value.get_parameter_source.return_value = None

        module.config_build(lean_config, mock.Mock(), interactive=True)

    mock_prompt.assert_called_once()
    account_config = next(c for c in module._lean_configs if c._id == "test-account-number")
    assert account_config._value == "60102549"


def test_config_build_prompts_when_api_returns_multiple_accounts() -> None:
    create_fake_lean_cli_directory()
    initialize_container()

    module = JsonModule(_SCHWAB_LIKE_MODULE_DATA, MODULE_BROKERAGE, MODULE_CLI_PLATFORM)

    lean_config = {"project-id": 123, "test-account-number": "60102549"}  # valid but ambiguous

    mock_auth = mock.MagicMock()
    mock_auth.get_authorization_config_without_account.return_value = {"token": "abc"}
    mock_auth.get_account_ids.return_value = ["60102549", "99887766"]  # multiple accounts

    with mock.patch("lean.models.json_module.get_current_context") as mock_ctx, \
         mock.patch("lean.models.json_module.get_authorization", return_value=mock_auth), \
         mock.patch("lean.models.configuration.prompt", return_value="60102549") as mock_prompt, \
         mock.patch.object(module, "_save_property"):
        mock_ctx.return_value.get_parameter_source.return_value = None

        module.config_build(lean_config, mock.Mock(), interactive=True)

    mock_prompt.assert_called_once()
    account_config = next(c for c in module._lean_configs if c._id == "test-account-number")
    assert account_config._value == "60102549"


def test_config_build_uses_lean_config_account_when_valid() -> None:
    create_fake_lean_cli_directory()
    initialize_container()

    module = JsonModule(_SCHWAB_LIKE_MODULE_DATA, MODULE_BROKERAGE, MODULE_CLI_PLATFORM)

    lean_config = {"project-id": 123, "test-account-number": "60102549"}  # valid — matches API response

    mock_auth = mock.MagicMock()
    mock_auth.get_authorization_config_without_account.return_value = {"token": "abc"}
    mock_auth.get_account_ids.return_value = ["60102549"]

    with mock.patch("lean.models.json_module.get_current_context") as mock_ctx, \
         mock.patch("lean.models.json_module.get_authorization", return_value=mock_auth), \
         mock.patch("lean.models.configuration.prompt") as mock_prompt, \
         mock.patch.object(module, "_save_property"):
        mock_ctx.return_value.get_parameter_source.return_value = None

        module.config_build(lean_config, mock.Mock(), interactive=True)

    mock_prompt.assert_not_called()
    account_config = next(c for c in module._lean_configs if c._id == "test-account-number")
    assert account_config._value == "60102549"
