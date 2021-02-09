from click.testing import CliRunner

from lean.commands import lean
from lean.models.options import Option
from tests.test_helpers import create_option, MockContainer


def test_config_get_should_print_the_value_of_the_option_with_the_given_key(mock_container: MockContainer) -> None:
    option = create_option("my-key", "my-value", False)

    mock_container.cli_config_manager_mock.get_option_by_key.side_effect = lambda k: option if k == "my-key" else None

    runner = CliRunner()
    result = runner.invoke(lean, ["config", "get", "my-key"])

    assert result.exit_code == 0
    assert result.output == "my-value\n"


def test_config_get_should_fail_when_no_option_with_given_key_exists(mock_container: MockContainer) -> None:
    def get_option_by_key(key: str) -> Option:
        raise RuntimeError("Not found")

    mock_container.cli_config_manager_mock.get_option_by_key.side_effect = get_option_by_key

    runner = CliRunner()
    result = runner.invoke(lean, ["config", "get", "this-option-does-not-exist"])

    assert result.exit_code != 0


def test_config_get_should_fail_when_option_has_no_value(mock_container: MockContainer) -> None:
    option = create_option("my-key", None, False)

    mock_container.cli_config_manager_mock.get_option_by_key.side_effect = lambda k: option if k == "my-key" else None

    runner = CliRunner()
    result = runner.invoke(lean, ["config", "get", "my-value"])

    assert result.exit_code != 0


def test_config_get_should_fail_when_option_is_credential(mock_container: MockContainer) -> None:
    option = create_option("my-key", "my-value", True)

    mock_container.cli_config_manager_mock.get_option_by_key.side_effect = lambda k: option if k == "my-key" else None

    runner = CliRunner()
    result = runner.invoke(lean, ["config", "get", "my-key"])

    assert result.exit_code != 0
