from unittest import mock

from click.testing import CliRunner
from rich.console import ConsoleDimensions

from lean.commands import lean
from tests.test_helpers import create_option, MockContainer


@mock.patch("rich.console.Console.size", new_callable=mock.PropertyMock)
def test_config_list_should_list_all_options(size, mock_container: MockContainer) -> None:
    short_option = create_option("short", "123", False)
    long_option = create_option("long", "abcdefghijklmnopqrstuvwxyz", False)

    mock_container.cli_config_manager_mock.all_options = [short_option, long_option]

    size.return_value = ConsoleDimensions(1000, 1000)

    runner = CliRunner()
    result = runner.invoke(lean, ["config", "list"])

    assert result.exit_code == 0

    for option in [short_option, long_option]:
        assert option.key in result.output
        assert option.description in result.output


@mock.patch("rich.console.Console.size", new_callable=mock.PropertyMock)
def test_config_list_should_not_show_complete_value_of_credentials(size, mock_container: MockContainer) -> None:
    short_option = create_option("short", "123", True)
    long_option = create_option("long", "abcdefghijklmnopqrstuvwxyz", True)

    mock_container.cli_config_manager_mock.all_options = [short_option, long_option]

    size.return_value = ConsoleDimensions(1000, 1000)

    runner = CliRunner()
    result = runner.invoke(lean, ["config", "list"])

    assert result.exit_code == 0

    assert "123" not in result.output
    assert "abcdefghijklmnopqrstuvwxyz" not in result.output
