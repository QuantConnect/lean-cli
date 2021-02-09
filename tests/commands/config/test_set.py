from click.testing import CliRunner

from lean.commands import lean
from lean.models.options import Option
from tests.test_helpers import create_option, MockContainer


def test_config_get_should_update_the_value_of_the_option(mock_container: MockContainer) -> None:
    option = create_option("my-key", "my-value", False)

    mock_container.cli_config_manager_mock.get_option_by_key.side_effect = lambda k: option if k == "my-key" else None

    runner = CliRunner()
    result = runner.invoke(lean, ["config", "set", "my-key", "12345"])

    assert result.exit_code == 0

    option.set_value.assert_called_once_with("12345")


def test_config_set_should_fail_when_no_option_with_given_key_exists(mock_container: MockContainer) -> None:
    def get_option_by_key(key: str) -> Option:
        raise RuntimeError("Not found")

    mock_container.cli_config_manager_mock.get_option_by_key.side_effect = get_option_by_key

    runner = CliRunner()
    result = runner.invoke(lean, ["config", "set", "this-option-does-not-exist", "value"])

    assert result.exit_code != 0
