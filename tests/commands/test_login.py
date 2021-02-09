from click.testing import CliRunner

from lean.commands import lean
from tests.test_helpers import MockContainer


def test_login_should_log_in_with_options_when_given(mock_container: MockContainer) -> None:
    mock_container.api_client_mock.is_authenticated.return_value = True

    result = CliRunner().invoke(lean, ["login", "--user-id", "123", "--api-token", "456"])

    assert result.exit_code == 0

    mock_container.cli_config_manager_mock.user_id.set_value.assert_called_once_with("123")
    mock_container.cli_config_manager_mock.api_token.set_value.assert_called_once_with("456")


def test_login_should_prompt_when_user_id_not_given(mock_container: MockContainer) -> None:
    mock_container.api_client_mock.is_authenticated.return_value = True

    result = CliRunner().invoke(lean, ["login", "--api-token", "456"], input="123\n")

    assert result.exit_code == 0
    assert "User id:" in result.output

    mock_container.cli_config_manager_mock.user_id.set_value.assert_called_once_with("123")
    mock_container.cli_config_manager_mock.api_token.set_value.assert_called_once_with("456")


def test_login_should_prompt_when_api_token_not_given(mock_container: MockContainer) -> None:
    mock_container.api_client_mock.is_authenticated.return_value = True

    result = CliRunner().invoke(lean, ["login", "--user-id", "123"], input="456\n")

    assert result.exit_code == 0
    assert "API token:" in result.output

    mock_container.cli_config_manager_mock.user_id.set_value.assert_called_once_with("123")
    mock_container.cli_config_manager_mock.api_token.set_value.assert_called_once_with("456")


def test_login_should_abort_when_credentials_are_invalid(mock_container: MockContainer) -> None:
    mock_container.api_client_mock.is_authenticated.return_value = False

    result = CliRunner().invoke(lean, ["login", "--user-id", "123", "--api-token", "456"])

    assert result.exit_code != 0

    mock_container.cli_config_manager_mock.user_id.set_value.assert_not_called()
    mock_container.cli_config_manager_mock.api_token.set_value.assert_not_called()
