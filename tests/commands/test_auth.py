import json
from pathlib import Path
from unittest import mock

from click.testing import CliRunner

from lean.main import lean


def get_credentials_path() -> Path:
    return Path.home() / ".lean" / "credentials"


def assert_credentials(user_id: str, api_token: str) -> None:
    credentials_path = get_credentials_path()

    assert credentials_path.exists()

    with open(credentials_path) as file:
        data = json.load(file)

        assert "user_id" in data
        assert "api_token" in data

        assert data["user_id"] == user_id
        assert data["api_token"] == api_token


@mock.patch("lean.api.api_client.APIClient.is_authenticated")
def test_login_logs_in_with_options_if_given(is_authenticated) -> None:
    is_authenticated.return_value = True

    runner = CliRunner()
    result = runner.invoke(lean, ["login", "--user-id", "123", "--api-token", "456"])

    assert result.exit_code == 0
    assert_credentials("123", "456")


@mock.patch("lean.api.api_client.APIClient.is_authenticated")
def test_login_prompts_if_user_id_not_given(is_authenticated) -> None:
    is_authenticated.return_value = True

    runner = CliRunner()
    result = runner.invoke(lean, ["login", "--api-token", "456"], input="123\n")

    assert result.exit_code == 0
    assert "User ID:" in result.output
    assert_credentials("123", "456")


@mock.patch("lean.api.api_client.APIClient.is_authenticated")
def test_login_prompts_if_api_token_not_given(is_authenticated) -> None:
    is_authenticated.return_value = True

    runner = CliRunner()
    result = runner.invoke(lean, ["login", "--user-id", "123"], input="456\n")

    assert result.exit_code == 0
    assert "API token:" in result.output
    assert_credentials("123", "456")


@mock.patch("lean.api.api_client.APIClient.is_authenticated")
def test_login_aborts_if_credentials_are_invalid(is_authenticated) -> None:
    is_authenticated.return_value = False

    runner = CliRunner()
    result = runner.invoke(lean, ["login", "--user-id", "123", "--api-token", "456"])

    assert result.exit_code == 1


def test_logout_deletes_credentials() -> None:
    with open(get_credentials_path(), "w+") as file:
        file.write("{}")

    runner = CliRunner()
    result = runner.invoke(lean, ["logout"])

    assert result.exit_code == 0
    assert not get_credentials_path().exists()
