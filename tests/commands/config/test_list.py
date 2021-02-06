from unittest import mock

from click.testing import CliRunner
from rich.console import ConsoleDimensions

from lean.commands import lean
from lean.config.global_config import all_options, api_token_option, user_id_option


@mock.patch("rich.console.Console.size", new_callable=mock.PropertyMock)
def test_config_list_should_list_all_options(size) -> None:
    size.return_value = ConsoleDimensions(1000, 1000)

    runner = CliRunner()
    result = runner.invoke(lean, ["config", "list"])

    assert result.exit_code == 0

    for option in all_options:
        assert option.key in result.output
        assert option.description in result.output


@mock.patch("rich.console.Console.size", new_callable=mock.PropertyMock)
def test_config_list_should_not_show_complete_value_of_credentials(size) -> None:
    user_id_option.set_value("12345")
    api_token_option.set_value("abcdefghijklmnopqrstuvwxyz")

    size.return_value = ConsoleDimensions(1000, 1000)

    runner = CliRunner()
    result = runner.invoke(lean, ["config", "list"])

    assert result.exit_code == 0

    assert "12345" not in result.output
    assert "abcdefghijklmnopqrstuvwxyz" not in result.output
