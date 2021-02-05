from unittest import mock

from click.testing import CliRunner
from rich.console import ConsoleDimensions

from lean.commands import lean
from lean.config.global_config import all_options, user_id_option


@mock.patch("rich.console.Console.size", new_callable=mock.PropertyMock)
def test_config_list_should_list_all_options_with_their_values_and_descriptions(size) -> None:
    user_id_option.set_value("12345")

    size.return_value = ConsoleDimensions(1000, 1000)

    runner = CliRunner()
    result = runner.invoke(lean, ["config", "list"])

    assert result.exit_code == 0

    for option in all_options:
        assert option.key in result.output
        assert option.description in result.output

        if option.key == "user-id":
            assert "12345" in result.output
