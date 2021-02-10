from unittest import mock

from click.testing import CliRunner
from rich.console import ConsoleDimensions

from lean.commands import lean
from lean.container import container


@mock.patch("rich.console.Console.size", new_callable=mock.PropertyMock)
def test_config_list_lists_all_options(size) -> None:
    size.return_value = ConsoleDimensions(1000, 1000)

    runner = CliRunner()
    result = runner.invoke(lean, ["config", "list"])

    assert result.exit_code == 0

    for option in container.cli_config_manager().all_options:
        assert option.key in result.output
        assert option.description in result.output


@mock.patch("rich.console.Console.size", new_callable=mock.PropertyMock)
def test_config_list_does_not_show_complete_values_of_sensitive_options(size) -> None:
    container.cli_config_manager().user_id.set_value("123")
    container.cli_config_manager().api_token.set_value("abcdefghijklmnopqrstuvwxyz")

    size.return_value = ConsoleDimensions(1000, 1000)

    runner = CliRunner()
    result = runner.invoke(lean, ["config", "list"])

    assert result.exit_code == 0

    assert "123" not in result.output
    assert "abcdefghijklmnopqrstuvwxyz" not in result.output
