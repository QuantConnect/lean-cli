import json
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from lean.commands import lean
from lean.constants import CREDENTIALS_FILE, GLOBAL_CONFIG_DIR


def get_credentials_path() -> Path:
    return Path.home() / GLOBAL_CONFIG_DIR / CREDENTIALS_FILE


def assert_credentials(user_id: str, api_token: str) -> None:
    credentials_path = get_credentials_path()

    assert credentials_path.exists()

    with open(credentials_path) as file:
        data = json.load(file)

        assert "user-id" in data
        assert "api-token" in data

        assert data["user-id"] == user_id
        assert data["api-token"] == api_token


@mock.patch("lean.api.api_client.APIClient.is_authenticated")
def test_login_should_log_in_with_options_when_given(is_authenticated) -> None:
    is_authenticated.return_value = True

    runner = CliRunner()
    result = runner.invoke(lean, ["login", "--user-id", "123", "--api-token", "456"])

    assert result.exit_code == 0
    assert_credentials("123", "456")


@mock.patch("lean.api.api_client.APIClient.is_authenticated")
def test_login_should_prompt_when_user_id_not_given(is_authenticated) -> None:
    is_authenticated.return_value = True

    runner = CliRunner()
    result = runner.invoke(lean, ["login", "--api-token", "456"], input="123\n")

    assert result.exit_code == 0
    assert "User id:" in result.output
    assert_credentials("123", "456")


@mock.patch("lean.api.api_client.APIClient.is_authenticated")
def test_login_should_prompt_when_api_token_not_given(is_authenticated) -> None:
    is_authenticated.return_value = True

    runner = CliRunner()
    result = runner.invoke(lean, ["login", "--user-id", "123"], input="456\n")

    assert result.exit_code == 0
    assert "API token:" in result.output
    assert_credentials("123", "456")


@mock.patch("lean.api.api_client.APIClient.is_authenticated")
def test_login_should_abort_when_credentials_are_invalid(is_authenticated) -> None:
    is_authenticated.return_value = False

    runner = CliRunner()
    result = runner.invoke(lean, ["login", "--user-id", "123", "--api-token", "456"])

    assert result.exit_code != 0
