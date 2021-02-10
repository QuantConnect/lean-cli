from unittest import mock

from click.testing import CliRunner
from dependency_injector import providers

from lean.commands import lean
from lean.container import container


def test_login_logs_in_with_options_when_given() -> None:
    api_client = mock.Mock()
    api_client.is_authenticated.return_value = True
    container.api_client.override(providers.Object(api_client))

    result = CliRunner().invoke(lean, ["login", "--user-id", "123", "--api-token", "456"])

    assert result.exit_code == 0

    assert container.cli_config_manager().user_id.get_value() == "123"
    assert container.cli_config_manager().api_token.get_value() == "456"


def test_login_prompts_when_user_id_not_given() -> None:
    api_client = mock.Mock()
    api_client.is_authenticated.return_value = True
    container.api_client.override(providers.Object(api_client))

    result = CliRunner().invoke(lean, ["login", "--api-token", "456"], input="123\n")

    assert result.exit_code == 0
    assert "User id:" in result.output

    assert container.cli_config_manager().user_id.get_value() == "123"
    assert container.cli_config_manager().api_token.get_value() == "456"


def test_login_prompts_when_api_token_not_given() -> None:
    api_client = mock.Mock()
    api_client.is_authenticated.return_value = True
    container.api_client.override(providers.Object(api_client))

    result = CliRunner().invoke(lean, ["login", "--user-id", "123"], input="456\n")

    assert result.exit_code == 0
    assert "API token:" in result.output

    assert container.cli_config_manager().user_id.get_value() == "123"
    assert container.cli_config_manager().api_token.get_value() == "456"


def test_login_aborts_when_credentials_are_invalid() -> None:
    api_client = mock.Mock()
    api_client.is_authenticated.return_value = False
    container.api_client.override(providers.Object(api_client))

    result = CliRunner().invoke(lean, ["login", "--user-id", "123", "--api-token", "456"])

    assert result.exit_code != 0
